from prettytable import PrettyTable


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

    def print_ep(
            self,
            s3_gateway_ep=None,
            dynamodb_gateway_ep=None
    ):
        self.table.clear()
        self.table.title = 'Gateway Endpoints'
        self.table.field_names = ['Type', 'Route Table']

        if s3_gateway_ep and s3_gateway_ep.get('route-table'):
            self.table.add_row(['S3', '\n'.join(s3_gateway_ep['route-table'])])
            # for route_table in s3_gateway_ep['route-table']:
            #     self.table.add_row([route_table])
        else:
            self.table.add_row(['S3', 'None'])

        if dynamodb_gateway_ep and dynamodb_gateway_ep.get('route-table'):
            self.table.add_row(['DynamoDB', '\n'.join(dynamodb_gateway_ep['route-table'])])
            # for route_table in s3_gateway_ep['route-table']:
            #     self.table.add_row([route_table])
        else:
            self.table.add_row(['DynamoDB', 'None'])

        print(self.table)

    def print_flow_logs(self, flow_logs=None):
        if flow_logs is None:
            flow_logs = {'log-group': '', 'role-name': ''}
        self.table.clear()
        self.table.title = 'VPC Flow Logs'
        self.table.field_names = ['Log Group Name', 'Role Name']

        self.table.add_row([flow_logs.get('log-group'), flow_logs.get('role-name')])

        print(self.table)
