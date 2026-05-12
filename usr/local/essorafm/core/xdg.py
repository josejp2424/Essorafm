# EssoraFM - XDG user directories helper
# Author: josejp2424 and Nilsonmorales - GPL-3.0
"""Resuelve las carpetas estándar XDG (Desktop, Documents, Downloads, etc.)
respetando el idioma del usuario.

Lee de ~/.config/user-dirs.dirs vía GLib.get_user_special_dir(), que es la
fuente que mantiene el escritorio actualizada según la locale del usuario.
Si vos tenés ~/Descargas, devuelve eso; si un francés tiene ~/Téléchargements,
le devuelve eso; si un sistema sin XDG configurado deja todo en inglés, ese
es el valor que se devuelve.

Uso:
    from core.xdg import xdg_dir, XDG
    desktop = xdg_dir(XDG.DESKTOP)
    downloads = xdg_dir(XDG.DOWNLOAD)
"""

import os

import gi
gi.require_version('GLib', '2.0')
from gi.repository import GLib


class XDG:
    """Constantes para identificar cada directorio XDG estándar."""
    DESKTOP   = GLib.UserDirectory.DIRECTORY_DESKTOP
    DOCUMENTS = GLib.UserDirectory.DIRECTORY_DOCUMENTS
    DOWNLOAD  = GLib.UserDirectory.DIRECTORY_DOWNLOAD
    MUSIC     = GLib.UserDirectory.DIRECTORY_MUSIC
    PICTURES  = GLib.UserDirectory.DIRECTORY_PICTURES
    VIDEOS    = GLib.UserDirectory.DIRECTORY_VIDEOS
    PUBLIC_SHARE = GLib.UserDirectory.DIRECTORY_PUBLIC_SHARE
    TEMPLATES    = GLib.UserDirectory.DIRECTORY_TEMPLATES


_FALLBACKS = {
    XDG.DESKTOP:   'Desktop',
    XDG.DOCUMENTS: 'Documents',
    XDG.DOWNLOAD:  'Downloads',
    XDG.MUSIC:     'Music',
    XDG.PICTURES:  'Pictures',
    XDG.VIDEOS:    'Videos',
    XDG.PUBLIC_SHARE: 'Public',
    XDG.TEMPLATES:    'Templates',
}


def xdg_dir(directory):
    """Devuelve la ruta absoluta del directorio XDG indicado.

    Si user-dirs.dirs lo define, se respeta su valor (incluso si está en
    español, francés, japonés, etc.). Si no, cae al nombre genérico en
    inglés bajo $HOME.
    """
    path = GLib.get_user_special_dir(directory)
    if path:
        return path
    return os.path.join(os.path.expanduser('~'), _FALLBACKS.get(directory, ''))


def all_xdg_dirs():
    """Diccionario con todos los XDG dirs resueltos: { XDG.DESKTOP: '/home/user/Escritorio', ... }

    Útil para construir mapas de path -> icono sin tener que llamar
    xdg_dir() varias veces.
    """
    return {key: xdg_dir(key) for key in (
        XDG.DESKTOP, XDG.DOCUMENTS, XDG.DOWNLOAD,
        XDG.MUSIC, XDG.PICTURES, XDG.VIDEOS,
        XDG.PUBLIC_SHARE, XDG.TEMPLATES,
    )}
