#!/usr/bin/env python3
# EssoraFM
# Author: josejp2424 - GPL-3.0
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

ICON_PATH = os.path.join(BASE_DIR, 'ui', 'icons', 'essorafm.svg')

if os.path.exists(ICON_PATH):
    try:
        Gtk.Window.set_default_icon_from_file(ICON_PATH)
    except Exception:
        pass

from app.window import EssoraFMApp


def main() -> int:
    args = list(sys.argv[1:])

    if '--desktop' in args:
        from app.desktop import run_desktop
        run_desktop()
        return 0

    app = EssoraFMApp()
    return app.run(sys.argv)


if __name__ == '__main__':
    raise SystemExit(main())
