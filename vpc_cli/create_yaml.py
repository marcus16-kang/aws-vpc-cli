import yaml


class CreateYAML:
    resources = {}
    region = None
    public_subnet_name = []
    private_subnet_name = []
    protected_subnet_name = []
    rtb_name = []

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
        self.create_nat(nat=nat, private_rtb=private_rtb)
        self.create_s3_ep(s3_gateway_ep=s3_gateway_ep)
        self.create_yaml()

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

            self.rtb_name.append({'cloudformation': 'PublicRouteTable', 'name': public_rtb})

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

                self.rtb_name.append(
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

            self.rtb_name.append({'cloudformation': 'ProtectRouteTable', 'name': protected_rtb})

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
            nat_rtb_name = next(item for item in private_rtb if item['nat'] == _nat['name'])
            rtb_cfn_name = next(item for item in self.rtb_name if item['name'] == nat_rtb_name['name'])['cloudformation']
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

    def create_s3_ep(self, s3_gateway_ep=None):
        if s3_gateway_ep.get('route-table'):
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