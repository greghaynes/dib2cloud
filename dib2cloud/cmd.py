import argparse
import sys

from dib2cloud import app


def cmd_build(args):
    ao = app.App(config_path=args.config_path)
    ao.build_image(args.image_name)


def main(argv=None):
    argv = argv or sys.argv

    parser = argparse.ArgumentParser(prog='dib2cloud')
    parser.add_argument('--config', dest='config_path', type=str,
                        default='/etc/dib2cloud.conf')
    subparsers = parser.add_subparsers(help='sub-command help')

    build_subparser = subparsers.add_parser('build-image')
    build_subparser.set_defaults(func=cmd_build)
    build_subparser.add_argument('image_name', type=str)

    args = parser.parse_args(argv[1:])
    args.func(args)
