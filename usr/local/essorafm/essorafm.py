#!/usr/bin/env python3
# EssoraFM
# Author: josejp2424 and Nilsonmorales - GPL-3.0
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Gio, GLib

ICON_PATH = os.path.join(BASE_DIR, 'ui', 'icons', 'essorafm.svg')

if os.path.exists(ICON_PATH):
    try:
        Gtk.Window.set_default_icon_from_file(ICON_PATH)
    except Exception:
        pass

from app.window import EssoraFMApp


def _unmount_path(path: str) -> int:
    """Unmount a mounted path and exit.

    This makes the locked command below useful for old integrations too:
        /usr/local/essorafm/bin/essorafm -D '$dir'
    """
    if not path:
        return 1
    target = os.path.abspath(os.path.expanduser(path))
    loop = GLib.MainLoop()
    result = {'code': 1}

    def finish(_obj, async_result, _data=None):
        try:
            if hasattr(mount, 'unmount_with_operation_finish'):
                mount.unmount_with_operation_finish(async_result)
            else:
                mount.unmount_finish(async_result)
            result['code'] = 0
        except Exception as exc:
            print(f"EssoraFM: could not unmount {target}: {exc}", file=sys.stderr)
            result['code'] = 1
        finally:
            loop.quit()

    try:
        gfile = Gio.File.new_for_path(target)
        mount = gfile.find_enclosing_mount(None)
        operation = Gtk.MountOperation.new(None)
        if hasattr(mount, 'unmount_with_operation'):
            mount.unmount_with_operation(0, operation, None, finish, None)
        else:
            mount.unmount(0, None, finish, None)
        loop.run()
        return int(result['code'])
    except Exception as exc:
        print(f"EssoraFM: could not unmount {target}: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    args = list(sys.argv[1:])

    if '--desktop' in args:
        from app.desktop import run_desktop
        run_desktop()
        return 0

    if '-D' in args:
        idx = args.index('-D')
        target = args[idx + 1] if idx + 1 < len(args) else ''
        return _unmount_path(target)

    app = EssoraFMApp()
    return app.run(sys.argv)


if __name__ == '__main__':
    raise SystemExit(main())
