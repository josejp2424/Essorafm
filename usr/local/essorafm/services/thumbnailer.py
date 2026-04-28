# EssoraFM
# Author: josejp2424 - GPL-3.0
import hashlib
import os
import shutil
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET

import gi

gi.require_version('GdkPixbuf', '2.0')
from gi.repository import GdkPixbuf, Gio

CACHE_DIR = os.path.join(os.path.expanduser('~'), '.cache', 'essorafm', 'thumbnails', 'normal')
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff', '.tif', '.svg'}
PDF_EXTS = {'.pdf'}
TXT_EXTS = {'.txt', '.log', '.md', '.conf', '.cfg', '.ini', '.desktop', '.sh', '.py', '.c', '.h', '.cpp', '.json', '.xml', '.css'}
EPUB_EXTS = {'.epub'}


class Thumbnailer:
    """Generador de miniaturas Nivel A para EssoraFM.

    Nivel A significa: rápido, simple y seguro. No intenta renderizar documentos
    completos; solo genera una miniatura básica para imágenes, PDF, TXT y ePub.
    """

    def __init__(self, icon_loader, enabled=True):
        self.icon_loader = icon_loader
        self.enabled = enabled
        os.makedirs(CACHE_DIR, exist_ok=True)

    def thumbnail_for(self, path, gio_file=None, file_info=None, size=64):
        if not self.enabled or not os.path.isfile(path):
            return self._fallback(gio_file, file_info, size)
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in IMAGE_EXTS:
                pix = self._image_thumb(path, size)
            elif ext in PDF_EXTS:
                pix = self._pdf_thumb(path, size)
            elif ext in TXT_EXTS:
                pix = self._text_thumb(path, size)
            elif ext in EPUB_EXTS:
                pix = self._epub_thumb(path, size)
            else:
                pix = None
            return pix or self._fallback(gio_file, file_info, size)
        except Exception:
            return self._fallback(gio_file, file_info, size)

    def _fallback(self, gio_file, file_info, size):
        return self.icon_loader.file_icon(gio_file, file_info, size)

    def _cache_path(self, path, size, suffix='png'):
        try:
            st = os.stat(path)
            key = f'{path}|{st.st_mtime_ns}|{st.st_size}|{size}'
        except Exception:
            key = f'{path}|{size}'
        digest = hashlib.sha256(key.encode('utf-8', 'replace')).hexdigest()
        return os.path.join(CACHE_DIR, f'{digest}.{suffix}')

    def _load_cached(self, cache_path, size):
        if os.path.exists(cache_path):
            try:
                return GdkPixbuf.Pixbuf.new_from_file_at_scale(cache_path, size, size, True)
            except Exception:
                return None
        return None

    def _save_pixbuf(self, pixbuf, cache_path):
        try:
            pixbuf.savev(cache_path, 'png', [], [])
        except Exception:
            pass
        return pixbuf

    def _image_thumb(self, path, size):
        cache = self._cache_path(path, size)
        pix = self._load_cached(cache, size)
        if pix:
            return pix
        pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
        return self._save_pixbuf(pix, cache)

    def _pdf_thumb(self, path, size):
        cache = self._cache_path(path, size)
        pix = self._load_cached(cache, size)
        if pix:
            return pix
        pdftoppm = shutil.which('pdftoppm')
        if not pdftoppm:
            return None
        with tempfile.TemporaryDirectory(prefix='essorafm-pdf-') as tmp:
            out_prefix = os.path.join(tmp, 'page')
            cmd = [pdftoppm, '-f', '1', '-singlefile', '-png', '-scale-to', str(max(size, 96)), path, out_prefix]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8, check=False)
            png = out_prefix + '.png'
            if os.path.exists(png):
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(png, size, size, True)
                return self._save_pixbuf(pix, cache)
        return None

    def _text_thumb(self, path, size):
        cache = self._cache_path(path, size)
        pix = self._load_cached(cache, size)
        if pix:
            return pix
        try:
            import cairo
        except Exception:
            return None
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                lines = [line.rstrip('\n')[:28] for line in fh.readlines()[:8]]
        except Exception:
            lines = []
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        ctx = cairo.Context(surface)
        ctx.set_source_rgb(0.98, 0.98, 0.96)
        ctx.paint()
        ctx.set_source_rgb(0.72, 0.72, 0.68)
        ctx.rectangle(1, 1, size - 2, size - 2)
        ctx.stroke()
        ctx.set_source_rgb(0.12, 0.12, 0.12)
        ctx.select_font_face('Sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(max(5, int(size / 10)))
        y = max(10, int(size / 6))
        for line in lines:
            ctx.move_to(5, y)
            ctx.show_text(line)
            y += max(7, int(size / 9))
            if y > size - 5:
                break
        surface.write_to_png(cache)
        return GdkPixbuf.Pixbuf.new_from_file_at_scale(cache, size, size, True)

    def _epub_thumb(self, path, size):
        cache = self._cache_path(path, size)
        pix = self._load_cached(cache, size)
        if pix:
            return pix
        cover_data = self._extract_epub_cover(path)
        if not cover_data:
            return None
        with tempfile.NamedTemporaryFile(prefix='essorafm-epub-cover-', suffix='.img', delete=False) as fh:
            tmpname = fh.name
            fh.write(cover_data)
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(tmpname, size, size, True)
            return self._save_pixbuf(pix, cache)
        finally:
            try:
                os.unlink(tmpname)
            except Exception:
                pass

    def _extract_epub_cover(self, path):
        with zipfile.ZipFile(path, 'r') as zf:
            names = zf.namelist()
            for name in names:
                low = name.lower()
                if 'cover' in low and low.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    return zf.read(name)
            try:
                container = ET.fromstring(zf.read('META-INF/container.xml'))
                rootfile = container.find('.//{*}rootfile')
                opf_path = rootfile.attrib.get('full-path') if rootfile is not None else None
            except Exception:
                opf_path = None
            if not opf_path or opf_path not in names:
                return None
            opf_dir = os.path.dirname(opf_path)
            opf = ET.fromstring(zf.read(opf_path))
            cover_id = None
            for meta in opf.findall('.//{*}meta'):
                if meta.attrib.get('name') == 'cover':
                    cover_id = meta.attrib.get('content')
                    break
            if cover_id:
                for item in opf.findall('.//{*}item'):
                    if item.attrib.get('id') == cover_id:
                        href = item.attrib.get('href')
                        if href:
                            full = os.path.normpath(os.path.join(opf_dir, href)).replace('\\', '/')
                            if full in names:
                                return zf.read(full)
        return None
