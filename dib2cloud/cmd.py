import argparse
import json
import sys

from dib2cloud import app


# This gives us a convenient place to monkeypatch for testing
def output(out):
    print(out)


def upload_summary_dict(upload):
    return {
        'upload_name': upload.upload_name,
        'glance_uuid': upload.glance_uuid
    }


def dib_summary_dict(dib, status_str=None):
    if status_str is None:
        status = dib.succeeded()
        if status[0] is True:
            status_str = 'built'
        else:
            if status[1] == app.DibError.StillRunning:
                status_str = 'building'
            else:
                status_str = 'error'

    if dib.is_running():
        pid = dib.pid
    else:
        pid = None

    return {
        'name': dib.name,
        'status': status_str,
        'id': dib.uuid,
        'pid': pid,
        'log': dib.log_path,
        'destinations': dib.dest_paths
    }


def cmd_build(d2c, args):
    dib = d2c.build(args.image_name)
    output(json.dumps(dib_summary_dict(dib)).encode('utf-8'))


def cmd_list_builds(d2c, args):
    dibs = d2c.get_builds()
    output(json.dumps(list(map(dib_summary_dict, dibs))).encode('utf-8'))


def cmd_delete_build(d2c, args):
    dib = d2c.delete_build(args.build_id)
    output(json.dumps(dib_summary_dict(dib, 'deleted')).encode('utf-8'))


def cmd_upload(d2c, args):
    upload = d2c.upload(args.build_id, args.cloud_name)
    output(json.dumps(upload_summary_dict(upload)).encode('utf-8'))


def main(argv=None):
    argv = argv or sys.argv

    parser = argparse.ArgumentParser(prog='dib2cloud')
    parser.add_argument('--config', dest='config_path', type=str,
                        default='/etc/dib2cloud.conf')
    subparsers = parser.add_subparsers(help='sub-command help')

    build_subparser = subparsers.add_parser('build')
    build_subparser.set_defaults(func=cmd_build)
    build_subparser.add_argument('image_name', type=str)

    list_builds_subparser = subparsers.add_parser('list-builds')
    list_builds_subparser.set_defaults(func=cmd_list_builds)

    delete_build_subparser = subparsers.add_parser('delete-build')
    delete_build_subparser.set_defaults(func=cmd_delete_build)
    delete_build_subparser.add_argument('build_id', type=str)

    upload_subparser = subparsers.add_parser('upload')
    upload_subparser.set_defaults(func=cmd_upload)
    upload_subparser.add_argument('build_id', type=str)
    upload_subparser.add_argument('cloud_name', type=str)

    args = parser.parse_args(argv[1:])
    args.func(app.App(config_path=args.config_path), args)
