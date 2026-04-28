# EssoraFM - Sidebar con sección Red (SMB/FTP/SFTP/WebDAV/NFS)
# Author: josejp2424 - GPL-3.0

import os
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, GdkPixbuf, Pango

from services.volumes import VolumeService
from services.icon_loader import IconLoader
from services.trash import TrashService
from services.network_bookmarks import NetworkBookmarkService
from app.network_dialog import NetworkConnectDialog
from core.i18n import tr


class Sidebar(Gtk.Box):
    COL_PIXBUF  = 0
    COL_NAME    = 1
    COL_PATH    = 2
    COL_KIND    = 3  
    COL_OBJECT  = 4   

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

        size = settings_manager.get_int('sidebar_icon_size', 20) if settings_manager else 20
        self.icon_loader = IconLoader(size)

        self.store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str, str, object)
        self.tree  = Gtk.TreeView(model=self.store)
        self.tree.get_style_context().add_class('essorafm-sidebar-tree')
        self.tree.set_headers_visible(False)
        self.tree.connect('row-activated',    self._on_row_activated)
        self.tree.connect('button-press-event', self._on_button_press)

        column = Gtk.TreeViewColumn()
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column.set_fixed_width(188)

        renderer_pix = Gtk.CellRendererPixbuf()
        renderer_txt = Gtk.CellRendererText()
        renderer_txt.set_property('ellipsize', Pango.EllipsizeMode.END)
        renderer_txt.set_property('ellipsize-set', True)
        renderer_txt.set_property('max-width-chars', 18)

        column.pack_start(renderer_pix, False)
        column.pack_start(renderer_txt, True)
        column.add_attribute(renderer_pix, 'pixbuf', self.COL_PIXBUF)
        column.add_attribute(renderer_txt, 'text',   self.COL_NAME)

        column.set_cell_data_func(renderer_txt, self._cell_data_func)

        self.tree.append_column(column)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_shadow_type(Gtk.ShadowType.NONE)
        scroll.add(self.tree)
        self.pack_start(scroll, True, True, 0)

        for sig in ('mount-added', 'mount-removed', 'volume-added',
                    'volume-removed', 'volume-changed', 'mount-changed'):
            self.volume_service.connect(sig, lambda *_: self.refresh())

        self.refresh()

    def _cell_data_func(self, column, cell, model, it, data=None):
        kind = model.get_value(it, self.COL_KIND)
        if kind == 'net_header':
            cell.set_property('weight', Pango.Weight.BOLD)
            cell.set_property('foreground-rgba', None)
        else:
            cell.set_property('weight', Pango.Weight.NORMAL)

    def apply_preferences(self):
        size = self.settings_manager.get_int('sidebar_icon_size', 20) if self.settings_manager else 20
        self.icon_loader = IconLoader(size)
        self.refresh()

    def refresh(self):
        self.store.clear()
        theme = Gtk.IconTheme.get_default()
        size  = self.settings_manager.get_int('sidebar_icon_size', 20) if self.settings_manager else 20
        home  = os.path.expanduser('~')

        static_places = [
            (tr('home_folder'),  home,                              'folder-home'),
            (tr('desktop'),      os.path.join(home, 'Desktop'),     'user-desktop'),
            (tr('documents'),    os.path.join(home, 'Documents'),   'folder-documents'),
            (tr('downloads'),    os.path.join(home, 'Downloads'),   'folder-download'),
            (tr('filesystem'),   '/',                               'drive-harddisk'),
            (tr('trash'),        self.trash.trash_path(),           'user-trash'),
        ]
        for name, path, icon_name in static_places:
            if not os.path.exists(path):
                continue
            try:
                pix = theme.load_icon(icon_name, size, 0)
            except Exception:
                pix = self.icon_loader.folder_icon(size)
            self.store.append([pix, name, path, 'place', None])

        for item in self.volume_service.list_sidebar_items():
            pix = self.icon_loader._load_from_gicon(item.get('icon'), size)
            self.store.append([pix, item['name'], item.get('path') or '',
                               item['kind'], item])

        try:
            net_icon = theme.load_icon('network-workgroup', size, 0)
        except Exception:
            try:
                net_icon = theme.load_icon('network', size, 0)
            except Exception:
                net_icon = None

        self.store.append([net_icon, tr('net_section'), '', 'net_header', None])

        bookmarks = self.net_service.list()
        for bm in bookmarks:
            mounted   = self.net_service.is_mounted(bm['uri'])
            icon_name = 'folder-remote' if mounted else 'network-server'
            try:
                pix = theme.load_icon(icon_name, size, 0)
            except Exception:
                pix = net_icon
            label = bm['name']
            if mounted:
                label += ' ✓'
            path = self.net_service.mount_path(bm['uri']) if mounted else ''
            self.store.append([pix, label, path, 'net_entry', bm])

        try:
            add_icon = theme.load_icon('list-add', size, 0)
        except Exception:
            add_icon = None
        self.store.append([add_icon, tr('net_add'), '', 'net_add', None])

    def _on_row_activated(self, tree, path, _column):
        model = tree.get_model()
        it    = model.get_iter(path)
        kind  = model.get_value(it, self.COL_KIND)
        tpath = model.get_value(it, self.COL_PATH)
        obj   = model.get_value(it, self.COL_OBJECT)

        if kind in ('place', 'mount') and tpath:
            self.on_open_path(tpath)

        elif kind == 'volume' and obj:
            volume = obj.get('volume')
            if volume and obj.get('can_mount', True):
                self.show_message(tr('mounting_volume'))
                self.volume_service.mount_volume(volume, self._after_mount)

        elif kind == 'net_entry' and obj:
            self._activate_net_entry(obj)

        elif kind == 'net_add':
            self._show_add_dialog()

        elif kind == 'net_header':
            pass 

    def _activate_net_entry(self, bm):
        """Si ya montado, abre. Si no, monta primero."""
        if self.net_service.is_mounted(bm['uri']):
            path = self.net_service.mount_path(bm['uri'])
            if path:
                self.on_open_path(path)
                return
        self._mount_bookmark(bm)

    def _mount_bookmark(self, bm):
        """Muestra diálogo de contraseña si hace falta y monta."""
        password = bm.get('password', '')
        if not password:
            password = self._ask_password(bm)
            if password is None:
                return 

        self.show_message(f"{tr('net_connecting')} {bm['name']}...")
        self.net_service.mount(bm, password=password,
                               callback=self._after_mount_net)

    def _ask_password(self, bm):
        """Diálogo compacto para pedir contraseña."""
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
        """Monta directamente sin pedir contraseña otra vez."""
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

        menu = Gtk.Menu()

        if kind in ('place', 'mount') and tpath:
            open_item = Gtk.MenuItem(label=tr('open'))
            open_item.connect('activate', lambda *_: self.on_open_path(tpath))
            menu.append(open_item)

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
        elif kind == 'volume' and obj and obj.get('can_mount'):
            m = Gtk.MenuItem(label=tr('mount'))
            m.connect('activate', lambda *_: self.volume_service.mount_volume(
                obj['volume'], self._after_mount))
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

        if kind == 'net_add':
            add_item = Gtk.MenuItem(label=tr('net_add'))
            add_item.connect('activate', lambda *_: self._show_add_dialog())
            menu.append(add_item)

        if not menu.get_children():
            return False

        menu.show_all()
        menu.popup_at_pointer(event)
        return True

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
