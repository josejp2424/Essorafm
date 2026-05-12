# EssoraFM
# Author: josejp2424 and Nilsonmorales - GPL-3.0
# -*- coding: utf-8 -*-
import os
from pathlib import Path
from gi.repository import Gtk, GLib, GdkPixbuf, Gdk
from services.previewer import get_preview, is_previewable
from core.i18n import tr


class PreviewPanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_margin_start(6)
        self.set_margin_end(6)
        self.set_margin_top(6)
        self.set_margin_bottom(6)

        self.current_path = None
        self._pending_id = None
        self._raw_pixbuf = None

        self.title = Gtk.Label(label=tr('preview'), xalign=0)
        self.title.set_margin_bottom(4)
        self.pack_start(self.title, False, False, 0)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)

        self.empty = Gtk.Label(label=tr('preview_empty'))
        self.empty.set_line_wrap(True)
        self.empty.set_xalign(0.5)
        self.empty.set_yalign(0.5)
        self.stack.add_named(self.empty, 'empty')

        self.drawing = Gtk.DrawingArea()
        self.drawing.set_hexpand(True)
        self.drawing.set_vexpand(True)
        self.drawing.connect('draw', self._on_draw)
        self.drawing.connect('size-allocate', lambda w, a: w.queue_draw())
        self.stack.add_named(self.drawing, 'image')

        self.text = Gtk.TextView()
        self.text.set_editable(False)
        self.text.set_cursor_visible(False)
        self.text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_scroll = Gtk.ScrolledWindow()
        text_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        text_scroll.set_hexpand(True)
        text_scroll.set_vexpand(True)
        text_scroll.add(self.text)
        self.stack.add_named(text_scroll, 'text')

        self.pack_start(self.stack, True, True, 0)
        self.stack.set_visible_child_name('empty')

    def _on_draw(self, widget, cr):
        """Dibuja la imagen escalada y centrada en el área disponible."""
        if self._raw_pixbuf is None:
            return False

        alloc = widget.get_allocation()
        panel_w = alloc.width
        panel_h = alloc.height
        if panel_w < 2 or panel_h < 2:
            return False

        img_w = self._raw_pixbuf.get_width()
        img_h = self._raw_pixbuf.get_height()
        if img_w <= 0 or img_h <= 0:
            return False

        scale = min(panel_w / img_w, panel_h / img_h)
        new_w = max(1, int(img_w * scale))
        new_h = max(1, int(img_h * scale))

        scaled = self._raw_pixbuf.scale_simple(new_w, new_h, GdkPixbuf.InterpType.BILINEAR)
        if scaled is None:
            return False

        x = (panel_w - new_w) // 2
        y = (panel_h - new_h) // 2

        Gdk.cairo_set_source_pixbuf(cr, scaled, x, y)
        cr.paint()
        return False

    def set_file(self, path):
        if not path or not os.path.isfile(path) or path == self.current_path:
            return
        self.current_path = path
        self.title.set_text(Path(path).name)
        if self._pending_id:
            GLib.source_remove(self._pending_id)
            self._pending_id = None
        self._pending_id = GLib.timeout_add(80, self._load, path)

    def _load(self, path):
        self._pending_id = None
        if path != self.current_path:
            return False
        if not is_previewable(path):
            self._raw_pixbuf = None
            self.text.get_buffer().set_text(tr('preview_unavailable'))
            self.stack.set_visible_child_name('text')
            return False
        kind, data = get_preview(path)
        if kind == 'image' and data is not None:
            self._raw_pixbuf = data
            self.drawing.queue_draw()
            self.stack.set_visible_child_name('image')
        else:
            self._raw_pixbuf = None
            self.text.get_buffer().set_text(
                data if isinstance(data, str) else tr('preview_unavailable'))
            self.stack.set_visible_child_name('text')
        return False
