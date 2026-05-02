# EssoraFM - Theme loader
# Author: josejp2424 and Nilsonmorales - GPL-3.0
"""Carga temas desde /usr/local/essorafm/theme/*.theme.

Cada .theme es un archivo INI con secciones [Theme] (metadatos con i18n al
estilo de los .desktop) y [CSS] (código GTK CSS bajo la clave Code=).

Los IDs 'default' y 'gtk_system' están reservados y se manejan
internamente en la ventana; este loader los ignora si los encuentra como
archivo.
"""

import configparser
import os

from core.i18n import LANG


THEME_DIR = '/usr/local/essorafm/theme'

RESERVED_IDS = {'default', 'gtk_system'}


def _localized(section, key, lang):
    """Devuelve section[key[lang]] si existe, si no section[key]."""
    localized_key = f'{key}[{lang}]'
    if localized_key in section:
        return section[localized_key].strip()
    if key in section:
        return section[key].strip()
    return ''


def list_themes():
    """Devuelve la lista de temas instalados como lista de dicts:
    [{'id': str, 'name': str, 'description': str, 'emoji': str,
      'author': str, 'version': str, 'css': str, 'path': str}, ...]

    Los nombres y descripciones vienen en el idioma activo (LANG) con
    fallback al genérico.
    """
    themes = []
    if not os.path.isdir(THEME_DIR):
        return themes

    for fname in sorted(os.listdir(THEME_DIR)):
        if not fname.endswith('.theme'):
            continue
        path = os.path.join(THEME_DIR, fname)
        try:
            theme = _load_theme_file(path)
        except Exception:
            continue
        if theme and theme['id'] not in RESERVED_IDS:
            themes.append(theme)

    return themes


def get_theme(theme_id):
    """Devuelve el tema con ese ID, o None si no existe."""
    for t in list_themes():
        if t['id'] == theme_id:
            return t
    return None


def _load_theme_file(path):
    cp = configparser.ConfigParser(interpolation=None)
    cp.read(path, encoding='utf-8')

    if not cp.has_section('Theme'):
        return None

    theme_section = cp['Theme']
    theme_id = theme_section.get('Id', '').strip()
    if not theme_id:
        return None

    name = _localized(theme_section, 'Name', LANG) or theme_id
    description = _localized(theme_section, 'Description', LANG)

    css = ''
    if cp.has_section('CSS'):
        css = cp['CSS'].get('Code', '').strip()

    return {
        'id': theme_id,
        'name': name,
        'description': description,
        'emoji': theme_section.get('Emoji', '').strip(),
        'author': theme_section.get('Author', '').strip(),
        'version': theme_section.get('Version', '').strip(),
        'css': css,
        'path': path,
    }
