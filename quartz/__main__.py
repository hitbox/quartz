from .argparser import argument_parser

def main(argv=None):
    """
    Process command line arguments and call sub-command.
    """
    parser = argument_parser()
    args = parser.parse_args(argv)
    args.func(args)

main()
