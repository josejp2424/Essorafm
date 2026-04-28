# EssoraFM
# Author: josejp2424 - GPL-3.0
import configparser
import os

from core.settings import (
    CONFIG_DIR,
    CONFIG_FILE,
    LEGACY_CONFIG_FILE,
    DEFAULT_ICON_SIZE,
    DEFAULT_LIST_ICON_SIZE,
    DEFAULT_SIDEBAR_ICON_SIZE,
    DEFAULT_VIEW_MODE,
)


class SettingsManager:
    DEFAULTS = {
        'view_mode': DEFAULT_VIEW_MODE,
        'icon_size': str(DEFAULT_ICON_SIZE),
        'list_icon_size': str(DEFAULT_LIST_ICON_SIZE),
        'sidebar_icon_size': str(DEFAULT_SIDEBAR_ICON_SIZE),
        'toolbar_icon_size': '20',  # NUEVO: tamaño de iconos del toolbar
        'show_hidden': 'false',
        'single_click': 'false',
        'show_thumbnails': 'true',
        'desktop_drive_icons': 'true',
        'desktop_drive_icon_size': '48',
        'desktop_drive_show_internal': 'true',
        'desktop_drive_show_removable': 'true',
        'desktop_drive_show_network': 'false',
        'window_width': '940',
        'window_height': '600',
        'sidebar_layout': 'classic',
        'preview_enabled': 'true',
        'toolbar_style': 'text_right',
        'sort_field': 'name',
        'sort_direction': 'asc',
    }

    def __init__(self):
        self.config = configparser.ConfigParser(strict=False)
        self.data = dict(self.DEFAULTS)
        self.load()

    def load(self):
        self.data = dict(self.DEFAULTS)
        config_path = CONFIG_FILE
        if os.path.exists(config_path):
            try:
                parser = configparser.ConfigParser(strict=False)
                parser.read(config_path, encoding='utf-8')
                if parser.has_section('Main'):
                    for key, value in parser['Main'].items():
                        if key in self.DEFAULTS:
                            self.data[key] = value
            except Exception as e:
                print(f"Error loading config: {e}")
        if not os.path.exists(CONFIG_FILE):
            self.save()
        return self.data

    def save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.config = configparser.ConfigParser()
        self.config['Main'] = self.data
        with open(CONFIG_FILE, 'w', encoding='utf-8') as fh:
            self.config.write(fh)

    def get(self, key, fallback=None):
        return self.data.get(key, fallback)

    def get_bool(self, key, fallback=False):
        value = str(self.data.get(key, fallback)).strip().lower()
        return value in {'1', 'true', 'yes', 'on'}

    def get_int(self, key, fallback=0):
        try:
            return int(self.data.get(key, fallback))
        except (TypeError, ValueError):
            return fallback

    def set(self, key, value):
        self.data[key] = str(value)

    def update(self, mapping):
        for key, value in mapping.items():
            self.set(key, value)
        self.save()
