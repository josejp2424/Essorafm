# EssoraFM
# Author: josejp2424 - GPL-3.0
import os
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from core.i18n import tr


class PathBar(Gtk.Box):
    """Barra de dirección + búsqueda unificada en una sola línea.

    Layout:
      [Inicio] [entry de ruta──────────────] [🔍 campo de búsqueda] [✕]
    """

    def __init__(self, on_activate, on_search_changed=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.on_activate        = on_activate
        self.on_search_changed  = on_search_changed
        self._search_visible    = False

        # ── Botón Inicio ──────────────────────────────────────────────
        home_btn = Gtk.Button()
        home_btn.get_style_context().add_class('essorafm-toolbutton')
        home_btn.set_tooltip_text(tr('home_folder'))
        home_btn.add(Gtk.Image.new_from_icon_name('go-home-symbolic', Gtk.IconSize.MENU))
        home_btn.connect('clicked', lambda _: self.on_activate(os.path.expanduser('~')))
        self.pack_start(home_btn, False, False, 0)

        # ── Entrada de ruta ───────────────────────────────────────────
        self.entry = Gtk.Entry()
        self.entry.get_style_context().add_class('essorafm-pathbar')
        self.entry.set_hexpand(True)
        self.entry.connect('activate', self._emit_activate)
        self.pack_start(self.entry, True, True, 0)

        # ── Separador visual ─────────────────────────────────────────
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.set_margin_start(2)
        sep.set_margin_end(2)
        self.pack_start(sep, False, False, 0)

        # ── Campo de búsqueda (inline) ────────────────────────────────
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(tr('search_placeholder'))
        self.search_entry.set_width_chars(18)
        self.search_entry.connect('search-changed', self._on_search_changed)
        self.search_entry.connect('key-press-event', self._on_search_key)
        self.pack_start(self.search_entry, False, False, 0)

        # ── Botón limpiar búsqueda ────────────────────────────────────
        self.clear_btn = Gtk.Button()
        self.clear_btn.get_style_context().add_class('essorafm-toolbutton')
        self.clear_btn.set_tooltip_text(tr('clear_search'))
        self.clear_btn.add(Gtk.Image.new_from_icon_name('edit-clear-symbolic', Gtk.IconSize.MENU))
        self.clear_btn.connect('clicked', self._on_clear_search)
        self.clear_btn.set_no_show_all(True)
        self.clear_btn.hide()
        self.pack_start(self.clear_btn, False, False, 0)

    # ── Ruta ──────────────────────────────────────────────────────────

    def set_path(self, path):
        self.entry.set_text(path or '')

    def _emit_activate(self, entry):
        path = entry.get_text().strip()
        if path:
            self.on_activate(path)

    # ── Búsqueda ──────────────────────────────────────────────────────

    def _on_search_changed(self, entry):
        text = entry.get_text()
        # Mostrar/ocultar botón de limpiar
        if text:
            self.clear_btn.show()
        else:
            self.clear_btn.hide()
        if self.on_search_changed:
            self.on_search_changed(text)

    def _on_search_key(self, widget, event):
        from gi.repository import Gdk
        if event.keyval == Gdk.KEY_Escape:
            self._on_clear_search(None)
            return True
        return False

    def _on_clear_search(self, _btn):
        self.search_entry.set_text('')
        self.clear_btn.hide()
        if self.on_search_changed:
            self.on_search_changed('')

    def get_search_text(self):
        return self.search_entry.get_text()
