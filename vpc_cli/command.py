import re
from PyInquirer import prompt, Separator
from prompt_toolkit.validation import Validator, ValidationError

from vpc_cli.print_table import PrintTable
from vpc_cli.create_yaml import CreateYAML
from vpc_cli.tools import cidr_overlapped, get_azs, print_figlet

vpc_cidr = None
subnet_cidrs = []


class Command:
    # variables
    region = None
    vpc = {
        'name': None,
        'cidr': None
    }
    public_subnet = []
    private_subnet = []
    protected_subnet = []
    k8S_tag = False
    igw = None
    eip = []
    nat = []
    public_rtb = None
    private_rtb = []
    protected_rtb = None
    s3_gateway_ep = None

    # validators
    class NameValidator(Validator):
        def validate(self, document):
            ok = len(document.text) > 0

            if not ok:
                raise ValidationError(
                    message='Please enter the correct name.',
                    cursor_position=len(document.text)
                )

    class VPCCidrValidator(Validator):
        def validate(self, document):
            ok = re.match(pattern=r'(?<!\d\.)(?<!\d)(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}(?!\d|(?:\.\d))',
                          string=document.text)

            if not ok:
                raise ValidationError(
                    message='Please enter the correct CIDR.',
                    cursor_position=len(document.text)
                )

    class SubnetCountValidator(Validator):
        def validate(self, document):
            ok = document.text.isdigit()

            if not ok:
                raise ValidationError(
                    message='Please enter the number.',
                    cursor_position=len(document.text)
                )

    class SubnetCidrValidator(Validator):
        def validate(self, document):
            ok = re.match(pattern=r'(?<!\d\.)(?<!\d)(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}(?!\d|(?:\.\d))',
                          string=document.text)
            global vpc_cidr

            if not ok:
                raise ValidationError(
                    message='Please enter the correct CIDR.',
                    cursor_position=len(document.text)
                )

            elif not cidr_overlapped(vpc_cidr, document.text):
                raise ValidationError(
                    message='Subnet CIDR is not overlapped in VPC\'s CIDR.',
                    cursor_position=len(document.text)
                )

            else:
                global subnet_cidrs
                for subnet_cidr in subnet_cidrs:
                    if cidr_overlapped(subnet_cidr, document.text):
                        raise ValidationError(
                            message='CIDR Address overlaps with existing Subnet CIDR: {}.'.format(subnet_cidr),
                            cursor_position=len(document.text)
                        )

    # start command
    def __init__(self):
        print_figlet()
        self.choose_region()
        self.set_vpc()
        self.set_public_subnet()
        self.set_private_subnet()
        self.set_protected_subnet()

        # skip creating k8s tags weh public and private subnet hasn't nothing
        if len(self.public_subnet) or len(self.private_subnet):
            self.set_subnet_k8s_tags()

        # skip creating igw when public subnet hasn't nothing
        if len(self.public_subnet):
            self.set_internet_gateway()
        else:
            print('Skip creating Internet Gateway')

        # skip creating nat when public and private subnet hasn't nothing
        if len(self.public_subnet) and len(self.private_subnet):
            self.set_elastic_ip()
            self.set_nat_gateway()
        else:
            print('Skip creating NAT Gateway')

        # skip creating public route table when public subnet hasn't nothing
        if len(self.public_subnet):
            self.set_public_rtb()
        else:
            print('Skip creating Public Route Table')

        # skip creating private route table when private subnet hasn't nothing
        if len(self.private_subnet):
            self.set_private_rtb()
        else:
            print('Skip creating Private Route Table')

        # skip creating protected route table when protected subnet hasn't nothing
        if len(self.protected_subnet):
            self.set_protected_rtb()
        else:
            print('Skip creating Protected Route Table')

        # skip creating s3 gateway endpoint wen all types of subnet hasn't nothing
        if len(self.public_subnet) or len(self.private_subnet) or len(self.protected_subnet):
            self.set_s3_gateway()
        else:
            print('Skip creating S3 Gateway Endpoint')

        # print tables
        self.print_tables()

        # create template yaml file
        yaml_file = CreateYAML(
            region=self.region,
            vpc=self.vpc,
            public_subnet=self.public_subnet,
            private_subnet=self.private_subnet,
            protected_subnet=self.protected_subnet,
            k8s_tags=self.k8S_tag,
            igw=self.igw,
            public_rtb=self.public_rtb,
            private_rtb=self.private_rtb,
            protected_rtb=self.protected_rtb,
            nat=self.nat,
            s3_gateway_ep=self.s3_gateway_ep
        )
        yaml_file.create_yaml()

    def choose_region(self):
        questions = [
            {
                'type': 'list',
                'name': 'region',
                'message': 'Choose region:',
                'choices': [
                    'us-east-1 (N. Virginia)',
                    'us-east-2 (Ohio)',
                    'us-west-1 (N. California)',
                    'us-west-2 (Oregon)',
                    Separator(),
                    'ap-south-1 (Mumbai)',
                    'ap-northeast-3 (Osaka)',
                    'ap-northeast-2 (Seoul)',
                    'ap-southeast-1 (Singapore)',
                    'ap-southeast-2 (Sydney)',
                    'ap-northeast-1 (Tokyo)',
                    Separator(),
                    'ca-central-1 (Canada Central)',
                    Separator(),
                    'eu-central-1 (Frankfurt)',
                    'eu-west-1 (Ireland)',
                    'eu-west-2 (London)',
                    'eu-west-3 (Paris)',
                    'eu-north-1 (Stockholm)',
                    Separator(),
                    'sa-east-1 (Sao Paulo)',
                ],
                'filter': lambda val: re.sub(pattern=r'\([^)]*\)', repl='', string=val).strip()
            }
        ]

        answer = prompt(questions=questions)
        self.region = answer.get('region')

    def set_vpc(self):
        questions = [
            {
                'type': 'input',
                'name': 'name',
                'message': 'VPC name:',
                'validate': self.NameValidator
            },
            {
                'type': 'input',
                'name': 'cidr',
                'message': 'VPC CIDR:',
                'validate': self.VPCCidrValidator
            }
        ]

        answer = prompt(questions=questions)
        self.vpc = answer

        # set only vpc cidr in global variable
        global vpc_cidr
        vpc_cidr = answer['cidr']

    def set_public_subnet(self):
        questions = [
            {
                'type': 'confirm',
                'name': 'required',
                'message': 'Do you want to create PUBLIC SUBNET?',
                'default': True
            },
            {
                'type': 'input',
                'name': 'count',
                'message': 'How many subnets do you want to create?',
                'validate': self.SubnetCountValidator,
                'when': lambda answers: answers['required']
            }
        ]

        answer = prompt(questions=questions)

        if answer['required']:  # required public subnets
            for i in range(0, int(answer['count'])):
                questions = [
                    {
                        'type': 'input',
                        'name': 'name',
                        'message': 'Public Subnet {} name:'.format(i + 1),
                        'validate': self.NameValidator
                    },
                    {
                        'type': 'input',
                        'name': 'cidr',
                        'message': 'Public Subnet {} CIDR:'.format(i + 1),
                        'validate': self.SubnetCidrValidator
                    },
                    {
                        'type': 'list',
                        'name': 'az',
                        'message': 'Public Subnet {} AZ:'.format(i + 1),
                        'choices': get_azs(self.region)
                    }
                ]

                subnet_answer = prompt(questions=questions)
                self.public_subnet.append(subnet_answer)

                global subnet_cidrs
                subnet_cidrs.append(subnet_answer['cidr'])

        else:  # not create public subnets
            return None

    def set_private_subnet(self):
        questions = [
            {
                'type': 'confirm',
                'name': 'required',
                'message': 'Do you want to create PRIVATE SUBNET?',
                'default': True
            },
            {
                'type': 'input',
                'name': 'count',
                'message': 'How many subnets do you want to create?',
                'validate': self.SubnetCountValidator,
                'when': lambda answers: answers['required']
            }
        ]

        answer = prompt(questions=questions)

        if answer['required']:  # required private subnets
            for i in range(0, int(answer['count'])):
                questions = [
                    {
                        'type': 'input',
                        'name': 'name',
                        'message': 'Private Subnet {} Name:'.format(i + 1),
                        'validate': self.NameValidator
                    },
                    {
                        'type': 'input',
                        'name': 'cidr',
                        'message': 'Private Subnet {} CIDR:'.format(i + 1),
                        'validate': self.SubnetCidrValidator
                    },
                    {
                        'type': 'list',
                        'name': 'az',
                        'message': 'Private Subnet {} AZ:'.format(i + 1),
                        'choices': get_azs(self.region)
                    }
                ]

                subnet_answer = prompt(questions=questions)
                self.private_subnet.append(subnet_answer)

                global subnet_cidrs
                subnet_cidrs.append(subnet_answer['cidr'])

        else:  # not create private subnets
            return None

    def set_protected_subnet(self):
        questions = [
            {
                'type': 'confirm',
                'name': 'required',
                'message': 'Do you want to create PROTECTED SUBNET?',
                'default': False
            },
            {
                'type': 'input',
                'name': 'count',
                'message': 'How many subnets do you want to create?',
                'validate': self.SubnetCountValidator,
                'when': lambda answers: answers['required']
            }
        ]

        answer = prompt(questions=questions)

        if answer['required']:  # required protected subnets
            for i in range(0, int(answer['count'])):
                questions = [
                    {
                        'type': 'input',
                        'name': 'name',
                        'message': 'Protected Subnet {} Name:'.format(i + 1),
                        'validate': self.NameValidator
                    },
                    {
                        'type': 'input',
                        'name': 'cidr',
                        'message': 'Protected Subnet {} CIDR:'.format(i + 1),
                        'validate': self.SubnetCidrValidator
                    },
                    {
                        'type': 'list',
                        'name': 'az',
                        'message': 'Protected Subnet {} AZ:'.format(i + 1),
                        'choices': get_azs(self.region)
                    }
                ]

                subnet_answer = prompt(questions=questions)
                self.protected_subnet.append(subnet_answer)

                global subnet_cidrs
                subnet_cidrs.append(subnet_answer['cidr'])

        else:  # not create protected subnets
            return None

    def set_subnet_k8s_tags(self):
        questions = [
            {
                'type': 'confirm',
                'name': 'k8s-tag',
                'message': 'Do you want to create tags for Kubernetes?',
                'default': False
            }
        ]

        answer = prompt(questions=questions)
        self.k8S_tag = answer['k8s-tag']

    def set_internet_gateway(self):
        questions = [
            {
                'type': 'input',
                'name': 'name',
                'message': 'Type Internet Gateway name:',
                'validate': self.NameValidator
            }
        ]

        answer = prompt(questions=questions)
        self.igw = answer['name']

    def set_elastic_ip(self):
        for i in range(0, len(self.private_subnet)):
            questions = [
                {
                    'type': 'input',
                    'name': 'name',
                    'message': 'Elastic IP {} name:'.format(i + 1),
                    'validate': self.NameValidator
                }
            ]

            answer = prompt(questions=questions)
            self.eip.append(answer['name'])

    def set_nat_gateway(self):
        for i in range(0, len(self.private_subnet)):
            questions = [
                {
                    'type': 'input',
                    'name': 'name',
                    'message': 'NAT Gateway {} name:'.format(i + 1),
                    'validate': self.NameValidator
                },
                {
                    'type': 'list',
                    'name': 'subnet',
                    'message': 'NAT Gateway {} subnet:'.format(i + 1),
                    'choices': ['{} ({} {})'.format(d['name'], d['cidr'], d['az']) for d in self.public_subnet],
                    'filter': lambda val: re.sub(pattern=r'\([^)]*\)', repl='', string=val).strip(),
                    'default': i + 1
                },
                {
                    'type': 'list',
                    'name': 'eip',
                    'message': 'NAT Gateway {} elastic ip:'.format(i + 1),
                    'choices': self.eip,
                    'default': i + 1
                }
            ]

            answer = prompt(questions=questions)
            self.nat.append(answer)

    def set_public_rtb(self):
        questions = [
            {
                'type': 'input',
                'name': 'name',
                'message': 'Public Route Table name:',
                'validate': self.NameValidator
            }
        ]

        answer = prompt(questions=questions)
        self.public_rtb = answer['name']

    def set_private_rtb(self):
        for i in range(0, len(self.private_subnet)):
            questions = [
                {
                    'type': 'input',
                    'name': 'name',
                    'message': 'Private Route Table {} name:'.format(i + 1),
                    'validate': self.NameValidator
                },
                {
                    'type': 'list',
                    'name': 'subnet',
                    'message': 'Private Route Table {} subnet:'.format(i + 1),
                    'choices': ['{} ({} {})'.format(d['name'], d['cidr'], d['az']) for d in self.private_subnet],
                    'filter': lambda val: re.sub(pattern=r'\([^)]*\)', repl='', string=val).strip()
                }
            ]

            # skip choosing nat gateway weh public subnet hasn't nothing
            if len(self.public_subnet):
                questions.append({
                    'type': 'list',
                    'name': 'nat',
                    'message': 'Private Route Table {} nat gateway:'.format(i + 1),
                    'choices': self.nat
                })
            else:
                pass

            answer = prompt(questions=questions)
            self.private_rtb.append(answer)

    def set_protected_rtb(self):
        questions = [
            {
                'type': 'input',
                'name': 'name',
                'message': 'Protected Route Table name:',
                'validate': self.NameValidator
            }
        ]

        answer = prompt(questions=questions)
        self.protected_rtb = answer['name']

    def set_s3_gateway(self):
        route_table_list = []

        if self.public_rtb:
            route_table_list.append({'name': self.public_rtb})

        if self.private_rtb:
            for rtb in self.private_rtb:
                route_table_list.append({'name': rtb['name']})

        if self.protected_rtb:
            route_table_list.append({'name': self.protected_rtb})

        questions = [
            {
                'type': 'confirm',
                'name': 'required',
                'message': 'Do you want to create S3 GATEWAY ENDPOINT?',
                'default': True
            },
            {
                'type': 'input',
                'name': 'name',
                'message': 'S3 Gateway Endpoint name:',
                'validate': self.NameValidator,
                'when': lambda answers: answers['required']
            },
            {
                'type': 'checkbox',
                'name': 'route-table',
                'message': 'Select Route Tables:',
                'choices': route_table_list,
                'when': lambda answers: answers['required']
            }
        ]

        answer = prompt(questions=questions)
        self.s3_gateway_ep = answer

    def print_tables(self):
        print_table = PrintTable()
        print_table.print_vpc(self.region, self.vpc)
        print_table.print_subnets(
            public_subnet=self.public_subnet,
            private_subnet=self.private_subnet,
            protected_subnet=self.protected_subnet,
            public_rtb=self.public_rtb,
            private_rtb=self.private_rtb,
            protected_rtb=self.protected_rtb
        )
        print_table.print_route_tables(
            public_rtb=self.public_rtb,
            private_rtb=self.private_rtb,
            protected_rtb=self.protected_rtb,
            igw=self.igw
        )
        print_table.print_igw(igw=self.igw)
        print_table.print_nat(nat=self.nat)
        print_table.print_s3_ep(s3_gateway_ep=self.s3_gateway_ep)
