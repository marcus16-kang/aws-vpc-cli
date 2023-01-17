import boto3
from inquirer import prompt, List, Text, Confirm, Checkbox
from botocore.config import Config

from vpc_cli.print_table import PrintTable
from vpc_cli.create_yaml import CreateYAML
from vpc_cli.deploy_cfn import DeployCfn
from vpc_cli.tools import get_azs, print_figlet
from vpc_cli.validators import name_validator, vpc_cidr_validator, subnet_count_validator, subnet_cidr_validator, \
    stack_name_validator


class Command:
    # variables
    project = None
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
    flow_logs = {
        'log-group': None,
        'role-name': None
    }
    igw = None
    eip = []
    nat = []
    public_rtb = None
    private_rtb = []
    protected_rtb = None
    s3_gateway_ep = None
    dynamodb_gateway_ep = None

    # start command
    def __init__(self):
        print_figlet()
        self.set_project_name()
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
            self.set_dynamodb_gateway()
        else:
            print('Skip creating S3 and DynamoDB Gateway Endpoint')

        self.set_flow_logs()

        # print tables
        self.print_tables()

        # create template yaml file
        yaml_file = CreateYAML(
            project=self.project,
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
            s3_gateway_ep=self.s3_gateway_ep,
            dynamodb_gateway_ep=self.dynamodb_gateway_ep,
            flow_logs=self.flow_logs
        )
        yaml_file.create_yaml()
        DeployCfn(project=self.project, region=self.region)

    def set_project_name(self):
        questions = [
            Text(
                name='name',
                message='Project name',
                validate=lambda _, x: name_validator(x)
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.project = answer['name']

    def choose_region(self):
        questions = [
            List(
                name='region',
                message='Choose region',
                choices=[
                    ('us-east-1      (N. Virginia)', 'us-east-1'),
                    ('us-east-2      (Ohio)', 'us-east-2'),
                    ('us-west-1      (N. California)', 'us-west-1'),
                    ('us-west-2      (Oregon)', 'us-west-2'),
                    ('ap-south-1     (Mumbai)', 'ap-south-1'),
                    ('ap-northeast-3 (Osaka)', 'ap-northeast-3'),
                    ('ap-northeast-2 (Seoul)', 'ap-northeast-2'),
                    ('ap-southeast-1 (Singapore)', 'ap-southeast-1'),
                    ('ap-southeast-2 (Sydney)', 'ap-southeast-2'),
                    ('ap-northeast-1 (Tokyo)', 'ap-northeast-1'),
                    ('ca-central-1   (Canada Central)', 'ca-central-1'),
                    ('eu-central-1   (Frankfurt)', 'eu-central-1'),
                    ('eu-west-1      (Ireland)', 'eu-west-1'),
                    ('eu-west-2      (London)', 'eu-west-2'),
                    ('eu-west-3      (Paris)', 'eu-west-3'),
                    ('eu-north-1     (Stockholm)', 'eu-north-1'),
                    ('sa-east-1      (Sao Paulo)', 'sa-east-1')
                ]
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.region = answer.get('region')

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
                        choices=get_azs(self.region)
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
                        choices=get_azs(self.region)
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
                        choices=get_azs(self.region)
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
            Checkbox(
                name='route-table',
                message='Select S3 Gateway Endpoint Route Tables',
                choices=[d['name'] for d in route_table_list]
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.s3_gateway_ep = answer

    def set_dynamodb_gateway(self):
        route_table_list = []

        if self.public_rtb:
            route_table_list.append({'name': self.public_rtb})

        if self.private_rtb:
            for rtb in self.private_rtb:
                route_table_list.append({'name': rtb['name']})

        if self.protected_rtb:
            route_table_list.append({'name': self.protected_rtb})
        questions = [
            Checkbox(
                name='route-table',
                message='Select DynamoDB Gateway Endpoint Route Tables',
                choices=[d['name'] for d in route_table_list]
            )
        ]

        answer = prompt(questions=questions, raise_keyboard_interrupt=True)
        self.dynamodb_gateway_ep = answer

    def set_flow_logs(self):
        question = [
            Confirm(
                name='enable',
                message='Do you want to enable VPC Flow Logs?',
                default=True
            )
        ]
        answer = prompt(questions=question, raise_keyboard_interrupt=True)

        if answer.get('enable'):
            question = [
                Text(
                    name='log-group-name',
                    message='Please type the log group name',
                    validate=lambda _, x: name_validator(x),
                    default=f'/aws/vpc/{self.vpc["name"]}'
                ),
                Text(
                    name='log-group-role-name',
                    message='Please type the log group IAM role name',
                    validate=lambda _, x: name_validator(x),
                    default=f'{self.vpc["name"]}-flow-logs-role'
                ),
            ]
            answer = prompt(questions=question, raise_keyboard_interrupt=True)
            self.flow_logs = {
                'log-group': answer.get('log-group-name'),
                'role-name': answer.get('log-group-role-name'),
            }

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
        print_table.print_ep(s3_gateway_ep=self.s3_gateway_ep, dynamodb_gateway_ep=self.dynamodb_gateway_ep)
        print_table.print_flow_logs(flow_logs=self.flow_logs)

    def create_stack(self):
        questions = [
            Confirm(
                name='deploy',
                message='Do you want to deploy stack in \033[1m\033[96m{}\033[0mtest?'.format(self.region),
                default=True
            )
        ]

        answer = prompt(questions, raise_keyboard_interrupt=True)

        if answer['deploy']:
            questions = [
                Text(
                    name='stack-name',
                    message='Type your stack name',
                    validate=lambda _, x: stack_name_validator(x, self.region)
                )
            ]

            answer = prompt(questions, raise_keyboard_interrupt=True)

            try:
                client = boto3.client('cloudformation', config=Config(region_name=self.region))

                response = client.create_stack(
                    StackName=answer['stack-name'],
                    TemplateBody='file://template.yaml'
                )
                stack_id = response['StackId']

            except Exception as e:
                print(e)
