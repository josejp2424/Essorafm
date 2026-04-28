# EssoraFM
# Author: josejp2424 - GPL-3.0
import configparser
import os
import shutil

from core.settings import CONFIG_DIR

# EssoraFM desktop settings now live here, as requested.
# Archivo exclusivo para iconos de escritorio — NO compartir con config.ini
DESKTOP_DRIVES_CONFIG        = os.path.join(CONFIG_DIR, 'desktop_drives.ini')
# config.ini es de SettingsManager; ya no se usa como compat para evitar duplicados
DESKTOP_DRIVES_COMPAT_CONFIG = None


class DesktopDriveSettings:
    """EssoraFM desktop/drive icon settings.

    Main configuration file:
        ~/.config/essorafm/settings.ini
        [Main]

    A compatibility copy is also written to:
        ~/.config/essorafm/config.ini

    This lets EssoraFM use settings.ini while keeping essora-desktop-drive-icons
    compatible if the external binary still expects config.ini.
    """

    SECTION = 'Main'

    DEFAULTS = {
        'XPos': '0.010',
        'YPos': '0.990',
        'XOffset': '0',
        'YOffset': '-40',
        'NLines': '2',
        'ShowFrame': 'true',
        'Vertical': 'false',
        'ReversePack': 'true',
        'MountAction': "/usr/local/bin/essorafm '$dir'",
        'UMountAction': "/usr/local/bin/essorafm -D '$dir'",
        'DrawShadow': 'true',
        'FontColor': '#ffffffffffff',
        'ShadowColor': '#000000000000',

        'Enabled': 'true',
        'UseExternalDriveIcons': 'true',
        'ShowInternal': 'true',
        'ShowRemovable': 'true',
        'ShowNetwork': 'false',
        'ShowLabels': 'true',
        'ShowDesktopFiles': 'true',
        'IconSize': '48',
        'SpacingX': '112',
        'SpacingY': '112',
        'LabelWidth': '12',
        'OpenCommand': 'essorafm',
        'PymenuCommand': '/usr/local/bin/pymenu',
        'Wallpaper': '',
        'WallpaperMode': 'zoom',
        'WallpaperDirectory': '/usr/share/backgrounds',
        'SortBy': 'name',
    }

    LEGACY_MAP = {
        'enabled': 'Enabled',
        'show_internal': 'ShowInternal',
        'show_removable': 'ShowRemovable',
        'show_network': 'ShowNetwork',
        'show_labels': 'ShowLabels',
        'show_desktop_files': 'ShowDesktopFiles',
        'icon_size': 'IconSize',
        'spacing_x': 'SpacingX',
        'spacing_y': 'SpacingY',
        'label_width': 'LabelWidth',
        'open_command': 'OpenCommand',
        'pymenu_command': 'PymenuCommand',
        'wallpaper': 'Wallpaper',
        'wallpaper_mode': 'WallpaperMode',
        'wallpaper_directory': 'WallpaperDirectory',
        'sort_by': 'SortBy',
        'start_x': 'XOffset',
        'start_y': 'YOffset',
        'use_external_drive_icons': 'UseExternalDriveIcons',
        'UseExternalDriveIcons': 'UseExternalDriveIcons',
        'desktop_drive_icons': 'UseExternalDriveIcons',
        'DesktopDriveIcons': 'UseExternalDriveIcons',
        'desktop_drive_icons_enabled': 'UseExternalDriveIcons',
        'DesktopDriveIconsEnabled': 'UseExternalDriveIcons',
        'show_drive_icons': 'UseExternalDriveIcons',
        'ShowDriveIcons': 'UseExternalDriveIcons',
    }

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.optionxform = str
        self.data = dict(self.DEFAULTS)
        self.load()

    def _read_file(self, path):
        parser = configparser.ConfigParser()
        parser.optionxform = str
        if not os.path.exists(path):
            return
        try:
            parser.read(path, encoding='utf-8')
        except Exception:
            return
        for section in (self.SECTION, 'General', 'DesktopDriveIcons', 'Desktop', 'Settings'):
            if parser.has_section(section):
                for key, value in parser[section].items():
                    canonical = self.LEGACY_MAP.get(key, key)
                    self.data[canonical] = value

    def load(self):
        self.data = dict(self.DEFAULTS)
        os.makedirs(CONFIG_DIR, exist_ok=True)

        if DESKTOP_DRIVES_COMPAT_CONFIG:
            self._read_file(DESKTOP_DRIVES_COMPAT_CONFIG)
        self._read_file(DESKTOP_DRIVES_CONFIG)

        if not os.path.exists(DESKTOP_DRIVES_CONFIG):
            self.save()
        return self.data

    def save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.config = configparser.ConfigParser()
        self.config.optionxform = str
        self.config[self.SECTION] = self.data
        with open(DESKTOP_DRIVES_CONFIG, 'w', encoding='utf-8') as fh:
            self.config.write(fh)

        if DESKTOP_DRIVES_COMPAT_CONFIG:
            try:
                with open(DESKTOP_DRIVES_COMPAT_CONFIG, 'w', encoding='utf-8') as fh:
                    self.config.write(fh)
            except Exception:
                pass

    def update(self, mapping):
        for key, value in mapping.items():
            canonical = self.LEGACY_MAP.get(key, key)
            self.data[canonical] = str(value)
        self.save()

    def get(self, key, fallback=None):
        canonical = self.LEGACY_MAP.get(key, key)
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
