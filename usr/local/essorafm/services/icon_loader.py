# EssoraFM
# Author: josejp2424 and Nilsonmorales - GPL-3.0
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Gio, GdkPixbuf


class IconLoader:
    def __init__(self, size: int = 24):
        self.size = size
        self.theme = Gtk.IconTheme.get_default()

    def _load_from_gicon(self, gicon, size=None):
        size = size or self.size
        if not gicon:
            return self.folder_icon(size)
        try:
            info = self.theme.lookup_by_gicon(gicon, size, 0)
            if info:
                return info.load_icon()
        except Exception:
            pass
        return self.folder_icon(size)

    def folder_icon(self, size=None):
        size = size or self.size
        for name in ('folder', 'inode-directory', 'text-x-generic'):
            try:
                return self.theme.load_icon(name, size, 0)
            except Exception:
                continue
        return None

    def mount_icon(self, size=None):
        size = size or self.size
        for name in ('drive-harddisk', 'drive-removable-media', 'media-flash'):
            try:
                return self.theme.load_icon(name, size, 0)
            except Exception:
                continue
        return self.folder_icon(size)

    def file_icon(self, gio_file, file_info=None, size=None):
        size = size or self.size
        try:
            if file_info is None:
                file_info = gio_file.query_info('standard::icon', 0, None)
            return self._load_from_gicon(file_info.get_icon(), size)
        except Exception:
            return self.folder_icon(size)

    def pixbuf_from_path(self, path, size=None):
        size = size or self.size
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
        except Exception:
            return None
