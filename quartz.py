import argparse
import configparser
import os

APPNAME = os.path.splitext(os.path.basename(__file__))[0]

CONFIGVAR = APPNAME.upper() + '_CONFIG'

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config',
        nargs = '+',
        help =
            f'One or more config files. Read paths from {CONFIGVAR}'
            ' environment variable if not given.',
    )
    args = parser.parse_args(argv)

    if args.config:
        config_filenames = args.config
    else:
        config_filenames = os.environ[CONFIGVAR].split(':')

    cp = configparser.ConfigParser()
    cp.read(config_filenames)

    tasks = cp[APPNAME]['tasks'].split()
    print(tasks)

if __name__ == '__main__':
    main()
