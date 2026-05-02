# EssoraFM
# Author: josejp2424 and Nilsonmorales - GPL-3.0
import os
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Pango

from app.fileview import FileView
from core.i18n import tr
from core.xdg import xdg_dir, XDG


class Tabs(Gtk.Notebook):
    def __init__(self, show_message, on_current_view_changed=None, settings_manager=None):
        super().__init__()
        self.get_style_context().add_class('essorafm-tabs')
        self.set_scrollable(True)
        self.set_show_tabs(True)
        self.set_show_border(False)
        
        self.show_message = show_message
        self.on_current_view_changed = on_current_view_changed
        self.settings_manager = settings_manager
        self.connect('switch-page', self._on_switch_page)

    def _get_folder_icon(self, path):
        """
        Retorna el nombre del ícono apropiado según el tipo de carpeta.

        Las rutas XDG se resuelven dinámicamente vía core.xdg para que
        funcione con cualquier idioma del sistema (Descargas, Téléchargements,
        ダウンロード, etc.) — no hay que mantener listas hardcoded.
        """

        special_icons = {
            os.path.expanduser('~'):       'user-home-symbolic',
            xdg_dir(XDG.DESKTOP):          'user-desktop-symbolic',
            xdg_dir(XDG.DOCUMENTS):        'folder-documents-symbolic',
            xdg_dir(XDG.DOWNLOAD):         'folder-download-symbolic',
            xdg_dir(XDG.MUSIC):            'folder-music-symbolic',
            xdg_dir(XDG.PICTURES):         'folder-pictures-symbolic',
            xdg_dir(XDG.VIDEOS):           'folder-videos-symbolic',
            '/':                           'drive-harddisk-symbolic',
            '/usr':                        'folder-system-symbolic',
            '/etc':                        'folder-system-symbolic',
            '/var':                        'folder-system-symbolic',
            '/tmp':                        'folder-temp-symbolic',
        }


        try:
            realpath = os.path.realpath(path)
            for special_path, icon in special_icons.items():
                if special_path and os.path.realpath(special_path) == realpath:
                    return icon
        except Exception:
            pass

        return 'folder-symbolic'

    def _get_tab_display_name(self, path):
        """
        Obtiene el nombre para mostrar en la pestaña - versión compacta.
        """

        if path == '/' or path == '':
            return "/"
        

        try:
            home = os.path.expanduser('~')
            if os.path.realpath(path) == os.path.realpath(home):
                return "~"
        except Exception:
            pass
        

        name = os.path.basename(path.rstrip('/'))
        

        if not name:
            name = os.path.basename(os.path.dirname(path.rstrip('/')))
        

        if len(name) > 15:
            name = name[:12] + "..."
        
        return name or path

    def add_tab(self, path, switch=True):
        file_view = FileView(self._on_view_path_changed, self.show_message, self.settings_manager)
        file_view.load_path(path, add_to_history=False)
        tab_label_box = self._make_tab_label(file_view)
        page_num = self.append_page(file_view, tab_label_box)
        self.set_tab_reorderable(file_view, True)
        self.set_tab_detachable(file_view, True)
        file_view.show_all()
        if switch:
            self.set_current_page(page_num)
        if self.on_current_view_changed:
            self.on_current_view_changed()
        return file_view

    def _make_tab_label(self, file_view):
        """
        Crea un widget de pestaña compacto con ícono, texto y botón de cerrar.
        """
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.get_style_context().add_class('essorafm-tab-label')
        
        icon = Gtk.Image.new_from_icon_name(
            self._get_folder_icon(file_view.current_path),
            Gtk.IconSize.MENU
        )
        icon.set_pixel_size(14)
        box.pack_start(icon, False, False, 0)
        
        display_name = self._get_tab_display_name(file_view.current_path)
        label = Gtk.Label(label=display_name)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(15)
        label.set_tooltip_text(file_view.current_path)
        label.set_xalign(0)
        box.pack_start(label, True, True, 0)
        
        close_btn = Gtk.Button()
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.get_style_context().add_class('essorafm-tab-close')
        close_btn.set_focus_on_click(False)
        close_btn.set_tooltip_text(tr('close_tab'))
        close_btn.set_size_request(20, 20)
        
        close_icon = Gtk.Image.new_from_icon_name('window-close-symbolic', Gtk.IconSize.MENU)
        close_icon.set_pixel_size(12)
        close_btn.add(close_icon)
        close_btn.connect('clicked', lambda *_: self.close_tab(file_view))
        
        box.pack_start(close_btn, False, False, 0)
        
        box._title_label = label
        box._title_icon = icon
        box._current_path = file_view.current_path
        
        box.show_all()
        return box

    def update_tab_label(self, file_view, new_path):
        """Actualiza el texto e ícono de una pestaña."""
        tab_box = self.get_tab_label(file_view)
        if tab_box and hasattr(tab_box, '_title_label'):
            new_display_name = self._get_tab_display_name(new_path)
            tab_box._title_label.set_text(new_display_name)
            tab_box._title_label.set_tooltip_text(new_path)
            tab_box._current_path = new_path
            
            new_icon = self._get_folder_icon(new_path)
            tab_box._title_icon.set_from_icon_name(new_icon, Gtk.IconSize.MENU)
            tab_box._title_icon.set_pixel_size(14)

    def close_tab(self, file_view):
        if self.get_n_pages() <= 1:
            if hasattr(self, 'show_message'):
                self.show_message(tr('cant_close_last_tab'))
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
        self.update_tab_label(view, path)
        if self.on_current_view_changed:
            self.on_current_view_changed()

    def _on_switch_page(self, notebook, page, page_num):
        if self.on_current_view_changed:
            self.on_current_view_changed()

    def get_all_paths(self):
        paths = []
        for idx in range(self.get_n_pages()):
            view = self.get_nth_page(idx)
            if view and hasattr(view, 'current_path'):
                paths.append(view.current_path)
        return paths
