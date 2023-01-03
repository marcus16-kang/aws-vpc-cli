import boto3
from botocore.config import Config
from tqdm import tqdm


class DeployBoto3:
    # resources = {}
    # region = None
    # public_subnet_name = {}
    # private_subnet_name = {}
    # protected_subnet_name = []
    # rtb_name = []
    client = None
    resources = {'VPC': [], 'Subnet': [], 'Internet Gateway': [], 'Route Table': []}
    pbar = None

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
            nat=None,
            s3_gateway_ep=None
    ):
        self.pbar = tqdm(total=100)
        self.client = boto3.client('ec2', config=Config(region_name=region))
        self.create_vpc(vpc=vpc)
        self.create_subnets(
            public_subnet=public_subnet,
            private_subnet=private_subnet,
            protected_subnet=protected_subnet,
            set_k8s_tags=k8s_tags
        )
        self.create_igw(igw=igw)
        self.create_route_tables(public_rtb=public_rtb, private_rtb=private_rtb, protected_rtb=protected_rtb)
        self.create_route_table_associations(public_subnet=public_subnet, private_subnet=private_subnet,
                                             protected_subnet=protected_subnet, public_rtb=public_rtb,
                                             private_rtb=private_rtb, protected_rtb=protected_rtb)
        # self.create_nat(nat=nat, private_rtb=private_rtb)
        # self.create_s3_ep(s3_gateway_ep=s3_gateway_ep)
        # self.create_yaml()

    def create_vpc(self, vpc):
        response = self.client.create_vpc(
            CidrBlock=vpc['cidr'],
            InstanceTenancy='default',
            TagSpecifications=[
                {
                    'ResourceType': 'vpc',
                    'Tags': [{'Key': 'Name', 'Value': vpc['name']}]
                }
            ]
        )
        self.resources['VPC'].append({vpc['name']: response['Vpc']['VpcId']})
        self.pbar.update(5)

        self.client.modify_vpc_attribute(
            EnableDnsHostnames={
                'Value': True
            },
            VpcId=response['Vpc']['VpcId']
        )
        self.client.modify_vpc_attribute(
            EnableDnsSupport={
                'Value': True
            },
            VpcId=response['Vpc']['VpcId']
        )
        self.pbar.update(5)

    def create_subnets(self, public_subnet=None, private_subnet=None, protected_subnet=None, set_k8s_tags=False):
        if public_subnet:
            pbar_value = len(public_subnet)

            for i, subnet in enumerate(public_subnet):
                tags = [{'Key': 'Name', 'Value': subnet['name']}]

                if set_k8s_tags:
                    tags.append(
                        {'Key': 'kubernetes.io/role/elb', 'Value': '1'}
                    )

                response = self.client.create_subnet(
                    TagSpecifications=[
                        {
                            'ResourceType': 'subnet',
                            'Tags': tags
                        }
                    ],
                    AvailabilityZone=subnet['az'],
                    CidrBlock=subnet['cidr'],
                    VpcId=next(iter(self.resources['VPC'][0].values()))
                )
                self.client.modify_subnet_attribute(
                    MapPublicIpOnLaunch={
                        'Value': True
                    },
                    SubnetId=response['Subnet']['SubnetId']
                )
                self.resources['Subnet'].append({subnet['name']: response['Subnet']['SubnetId']})
                self.pbar.update(10 / pbar_value)

            self.pbar.update(round(1 - (self.pbar.n % 1), 1))
        else:
            self.pbar.update(10)

        if private_subnet:
            pbar_value = len(private_subnet)

            for i, subnet in enumerate(private_subnet):
                tags = [{'Key': 'Name', 'Value': subnet['name']}]

                if set_k8s_tags:
                    tags.append(
                        {'Key': 'kubernetes.io/role/internal-elb', 'Value': '1'}
                    )

                response = self.client.create_subnet(
                    TagSpecifications=[
                        {
                            'ResourceType': 'subnet',
                            'Tags': tags
                        }
                    ],
                    AvailabilityZone=subnet['az'],
                    CidrBlock=subnet['cidr'],
                    VpcId=next(iter(self.resources['VPC'][0].values()))
                )
                self.resources['Subnet'].append({subnet['name']: response['Subnet']['SubnetId']})
                self.pbar.update(10 / pbar_value)

            self.pbar.update(round(1 - (self.pbar.n % 1), 1))
        else:
            self.pbar.update(10)

        if protected_subnet:
            pbar_value = len(protected_subnet)

            for i, subnet in enumerate(protected_subnet):
                tags = [{'Key': 'Name', 'Value': subnet['name']}]

                response = self.client.create_subnet(
                    TagSpecifications=[
                        {
                            'ResourceType': 'subnet',
                            'Tags': tags
                        }
                    ],
                    AvailabilityZone=subnet['az'],
                    CidrBlock=subnet['cidr'],
                    VpcId=next(iter(self.resources['VPC'][0].values()))
                )
                self.resources['Subnet'].append({subnet['name']: response['Subnet']['SubnetId']})
                self.pbar.update(10 / pbar_value)

                self.pbar.update(round(1 - (self.pbar.n % 1), 1))
        else:
            self.pbar.update(10)

    def create_igw(self, igw=None):
        response = self.client.create_internet_gateway(
            TagSpecifications=[
                {
                    'ResourceType': 'internet-gateway',
                    'Tags': [{'Key': 'Name', 'Value': igw}]
                }
            ]
        )
        self.pbar.update(5)

        self.client.attach_internet_gateway(
            InternetGatewayId=response['InternetGateway']['InternetGatewayId'],
            VpcId=next(iter(self.resources['VPC'][0].values()))
        )
        self.resources['Internet Gateway'].append({igw: response['InternetGateway']['InternetGatewayId']})
        self.pbar.update(5)

    # TODO: Create route tables with Boto3
    def create_route_tables(self, public_rtb=None, private_rtb=None, protected_rtb=None):
        if public_rtb:
            response = self.client.create_route_table(
                VpcId=next(iter(self.resources['VPC'][0].values())),
                TagSpecifications=[
                    {
                        'ResourceType': 'route-table',
                        'Tags': [{'Key': 'Name', 'Value': public_rtb}],
                    }
                ]
            )
            self.resources['Route Table'].append({public_rtb: response['RouteTable']['RouteTableId']})
            self.pbar.update(3)

            self.client.create_route(
                DestinationCidrBlock='0.0.0.0/0',
                GatewayId=next(iter(self.resources['Internet Gateway'][0].values())),
                RouteTableId=response['RouteTable']['RouteTableId']
            )
            self.pbar.update(4)
        else:
            self.pbar.update(4)

        if private_rtb:
            pbar_value = len(private_rtb)

            for i, rtb in enumerate(private_rtb):
                response = self.client.create_route_table(
                    VpcId=next(iter(self.resources['VPC'][0].values())),
                    TagSpecifications=[
                        {
                            'ResourceType': 'route-table',
                            'Tags': [{'Key': 'Name', 'Value': rtb['name']}],
                        }
                    ]
                )
                self.resources['Route Table'].append({rtb['name']: response['RouteTable']['RouteTableId']})
                self.pbar.update(3 / pbar_value)
        else:
            self.pbar.update(3)

        if protected_rtb:
            response = self.client.create_route_table(
                VpcId=next(iter(self.resources['VPC'][0].values())),
                TagSpecifications=[
                    {
                        'ResourceType': 'route-table',
                        'Tags': [{'Key': 'Name', 'Value': protected_rtb}],
                    }
                ]
            )
            self.resources['Route Table'].append({protected_rtb: response['RouteTable']['RouteTableId']})
        self.pbar.update(3)

    def create_route_table_associations(self, public_subnet=None, private_subnet=None, protected_subnet=None,
                                        public_rtb=None, private_rtb=None, protected_rtb=None):
        if public_subnet:
            pbar_value = len(public_subnet)
            for i, subnet in enumerate(public_subnet):
                self.client.associate_route_table(
                    RouteTableId=next(item for item in self.resources['Route Table'] if public_rtb in item.keys())[
                        public_rtb],
                    SubnetId=next(item for item in self.resources['Subnet'] if subnet['name'] in item.keys())[
                        subnet['name']]
                )
                self.pbar.update(3.3 / pbar_value)
        else:
            self.pbar.update(3.3)

        # TODO: Create Private Route Table Association
        if private_subnet:
            # print(private_subnet)
            pbar_value = len(private_subnet)
            for i, subnet in enumerate(private_subnet):
                self.client.associate_route_table(
                    RouteTableId=
                    next(item for item in self.resources['Route Table'] if
                         private_rtb['name'] in item.keys() and private_subnet['name'] == private_rtb['subnet'])[
                        private_rtb['name']],
                    SubnetId=next(item for item in self.resources['Subnet'] if private_rtb['subnet'] in item.keys())[
                        private_rtb['subnet']]
                )
                self.pbar.update(3.3 / pbar_value)
        else:
            self.pbar.update(3.3)

        if protected_subnet:
            pbar_value = len(protected_subnet)
            for i, subnet in enumerate(protected_subnet):
                self.client.associate_route_table(
                    RouteTableId=next(item for item in self.resources['Route Table'] if protected_rtb in item.keys())[
                        public_rtb],
                    SubnetId=next(item for item in self.resources['Subnet'] if subnet in item.keys())[subnet]
                )
                self.pbar.update(3.3 / pbar_value)
        else:
            self.pbar.update(3.3)

        self.pbar.update(round(1 - (self.pbar.n % 1), 1))

    # TODO: Create nat gateways with Boto3
    def create_nat(self, nat=None, private_rtb=None):
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
            subnet_cfn_name = self.public_subnet_name[_nat['subn' \
                                                           'et']]
            self.resources['NAT' + str(i)] = {
                'Type': 'AWS::EC2::NatGateway',
                'Properties': {
                    'AllocationId': {
                        'Fn::GetAtt': ['EIP' + str(i), 'AllocationId']
                    },
                    'SubnetId': {
                        'Ref': subnet_cfn_name
                    },
                    'Tags': [{'Key': 'Name', 'Value': _nat['name']}]
                }
            }

            # routing
            nat_rtb_name = next(item for item in private_rtb if item['nat'] == _nat['name'])
            rtb_cfn_name = next(item for item in self.rtb_name if item['name'] == nat_rtb_name['name'])[
                'cloudformation']
            self.resources['{}RouteNAT{}'.format(rtb_cfn_name, str(i))] = {
                'Type': 'AWS::EC2::Route',
                'Properties': {
                    'DestinationCidrBlock': '0.0.0.0/0',
                    'NatGatewayId': {
                        'Ref': 'NAT' + str(i)
                    },
                    'RouteTableId': {
                        'Ref': rtb_cfn_name
                    }
                }
            }

    # TODO: Create s3 endpoint with Boto3
    def create_s3_ep(self, s3_gateway_ep):
        if s3_gateway_ep and s3_gateway_ep.get('route-table'):
            rtb_list = []

            for rtb in s3_gateway_ep['route-table']:
                rtb_name = next(item for item in self.rtb_name if item['name'] == rtb)
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
