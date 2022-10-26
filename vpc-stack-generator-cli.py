import re
import ipaddr
import yaml
from pyfiglet import Figlet
from PyInquirer import prompt, Separator
from prompt_toolkit.validation import Validator, ValidationError
from prettytable import PrettyTable

vpc_cidr = None
subnet_cidrs = []


def cidr_overlapped(cidr1, cidr2):
    return ipaddr.IPNetwork(cidr1).overlaps(ipaddr.IPNetwork(cidr2))


def get_azs(region):
    az_lists = {
        'us-east-1': [
            'us-east-1a',
            'us-east-1b',
            'us-east-1c',
            'us-east-1d',
            'us-east-1e',
            'us-east-1f'
        ],
        'us-east-2': [
            'us-east-2a',
            'us-east-2b',
            'us-east-2c'
        ],
        'us-west-1': [
            'us-west-1a',
            'us-west-1c'
        ],
        'us-west-2': [
            'us-west-2a',
            'us-west-2b',
            'us-west-2c',
            'us-west-2d'
        ],
        'ap-south-1': [
            'ap-south-1a',
            'ap-south-1b',
            'ap-south-1c'
        ],
        'ap-northeast-3': [
            'ap-northeast-3a',
            'ap-northeast-3b',
            'ap-northeast-3c'
        ],
        'ap-northeast-2': [
            'ap-northeast-2a',
            'ap-northeast-2b',
            'ap-northeast-2c',
            'ap-northeast-2d'
        ],
        'ap-southeast-1': [
            'ap-southeast-1a',
            'ap-southeast-1b',
            'ap-southeast-1c'
        ],
        'ap-southeast-2': [
            'ap-southeast-2a',
            'ap-southeast-2b',
            'ap-southeast-2c'
        ],
        'ap-northeast-1': [
            'ap-northeast-1a',
            'ap-northeast-1c',
            'ap-northeast-1d'
        ],
        'ca-central-1': [
            'ca-central-1a',
            'ca-central-1b',
            'ca-central-1d'
        ],
        'eu-central-1': [
            'eu-central-1a',
            'eu-central-1b',
            'eu-central-1c'
        ],
        'eu-west-1': [
            'eu-west-1a',
            'eu-west-1b',
            'eu-west-1c'
        ],
        'eu-west-2': [
            'eu-west-2a',
            'eu-west-2b',
            'eu-west-2c'
        ],
        'eu-west-3': [
            'eu-west-3a',
            'eu-west-3b',
            'eu-west-3c'
        ],
        'eu-north-1': [
            'eu-north-1a',
            'eu-north-1b',
            'eu-north-1c'
        ],
        'sa-east-1': [
            'sa-east-1a',
            'sa-east-1b',
            'sa-east-1c'
        ]
    }

    return az_lists[region]


class PrintTable:
    table = None

    def __init__(self):
        self.table = PrettyTable()
        self.table.set_style(15)

    def print_vpc(self, region, vpc):
        self.table.clear()
        self.table.title = 'VPC'
        self.table.field_names = ['Region', 'Name', 'CIDR']
        self.table.add_row([region, vpc['name'], vpc['cidr']])
        print(self.table)

    def print_subnets(
            self,
            public_subnet=None,
            private_subnet=None,
            protected_subnet=None,
            public_rtb=None,
            private_rtb=None,
            protected_rtb=None
    ):
        self.table.clear()
        self.table.title = 'Subnets'
        self.table.field_names = ['AZ', 'Name', 'CIDR', 'Route Table']

        if public_subnet:
            for subnet in public_subnet:
                self.table.add_row([subnet['az'], subnet['name'], subnet['cidr'], public_rtb])

        if private_subnet:
            for subnet in private_subnet:
                route_table_name = next((item for item in private_rtb if item['subnet'] == subnet['name']))['name']
                self.table.add_row([subnet['az'], subnet['name'], subnet['cidr'], route_table_name])

        if protected_subnet:
            for subnet in protected_subnet:
                self.table.add_row([subnet['az'], subnet['name'], subnet['cidr'], protected_rtb])

        print(self.table)

    def print_route_tables(
            self,
            public_rtb=None,
            private_rtb=None,
            protected_rtb=None,
            igw=None
    ):
        self.table.clear()
        self.table.title = 'Route Tables'
        self.table.field_names = ['Type', 'Name', 'Gateway']

        if public_rtb:
            self.table.add_row(['Public', public_rtb, igw])

        if private_rtb:
            for rtb in private_rtb:
                self.table.add_row(['Private', rtb['name'], rtb['nat']])

        if protected_rtb:
            self.table.add_row(['Protected', protected_rtb, 'None'])

        print(self.table)

    def print_igw(
            self,
            igw='None'
    ):
        self.table.clear()
        self.table.title = 'Internet Gateway'
        self.table.field_names = ['Name']
        self.table.add_row([igw])

        print(self.table)

    def print_nat(
            self,
            nat=None,
    ):
        self.table.clear()
        self.table.title = 'NAT Gateways'
        self.table.field_names = ['Name', 'Elastic IP', 'Subnet']

        if nat:
            for nat_gw in nat:
                self.table.add_row([nat_gw['name'], nat_gw['eip'], nat_gw['subnet']])
        else:
            self.table.add_row(['None', 'None', 'None'])

        print(self.table)

    def print_s3_ep(
            self,
            s3_gateway_ep=None,
    ):
        self.table.clear()
        self.table.title = 'S3 Gateway Endpoint'
        self.table.field_names = ['Name', 'Route Table']

        if s3_gateway_ep['required']:
            for route_table in s3_gateway_ep['route-table']:
                self.table.add_row([s3_gateway_ep['name'], route_table])
        else:
            self.table.add_row(['None', 'None'])

        print(self.table)


class CreateYAML:
    resources = {}
    region = None
    public_subnet_name = []
    private_subnet_name = []
    protected_subnet_name = []
    private_rtb_name = []

    def __init__(
            self,
            region,
            vpc,
            public_subnet=None,
            private_subnet=None,
            protected_subnet=None,
            k8s_tags=False,
            igw=None,
            public_rtb=None,
            private_rtb=None,
            protected_rtb=None,
            s3_gateway_ep=None
    ):
        self.region = region
        self.create_vpc(vpc=vpc)
        self.create_subnets(
            public_subnet=public_subnet,
            private_subnet=private_subnet,
            protected_subnet=protected_subnet,
            set_k8s_tags=k8s_tags
        )
        self.create_igw(igw=igw)
        self.create_route_tables(public_rtb=public_rtb, private_rtb=private_rtb, protected_rtb=protected_rtb)
        self.create_s3_ep(s3_gateway_ep=s3_gateway_ep)

    def create_vpc(self, vpc):
        self.resources['VPC'] = {
            'Type': 'AWS::EC2::VPC',
            'Properties': {
                'CidrBlock': vpc['cidr'],
                'EnableDnsHostnames': True,
                'EnableDnsSupport': True,
                'InstanceTenancy': 'default',
                'Tags': [{'Key': 'Name', 'Value': vpc['name']}]
            }
        }

    def create_subnets(self, public_subnet=None, private_subnet=None, protected_subnet=None, set_k8s_tags=False):
        if public_subnet:
            for i, subnet in enumerate(public_subnet):
                self.resources['PublicSubnet' + str(i)] = {
                    'Type': 'AWS::EC2::Subnet',
                    'Properties': {
                        'AvailabilityZone': subnet['az'],
                        'CidrBlock': subnet['cidr'],
                        'MapPublicIpOnLaunch': True,
                        'Tags': [{'Key': 'Name', 'Value': subnet['name']}],
                        'VpcId': {
                            'Ref': 'VPC'
                        }
                    }
                }
                self.public_subnet_name.append({'cloudformation': 'PublicSubnet' + str(i), 'name': subnet['name']})

                if set_k8s_tags:
                    self.resources['PublicSubnet' + str(i)]['Properties']['Tags'].append(
                        {'Key': 'kubernetes.io/role/elb', 'Value': '1'}
                    )

        if private_subnet:
            for i, subnet in enumerate(private_subnet):
                self.resources['PrivateSubnet' + str(i)] = {
                    'Type': 'AWS::EC2::Subnet',
                    'Properties': {
                        'AvailabilityZone': subnet['az'],
                        'CidrBlock': subnet['cidr'],
                        'MapPublicIpOnLaunch': False,
                        'Tags': [{'Key': 'Name', 'Value': subnet['name']}],
                        'VpcId': {
                            'Ref': 'VPC'
                        }
                    }
                }
                self.private_subnet_name.append({'cloudformation': 'PrivateSubnet' + str(i), 'name': subnet['name']})

                if set_k8s_tags:
                    self.resources['PrivateSubnet' + str(i)]['Properties']['Tags'].append(
                        {'Key': 'kubernetes.io/role/internal-elb', 'Value': '1'}
                    )

        if protected_subnet:
            for i, subnet in enumerate(protected_subnet):
                self.resources['ProtectedSubnet' + str(i)] = {
                    'Type': 'AWS::EC2::Subnet',
                    'Properties': {
                        'AvailabilityZone': subnet['az'],
                        'CidrBlock': subnet['cidr'],
                        'MapPublicIpOnLaunch': False,
                        'Tags': [{'Key': 'Name', 'Value': subnet['name']}],
                        'VpcId': {
                            'Ref': 'VPC'
                        }
                    }
                }
                self.protected_subnet_name.append(
                    {'cloudformation': 'ProtectedSubnet' + str(i), 'name': subnet['name']})

    def create_igw(self, igw=None):
        self.resources['IGW'] = {
            'ype': 'AWS::EC2::InternetGateway',
            'Properties': {
                'Tags': [{'Name': igw}]
            }
        }
        self.resources['IGWAttachmentVPC'] = {
            'Type': 'AWS::EC2::VPCGatewayAttachment',
            'Properties': {
                'InternetGatewayId': {
                    'Ref': 'IGW'
                },
                'VpcId': {
                    'Ref': 'VPC'
                }
            }
        }
        self.resources['PublicRouteTableRouteIGW'] = {
            'Type': 'AWS::EC2::Route',
            'Properties': {
                'DestinationCidrBlock': '0.0.0.0/0',
                'GatewayId': {
                    'Ref': 'IGW'
                },
                'RouteTableId': {
                    'Ref': 'PublicRouteTable'
                }
            }
        }

    def create_route_tables(self, public_rtb=None, private_rtb=None, protected_rtb=None):
        if public_rtb:
            # create public route table
            self.resources['PublicRouteTable'] = {
                'Type': 'AWS::EC2::RouteTable',
                'Properties': {
                    'Tags': [{'Key': 'Name', 'Value': public_rtb}],
                    'VpcId': {
                        'Ref': 'VPC'
                    }
                }
            }

            # associate public subnets to public route table
            for subnet_name in self.public_subnet_name:
                self.resources[subnet_name['cloudformation'] + 'RouteTableAssociation'] = {
                    'Type': 'AWS::EC2::SubnetRouteTableAssociation',
                    'Properties': {
                        'SubnetId': {
                            'Ref': subnet_name['cloudformation']
                        },
                        'RouteTableId': {
                            'Ref': 'PublicRouteTable'
                        }
                    }
                }

        if private_rtb:
            # create private route tables
            for i, rtb in enumerate(private_rtb):
                self.resources['PrivateRouteTable' + str(i)] = {
                    'Type': 'AWS::EC2::RouteTable',
                    'Properties': {
                        'Tags': [{'Key': 'Name', 'Value': rtb['name']}],
                        'VpcId': {
                            'Ref': 'VPC'
                        }
                    }
                }

                # associate each private subnet to each private route table
                subnet_cloudformation_name = next(
                    item for item in self.private_subnet_name if item['name'] == rtb['subnet'])
                self.resources[subnet_cloudformation_name['cloudformation'] + 'RouteTableAssociation'] = {
                    'Type': 'AWS::EC2::SubnetRouteTableAssociation',
                    'Properties': {
                        'SubnetId': {
                            'Ref': subnet_cloudformation_name['cloudformation']
                        },
                        'RouteTableId': {
                            'Ref': 'PrivateRouteTable' + str(i)
                        }
                    }
                }

                self.private_rtb_name.append(
                    {'cloudformation': 'PrivateRouteTable' + str(i), 'name': rtb['name']})

        if protected_rtb:
            # create protected route table
            self.resources['ProtectRouteTable'] = {
                'Type': 'AWS::EC2::RouteTable',
                'Properties': {
                    'Tags': [{'Key': 'Name', 'Value': protected_rtb}],
                    'VpcId': {
                        'Ref': 'VPC'
                    }
                }
            }

            # associate protected subnets to protected route table
            for subnet_name in self.protected_subnet_name:
                self.resources[subnet_name['cloudformation'] + 'RouteTableAssociation'] = {
                    'Type': 'AWS::EC2::SubnetRouteTableAssociation',
                    'Properties': {
                        'SubnetId': {
                            'Ref': subnet_name['cloudformation']
                        },
                        'RouteTableId': {
                            'Ref': 'ProtectRouteTable'
                        }
                    }
                }

    def create_nat(self, nat=None):
        # create nat
        for i, _nat in enumerate(nat):
            # create elastic ip
            self.resources['EIP' + str(i)] = {
                'Type': 'AWS::EC2::EIP',
                'Properties': {
                    'Tags': [{'Key': 'Name', 'Value': _nat['eip']}],
                }
            }

            # create nat gateway
            self.resources['NAT' + str(i)] = {
                'Type': 'AWS::EC2::NatGateway',
                'Properties': {
                    'AllocationId': {
                        'GetAtt': 'EIP' + str(i)
                    },
                    'SubnetId': {
                        'Ref': _nat['subnet']
                    },
                    'Tags': [{'Key': 'Name', 'Value': _nat['name']}]
                }
            }

            # routing
            rtb_name = next(item for item in self.private_rtb_name if item['name'] == _nat['subnet'])
            self.resources['{}RouteNAT{}'.format(rtb_name, str(i))] = {
                'Type': 'AWS::EC2::Route',
                'Properties': {
                    'DestinationCidrBlock': '0.0.0.0/0',
                    'NatGatewayId': {
                        'Ref': 'NAT' + str(i)
                    },
                    'RouteTableId': {
                        'Ref': rtb_name
                    }
                }
            }

    def create_s3_ep(self, s3_gateway_ep=None):
        rtb_list = []

        for rtb in s3_gateway_ep['route-table']:
            rtb_name = next(item for item in self.private_rtb_name if item['name'] == rtb)
            rtb_list.append({'Ref': rtb_name['cloudformation']})

        self.resources['S3EP'] = {
            'Type': 'AWS::EC2::VPCEndpoint',
            'Properties': {
                'RouteTableIds': rtb_list,
                'ServiceName': 'com.amazonaws.{}.s3'.format(self.region),
                'VpcId': {
                    'Ref': 'VPC'
                }
            }
        }

    def create_yaml(self):
        template = {
            'AWSTemplateFormatVersion': '2010-09-09',
            'Description': 'VPC Stack Generator CLI',
            'Resources': self.resources
        }

        try:
            with open('template.yaml', 'w') as f:
                yaml.dump(template, f)

        except Exception as e:
            print(e)


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
        self.print_figlet()
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
            s3_gateway_ep=self.s3_gateway_ep
        )
        yaml_file.create_yaml()

    # print figlet
    def print_figlet(self):
        figlet_title = Figlet(font='slant')

        print(figlet_title.renderText('VPC Stack Generator'))

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


def main():
    Command()


if __name__ == '__main__':
    main()
