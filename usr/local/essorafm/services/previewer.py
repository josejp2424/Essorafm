#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# EssoraFM preview helper
# Author: josejp2424

import os
import tempfile
import subprocess
import zipfile
from pathlib import Path

from gi.repository import GdkPixbuf

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".svg"}
TEXT_EXTS = {".txt", ".log", ".md", ".conf", ".ini", ".desktop", ".sh", ".py", ".c", ".h", ".cpp", ".json", ".xml", ".css"}
PDF_EXTS = {".pdf"}
EPUB_EXTS = {".epub"}

def is_previewable(path):
    ext = Path(path).suffix.lower()
    return ext in IMAGE_EXTS or ext in TEXT_EXTS or ext in PDF_EXTS or ext in EPUB_EXTS

def _scale_pixbuf(pixbuf, max_w=760, max_h=680):
    if not pixbuf:
        return None
    w = pixbuf.get_width()
    h = pixbuf.get_height()
    if w <= 0 or h <= 0:
        return pixbuf
    ratio = min(max_w / float(w), max_h / float(h), 1.0)
    nw = max(1, int(w * ratio))
    nh = max(1, int(h * ratio))
    if nw == w and nh == h:
        return pixbuf
    return pixbuf.scale_simple(nw, nh, GdkPixbuf.InterpType.BILINEAR)

def load_image_preview(path, max_w=None, max_h=None):
    """Carga el pixbuf original; PreviewPanel.DrawingArea escala dinamicamente."""
    try:
        return GdkPixbuf.Pixbuf.new_from_file(path)
    except Exception:
        return None

def load_pdf_preview(path, max_w=760, max_h=680):
    tmpdir = tempfile.mkdtemp(prefix="essorafm_pdf_preview_")
    outbase = os.path.join(tmpdir, "page")
    try:
        subprocess.run(
            ["pdftoppm", "-f", "1", "-singlefile", "-png", "-r", "110", path, outbase],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
            check=False,
        )
        img = outbase + ".png"
        if os.path.exists(img):
            return load_image_preview(img, max_w, max_h)
    except Exception:
        return None
    return None

def load_epub_cover(path, max_w=760, max_h=680):
    try:
        with zipfile.ZipFile(path, "r") as z:
            candidates = []
            for name in z.namelist():
                lname = name.lower()
                if lname.endswith((".jpg", ".jpeg", ".png", ".webp")):
                    score = 0
                    if "cover" in lname:
                        score += 10
                    if "title" in lname:
                        score += 3
                    candidates.append((score, name))
            if not candidates:
                return None
            candidates.sort(reverse=True)
            data = z.read(candidates[0][1])
            fd, temp_img = tempfile.mkstemp(prefix="essorafm_epub_cover_", suffix=Path(candidates[0][1]).suffix)
            os.close(fd)
            with open(temp_img, "wb") as f:
                f.write(data)
            return load_image_preview(temp_img, max_w, max_h)
    except Exception:
        return None

def read_text_preview(path, limit=5000):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = f.read(limit)
        if len(data) >= limit:
            data += "\n..."
        return data
    except Exception as e:
        return f"No se pudo leer el texto:\n{e}"

def get_preview(path, max_w=760, max_h=680):
    ext = Path(path).suffix.lower()
    if ext in IMAGE_EXTS:
        return ("image", load_image_preview(path, max_w, max_h))
    if ext in PDF_EXTS:
        return ("image", load_pdf_preview(path, max_w, max_h))
    if ext in EPUB_EXTS:
        cover = load_epub_cover(path, max_w, max_h)
        if cover:
            return ("image", cover)
        return ("text", "ePub sin portada disponible.")
    if ext in TEXT_EXTS:
        return ("text", read_text_preview(path))
    return ("text", "Sin vista previa disponible.")
