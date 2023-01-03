from vpc_cli.command import Command


def main():
    try:
        Command()

    except KeyboardInterrupt:
        print('Cancelled by user.')


if __name__ == '__main__':
    main()
