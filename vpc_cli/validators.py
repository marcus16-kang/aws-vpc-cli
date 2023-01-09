import re
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from vpc_cli.tools import cidr_overlapped


def name_validator(text):
    return len(text) > 0


def vpc_cidr_validator(text):
    return re.match(pattern=r'(?<!\d\.)(?<!\d)(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}(?!\d|(?:\.\d))',
                    string=text)


def subnet_count_validator(text):
    return re.match(pattern=r'^[0-9]{1,}$', string=text)


def subnet_cidr_validator(text, vpc_cidr, subnet_cidrs):
    re_match = re.match(pattern=r'(?<!\d\.)(?<!\d)(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}(?!\d|(?:\.\d))',
                        string=text)

    if not re_match:
        return False

    elif not cidr_overlapped(vpc_cidr, text):
        return False

    else:
        for subnet_cidr in subnet_cidrs:
            if cidr_overlapped(subnet_cidr, text):
                return False

        return True


def stack_name_validator(text, region):
    if not len(text):
        return False

    else:
        try:
            boto3.client('cloudformation', config=Config(region_name=region)).describe_stacks(StackName=text)

        except ClientError:  # stack doest
            return True

        except Exception as e:
            print(e)

            return False
