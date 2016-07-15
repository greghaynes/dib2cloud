import argparse
import json
import sys

from dib2cloud import app


def dib_summary_dict(dib):
    status = dib.succeeded()
    status_str = None
    if status[0] == True:
        status_str = 'built'
    else:
        if status[1] == app.DibError.StillRunning:
            status_str = 'building'
        else:
            status_str = 'error'
    return {
        'name': dib.name,
        'status': status_str,
        'id': dib.uuid
    }


def cmd_list(d2c, args):
    dibs = d2c.get_local_images()
    print(json.dumps(list(map(dib_summary_dict, dibs))))


def cmd_build(d2c, args):
    d2c.build_image(args.image_name)


def main(argv=None):
    argv = argv or sys.argv

    parser = argparse.ArgumentParser(prog='dib2cloud')
    parser.add_argument('--config', dest='config_path', type=str,
                        default='/etc/dib2cloud.conf')
    subparsers = parser.add_subparsers(help='sub-command help')

    build_subparser = subparsers.add_parser('build-image')
    build_subparser.set_defaults(func=cmd_build)
    build_subparser.add_argument('image_name', type=str)

    list_subparser = subparsers.add_parser('list')
    list_subparser.set_defaults(func=cmd_list)

    args = parser.parse_args(argv[1:])
    args.func(app.App(config_path=args.config_path), args)
