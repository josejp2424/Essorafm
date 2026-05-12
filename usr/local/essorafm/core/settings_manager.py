# EssoraFM
# Author: josejp2424 and Nilsonmorales - GPL-3.0
import configparser
import os

from core.settings import (
    CONFIG_DIR,
    CONFIG_FILE,
    LEGACY_CONFIG_FILE,
)


ESSORAFM_MOUNT_ACTION = "/usr/local/bin/essorafm '$dir'"
ESSORAFM_UMOUNT_ACTION = "/usr/local/bin/essorafm -D '$dir'"


class SettingsManager:
    """Single configuration manager for EssoraFM.

    EssoraFM now keeps both the file-manager preferences and the desktop drive
    icon preferences in one file only:

        ~/.config/essorafm/config.ini
        [Main]

    Missing keys are written back with sane Essora defaults.  MountAction and
    UMountAction are intentionally locked to the internal EssoraFM commands so
    the desktop integration cannot be broken from the GUI or by stale configs.
    """

    SECTION = 'Main'

    DEFAULTS = {
        'view_mode': 'list',
        'icon_size': '48',
        'list_icon_size': '32',
        'sidebar_icon_size': '32',
        'toolbar_icon_size': '20',
        'show_hidden': 'false',
        'single_click': 'false',
        'show_thumbnails': 'true',
        'desktop_drive_icons': 'true',
        'desktop_drive_icon_size': '48',
        'desktop_drive_show_internal': 'true',
        'desktop_drive_show_removable': 'true',
        'desktop_drive_show_network': 'false',
        'window_width': '880',
        'window_height': '550',
        'sidebar_layout': 'classic',
        'preview_enabled': 'false',
        'toolbar_style': 'text_below',
        'sort_field': 'name',
        'sort_direction': 'asc',
        'app_theme': 'default',
        'theme_rounded': 'false',
        'theme_cards': 'true',
        'theme_glass': 'true',
        'XPos': '0',
        'YPos': '1',
        'XOffset': '0',
        'YOffset': '-40',
        'NLines': '2',
        'ShowFrame': 'false',
        'Vertical': 'false',
        'ReversePack': 'true',
        'ShowLabels': 'true',
        'ShowDesktopFiles': 'true',
        'SpacingX': '112',
        'SpacingY': '126',
        'LabelWidth': '12',
        'OpenCommand': '/usr/local/bin/essorafm',
        'PymenuCommand': '/usr/local/bin/pymenu',
        'Wallpaper': '',
        'WallpaperMode': 'zoom',
        'WallpaperDirectory': '/usr/share/backgrounds',
        'MountAction': ESSORAFM_MOUNT_ACTION,
        'UMountAction': ESSORAFM_UMOUNT_ACTION,
        'DrawShadow': 'true',
        'FontColor': '#ffffffffffff',
        'ShadowColor': '#000000000000',
    }

    LEGACY_MAP = {
        'enabled': 'desktop_drive_icons',
        'Enabled': 'desktop_drive_icons',
        'DesktopDriveIcons': 'desktop_drive_icons',
        'desktop_drive_icons_enabled': 'desktop_drive_icons',
        'DesktopDriveIconsEnabled': 'desktop_drive_icons',
        'show_drive_icons': 'desktop_drive_icons',
        'ShowDriveIcons': 'desktop_drive_icons',
        'UseExternalDriveIcons': 'desktop_drive_icons',
        'use_external_drive_icons': 'desktop_drive_icons',

        'IconSize': 'desktop_drive_icon_size',
        'icon_size_desktop': 'desktop_drive_icon_size',
        'ShowInternal': 'desktop_drive_show_internal',
        'show_internal': 'desktop_drive_show_internal',
        'ShowRemovable': 'desktop_drive_show_removable',
        'show_removable': 'desktop_drive_show_removable',
        'ShowNetwork': 'desktop_drive_show_network',
        'show_network': 'desktop_drive_show_network',
        'show_labels': 'ShowLabels',
        'show_desktop_files': 'ShowDesktopFiles',
        'spacing_x': 'SpacingX',
        'spacing_y': 'SpacingY',
        'label_width': 'LabelWidth',
        'open_command': 'OpenCommand',
        'pymenu_command': 'PymenuCommand',
        'wallpaper': 'Wallpaper',
        'wallpaper_mode': 'WallpaperMode',
        'wallpaper_directory': 'WallpaperDirectory',
        'start_x': 'XOffset',
        'start_y': 'YOffset',
    }

    LOCKED_VALUES = {
        'MountAction': ESSORAFM_MOUNT_ACTION,
        'UMountAction': ESSORAFM_UMOUNT_ACTION,
    }

    def __init__(self):
        self.config = configparser.ConfigParser(strict=False)
        self.config.optionxform = str
        self.data = dict(self.DEFAULTS)
        self.load()

    def _canonical_key(self, key):
        return self.LEGACY_MAP.get(key, key)

    def _new_parser(self):
        parser = configparser.ConfigParser(strict=False)
        parser.optionxform = str
        return parser

    def load(self):
        self.data = dict(self.DEFAULTS)
        os.makedirs(CONFIG_DIR, exist_ok=True)
        changed = False

        paths = []
        if not os.path.exists(CONFIG_FILE) and os.path.exists(LEGACY_CONFIG_FILE):
            paths.append(LEGACY_CONFIG_FILE)
        paths.append(CONFIG_FILE)

        for config_path in paths:
            if not os.path.exists(config_path):
                continue
            try:
                parser = self._new_parser()
                parser.read(config_path, encoding='utf-8')
            except Exception as exc:
                print(f"Error loading config: {exc}")
                continue

            for section in (self.SECTION, 'General', 'DesktopDriveIcons', 'Desktop', 'Settings'):
                if not parser.has_section(section):
                    continue
                for key, value in parser[section].items():
                    canonical = self._canonical_key(key)
                    self.data[canonical] = value
                    if canonical != key:
                        changed = True

        for key, value in self.DEFAULTS.items():
            if key not in self.data:
                self.data[key] = value
                changed = True
        for key, value in self.LOCKED_VALUES.items():
            if self.data.get(key) != value:
                self.data[key] = value
                changed = True

        if changed or not os.path.exists(CONFIG_FILE):
            self.save()
        return self.data

    def save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        for key, value in self.LOCKED_VALUES.items():
            self.data[key] = value
        self.config = self._new_parser()
        self.config[self.SECTION] = self.data
        with open(CONFIG_FILE, 'w', encoding='utf-8') as fh:
            self.config.write(fh)

    def get(self, key, fallback=None):
        canonical = self._canonical_key(key)
        return self.data.get(canonical, fallback)

    def get_bool(self, key, fallback=False):
        value = str(self.get(key, fallback)).strip().lower()
        return value in {'1', 'true', 'yes', 'on'}

    def get_int(self, key, fallback=0):
        try:
            return int(float(self.get(key, fallback)))
        except (TypeError, ValueError):
            return fallback

    def get_float(self, key, fallback=0.0):
        try:
            return float(self.get(key, fallback))
        except (TypeError, ValueError):
            return fallback

    def set(self, key, value):
        canonical = self._canonical_key(key)
        if canonical in self.LOCKED_VALUES:
            self.data[canonical] = self.LOCKED_VALUES[canonical]
        else:
            self.data[canonical] = str(value)

    def update(self, mapping):
        for key, value in mapping.items():
            self.set(key, value)
        self.save()
