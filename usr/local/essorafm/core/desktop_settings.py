# EssoraFM
# Author: josejp2424 and Nilsonmorales - GPL-3.0

from core.settings import CONFIG_FILE
from core.settings_manager import SettingsManager, ESSORAFM_MOUNT_ACTION, ESSORAFM_UMOUNT_ACTION

DESKTOP_DRIVES_CONFIG = CONFIG_FILE
DESKTOP_DRIVES_COMPAT_CONFIG = None


class DesktopDriveSettings:
    """Compatibility wrapper for the EssoraFM internal desktop engine.

    Older code used names like Enabled, ShowInternal or IconSize.  This wrapper
    maps those names to ~/.config/essorafm/config.ini so the rest of EssoraFM can
    stay stable while desktop-drive-icons is removed completely.
    """

    SECTION = 'Main'
    EXTRA_DEFAULTS = {
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
    }
    DEFAULTS = dict(SettingsManager.DEFAULTS, **EXTRA_DEFAULTS)

    LEGACY_MAP = {
        'Enabled': 'desktop_drive_icons',
        'enabled': 'desktop_drive_icons',
        'UseExternalDriveIcons': 'desktop_drive_icons',
        'use_external_drive_icons': 'desktop_drive_icons',
        'DesktopDriveIcons': 'desktop_drive_icons',
        'desktop_drive_icons_enabled': 'desktop_drive_icons',
        'ShowDriveIcons': 'desktop_drive_icons',
        'show_drive_icons': 'desktop_drive_icons',

        'IconSize': 'desktop_drive_icon_size',
        'ShowInternal': 'desktop_drive_show_internal',
        'show_internal': 'desktop_drive_show_internal',
        'ShowRemovable': 'desktop_drive_show_removable',
        'show_removable': 'desktop_drive_show_removable',
        'ShowNetwork': 'desktop_drive_show_network',
        'show_network': 'desktop_drive_show_network',

        'ShowLabels': 'ShowLabels',
        'ShowDesktopFiles': 'ShowDesktopFiles',
        'SpacingX': 'SpacingX',
        'SpacingY': 'SpacingY',
        'LabelWidth': 'LabelWidth',
        'OpenCommand': 'OpenCommand',
        'PymenuCommand': 'PymenuCommand',
        'Wallpaper': 'Wallpaper',
        'WallpaperMode': 'WallpaperMode',
        'WallpaperDirectory': 'WallpaperDirectory',
        'XPos': 'XPos',
        'YPos': 'YPos',
        'XOffset': 'XOffset',
        'YOffset': 'YOffset',
        'NLines': 'NLines',
        'ShowFrame': 'ShowFrame',
        'Vertical': 'Vertical',
        'ReversePack': 'ReversePack',
        'MountAction': 'MountAction',
        'UMountAction': 'UMountAction',
        'DrawShadow': 'DrawShadow',
        'FontColor': 'FontColor',
        'ShadowColor': 'ShadowColor',
    }

    LOCKED_VALUES = {
        'MountAction': ESSORAFM_MOUNT_ACTION,
        'UMountAction': ESSORAFM_UMOUNT_ACTION,
    }

    def __init__(self):
        self.manager = SettingsManager()
        self.data = self.manager.data

    def _canonical_key(self, key):
        return self.LEGACY_MAP.get(key, key)

    def load(self):
        self.manager.load()
        self.data = dict(self.EXTRA_DEFAULTS)
        self.data.update(self.manager.data)
        return self.data

    def save(self):
        self.manager.save()
        self.data = dict(self.EXTRA_DEFAULTS)
        self.data.update(self.manager.data)

    def update(self, mapping):
        normalized = {}
        for key, value in mapping.items():
            canonical = self._canonical_key(key)
            if canonical in self.LOCKED_VALUES:
                normalized[canonical] = self.LOCKED_VALUES[canonical]
            else:
                normalized[canonical] = value
        self.manager.update(normalized)
        self.data = dict(self.EXTRA_DEFAULTS)
        self.data.update(self.manager.data)

    def get(self, key, fallback=None):
        canonical = self._canonical_key(key)
        if canonical in self.manager.data:
            return self.manager.get(canonical, fallback)
        return self.EXTRA_DEFAULTS.get(canonical, fallback)

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
