# EssoraFM
# Author: josejp2424 and Nilsonmorales - GPL-3.0
import os

APP_NAME = 'EssoraFM'
APP_ID = 'org.essora.fm'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_PATH = os.path.join(BASE_DIR, 'ui', 'icons', 'essorafm.svg')
ABOUT_ICON_PATH = os.path.join(BASE_DIR, 'ui', 'icons', 'essorafm-about.png')
HOME = os.path.expanduser('~')
GTK3_SETTINGS_INI = os.path.join(HOME, '.config', 'gtk-3.0', 'settings.ini')
DEFAULT_START_DIR = HOME
RSYNC_BINARY = '/usr/bin/rsync'
COPY_PROGRESS_PULSE_MS = 150
CONFIG_DIR = os.path.join(HOME, '.config', 'essorafm')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.ini')
LEGACY_CONFIG_FILE = os.path.join(CONFIG_DIR, 'settings.ini')
TRASH_DIR = os.path.join(HOME, '.local', 'share', 'Trash')
TRASH_FILES_DIR = os.path.join(TRASH_DIR, 'files')
TRASH_INFO_DIR = os.path.join(TRASH_DIR, 'info')
DEFAULT_ICON_SIZE = 64
DEFAULT_LIST_ICON_SIZE = 32
DEFAULT_SIDEBAR_ICON_SIZE = 32
DEFAULT_VIEW_MODE = 'icons'
ABOUT_GREEN = '#77960A'
VERSION = "0.4.21"
