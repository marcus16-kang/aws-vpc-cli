import os
import boto3
from botocore.config import Config
from inquirer import prompt, Confirm, Text
from datetime import datetime
from dateutil import tz
from prettytable import PrettyTable
from plyer import notification
from cfn_visualizer import visualizer

import vpc_cli
from vpc_cli.validators import stack_name_validator


class DeployCfn:
    client = None
    deploy = False
    project = ''
    name = ''
    region = ''

    def __init__(
            self,
            project,
            region,
    ):
        self.project = project
        self.region = region
        self.ask_deployment()
        self.input_stack_name()
        self.deployment(project, self.name, region)

    def ask_deployment(self):
        questions = [
            Confirm(
                name='required',
                message='Do you want to deploy using CloudFormation in here?',
                default=True
            )
        ]

        self.deploy = prompt(questions=questions, raise_keyboard_interrupt=True)['required']

    def input_stack_name(self):
        questions = [
            Text(
                name='name',
                message='Type CloudFormation Stack name',
                validate=lambda _, x: stack_name_validator(x, self.region)
            )
        ]

        self.name = prompt(questions=questions, raise_keyboard_interrupt=True)['name']

    def deployment(self, project, name, region):
        if self.deploy:  # deploy using cloudformation
            self.client = boto3.client('cloudformation', config=Config(region_name=region))
            response = self.client.create_stack(
                StackName=name,
                TemplateBody=self.get_template(),
                TimeoutInMinutes=15,
                Tags=[{'Key': 'Name', 'Value': name}, {'Key': 'project', 'Value': self.project}],
                Capabilities=['CAPABILITY_NAMED_IAM'],
            )
            stack_id = response['StackId']

            while True:
                # 1. get stack status
                response = self.client.describe_stacks(
                    StackName=name
                )
                stack_status = response['Stacks'][0]['StackStatus']

                if stack_status in ['CREATE_FAILED', 'ROLLBACK_FAILED',
                                    'ROLLBACK_COMPLETE']:  # create failed
                    print()
                    print('\x1b[91m' + 'Failed!' + '\x1b[0m')
                    print()
                    print('\x1b[91m' + 'Please check CloudFormation at here:' + '\x1b[0m')
                    print()
                    print(
                        '\x1b[91m' +
                        'https://{0}.console.aws.amazon.com/cloudformation/home?region={0}#/stacks/stackinfo?stackId={1}'.format(
                            region, stack_id) +
                        '\x1b[0m')

                    # notification.notify(
                    #     title='Failed!',
                    #     message=f'{self.name} creation failed.',
                    #     app_name=f'VPC CLI',
                    #     app_icon=f'{os.path.dirname(vpc_cli.__file__)}/assets/logo.ico',
                    #     timeout=0
                    # )

                    break

                elif stack_status == 'CREATE_COMPLETE':  # create complete successful
                    print()
                    self.print_table()
                    print('\x1b[92m' + 'Success!' + '\x1b[0m')

                    # notification.notify(
                    #     title='Success!',
                    #     message=f'{self.name} creation successful.',
                    #     app_name=f'VPC CLI',
                    #     app_icon=f'{os.path.dirname(vpc_cli.__file__)}/assets/logo.ico',
                    #     timeout=0
                    # )

                    break

                else:
                    visualizer(client=self.client, stack_name=self.name)

        else:
            print('Done!\n\n')
            print('You can deploy VPC using AWS CLI\n\n\n')
            print(
                'aws cloudformation deploy --stack-name {} --region {} --template-file ./vpc.yaml'.format(
                    name, region))

    def get_template(self):
        with open('vpc.yaml', 'r') as f:
            # content = yaml.full_load(f)
            content = f.read()

        # content = json.dumps(content)

        return content

    def get_timestamp(self, timestamp: datetime):
        return timestamp.replace(tzinfo=tz.tzutc()).astimezone(tz.tzlocal()).strftime('%I:%M:%S %p')

    def get_color(self, status: str):
        if 'ROLLBACK' in status or 'FAILED' in status:
            return '91m'

        elif 'PROGRESS' in status:
            return '96m'

        elif 'COMPLETE' in status:
            return '92m'

    def print_table(self):
        table = PrettyTable()
        table.set_style(15)
        table.field_names = ['Logical ID', 'Physical ID', 'Type']
        table.vrules = 0
        table.hrules = 1
        table.align = 'l'
        rows = []

        response = self.client.describe_stack_resources(StackName=self.name)['StackResources']

        for resource in response:
            rows.append([resource['LogicalResourceId'], resource['PhysicalResourceId'], resource['ResourceType']])

        rows = sorted(rows, key=lambda x: (x[2], x[0]))
        table.add_rows(rows)
        print(table)
