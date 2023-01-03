import ipaddr
from pyfiglet import Figlet
import boto3
from botocore.config import Config


def print_figlet():
    figlet_title = Figlet(font='slant')

    print(figlet_title.renderText('VPC Stack Generator'))


def cidr_overlapped(cidr1, cidr2):
    return ipaddr.IPNetwork(cidr1).overlaps(ipaddr.IPNetwork(cidr2))


def get_regions():
    region_codes = {
        'us-east-1': 'US East (N. Virginia)',
        'us-east-2': 'US East (Ohio)',
        'us-west-1': 'US West (N. California)',
        'us-west-2': 'US West (Oregon)',
        'ap-south-1': 'Asia Pacific (Mumbai)',
        'ap-northeast-3': 'Asia Pacific (Osaka)',
        'ap-northeast-2': 'Asia Pacific (Seoul)',
        'ap-southeast-1': 'Asia Pacific (Singapore)',
        'ap-southeast-2': 'Asia Pacific (Sydney)',
        'ap-northeast-1': 'Asia Pacific (Tokyo)',
        'ca-central-1': 'Canada (Central)',
        'eu-central-1': 'Europe (Frankfurt)',
        'eu-west-1': 'Europe (Ireland)',
        'eu-west-2': 'Europe (London)',
        'eu-west-3': 'Europe (Paris)',
        'eu-north-1': 'Europe (Stockholm)',
        'sa-east-1': 'South America (São Paulo)',
        'af-south-1': 'Africa (Cape Town)',
        'ap-east-1': 'Asia Pacific (Hong Kong)',
        'ap-south-2': 'Asia Pacific (Hyderabad)',
        'ap-southeast-3': 'Asia Pacific (Jakarta)',
        'eu-south-1': 'Europe (Milan)',
        'eu-south-2': 'Europe (Spain)',
        'eu-central-2': 'Europe (Zurich)',
        'me-south-1': 'Middle East (Bahrain)',
        'me-central-1': 'Middle East (UAE)',
    }

    client = boto3.client('ec2', config=Config(region_name='us-east-1'))
    response = client.describe_regions()
    available_region = [item['RegionName'] for item in response['Regions']]

    available_list = []

    for region in region_codes:
        if region in available_region:
            available_list.append((
                '{0:<14} {1}'.format(region, region_codes[region]),
                region
            ))

    return available_list


def get_azs(region):
    client = boto3.client('ec2', config=Config(region_name='us-east-1'))
    response = client.describe_availability_zones(
        Filters=[
            {
                'Name': 'region-name',
                'Values': [region]
            }
        ]
    )

    az_list = [item['ZoneName'] for item in response['AvailabilityZones']]
    az_list.sort()

    return az_list
