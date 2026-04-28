# EssoraFM
# Author: josejp2424 - GPL-3.0
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Pango

from app.fileview import FileView
from core.i18n import tr


class Tabs(Gtk.Notebook):
    def __init__(self, show_message, on_current_view_changed=None, settings_manager=None):
        super().__init__()
        self.get_style_context().add_class('essorafm-tabs')
        self.set_scrollable(True)
        self.show_message = show_message
        self.on_current_view_changed = on_current_view_changed
        self.settings_manager = settings_manager
        self.connect('switch-page', self._on_switch_page)

    def add_tab(self, path, switch=True):
        file_view = FileView(self._on_view_path_changed, self.show_message, self.settings_manager)
        file_view.load_path(path, add_to_history=False)
        tab_label_box = self._make_tab_label(file_view)
        page_num = self.append_page(file_view, tab_label_box)
        self.set_tab_reorderable(file_view, True)
        file_view.show_all()
        if switch:
            self.set_current_page(page_num)
        if self.on_current_view_changed:
            self.on_current_view_changed()
        return file_view

    def _make_tab_label(self, file_view):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        box.get_style_context().add_class('essorafm-tab-label')
        label = Gtk.Label(label=file_view.current_path.rstrip('/').split('/')[-1] or '/')
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(16)
        box.pack_start(label, True, True, 0)

        close_btn = Gtk.Button()
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.get_style_context().add_class('essorafm-tab-close')
        close_btn.set_focus_on_click(False)
        close_btn.add(Gtk.Image.new_from_icon_name('window-close-symbolic', Gtk.IconSize.MENU))
        close_btn.set_tooltip_text(tr('close_tab'))
        close_btn.connect('clicked', lambda *_: self.close_tab(file_view))
        box.pack_start(close_btn, False, False, 0)

        box.show_all()
        box._title_label = label
        return box

    def close_tab(self, file_view):
        if self.get_n_pages() <= 1:
            return
        page_num = self.page_num(file_view)
        if page_num != -1:
            self.remove_page(page_num)
            if self.on_current_view_changed:
                self.on_current_view_changed()

    def current_view(self):
        return self.get_nth_page(self.get_current_page())

    def apply_preferences_all(self):
        page_count = self.get_n_pages()
        for idx in range(page_count):
            view = self.get_nth_page(idx)
            if view:
                view.apply_preferences()
                view.refresh()
        if self.on_current_view_changed:
            self.on_current_view_changed()

    def _on_view_path_changed(self, path):
        view = self.current_view()
        if view is None:
            return
        tab_box = self.get_tab_label(view)
        if tab_box and hasattr(tab_box, '_title_label'):
            tab_box._title_label.set_text(path.rstrip('/').split('/')[-1] or '/')
        if self.on_current_view_changed:
            self.on_current_view_changed()

    def _on_switch_page(self, *_args):
        if self.on_current_view_changed:
            self.on_current_view_changed()
