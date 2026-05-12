# EssoraFM - Sidebar con secciones (Favoritos, Lugares, Dispositivos, Red)
# Author: josejp2424 and Nilsonmorales - GPL-3.0

import os
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib

from services.volumes import VolumeService
from services.icon_loader import IconLoader
from services.trash import TrashService
from services.network_bookmarks import NetworkBookmarkService
from services.favorites import FavoritesService
from app.network_dialog import NetworkConnectDialog
from core.i18n import tr
from core.xdg import xdg_dir, XDG


ESSORAFM_ICONS_DIR = '/usr/local/essorafm/ui/icons'


class Sidebar(Gtk.Box):
    COL_PIXBUF  = 0
    COL_NAME    = 1
    COL_PATH    = 2
    COL_KIND    = 3  
    COL_OBJECT  = 4   
    COL_ID      = 5

    def __init__(self, on_open_path, show_message,
                 on_about=None, on_preferences=None, settings_manager=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.get_style_context().add_class('essorafm-sidebar')
        self.on_open_path   = on_open_path
        self.show_message   = show_message
        self.on_about       = on_about
        self.on_preferences = on_preferences
        self.settings_manager = settings_manager

        self.volume_service  = VolumeService()
        self.trash           = TrashService()
        self.net_service     = NetworkBookmarkService()
        self.favorites       = FavoritesService()

        size = settings_manager.get_int('sidebar_icon_size', 20) if settings_manager else 20
        self.icon_loader = IconLoader(size)

        self.store = Gtk.TreeStore(GdkPixbuf.Pixbuf, str, str, str, object, str)
        self.tree  = Gtk.TreeView(model=self.store)
        self.tree.get_style_context().add_class('essorafm-sidebar-tree')
        self.tree.set_headers_visible(False)
        self.tree.connect('row-activated',    self._on_row_activated)
        self.tree.connect('button-press-event', self._on_button_press)

        column = Gtk.TreeViewColumn()
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column.set_fixed_width(188)

        self.renderer_pix = Gtk.CellRendererPixbuf()
        renderer_pix = self.renderer_pix
        renderer_pix.set_property('xpad', 2)
        self.renderer_txt = Gtk.CellRendererText()
        renderer_txt = self.renderer_txt
        renderer_txt.set_property('ellipsize', Pango.EllipsizeMode.END)
        renderer_txt.set_property('ellipsize-set', True)
        renderer_txt.set_property('max-width-chars', 18)
        renderer_txt.set_property('xpad', 4)

        column.pack_start(renderer_pix, False)
        column.pack_start(renderer_txt, True)
        column.add_attribute(renderer_pix, 'pixbuf', self.COL_PIXBUF)
        column.add_attribute(renderer_txt, 'text',   self.COL_NAME)

        column.set_cell_data_func(renderer_txt, self._cell_data_func_txt)
        column.set_cell_data_func(renderer_pix, self._cell_data_func_pix)

        self.tree.append_column(column)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_shadow_type(Gtk.ShadowType.NONE)
        scroll.get_style_context().add_class('essorafm-sidebar-scroll')
        scroll.add(self.tree)
        self.pack_start(scroll, True, True, 0)

        for sig in ('mount-added', 'mount-removed', 'volume-added',
                    'volume-removed', 'volume-changed', 'mount-changed'):
            self.volume_service.connect(sig, lambda *_: self.refresh())

        self.refresh()

    def _cell_data_func_txt(self, column, cell, model, it, data=None):
        kind = model.get_value(it, self.COL_KIND)
        if kind in ('section_favorites', 'section_places', 'section_devices', 'section_network'):
            cell.set_property('weight', Pango.Weight.BOLD)
            cell.set_property('foreground', '#888888')
            cell.set_property('ypad', 3)
        elif kind == 'separator':
            cell.set_property('foreground', '#333333')
            cell.set_property('ypad', 1)
        else:
            cell.set_property('weight', Pango.Weight.NORMAL)
            cell.set_property('foreground', None)
            cell.set_property('ypad', 2)

    def _cell_data_func_pix(self, column, cell, model, it, data=None):
        kind = model.get_value(it, self.COL_KIND)
        if kind == 'separator':
            cell.set_property('ypad', 1)
        elif kind in ('section_favorites', 'section_places', 'section_devices', 'section_network'):
            cell.set_property('ypad', 3)
        else:
            cell.set_property('ypad', 2)

    def apply_preferences(self):
        size = self.settings_manager.get_int('sidebar_icon_size', 20) if self.settings_manager else 20
        self.icon_loader = IconLoader(size)
        self.refresh()

    def refresh(self):
        self.store.clear()
        theme = Gtk.IconTheme.get_default()
        size  = self.settings_manager.get_int('sidebar_icon_size', 20) if self.settings_manager else 20
        home  = os.path.expanduser('~')

        fav_icon = self._load_essorafm_icon('favorite.svg', size) \
                   or self._load_icon(theme, 'starred', 'bookmark-new', 'folder', size)
        fav_section = self.store.append(None, [fav_icon, tr('quick_access'), '', 'section_favorites', None, None])
        
        favorites = self.favorites.list()
        if favorites:
            for fav in favorites:
                icon_name = fav.get('icon', 'starred')
                pix = self._load_icon(theme, icon_name, 'folder', size)
                self.store.append(fav_section, [pix, fav['name'], fav['path'], 'favorite', fav, None])
        else:
            self.store.append(fav_section, [None, tr('no_favorites_hint'), '', 'favorite_hint', None, None])
        
        self._add_separator()

        places_icon = self._load_icon(theme, 'folder', 'folder', size)
        places_section = self.store.append(None, [places_icon, tr('places'), '', 'section_places', None, None])

        static_places = [
            (tr('home_folder'),  home,                     'folder-home'),
            (tr('desktop'),      xdg_dir(XDG.DESKTOP),     'user-desktop'),
            (tr('documents'),    xdg_dir(XDG.DOCUMENTS),   'folder-documents'),
            (tr('downloads'),    xdg_dir(XDG.DOWNLOAD),    'folder-download'),
            (tr('filesystem'),   '/',                      'drive-harddisk'),
            (tr('trash'),        self.trash.trash_path(),  'user-trash'),
        ]
        for name, path, icon_name in static_places:
            if not os.path.exists(path):
                continue
            pix = self._load_icon(theme, icon_name, 'folder', size)
            self.store.append(places_section, [pix, name, path, 'place', None, None])

        self._add_separator()

        devices_icon = self._load_icon(theme, 'drive-multidisk', 'drive-harddisk', size)
        devices_section = self.store.append(None, [devices_icon, tr('devices'), '', 'section_devices', None, None])

        items = [item for item in self.volume_service.list_sidebar_items() if not item.get('hidden_sidebar')]
        mounted_items = []
        unmounted_items = []
        
        for item in items:
            if item.get('mounted', False) or item.get('kind') == 'mount':
                mounted_items.append(item)
            else:
                unmounted_items.append(item)
        
        for item in mounted_items:
            pix = self.icon_loader._load_from_gicon(item.get('icon'), size)
            self.store.append(devices_section, [pix, item['name'], item.get('path') or '',
                               item['kind'], item, None])
        
        for item in unmounted_items:
            pix = self.icon_loader._load_from_gicon(item.get('icon'), size)
            self.store.append(devices_section, [pix, item['name'], item.get('path') or '',
                               'volume_disabled', item, None])

        self._add_separator()

        net_icon = self._load_essorafm_icon('red.svg', size) \
                   or self._load_icon(theme, 'network-workgroup', 'network-server', 'folder', size)
        net_section = self.store.append(None, [net_icon, tr('network'), '', 'section_network', None, None])

        network_folders = self.net_service.list_network_folders()
        for nf in network_folders:
            pix = self._load_icon(theme, 'folder-remote', 'network-server', size)
            self.store.append(net_section, [pix, nf['name'], nf['path'], 'network_folder', nf, None])

        bookmarks = self.net_service.list()
        for bm in bookmarks:
            mounted = self.net_service.is_mounted(bm['uri'])
            icon_name = 'folder-remote-symbolic' if mounted else 'network-server-symbolic'
            pix = self._load_icon(theme, icon_name, 'network-server', size)
            label = bm['name']
            if mounted:
                label += ' ✓'
            path = self.net_service.mount_path(bm['uri']) if mounted else ''
            self.store.append(net_section, [pix, label, path, 'net_entry', bm, None])

        add_icon = self._load_icon(theme, 'list-add', 'list-add', size)
        self.store.append(net_section, [add_icon, tr('net_add_connection'), '', 'net_add', None, None])

        gh_icon = self._load_essorafm_icon('github.svg', size) \
                  or self._load_icon(theme, 'applications-development', 'system-software-install', size)
        self.store.append(net_section, [gh_icon, tr('github_entry'), '', 'github', None, None])

        self.tree.expand_all()

    def _load_essorafm_icon(self, filename, size):
        """Carga un icono SVG/PNG desde /usr/local/essorafm/ui/icons/."""
        path = os.path.join(ESSORAFM_ICONS_DIR, filename)
        if not os.path.exists(path):
            return None
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
        except Exception:
            return None

    def _load_icon(self, theme, *icon_names, default_size=20):
        names = list(icon_names)
        if names and isinstance(names[-1], int):
            default_size = names.pop()
        for icon_name in names:
            try:
                return theme.load_icon(icon_name, default_size, 0)
            except Exception:
                continue
        return self.icon_loader.folder_icon(default_size)

    def _add_separator(self):
        self.store.append(None, [None, '', '', 'separator', None, None])

    def _on_row_activated(self, tree, path, _column):
        model = tree.get_model()
        it    = model.get_iter(path)
        kind  = model.get_value(it, self.COL_KIND)
        tpath = model.get_value(it, self.COL_PATH)
        obj   = model.get_value(it, self.COL_OBJECT)

        if kind in ('section_favorites', 'section_places', 'section_devices', 'section_network'):
            if tree.row_expanded(path):
                tree.collapse_row(path)
            else:
                tree.expand_row(path, False)
            return

        if kind in ('place', 'mount', 'favorite', 'network_folder') and tpath:
            self.on_open_path(tpath)

        elif kind == 'volume_disabled' and obj:
            self.show_message(tr('mounting_volume'))
            self.volume_service.mount_item(obj, self._after_mount)

        elif kind == 'volume' and obj:
            self.show_message(tr('mounting_volume'))
            self.volume_service.mount_item(obj, self._after_mount)

        elif kind == 'net_entry' and obj:
            self._activate_net_entry(obj)

        elif kind == 'net_add':
            self._show_add_dialog()

        elif kind == 'github':
            self._launch_gitgui()

    def _activate_net_entry(self, bm):
        if self.net_service.is_mounted(bm['uri']):
            path = self.net_service.mount_path(bm['uri'])
            if path:
                self.on_open_path(path)
                return
        self._mount_bookmark(bm)

    def _mount_bookmark(self, bm):
        password = bm.get('password', '')
        if not password:
            password = self._ask_password(bm)
            if password is None:
                return 

        self.show_message(f"{tr('net_connecting')} {bm['name']}...")
        self.net_service.mount(bm, password=password,
                               callback=self._after_mount_net)

    def _ask_password(self, bm):
        parent = self.get_toplevel()
        dlg = Gtk.Dialog(title=tr('net_password'),
                         transient_for=parent, modal=True)
        dlg.set_default_size(320, -1)
        dlg.add_buttons(tr('cancel'), Gtk.ResponseType.CANCEL,
                        tr('connect'), Gtk.ResponseType.OK)
        dlg.set_default_response(Gtk.ResponseType.OK)

        box = dlg.get_content_area()
        box.set_margin_top(12); box.set_margin_bottom(8)
        box.set_margin_start(14); box.set_margin_end(14)
        box.set_spacing(8)

        box.add(Gtk.Label(label=f"{tr('net_password_for')} {bm['name']}:", xalign=0))
        entry = Gtk.Entry()
        entry.set_visibility(False)
        entry.set_activates_default(True)
        box.add(entry)
        dlg.show_all()

        resp = dlg.run()
        password = entry.get_text() if resp == Gtk.ResponseType.OK else None
        dlg.destroy()
        return password

    def _after_mount_net(self, ok, path_or_error):
        if ok:
            uri = None
            for bm in self.net_service.list():
                if self.net_service.is_mounted(bm['uri']):
                    self.net_service.update_mount_path(bm['uri'], path_or_error)
                    uri = bm['uri']
            self.refresh()
            if path_or_error and os.path.isdir(path_or_error):
                self.on_open_path(path_or_error)
            self.show_message(tr('net_connected'))
        else:
            self.show_message(f"{tr('net_error')}: {path_or_error}")
            self.refresh()

    def _show_add_dialog(self, bookmark=None):
        parent = self.get_toplevel()
        dlg = NetworkConnectDialog(parent, bookmark)
        resp = dlg.run()
        if resp == Gtk.ResponseType.OK:
            result = dlg.get_result()
            dlg.destroy()
            if result and result.get('uri', '').count('://') == 1:
                self.net_service.add(result['name'], result['uri'], result['username'])
                self.refresh()
                bm = {'name': result['name'], 'uri': result['uri'],
                      'username': result['username'], 'password': result['password']}
                self._mount_bookmark_direct(bm, result['password'])
            else:
                self.show_message(tr('net_invalid_uri'))
        else:
            dlg.destroy()

    def _mount_bookmark_direct(self, bm, password):
        self.show_message(f"{tr('net_connecting')} {bm['name']}...")
        self.net_service.mount(bm, password=password,
                               callback=self._after_mount_net)

    def _show_edit_dialog(self, bm):
        self._show_add_dialog(bookmark=bm)

    def _on_button_press(self, _widget, event):
        if event.button != 3:
            return False
        hit = self.tree.get_path_at_pos(int(event.x), int(event.y))
        if not hit:
            return False
        path, _col, _cx, _cy = hit
        sel = self.tree.get_selection()
        sel.unselect_all(); sel.select_path(path)
        model = self.tree.get_model()
        it    = model.get_iter(path)
        kind  = model.get_value(it, self.COL_KIND)
        obj   = model.get_value(it, self.COL_OBJECT)
        tpath = model.get_value(it, self.COL_PATH)
        name  = model.get_value(it, self.COL_NAME)

        menu = Gtk.Menu()

        if kind == 'favorite' and obj:
            open_item = Gtk.MenuItem(label=tr('open'))
            open_item.connect('activate', lambda *_: self.on_open_path(obj['path']))
            menu.append(open_item)
            
            rename_item = Gtk.MenuItem(label=tr('rename'))
            rename_item.connect('activate', lambda *_: self._rename_favorite(obj))
            menu.append(rename_item)
            
            change_icon_item = Gtk.MenuItem(label=tr('change_icon'))
            change_icon_item.connect('activate', lambda *_: self._change_favorite_icon(obj))
            menu.append(change_icon_item)
            
            remove_item = Gtk.MenuItem(label=tr('remove_favorite'))
            remove_item.connect('activate', lambda *_: self._remove_favorite(obj))
            menu.append(remove_item)

        elif kind == 'section_favorites':
            add_fav_item = Gtk.MenuItem(label=tr('add_to_favorites'))
            add_fav_item.connect('activate', lambda *_: self._show_add_favorite_dialog())
            menu.append(add_fav_item)

        elif kind in ('place', 'mount', 'network_folder') and tpath:
            open_item = Gtk.MenuItem(label=tr('open'))
            open_item.connect('activate', lambda *_: self.on_open_path(tpath))
            menu.append(open_item)
            
            if kind != 'favorite':
                fav_item = Gtk.MenuItem(label=tr('add_to_favorites'))
                fav_item.connect('activate', lambda *_: self._add_path_to_favorites(tpath, name))
                menu.append(fav_item)

        if kind == 'mount' and obj:
            if obj.get('can_unmount'):
                u = Gtk.MenuItem(label=tr('unmount'))
                u.connect('activate', lambda *_: self.volume_service.unmount_mount(
                    obj['mount'], self._after_unmount))
                menu.append(u)
            if obj.get('can_eject') and obj.get('volume'):
                e = Gtk.MenuItem(label=tr('eject'))
                e.connect('activate', lambda *_: self.volume_service.eject_volume(
                    obj['volume'], self._after_eject))
                menu.append(e)
        elif kind == 'volume_disabled' and obj:
            m = Gtk.MenuItem(label=tr('mount'))
            m.connect('activate', lambda *_: self.volume_service.mount_item(obj, self._after_mount))
            menu.append(m)
        elif kind == 'volume' and obj:
            m = Gtk.MenuItem(label=tr('mount'))
            m.connect('activate', lambda *_: self.volume_service.mount_item(obj, self._after_mount))
            menu.append(m)

        if kind == 'net_entry' and obj:
            mounted = self.net_service.is_mounted(obj['uri'])
            if mounted:
                open_item = Gtk.MenuItem(label=tr('open'))
                open_item.connect('activate', lambda *_: self._activate_net_entry(obj))
                menu.append(open_item)
                disc_item = Gtk.MenuItem(label=tr('net_disconnect'))
                disc_item.connect('activate', lambda *_: self._disconnect_net(obj))
                menu.append(disc_item)
            else:
                conn_item = Gtk.MenuItem(label=tr('net_connect'))
                conn_item.connect('activate', lambda *_: self._mount_bookmark(obj))
                menu.append(conn_item)
            menu.append(Gtk.SeparatorMenuItem())
            edit_item = Gtk.MenuItem(label=tr('net_edit'))
            edit_item.connect('activate', lambda *_: self._show_edit_dialog(obj))
            menu.append(edit_item)
            del_item = Gtk.MenuItem(label=tr('net_remove'))
            del_item.connect('activate', lambda *_: self._remove_net(obj))
            menu.append(del_item)

        elif kind == 'net_add':
            add_item = Gtk.MenuItem(label=tr('net_add_connection'))
            add_item.connect('activate', lambda *_: self._show_add_dialog())
            menu.append(add_item)

        elif kind == 'github':
            open_item = Gtk.MenuItem(label=tr('github_open'))
            open_item.connect('activate', lambda *_: self._launch_gitgui())
            menu.append(open_item)

        if not menu.get_children():
            return False

        menu.show_all()
        menu.popup_at_pointer(event)
        return True

    def _change_favorite_icon(self, fav):
        """Diálogo para que el usuario elija un ícono para el favorito."""
        parent = self.get_toplevel()
        dialog = Gtk.Dialog(title=tr('choose_icon'), transient_for=parent, modal=True)
        dialog.set_default_size(420, 480)
        dialog.add_buttons(tr('cancel'), Gtk.ResponseType.CANCEL,
                           tr('apply'), Gtk.ResponseType.OK)
        
        content = dialog.get_content_area()
        content.set_spacing(8)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        
        icon_list = [
            'starred', 'bookmark-new', 'bookmarks', 'folder', 'folder-documents',
            'folder-downloads', 'folder-music', 'folder-pictures', 'folder-videos',
            'emblem-favorite', 'emblem-important', 'emblem-documents', 'emblem-photos',
            'folder-desktop', 'user-home', 'drive-harddisk', 'network-server',
            'application-x-executable', 'text-x-generic', 'image-x-generic',
            'video-x-generic', 'audio-x-generic', 'package-x-generic',
            'go-home', 'system-run', 'utilities-terminal', 'preferences-system',
            'help-about', 'dialog-information', 'edit-copy', 'edit-paste',
            'edit-delete', 'view-refresh', 'list-add', 'list-remove'
        ]
        
        icon_store = Gtk.ListStore(GdkPixbuf.Pixbuf, str)
        icon_view = Gtk.IconView.new_with_model(icon_store)
        icon_view.set_pixbuf_column(0)
        icon_view.set_text_column(1)
        icon_view.set_item_width(80)
        icon_view.set_columns(4)
        icon_view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        
        theme = Gtk.IconTheme.get_default()
        icon_size = 32
        
        for icon_name in icon_list:
            try:
                pix = theme.load_icon(icon_name, icon_size, 0)
                icon_store.append([pix, icon_name])
            except Exception:
                continue
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(380, 380)
        scroll.add(icon_view)
        content.pack_start(scroll, True, True, 0)
        
        info_frame = Gtk.Frame()
        info_frame.set_margin_top(8)
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        info_box.set_margin_start(8)
        info_box.set_margin_end(8)
        info_box.set_margin_top(4)
        info_box.set_margin_bottom(4)
        
        current_label = Gtk.Label(label=f"{tr('current_icon')}: {fav.get('icon', 'starred')}", xalign=0)
        current_label.set_selectable(True)
        info_box.pack_start(current_label, True, True, 0)
        
        info_frame.add(info_box)
        content.pack_start(info_frame, False, False, 0)
        
        selected_icon = [fav.get('icon', 'starred')]
        
        def on_selection_changed(icon_view):
            selected = icon_view.get_selected_items()
            if selected:
                path = selected[0]
                it = icon_store.get_iter(path)
                selected_icon[0] = icon_store.get_value(it, 1)
                current_label.set_text(f"{tr('current_icon')}: {selected_icon[0]}")
        
        icon_view.connect('selection-changed', on_selection_changed)
        
        for row in icon_store:
            if row[1] == fav.get('icon', 'starred'):
                icon_view.select_path(row.path)
                break
        
        dialog.show_all()
        resp = dialog.run()
        
        if resp == Gtk.ResponseType.OK:
            self.favorites.update_icon(fav['id'], selected_icon[0])
            self.refresh()
            self.show_message(f"{tr('icon_changed')}: {selected_icon[0]}")
        
        dialog.destroy()

    def _show_add_favorite_dialog(self):
        """Mostrar diálogo para agregar un favorito manualmente con selección de ícono."""
        parent = self.get_toplevel()
        dialog = Gtk.Dialog(title=tr('add_favorite'), transient_for=parent, modal=True)
        dialog.set_default_size(450, 550)
        dialog.add_buttons(tr('cancel'), Gtk.ResponseType.CANCEL,
                          tr('add'), Gtk.ResponseType.OK)
        
        content = dialog.get_content_area()
        content.set_spacing(8)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        
        notebook = Gtk.Notebook()
        content.pack_start(notebook, True, True, 0)
        
        basic_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        basic_page.set_margin_top(12)
        basic_page.set_margin_bottom(12)
        basic_page.set_margin_start(12)
        basic_page.set_margin_end(12)
        
        grid = Gtk.Grid(column_spacing=8, row_spacing=8)
        basic_page.pack_start(grid, False, False, 0)
        
        grid.attach(Gtk.Label(label=tr('favorite_name'), xalign=0), 0, 0, 1, 1)
        name_entry = Gtk.Entry()
        grid.attach(name_entry, 1, 0, 2, 1)
        
        grid.attach(Gtk.Label(label=tr('path'), xalign=0), 0, 1, 1, 1)
        path_entry = Gtk.Entry()
        path_entry.set_hexpand(True)
        grid.attach(path_entry, 1, 1, 1, 1)
        
        browse_btn = Gtk.Button(label=tr('browse'))
        grid.attach(browse_btn, 2, 1, 1, 1)
        
        def on_browse(btn):
            chooser = Gtk.FileChooserDialog(title=tr('select_folder'), parent=dialog,
                                           action=Gtk.FileChooserAction.SELECT_FOLDER,
                                           buttons=(tr('cancel'), Gtk.ResponseType.CANCEL,
                                                   tr('open'), Gtk.ResponseType.OK))
            if chooser.run() == Gtk.ResponseType.OK:
                path_entry.set_text(chooser.get_filename())
            chooser.destroy()
        
        browse_btn.connect('clicked', on_browse)
        
        notebook.append_page(basic_page, Gtk.Label(label=tr('basic_info')))
        
        icon_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        icon_page.set_margin_top(12)
        icon_page.set_margin_bottom(12)
        icon_page.set_margin_start(12)
        icon_page.set_margin_end(12)
        
        icon_list = [
            'starred', 'bookmark-new', 'bookmarks', 'folder', 'folder-documents',
            'folder-downloads', 'folder-music', 'folder-pictures', 'folder-videos',
            'emblem-favorite', 'emblem-important', 'user-home', 'drive-harddisk',
            'network-server', 'application-x-executable', 'text-x-generic'
        ]
        
        icon_store = Gtk.ListStore(GdkPixbuf.Pixbuf, str)
        icon_view = Gtk.IconView.new_with_model(icon_store)
        icon_view.set_pixbuf_column(0)
        icon_view.set_text_column(1)
        icon_view.set_item_width(80)
        icon_view.set_columns(3)
        icon_view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        
        theme = Gtk.IconTheme.get_default()
        icon_size = 32
        
        for icon_name in icon_list:
            try:
                pix = theme.load_icon(icon_name, icon_size, 0)
                icon_store.append([pix, icon_name])
            except Exception:
                continue
        
        icon_scroll = Gtk.ScrolledWindow()
        icon_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        icon_scroll.set_size_request(400, 350)
        icon_scroll.add(icon_view)
        icon_page.pack_start(icon_scroll, True, True, 0)
        
        notebook.append_page(icon_page, Gtk.Label(label=tr('choose_icon')))
        
        selected_icon = ['starred']
        
        def on_icon_selected(icon_view):
            selected = icon_view.get_selected_items()
            if selected:
                path = selected[0]
                it = icon_store.get_iter(path)
                selected_icon[0] = icon_store.get_value(it, 1)
        
        icon_view.connect('selection-changed', on_icon_selected)
        
        dialog.show_all()
        resp = dialog.run()
        
        if resp == Gtk.ResponseType.OK:
            name = name_entry.get_text().strip()
            path = path_entry.get_text().strip()
            if name and path and os.path.exists(path):
                self.favorites.add(name, path, selected_icon[0])
                self.refresh()
                self.show_message(f"{tr('added_to_favorites')}: {name}")
        
        dialog.destroy()

    def _add_path_to_favorites(self, path, name):
        if not path or not os.path.exists(path):
            self.show_message(tr('invalid_path'))
            return
        
        if not name:
            name = os.path.basename(path.rstrip('/')) or path
        
        parent = self.get_toplevel()
        dialog = Gtk.Dialog(title=tr('choose_icon'), transient_for=parent, modal=True)
        dialog.set_default_size(400, 450)
        dialog.add_buttons(tr('cancel'), Gtk.ResponseType.CANCEL,
                          tr('add'), Gtk.ResponseType.OK)
        
        content = dialog.get_content_area()
        content.set_spacing(8)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        
        content.add(Gtk.Label(label=f"{tr('add_to_favorites')}: {name}", xalign=0))
        
        icon_list = ['starred', 'bookmark-new', 'folder', 'emblem-favorite', 'user-home']
        icon_store = Gtk.ListStore(GdkPixbuf.Pixbuf, str)
        icon_view = Gtk.IconView.new_with_model(icon_store)
        icon_view.set_pixbuf_column(0)
        icon_view.set_text_column(1)
        icon_view.set_item_width(80)
        icon_view.set_columns(3)
        icon_view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        
        theme = Gtk.IconTheme.get_default()
        for icon_name in icon_list:
            try:
                pix = theme.load_icon(icon_name, 32, 0)
                icon_store.append([pix, icon_name])
            except Exception:
                continue
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_size_request(360, 200)
        scroll.add(icon_view)
        content.pack_start(scroll, True, True, 0)
        
        selected_icon = ['starred']
        
        def on_selection(icon_view):
            selected = icon_view.get_selected_items()
            if selected:
                path = selected[0]
                it = icon_store.get_iter(path)
                selected_icon[0] = icon_store.get_value(it, 1)
        
        icon_view.connect('selection-changed', on_selection)
        
        dialog.show_all()
        resp = dialog.run()
        
        if resp == Gtk.ResponseType.OK:
            self.favorites.add(name, path, selected_icon[0])
            self.refresh()
            self.show_message(f"{tr('added_to_favorites')}: {name}")
        
        dialog.destroy()

    def _rename_favorite(self, fav):
        parent = self.get_toplevel()
        dialog = Gtk.Dialog(title=tr('rename_favorite'), transient_for=parent, modal=True)
        dialog.set_default_size(300, -1)
        dialog.add_buttons(tr('cancel'), Gtk.ResponseType.CANCEL,
                          tr('rename'), Gtk.ResponseType.OK)
        
        content = dialog.get_content_area()
        content.set_spacing(8)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        
        content.add(Gtk.Label(label=tr('favorite_name'), xalign=0))
        entry = Gtk.Entry()
        entry.set_text(fav['name'])
        entry.select_region(0, -1)
        content.add(entry)
        
        dialog.show_all()
        resp = dialog.run()
        
        if resp == Gtk.ResponseType.OK:
            new_name = entry.get_text().strip()
            if new_name:
                self.favorites.rename(fav['id'], new_name)
                self.refresh()
                self.show_message(f"{tr('favorite_renamed')}: {new_name}")
        
        dialog.destroy()

    def _remove_favorite(self, fav):
        parent = self.get_toplevel()
        dlg = Gtk.MessageDialog(transient_for=parent, modal=True,
                               message_type=Gtk.MessageType.QUESTION,
                               buttons=Gtk.ButtonsType.OK_CANCEL,
                               text=f"{tr('remove_favorite_confirm')} '{fav['name']}'?")
        resp = dlg.run()
        dlg.destroy()
        if resp == Gtk.ResponseType.OK:
            self.favorites.remove(fav['id'])
            self.refresh()
            self.show_message(f"{tr('favorite_removed')}: {fav['name']}")

    def _disconnect_net(self, bm):
        self.show_message(f"{tr('net_disconnecting')} {bm['name']}...")
        self.net_service.unmount(bm['uri'], callback=self._after_disconnect_net)

    def _after_disconnect_net(self, ok, msg):
        self.show_message(tr('net_disconnected') if ok else f"{tr('net_error')}: {msg}")
        self.refresh()

    def _remove_net(self, bm):
        parent = self.get_toplevel()
        dlg = Gtk.MessageDialog(transient_for=parent, modal=True,
                                message_type=Gtk.MessageType.QUESTION,
                                buttons=Gtk.ButtonsType.OK_CANCEL,
                                text=f"{tr('net_remove_confirm')} '{bm['name']}'?")
        resp = dlg.run(); dlg.destroy()
        if resp == Gtk.ResponseType.OK:
            self.net_service.remove(bm['uri'])
            self.refresh()

    def _after_mount(self, ok, error_text):
        self.show_message(tr('mounted_ok') if ok else (error_text or tr('mounted_fail')))
        self.refresh()

    def _after_unmount(self, ok, error_text):
        self.show_message(tr('unmounted_ok') if ok else (error_text or tr('unmounted_fail')))
        self.refresh()

    def _after_eject(self, ok, error_text):
        self.show_message(tr('ejected_ok') if ok else (error_text or tr('ejected_fail')))
        self.refresh()

    def _launch_gitgui(self):
        """Lanza GitGUI como usuario normal (sin pkexec).

        GitGUI configura git --global y SSH keys, que viven en la home del
        usuario. Lanzarlo como root corrompería /root en lugar del HOME real.
        Todo está integrado dentro de /usr/local/essorafm/gitgui/.

        Antes de lanzar verifica que `git` esté disponible. Si no lo está,
        muestra un diálogo informativo en el idioma del usuario en lugar
        de abrir la GUI que solo mostraría un error técnico en su log.
        """
        import shutil
        import subprocess

        gitgui_script = '/usr/local/essorafm/gitgui/gitgui.py'
        if not os.path.exists(gitgui_script):
            self.show_message(tr('github_not_installed'))
            return

        if shutil.which('git') is None:
            self._show_git_missing_dialog()
            return

        try:
            subprocess.Popen(
                ['python3', gitgui_script],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self.show_message(tr('github_launching'))
        except FileNotFoundError:
            self.show_message(tr('github_not_installed'))
        except Exception as e:
            self.show_message(f"{tr('github_error')}: {e}")

    def _show_git_missing_dialog(self):
        """Diálogo informativo cuando git no está instalado en el sistema."""
        parent = self.get_toplevel()
        dialog = Gtk.MessageDialog(
            transient_for=parent,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK,
            text=tr('git_missing_title'),
        )
        dialog.format_secondary_text(
            tr('git_missing_body') + '\n\n'
            + tr('git_missing_hint') + '\n'
            + '    sudo apt install git'
        )
        dialog.run()
        dialog.destroy()
