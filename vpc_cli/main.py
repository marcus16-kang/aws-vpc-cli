import sys
import argparse

from vpc_cli.command import Command
from vpc_cli import VERSION


def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', '-v', nargs='*', dest='version')

    show_version = parser.parse_args().version

    return {'version': True if show_version is not None else False}


def main():
    try:
        options = get_arguments()

        if options['version']:
            print(f'vpc-cli v{VERSION}')

        else:
            Command()

    except KeyboardInterrupt:
        print('Cancelled by user.')
        sys.exit()


if __name__ == '__main__':
    main()
