import ipaddr
from pyfiglet import Figlet


def print_figlet():
    figlet_title = Figlet(font='slant')

    print(figlet_title.renderText('VPC Stack Generator'))


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
