# EssoraFM - Diálogo compacto para agregar conexión de red
# Author: josejp2424 and Nilsonmorales - GPL-3.0

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from services.network_bookmarks import SUPPORTED_SCHEMES
from core.i18n import tr


class NetworkConnectDialog(Gtk.Dialog):
    """
    Diálogo compacto para agregar o editar una conexión de red.
    Campos: tipo (combo), servidor, carpeta compartida, usuario, contraseña, nombre.
    """

    SCHEME_OPTIONS = [
        ('smb',  'Samba / Windows (smb://)'),
        ('ftp',  'FTP (ftp://)'),
        ('sftp', 'SSH / SFTP (sftp://)'),
        ('dav',  'WebDAV (dav://)'),
        ('davs', 'WebDAV seguro (davs://)'),
        ('nfs',  'NFS (nfs://)'),
        ('ftps', 'FTP seguro (ftps://)'),
    ]

    def __init__(self, parent, bookmark=None):
        super().__init__(
            title=tr('net_add_connection') if not bookmark else tr('net_edit_connection'),
            transient_for=parent,
            modal=True,
        )
        self.set_default_size(400, -1)
        self.set_resizable(False)
        self.add_buttons(tr('cancel'), Gtk.ResponseType.CANCEL,
                         tr('connect') if not bookmark else tr('save'),
                         Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)

        area = self.get_content_area()
        area.set_margin_top(12)
        area.set_margin_bottom(8)
        area.set_margin_start(14)
        area.set_margin_end(14)

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(8)
        area.add(grid)

        row = 0

        grid.attach(Gtk.Label(label=tr('net_type'), xalign=1), 0, row, 1, 1)
        self.combo = Gtk.ComboBoxText()
        for scheme, label in self.SCHEME_OPTIONS:
            self.combo.append(scheme, label)
        self.combo.set_active(0)
        self.combo.connect('changed', self._on_type_changed)
        self.combo.set_hexpand(True)
        grid.attach(self.combo, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label=tr('net_server'), xalign=1), 0, row, 1, 1)
        self.server_entry = Gtk.Entry()
        self.server_entry.set_placeholder_text(tr('net_server_hint'))
        self.server_entry.set_hexpand(True)
        self.server_entry.set_activates_default(True)
        grid.attach(self.server_entry, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label=tr('net_port'), xalign=1), 0, row, 1, 1)
        self.port_entry = Gtk.Entry()
        self.port_entry.set_placeholder_text(tr('net_optional'))
        self.port_entry.set_max_width_chars(6)
        self.port_entry.set_width_chars(6)
        grid.attach(self.port_entry, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label=tr('net_share'), xalign=1), 0, row, 1, 1)
        self.share_entry = Gtk.Entry()
        self.share_entry.set_placeholder_text(tr('net_optional'))
        self.share_entry.set_hexpand(True)
        self.share_entry.set_activates_default(True)
        grid.attach(self.share_entry, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label=tr('net_user'), xalign=1), 0, row, 1, 1)
        self.user_entry = Gtk.Entry()
        self.user_entry.set_placeholder_text(tr('net_anonymous'))
        self.user_entry.set_hexpand(True)
        self.user_entry.set_activates_default(True)
        grid.attach(self.user_entry, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label=tr('net_password'), xalign=1), 0, row, 1, 1)
        self.pass_entry = Gtk.Entry()
        self.pass_entry.set_visibility(False)
        self.pass_entry.set_placeholder_text(tr('net_optional'))
        self.pass_entry.set_hexpand(True)
        self.pass_entry.set_activates_default(True)
        grid.attach(self.pass_entry, 1, row, 1, 1)
        row += 1

        grid.attach(Gtk.Label(label=tr('net_name'), xalign=1), 0, row, 1, 1)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text(tr('net_name_hint'))
        self.name_entry.set_hexpand(True)
        self.name_entry.set_activates_default(True)
        grid.attach(self.name_entry, 1, row, 1, 1)
        row += 1

        self.uri_preview = Gtk.Label(label='', xalign=0)
        self.uri_preview.get_style_context().add_class('dim-label')
        self.uri_preview.set_selectable(True)
        grid.attach(self.uri_preview, 0, row, 2, 1)

        for entry in (self.server_entry, self.port_entry,
                      self.share_entry, self.user_entry):
            entry.connect('changed', self._update_preview)
        self.combo.connect('changed', self._update_preview)

        if bookmark:
            self._fill_from_bookmark(bookmark)

        self.show_all()
        self._update_preview()

    def _on_type_changed(self, combo):
        scheme = combo.get_active_id() or 'smb'
        show_share = scheme in ('smb', 'nfs', 'dav', 'davs')
        self.share_entry.set_sensitive(show_share)

    def _update_preview(self, *_):
        self.uri_preview.set_text(self._build_uri())

    def _build_uri(self):
        scheme = self.combo.get_active_id() or 'smb'
        server = self.server_entry.get_text().strip()
        port   = self.port_entry.get_text().strip()
        share  = self.share_entry.get_text().strip().lstrip('/')
        user   = self.user_entry.get_text().strip()
        if not server:
            return f'{scheme}://'
        netloc = server
        if port:
            netloc += f':{port}'
        if user:
            netloc = f'{user}@{netloc}'
        path = f'/{share}' if share else ''
        return f'{scheme}://{netloc}{path}'

    def _fill_from_bookmark(self, bm):
        from urllib.parse import urlparse
        uri = bm.get('uri', '')
        try:
            p = urlparse(uri)
            scheme = p.scheme or 'smb'
            for i, (s, _) in enumerate(self.SCHEME_OPTIONS):
                if s == scheme:
                    self.combo.set_active(i)
                    break
            self.server_entry.set_text(p.hostname or '')
            if p.port:
                self.port_entry.set_text(str(p.port))
            path = p.path.lstrip('/')
            self.share_entry.set_text(path)
            self.user_entry.set_text(bm.get('username', '') or p.username or '')
        except Exception:
            pass
        self.name_entry.set_text(bm.get('name', ''))

    def get_result(self):
        """Devuelve dict {name, uri, username, password} o None si cancelado."""
        uri = self._build_uri()
        name = self.name_entry.get_text().strip() or uri
        username = self.user_entry.get_text().strip()
        password = self.pass_entry.get_text()
        return {'name': name, 'uri': uri, 'username': username, 'password': password}
