# EssoraFM
# Author: josejp2424 - GPL-3.0
import configparser
import datetime as dt
import os
import shutil
import urllib.parse

from core.settings import TRASH_DIR, TRASH_FILES_DIR, TRASH_INFO_DIR
from core.privilege import is_permission_error, rm_privileged, mv_privileged


class TrashService:
    def __init__(self):
        os.makedirs(TRASH_FILES_DIR, exist_ok=True)
        os.makedirs(TRASH_INFO_DIR, exist_ok=True)

    def ensure(self):
        os.makedirs(TRASH_FILES_DIR, exist_ok=True)
        os.makedirs(TRASH_INFO_DIR, exist_ok=True)

    def trash_path(self):
        self.ensure()
        return TRASH_FILES_DIR

    def is_in_trash(self, path):
        real = os.path.realpath(path)
        return real.startswith(os.path.realpath(TRASH_FILES_DIR) + os.sep)

    def move_to_trash(self, paths):
        self.ensure()
        for src in paths:
            if not os.path.exists(src):
                continue
            name = os.path.basename(os.path.normpath(src))
            dst = self._unique_path(os.path.join(TRASH_FILES_DIR, name))
            try:
                shutil.move(src, dst)
            except Exception as exc:
                if is_permission_error(exc):
                    mv_privileged(src, dst)
                else:
                    raise
            self._write_trashinfo(dst, src)

    def restore_from_trash(self, path):
        name = os.path.basename(path)
        info_path = os.path.join(TRASH_INFO_DIR, f'{name}.trashinfo')
        if not os.path.exists(info_path):
            raise FileNotFoundError('No se encontró la información de restauración')
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(info_path, encoding='utf-8')
        original = urllib.parse.unquote(parser['Trash Info'].get('Path', ''))
        if not original:
            raise RuntimeError('No se pudo leer la ruta original')
        target = self._unique_path(original) if os.path.exists(original) else original
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            shutil.move(path, target)
        except Exception as exc:
            if is_permission_error(exc):
                mv_privileged(path, target)
            else:
                raise
        try:
            os.remove(info_path)
        except OSError:
            pass
        return target

    def delete_permanently(self, paths):
        escalated = []
        for path in paths:
            try:
                if os.path.isdir(path) and not os.path.islink(path):
                    shutil.rmtree(path)
                elif os.path.exists(path):
                    os.remove(path)
            except Exception as exc:
                if is_permission_error(exc):
                    escalated.append(path)
                else:
                    raise
            if self.is_in_trash(path):
                info_path = os.path.join(TRASH_INFO_DIR, f"{os.path.basename(path)}.trashinfo")
                if os.path.exists(info_path):
                    try:
                        os.remove(info_path)
                    except PermissionError:
                        escalated.append(info_path)
        if escalated:
            rm_privileged(escalated)

    def empty_trash(self):
        self.delete_permanently([os.path.join(TRASH_FILES_DIR, name) for name in os.listdir(TRASH_FILES_DIR)])

    def _unique_path(self, path):
        base_dir = os.path.dirname(path)
        filename = os.path.basename(path)
        stem, ext = os.path.splitext(filename)
        counter = 1
        candidate = path
        while os.path.exists(candidate):
            candidate = os.path.join(base_dir, f'{stem}_{counter}{ext}')
            counter += 1
        return candidate

    def _write_trashinfo(self, trash_file, original_path):
        self.ensure()
        parser = configparser.ConfigParser(interpolation=None)
        parser['Trash Info'] = {
            'Path': urllib.parse.quote(original_path),
            'DeletionDate': dt.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        }
        info_path = os.path.join(TRASH_INFO_DIR, f"{os.path.basename(trash_file)}.trashinfo")
        with open(info_path, 'w', encoding='utf-8') as fh:
            parser.write(fh)
