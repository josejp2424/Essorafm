# EssoraFM
# Author: josejp2424 and Nilsonmorales - GPL-3.0
import os
import gi

gi.require_version('Gio', '2.0')
from gi.repository import Gio

from core.privilege import is_permission_error, mkdir_privileged


ATTRIBUTES = ','.join([
    'standard::name',
    'standard::display-name',
    'standard::type',
    'standard::size',
    'standard::content-type',
    'standard::icon',
    'time::modified',
])


class FileSystemService:
    def list_directory(self, path, show_hidden=False):
        gio_file = Gio.File.new_for_path(path)
        result = []
        enumerator = gio_file.enumerate_children(ATTRIBUTES, Gio.FileQueryInfoFlags.NONE, None)
        try:
            while True:
                info = enumerator.next_file(None)
                if info is None:
                    break
                name = info.get_name()
                if not show_hidden and name.startswith('.'):
                    continue
                child = gio_file.get_child(name)
                child_path = child.get_path()
                kind = info.get_file_type()
                is_dir = kind == Gio.FileType.DIRECTORY
                size = info.get_size() if not is_dir else 0
                modified = info.get_modification_date_time()
                modified_txt = modified.format('%Y-%m-%d %H:%M') if modified else ''
                mtime = 0
                try:
                    dt = info.get_modification_date_time()
                    if dt:
                        mtime = dt.to_unix()
                except Exception:
                    pass
                result.append({
                    'name': info.get_display_name() or name,
                    'real_name': name,
                    'path': child_path,
                    'gio_file': child,
                    'file_info': info,
                    'is_dir': is_dir,
                    'size': size,
                    'size_bytes': size,
                    'mtime': mtime,
                    'size_text': self.human_size(size) if not is_dir else '',
                    'modified_text': modified_txt,
                    'content_type': info.get_content_type() or '',
                })
        finally:
            enumerator.close(None)
        return result

    def create_folder(self, base_path, name):
        target = os.path.join(base_path, name)
        try:
            os.makedirs(target, exist_ok=False)
        except Exception as exc:
            if is_permission_error(exc):
                if os.path.exists(target):
                    raise FileExistsError(target)
                mkdir_privileged(target)
            else:
                raise
        return target

    def human_size(self, size):
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        value = float(size)
        for unit in units:
            if value < 1024.0 or unit == units[-1]:
                if unit == 'B':
                    return f'{int(value)} {unit}'
                return f'{value:.1f} {unit}'
            value /= 1024.0

    def same_filesystem(self, src, dst):
        try:
            return os.stat(src).st_dev == os.stat(dst).st_dev
        except FileNotFoundError:
            parent = os.path.dirname(dst) or '/'
            try:
                return os.stat(src).st_dev == os.stat(parent).st_dev
            except FileNotFoundError:
                return False
