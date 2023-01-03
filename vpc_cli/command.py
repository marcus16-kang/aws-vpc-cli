from inquirer import prompt, List, Text, Confirm, Checkbox

from vpc_cli.print_table import PrintTable
from vpc_cli.create_yaml import CreateYAML
from vpc_cli.deploy_boto3 import DeployBoto3
from vpc_cli.tools import get_regions, get_azs, print_figlet
from vpc_cli.validators import name_validator, vpc_cidr_validator, subnet_count_validator, subnet_cidr_validator


def interrupt(func):
    def wrapper():
        try:
            func()

        except KeyboardInterrupt:
            print('User cancelled')

            return 0

    return wrapper


class Command:
    az_list = []

    # variables
    region = None
    vpc = {
        'name': None,
        'cidr': None
    }
    subnet_cidrs = []
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

        # Choose deployment method using Boto3 or CloudFormation with YAML.
        if self.get_deployment_method():  # Using Cloudformation with YAML
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

        else:  # Using Boto3 Directly
            DeployBoto3(
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

    def choose_region(self):
        questions = [
            List(
                name='region',
                message='Choose region',
                choices=get_regions()
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.region = answer.get('region')
        self.az_list = get_azs(self.region)

    def set_vpc(self):
        questions = [
            Text(
                name='name',
                message='VPC name',
                validate=lambda _, x: name_validator(x)
            ),
            Text(
                name='cidr',
                message='VPC CIDR',
                validate=lambda _, x: vpc_cidr_validator(x)
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.vpc = answer

        # set only vpc cidr in global variable
        global vpc_cidr
        vpc_cidr = answer['cidr']

    def set_public_subnet(self):
        questions = [
            Confirm(
                name='required',
                message='Do you want to create PUBLIC SUBNET?',
                default=True
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)

        # required public subnets
        if answer['required']:
            questions = [
                Text(
                    name='count',
                    message='How many subnets do you want to create?',
                    validate=lambda _, x: subnet_count_validator(x)
                )
            ]

            answer = prompt(questions=questions, raise_keyboard_interrupt=True)

            for i in range(0, int(answer['count'])):
                questions = [
                    Text(
                        name='name',
                        message='Public Subnet {} name'.format(i + 1),
                        validate=lambda _, x: name_validator(x)
                    ),
                    Text(
                        name='cidr',
                        message='Public Subnet {} CIDR'.format(i + 1),
                        validate=lambda _, x: subnet_cidr_validator(x, self.vpc['cidr'], self.subnet_cidrs)
                    ),
                    List(
                        name='az',
                        message='Public Subnet {} AZ'.format(i + 1),
                        choices=self.az_list
                    )
                ]

                subnet_answer = prompt(questions=questions, raise_keyboard_interrupt=True)
                self.public_subnet.append(subnet_answer)
                self.subnet_cidrs.append(subnet_answer['cidr'])

        else:  # not create public subnets
            return None

    def set_private_subnet(self):
        questions = [
            Confirm(
                name='required',
                message='Do you want to create PRIVATE SUBNET?',
                default=True
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)

        # required private subnets
        if answer['required']:
            questions = [
                Text(
                    name='count',
                    message='How many subnets do you want to create?',
                    validate=lambda _, x: subnet_count_validator(x)
                )
            ]

            answer = prompt(questions=questions, raise_keyboard_interrupt=True)

            for i in range(0, int(answer['count'])):
                questions = [
                    Text(
                        name='name',
                        message='Private Subnet {} name'.format(i + 1),
                        validate=lambda _, x: name_validator(x)
                    ),
                    Text(
                        name='cidr',
                        message='Private Subnet {} CIDR'.format(i + 1),
                        validate=lambda _, x: subnet_cidr_validator(x, self.vpc['cidr'], self.subnet_cidrs)
                    ),
                    List(
                        name='az',
                        message='Private Subnet {} AZ'.format(i + 1),
                        choices=self.az_list
                    )
                ]

                subnet_answer = prompt(questions=questions, raise_keyboard_interrupt=True)
                self.private_subnet.append(subnet_answer)
                self.subnet_cidrs.append(subnet_answer['cidr'])

        else:  # not create private subnets
            return None

    def set_protected_subnet(self):
        questions = [
            Confirm(
                name='required',
                message='Do you want to create PROTECTED SUBNET?',
                default=False
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)

        if answer['required']:  # required protected subnets
            questions = [
                Text(
                    name='count',
                    message='How many subnets do you want to create?',
                    validate=lambda _, x: subnet_count_validator(x)
                )
            ]

            answer = prompt(questions=questions, raise_keyboard_interrupt=True)

            for i in range(0, int(answer['count'])):
                questions = [
                    Text(
                        name='name',
                        message='Protected Subnet {} name'.format(i + 1),
                        validate=lambda _, x: name_validator(x)
                    ),
                    Text(
                        name='cidr',
                        message='Protected Subnet {} CIDR'.format(i + 1),
                        validate=lambda _, x: subnet_cidr_validator(x, self.vpc['cidr'], self.subnet_cidrs)
                    ),
                    List(
                        name='az',
                        message='Protected Subnet {} AZ'.format(i + 1),
                        choices=self.az_list
                    )
                ]

                subnet_answer = prompt(questions=questions, raise_keyboard_interrupt=True)
                self.protected_subnet.append(subnet_answer)
                self.subnet_cidrs.append(subnet_answer['cidr'])

        else:  # not create protected subnets
            return None

    def set_subnet_k8s_tags(self):
        questions = [
            Confirm(
                name='k8s-tag',
                message='Do you want to create tags for Kubernetes?',
                default=False
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.k8S_tag = answer['k8s-tag']

    def set_internet_gateway(self):
        questions = [
            Text(
                name='name',
                message='Type Internet Gateway name',
                validate=lambda _, x: name_validator(x)
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.igw = answer['name']

    def set_elastic_ip(self):
        for i in range(0, len(self.private_subnet)):
            questions = [
                Text(
                    name='name',
                    message='Elastic IP {} name'.format(i + 1),
                    validate=lambda _, x: name_validator(x)
                )
            ]

            answer = prompt(questions=questions, raise_keyboard_interrupt=True)
            self.eip.append(answer['name'])

    def set_nat_gateway(self):
        for i in range(0, len(self.private_subnet)):
            questions = [
                Text(
                    name='name',
                    message='NAT Gateway {} name'.format(i + 1),
                    validate=lambda _, x: name_validator(x)
                ),
                List(
                    name='subnet',
                    message='NAT Gateway {} subnet'.format(i + 1),
                    choices=[
                        ('{} ({} {})'.format(d['name'], d['cidr'], d['az']), d['name']) for d in self.public_subnet
                    ],
                    default=i + 1
                ),
                List(
                    name='eip',
                    message='NAT Gateway {} elastic ip'.format(i + 1),
                    choices=self.eip,
                    default=i + 1
                )
            ]

            answer = prompt(questions=questions, raise_keyboard_interrupt=True)
            self.nat.append(answer)

    def set_public_rtb(self):
        questions = [
            Text(
                name='name',
                message='Public Route Table name',
                validate=lambda _, x: name_validator(x)
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.public_rtb = answer['name']

    def set_private_rtb(self):
        for i in range(0, len(self.private_subnet)):
            questions = [
                Text(
                    name='name',
                    message='Private Route Table {} name'.format(i + 1),
                    validate=lambda _, x: name_validator(x)
                ),
                List(
                    name='subnet',
                    message='Private Route Table {} subnet'.format(i + 1),
                    choices=[
                        ('{} ({} {})'.format(d['name'], d['cidr'], d['az']), d['name']) for d in self.private_subnet
                    ]
                )
            ]

            # skip choosing nat gateway weh public subnet hasn't nothing
            if len(self.public_subnet):
                questions.append(List(
                    name='nat',
                    message='Private Route Table {} nat gateway'.format(i + 1),
                    choices=[d['name'] for d in self.nat]
                ))
            else:
                pass

            answer = prompt(questions=questions, raise_keyboard_interrupt=True)
            self.private_rtb.append(answer)

    def set_protected_rtb(self):
        questions = [
            Text(
                name='name',
                message='Protected Route Table name',
                validate=lambda _, x: name_validator(x)
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
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
            Confirm(
                name='required',
                message='Do you want to create S3 GATEWAY ENDPOINT?',
                default=True
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)

        if answer['required']:
            questions = [
                Checkbox(
                    name='route-table',
                    message='Select Route Tables',
                    choices=[d['name'] for d in route_table_list]
                )
            ]

            answer = prompt(questions=questions, raise_keyboard_interrupt=True)
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

    def get_deployment_method(self):
        questions = [
            List(
                name='method',
                message='Choose deployment method',
                choices=[
                    ('Using CloudFormation with YAML', True),
                    ('Using Boto3 Directly', False)
                ]
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)

        return answer.get('method')
