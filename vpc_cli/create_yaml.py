import yaml


class CreateYAML:
    resources = {}
    project = ''
    region = None
    public_subnet_name = {}
    private_subnet_name = {}
    protected_subnet_name = []
    rtb_name = []

    def __init__(
            self,
            project,
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
            s3_gateway_ep=None,
            dynamodb_gateway_ep=None,
            flow_logs=None
    ):
        self.project = project
        self.region = region
        self.create_vpc(vpc=vpc)
        self.create_subnets(
            public_subnet=public_subnet,
            private_subnet=private_subnet,
            protected_subnet=protected_subnet,
            set_k8s_tags=k8s_tags
        )
        self.create_igw(igw=igw, public_subnet=public_subnet)
        self.create_route_tables(public_rtb=public_rtb, private_rtb=private_rtb, protected_rtb=protected_rtb)
        self.create_nat(nat=nat, private_rtb=private_rtb)
        self.create_s3_ep(s3_gateway_ep=s3_gateway_ep)
        self.create_dynamodb_ep(dynamodb_gateway_ep=dynamodb_gateway_ep)
        self.create_flow_logs(flow_logs=flow_logs)
        self.create_yaml()

    def create_vpc(self, vpc):
        self.resources['VPC'] = {
            'Type': 'AWS::EC2::VPC',
            'Properties': {
                'CidrBlock': vpc['cidr'],
                'EnableDnsHostnames': True,
                'EnableDnsSupport': True,
                'InstanceTenancy': 'default',
                'Tags': [{'Key': 'Name', 'Value': vpc['name']}, {'Key': 'project', 'Value': self.project}]
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
                        'Tags': [{'Key': 'Name', 'Value': subnet['name']}, {'Key': 'project', 'Value': self.project}],
                        'VpcId': {
                            'Ref': 'VPC'
                        }
                    }
                }
                self.public_subnet_name[subnet['name']] = 'PublicSubnet' + str(i)

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
                        'Tags': [{'Key': 'Name', 'Value': subnet['name']}, {'Key': 'project', 'Value': self.project}],
                        'VpcId': {
                            'Ref': 'VPC'
                        }
                    }
                }
                # self.private_subnet_name.append({'cloudformation': 'PrivateSubnet' + str(i), 'name': subnet['name']})
                self.private_subnet_name[subnet['name']] = 'PrivateSubnet' + str(i)

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
                        'Tags': [{'Key': 'Name', 'Value': subnet['name']}, {'Key': 'project', 'Value': self.project}],
                        'VpcId': {
                            'Ref': 'VPC'
                        }
                    }
                }
                self.protected_subnet_name.append(
                    {'cloudformation': 'ProtectedSubnet' + str(i), 'name': subnet['name']})

    def create_igw(self, igw=None, public_subnet=None):  # Create internet gateway when exists public subnet
        if public_subnet:
            self.resources['IGW'] = {
                'Type': 'AWS::EC2::InternetGateway',
                'Properties': {
                    'Tags': [{'Key': 'Name', 'Value': igw}, {'Key': 'project', 'Value': self.project}]
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
                'DependsOn': 'IGWAttachmentVPC',
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
                    'Tags': [{'Key': 'Name', 'Value': public_rtb}, {'Key': 'project', 'Value': self.project}],
                    'VpcId': {
                        'Ref': 'VPC'
                    }
                }
            }

            # associate public subnets to public route table
            for _, subnet_cfn_name in self.public_subnet_name.items():
                self.resources[subnet_cfn_name + 'RouteTableAssociation'] = {
                    'Type': 'AWS::EC2::SubnetRouteTableAssociation',
                    'Properties': {
                        'SubnetId': {
                            'Ref': subnet_cfn_name
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
                        'Tags': [{'Key': 'Name', 'Value': rtb['name']}, {'Key': 'project', 'Value': self.project}],
                        'VpcId': {
                            'Ref': 'VPC'
                        }
                    }
                }

                # associate each private subnet to each private route table
                # subnet_cloudformation_name = next(
                #     item for item in self.private_subnet_name if item['name'] == rtb['subnet'])
                subnet_cfn_name = self.private_subnet_name[rtb['subnet']]
                self.resources[subnet_cfn_name + 'RouteTableAssociation'] = {
                    'Type': 'AWS::EC2::SubnetRouteTableAssociation',
                    'Properties': {
                        'SubnetId': {
                            'Ref': subnet_cfn_name
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
                    'Tags': [{'Key': 'Name', 'Value': protected_rtb}, {'Key': 'project', 'Value': self.project}],
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
                    'Tags': [{'Key': 'Name', 'Value': _nat['eip']}, {'Key': 'project', 'Value': self.project}],
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
                    'Tags': [{'Key': 'Name', 'Value': _nat['name']}, {'Key': 'project', 'Value': self.project}]
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

    def create_dynamodb_ep(self, dynamodb_gateway_ep):
        if dynamodb_gateway_ep and dynamodb_gateway_ep.get('route-table'):
            rtb_list = []

            for rtb in dynamodb_gateway_ep['route-table']:
                rtb_name = next(item for item in self.rtb_name if item['name'] == rtb)
                rtb_list.append({'Ref': rtb_name['cloudformation']})

            self.resources['DynamoDBEP'] = {
                'Type': 'AWS::EC2::VPCEndpoint',
                'Properties': {
                    'RouteTableIds': rtb_list,
                    'ServiceName': 'com.amazonaws.{}.dynamodb'.format(self.region),
                    'VpcId': {
                        'Ref': 'VPC'
                    }
                }
            }

    def create_flow_logs(self, flow_logs):
        if flow_logs.get('log-group', None) is not None and flow_logs.get('role-name', None) is not None:
            self.resources['FlowLogIamRole'] = {
                'Type': 'AWS::IAM::Role',
                'Properties': {
                    'AssumeRolePolicyDocument': {
                        'Version': '2012-10-17',
                        'Statement': [
                            {
                                'Effect': 'Allow',
                                'Principal': {
                                    'Service': 'vpc-flow-logs.amazonaws.com'
                                },
                                'Action': 'sts:AssumeRole'
                            }
                        ]
                    },
                    'Path': '/',
                    'Policies': [{
                        'PolicyName': 'flow-logs-policy',
                        'PolicyDocument': {
                            'Version': '2012-10-17',
                            'Statement': [
                                {
                                    'Effect': 'Allow',
                                    'Action': [
                                        'logs:CreateLogGroup',
                                        'logs:CreateLogStream',
                                        'logs:PutLogEvents',
                                        'logs:DescribeLogGroups',
                                        'logs:DescribeLogStreams'
                                    ],
                                    'Resource': '*'
                                }
                            ]
                        }
                    }],
                    'RoleName': flow_logs.get('role-name'),
                    'Tags': [{'Key': 'Name', 'Value': flow_logs.get('role-name')},
                             {'Key': 'project', 'Value': self.project}]
                }
            }
            self.resources['FlowLogs'] = {
                'Type': 'AWS::EC2::FlowLog',
                'Properties': {
                    'DeliverLogsPermissionArn': {
                        'Fn::GetAtt': 'FlowLogIamRole.Arn'
                    },
                    'LogGroupName': flow_logs.get('log-group'),
                    'ResourceId': {
                        'Ref': 'VPC'
                    },
                    'ResourceType': 'VPC',
                    'TrafficType': 'ALL',
                    'Tags': [{'Key': 'project', 'Value': self.project}]
                }
            }

    def create_yaml(self):
        template = {
            'AWSTemplateFormatVersion': '2010-09-09',
            'Description': 'VPC Stack Generator CLI',
            'Resources': self.resources
        }

        try:
            with open('vpc.yaml', 'w') as f:
                yaml.dump(template, f)

        except Exception as e:
            print(e)
