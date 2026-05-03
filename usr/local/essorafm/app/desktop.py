#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# EssoraFM Desktop mode
# Original implementation for EssoraFM by josejp2424.
# Desktop control, wallpaper, desktop icons and drive icons.
# This uses GIO/GVolumeMonitor and EssoraFM's own config in ~/.config/essorafm/.
# EssoraFM
# Author: josejp2424 and Nilsonmorales - GPL-3.0
import os
import json
import shutil
import subprocess
import shlex
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Gio', '2.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, Gio, GLib, GdkPixbuf

from services.volumes import VolumeService
from services.icon_loader import IconLoader
from core.desktop_settings import DesktopDriveSettings, DESKTOP_DRIVES_CONFIG, DESKTOP_DRIVES_COMPAT_CONFIG
from core.settings import CONFIG_DIR
from core.i18n import tr
from core.xdg import xdg_dir, XDG
from app.wallpaper_carousel import WallpaperCarouselDialog


_ICON_POSITIONS_FILE = os.path.join(
    os.path.expanduser('~'), '.config', 'essorafm', 'desktop_icon_positions.json'
)


def _load_icon_positions():
    try:
        with open(_ICON_POSITIONS_FILE, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save_icon_positions(positions):
    try:
        os.makedirs(os.path.dirname(_ICON_POSITIONS_FILE), exist_ok=True)
        with open(_ICON_POSITIONS_FILE, 'w', encoding='utf-8') as fh:
            json.dump(positions, fh, indent=2)
    except Exception:
        pass


def _clear_icon_positions():
    try:
        if os.path.exists(_ICON_POSITIONS_FILE):
            os.remove(_ICON_POSITIONS_FILE)
    except Exception:
        pass


class DesktopDriveIcon(Gtk.EventBox):
    def __init__(self, item, desktop):
        super().__init__()
        self.item = item
        self.desktop = desktop
        self.set_visible_window(False)
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.connect('button-press-event', self._on_button_press)
        self.connect('button-release-event', self._on_button_release)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_size_request(self.desktop.cell_w, self.desktop.cell_h)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        self.add(box)

        is_mounted = bool(item.get('mounted')) or item.get('kind') == 'mount'
        can_eject = bool(item.get('can_eject') or item.get('can_unmount'))

        pix = self.desktop.icon_loader._load_from_gicon(item.get('icon'), self.desktop.icon_size)
        image = Gtk.Image.new_from_pixbuf(pix) if pix else Gtk.Image.new_from_icon_name('drive-harddisk', Gtk.IconSize.DIALOG)
        image.set_pixel_size(self.desktop.icon_size)
        if not is_mounted:
            image.set_opacity(0.5)

        overlay = Gtk.Overlay()
        overlay.add(image)

        if is_mounted and can_eject:
            badge = self._build_eject_badge()
            overlay.add_overlay(badge)

        box.pack_start(overlay, False, False, 0)

        if self.desktop.show_labels:
            label = Gtk.Label(label=item.get('name') or 'Drive')
            label.set_line_wrap(True)
            if getattr(self.desktop, 'label_lines', 0) > 0:
                label.set_lines(self.desktop.label_lines)
            label.set_justify(Gtk.Justification.CENTER)
            label.set_max_width_chars(self.desktop.label_width)
            label.set_ellipsize(3)
            label.get_style_context().add_class('essorafm-desktop-label')
            if not is_mounted:
                label.set_opacity(0.6)
            box.pack_start(label, False, False, 0)

        path = item.get('path') or ''
        self.set_tooltip_text(f"{item.get('name')}\n{path if is_mounted and path else tr('not_mounted')}")

    def _build_eject_badge(self):
        """Construye el badge de eject que aparece en la esquina inferior derecha
        de los iconos de discos montados. Es un EventBox propio: el click sobre
        él desmonta el disco sin propagarse al icono principal."""
        badge = Gtk.EventBox()
        badge.set_visible_window(False)
        badge.set_halign(Gtk.Align.END)
        badge.set_valign(Gtk.Align.END)
        badge.set_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        badge.set_tooltip_text(tr('unmount'))

        badge_size = max(16, self.desktop.icon_size // 3)
        img = Gtk.Image.new_from_icon_name('media-eject-symbolic', Gtk.IconSize.MENU)
        img.set_pixel_size(badge_size)
        img.get_style_context().add_class('essorafm-eject-badge')
        badge.add(img)

        badge.connect('button-press-event', self._on_badge_click)
        badge.connect('enter-notify-event', lambda *_: img.set_opacity(1.0) or False)
        badge.connect('leave-notify-event', lambda *_: img.set_opacity(0.85) or False)
        img.set_opacity(0.85)
        return badge

    def _on_badge_click(self, _widget, event):
        """Click sobre el badge -> desmonta el disco. Retorna True para que el
        evento NO se propague al EventBox padre (evita abrir el disco a la vez)."""
        if event.button != 1:
            return True
        self.desktop.unmount_item(self.item)
        return True

    def _on_button_press(self, _widget, event):
        if event.button == 3:
            self.desktop.popup_menu_for_item(self.item, event)
            return True
        single = getattr(self.desktop, 'desktop_single_click', False)
        if single and event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            self.desktop.open_item(self.item)
            return True
        if not single and event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and event.button == 1:
            self.desktop.open_item(self.item)
            return True
        return False

    def _on_button_release(self, _widget, event):
        return False


class DesktopFileIcon(Gtk.EventBox):


    _THUMB_EXTS = {
        '.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff', '.tif',
        '.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.m4v', '.ogv',
        '.ts', '.wmv', '.3gp', '.pdf', '.svg',
    }

    def __init__(self, path, desktop):
        super().__init__()
        self.path = path
        self.desktop = desktop
        self.set_visible_window(True)          
        self.get_style_context().add_class('essorafm-desktop-icon')
        self.set_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.BUTTON1_MOTION_MASK
        )
        self.connect('button-press-event',   self._on_button_press)
        self.connect('button-release-event', self._on_button_release)
        self.connect('motion-notify-event',  self._on_motion)


        self._dragging    = False
        self._drag_ptr_x  = 0
        self._drag_ptr_y  = 0
        self._drag_icon_x = 0
        self._drag_icon_y = 0
        self._DRAG_THRESHOLD = 6

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_size_request(self.desktop.cell_w, self.desktop.cell_h)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        self.add(box)

 
        pixbuf = self._best_pixbuf(path)
        if pixbuf is not None:
            image = Gtk.Image.new_from_pixbuf(pixbuf)
        else:
            image = Gtk.Image.new_from_gicon(self._gicon_for_path(path), Gtk.IconSize.DIALOG)
        image.set_pixel_size(self.desktop.icon_size)
        box.pack_start(image, False, False, 0)

        label = Gtk.Label(label=self._display_name(path))
        label.set_line_wrap(True)
        if getattr(self.desktop, 'label_lines', 0) > 0:
            label.set_lines(self.desktop.label_lines)
        label.set_justify(Gtk.Justification.CENTER)
        label.set_max_width_chars(self.desktop.label_width)
        label.set_ellipsize(3)
        label.get_style_context().add_class('essorafm-desktop-label')
        box.pack_start(label, False, False, 0)
        self.set_tooltip_text(path)

    def _best_pixbuf(self, path):
        """Devuelve un Pixbuf para el icono del escritorio con este orden de prioridad:
        1. Miniatura real (imagen/video/pdf) via Thumbnailer si está disponible
        2. Icono personalizado de carpeta (.directory file o metadata de Nautilus/Nemo)
        3. None → el llamador usará _gicon_for_path como fallback
        """
        size = self.desktop.icon_size

        real = os.path.realpath(path) if os.path.islink(path) else path

        ext = os.path.splitext(real)[1].lower()
        if ext in self._THUMB_EXTS and os.path.isfile(real):
            thumbnailer = getattr(self.desktop, '_thumbnailer', None)
            if thumbnailer is None:

                try:
                    from services.thumbnailer import Thumbnailer
                    thumbnailer = Thumbnailer(self.desktop.icon_loader, enabled=True)
                    self.desktop._thumbnailer = thumbnailer
                except Exception:
                    thumbnailer = None
            if thumbnailer is not None:
                try:
                    pix = thumbnailer.thumbnail_for(real, size=size)
                    if pix is not None:
                        return pix
                except Exception:
                    pass


        if os.path.isdir(real):
            pix = self._folder_custom_icon(real, size)
            if pix is not None:
                return pix

        return None

    def _folder_custom_icon(self, folder_path, size):
        """Lee el icono personalizado de una carpeta desde .directory o metadatos
        de gestores de archivos (Nautilus/Nemo/Thunar)."""
        icon_theme = Gtk.IconTheme.get_default()

        dot_dir = os.path.join(folder_path, '.directory')
        if os.path.isfile(dot_dir):
            try:
                kf = GLib.KeyFile()
                kf.load_from_file(dot_dir, GLib.KeyFileFlags.NONE)
                icon_name = ''
                try:
                    icon_name = kf.get_locale_string('Desktop Entry', 'Icon', None) or ''
                except Exception:
                    pass
                if not icon_name:
                    try:
                        icon_name = kf.get_string('Desktop Entry', 'Icon')
                    except Exception:
                        pass
                if icon_name:
                    if os.path.isabs(icon_name) and os.path.exists(icon_name):
                        try:
                            return GdkPixbuf.Pixbuf.new_from_file_at_size(icon_name, size, size)
                        except Exception:
                            pass
                    else:
                        for s in (size, 48, 64, 32):
                            try:
                                pix = icon_theme.load_icon(icon_name, s, Gtk.IconLookupFlags.FORCE_SIZE)
                                if pix:
                                    return pix
                            except Exception:
                                pass
            except Exception:
                pass

        try:
            meta_dir = os.path.join(os.path.expanduser('~'), '.local', 'share', 'gvfs-metadata')

            folder_name = os.path.basename(folder_path.rstrip('/'))
            for meta_name in (folder_name, 'home'):
                meta_file = os.path.join(meta_dir, meta_name)
                if not os.path.exists(meta_file):
                    continue

                break
        except Exception:
            pass


        folder_lower = os.path.basename(folder_path.rstrip('/')).lower()
        _XDG_ICONS = {
            'documents': 'folder-documents',
            'downloads': 'folder-download',
            'pictures':  'folder-pictures',
            'photos':    'folder-pictures',
            'music':     'folder-music',
            'videos':    'folder-videos',
            'movies':    'folder-videos',
            'desktop':   'user-desktop',
            'public':    'folder-publicshare',
            'templates': 'folder-templates',
        }
        xdg_icon = _XDG_ICONS.get(folder_lower)
        if xdg_icon:
            for s in (size, 48, 64):
                try:
                    pix = icon_theme.load_icon(xdg_icon, s, Gtk.IconLookupFlags.FORCE_SIZE)
                    if pix:
                        return pix
                except Exception:
                    pass

        return None

    def _display_name(self, path):
        name = os.path.basename(path)
        if name.endswith('.desktop'):
            keyfile = self._load_keyfile(path)
            if keyfile is not None:
                value = self._read_localized(keyfile, 'Name')
                if value:
                    return value
                target = self._link_target(keyfile)
                if target:
                    target_kf = self._load_keyfile(target)
                    if target_kf is not None:
                        value = self._read_localized(target_kf, 'Name')
                        if value:
                            return value
            return name[:-8]
        return name

    def _gicon_for_path(self, path):
        if path.endswith('.desktop'):
            keyfile = self._load_keyfile(path)
            if keyfile is not None:
                icon = self._read_localized(keyfile, 'Icon')
                if not icon:
                    target = self._link_target(keyfile)
                    if target:
                        target_kf = self._load_keyfile(target)
                        if target_kf is not None:
                            icon = self._read_localized(target_kf, 'Icon')
                if icon:
                    if os.path.isabs(icon) and os.path.exists(icon):
                        return Gio.FileIcon.new(Gio.File.new_for_path(icon))
                    return Gio.ThemedIcon.new(icon)
        try:
            info = Gio.File.new_for_path(path).query_info('standard::icon', Gio.FileQueryInfoFlags.NONE, None)
            icon = info.get_icon()
            if icon:
                return icon
        except Exception:
            pass
        return Gio.ThemedIcon.new('text-x-generic')

    def _load_keyfile(self, path):
        try:
            keyfile = GLib.KeyFile()
            keyfile.load_from_file(path, GLib.KeyFileFlags.NONE)
            return keyfile
        except Exception:
            return None

    def _read_localized(self, keyfile, key):
        try:
            value = keyfile.get_locale_string('Desktop Entry', key, None)
            if value:
                return value
        except Exception:
            pass
        try:
            return keyfile.get_string('Desktop Entry', key)
        except Exception:
            return ''

    def _link_target(self, keyfile):
        """Si el .desktop es Type=Link y URL apunta a otro .desktop existente,
        devuelve la ruta del .desktop apuntado, si no devuelve None."""
        try:
            entry_type = keyfile.get_string('Desktop Entry', 'Type')
        except Exception:
            return None
        if entry_type != 'Link':
            return None
        try:
            url = keyfile.get_string('Desktop Entry', 'URL')
        except Exception:
            return None
        if url and url.endswith('.desktop') and os.path.isabs(url) and os.path.exists(url):
            return url
        return None

    def _on_button_press(self, _widget, event):
        if event.button == 3:
            self.desktop.popup_menu_for_desktop_file(self.path, event)
            return True
        if event.button == 1:
            if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:

                if not getattr(self.desktop, 'desktop_single_click', False):
                    self.desktop.open_desktop_file(self.path)
                return True

            self._dragging   = False
            self._drag_ptr_x = event.x_root
            self._drag_ptr_y = event.y_root
            alloc = self.get_allocation()
            self._drag_icon_x = alloc.x
            self._drag_icon_y = alloc.y
            return True
        return False

    def _on_motion(self, _widget, event):
        if getattr(self.desktop, 'auto_arrange', False):
            return False
        if not (event.state & Gdk.ModifierType.BUTTON1_MASK):
            return False
        dx = event.x_root - self._drag_ptr_x
        dy = event.y_root - self._drag_ptr_y
        if not self._dragging:
            if abs(dx) < self._DRAG_THRESHOLD and abs(dy) < self._DRAG_THRESHOLD:
                return False
            self._dragging = True

        nx = int(self._drag_icon_x + dx)
        ny = int(self._drag_icon_y + dy)
        sw, sh = self.desktop._screen_size()
        nx = max(0, min(nx, sw - self.desktop.cell_w))
        ny = max(0, min(ny, sh - self.desktop.cell_h))
        self.desktop.fixed.move(self, nx, ny)
        return True

    def _on_button_release(self, _widget, event):
        if event.button == 1 and self._dragging and not getattr(self.desktop, 'auto_arrange', False):
            alloc = self.get_allocation()
            pos = _load_icon_positions()
            pos[os.path.basename(self.path)] = [alloc.x, alloc.y]
            _save_icon_positions(pos)
            self._dragging = False
            return True
        if event.button == 1 and not self._dragging:
            single = getattr(self.desktop, 'desktop_single_click', False)
            if single:
                self.desktop.open_desktop_file(self.path)
                return True
        return False


class AppPickerDialog(Gtk.Dialog):
    """Diálogo visual tipo grid para enviar apps, archivos o carpetas al escritorio.

    Tres modos seleccionables mediante botones:
      - Aplicaciones: grid de .desktop de /usr/share/applications (con búsqueda)
      - Archivos: lista de archivos comunes del home + botón Examinar
      - Carpetas: lista de carpetas comunes del home + botón Examinar
    """

    APP_DIRS = [
        '/usr/share/applications',
        '/usr/local/share/applications',
        os.path.expanduser('~/.local/share/applications'),
    ]
    CELL_SIZE = 90
    ICON_SIZE  = 48


    _COMMON_FILES = [
        ('~/Desktop',     'user-desktop',      'desktop'),
        ('~/.bashrc',     'text-x-script',     '.bashrc'),
        ('~/.bash_profile', 'text-x-script',   '.bash_profile'),
        ('~/.profile',    'text-x-script',     '.profile'),
        ('~/.zshrc',      'text-x-script',     '.zshrc'),
    ]
    _COMMON_FOLDERS = [
        ('~',             'user-home',         'Home'),
        ('~/Documents',   'folder-documents',  'Documents'),
        ('~/Downloads',   'folder-download',   'Downloads'),
        ('~/Pictures',    'folder-pictures',   'Pictures'),
        ('~/Music',       'folder-music',      'Music'),
        ('~/Videos',      'folder-videos',     'Videos'),
        ('~/Desktop',     'user-desktop',      'Desktop'),
        ('/tmp',          'folder',            '/tmp'),
        ('/usr/share/applications', 'folder',  'Applications'),
    ]

    def __init__(self, parent):
        super().__init__(title=tr('app_picker_title'), transient_for=parent,
                         modal=True, use_header_bar=0)
        self.set_default_size(720, 560)
        self.add_buttons(tr('cancel'), Gtk.ResponseType.CANCEL,
                         tr('add_selected'), Gtk.ResponseType.OK)
        self._selected_path = None
        self._all_apps = []
        self._filtered = []
        self._selected_vbox = None
        self._current_mode = 'apps'  

        content = self.get_content_area()


        mode_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        mode_bar.set_margin_top(10)
        mode_bar.set_margin_bottom(6)
        mode_bar.set_margin_start(12)
        mode_bar.set_margin_end(12)
        mode_bar.get_style_context().add_class('linked')

        self._btn_apps    = Gtk.ToggleButton(label=tr('picker_tab_apps'))
        self._btn_files   = Gtk.ToggleButton(label=tr('picker_tab_files'))
        self._btn_folders = Gtk.ToggleButton(label=tr('picker_tab_folders'))

        for btn in (self._btn_apps, self._btn_files, self._btn_folders):
            btn.set_size_request(140, 34)
        self._btn_apps.set_active(True)

        self._btn_apps.connect('toggled',    self._on_mode_toggled, 'apps')
        self._btn_files.connect('toggled',   self._on_mode_toggled, 'files')
        self._btn_folders.connect('toggled', self._on_mode_toggled, 'folders')

        mode_bar.pack_start(self._btn_apps,    True, True, 0)
        mode_bar.pack_start(self._btn_files,   True, True, 0)
        mode_bar.pack_start(self._btn_folders, True, True, 0)
        content.pack_start(mode_bar, False, False, 0)


        self._search_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._search_bar.set_margin_bottom(4)
        self._search_bar.set_margin_start(12)
        self._search_bar.set_margin_end(12)
        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text(tr('app_picker_search'))
        self._search_entry.set_hexpand(True)
        self._search_entry.connect('search-changed', self._on_search_changed)
        self._search_bar.pack_start(self._search_entry, True, True, 0)
        content.pack_start(self._search_bar, False, False, 0)

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(120)
        self._stack.set_hexpand(True)
        self._stack.set_vexpand(True)

        apps_scroll = Gtk.ScrolledWindow()
        apps_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        apps_scroll.set_margin_start(8)
        apps_scroll.set_margin_end(8)
        apps_scroll.set_margin_bottom(8)
        self._flowbox = Gtk.FlowBox()
        self._flowbox.set_valign(Gtk.Align.START)
        self._flowbox.set_max_children_per_line(20)
        self._flowbox.set_min_children_per_line(3)
        self._flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._flowbox.set_homogeneous(True)
        self._flowbox.set_row_spacing(4)
        self._flowbox.set_column_spacing(4)
        self._flowbox.set_margin_top(6)
        self._flowbox.set_margin_bottom(6)
        self._flowbox.set_margin_start(6)
        self._flowbox.set_margin_end(6)
        apps_scroll.add(self._flowbox)
        self._stack.add_named(apps_scroll, 'apps')

        self._files_panel = self._build_list_panel('files')
        self._stack.add_named(self._files_panel, 'files')

        self._folders_panel = self._build_list_panel('folders')
        self._stack.add_named(self._folders_panel, 'folders')

        content.pack_start(self._stack, True, True, 0)
        content.show_all()

        self._load_apps()
        self._rebuild_grid()
        self._stack.set_visible_child_name('apps')


    def _on_mode_toggled(self, btn, mode):
        if not btn.get_active():
            return

        for b, m in ((self._btn_apps, 'apps'), (self._btn_files, 'files'), (self._btn_folders, 'folders')):
            if m != mode and b.get_active():
                b.handler_block_by_func(self._on_mode_toggled)
                b.set_active(False)
                b.handler_unblock_by_func(self._on_mode_toggled)
        self._current_mode = mode
        self._selected_path = None
        self._selected_vbox = None
        self._search_bar.set_visible(mode == 'apps')
        self._stack.set_visible_child_name(mode)
        if mode == 'files':
            self._populate_list_panel(self._files_panel, 'files')
        elif mode == 'folders':
            self._populate_list_panel(self._folders_panel, 'folders')


    def _build_list_panel(self, kind):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.set_margin_start(10)
        scroll.set_margin_end(10)
        scroll.set_margin_top(4)
        scroll.set_margin_bottom(4)

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        listbox.set_activate_on_single_click(True)
        listbox.get_style_context().add_class('essorafm-picker-listbox')
        listbox.connect('row-activated', self._on_list_row_activated, kind)
        scroll.add(listbox)
        outer.pack_start(scroll, True, True, 0)

        browse_key = 'picker_browse_folder' if kind == 'folders' else 'picker_browse_file'
        browse_btn = Gtk.Button()
        browse_btn.set_margin_start(12)
        browse_btn.set_margin_end(12)
        browse_btn.set_margin_top(4)
        browse_btn.set_margin_bottom(10)
        browse_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        browse_icon = Gtk.Image.new_from_icon_name('document-open-symbolic', Gtk.IconSize.MENU)
        browse_lbl  = Gtk.Label(label=tr(browse_key))
        browse_hbox.pack_start(browse_icon, False, False, 0)
        browse_hbox.pack_start(browse_lbl, False, False, 0)
        browse_hbox.set_halign(Gtk.Align.CENTER)
        browse_btn.add(browse_hbox)
        browse_btn.connect('clicked', self._on_browse_panel_clicked, kind)
        outer.pack_start(browse_btn, False, False, 0)

        outer._listbox = listbox
        return outer

    def _populate_list_panel(self, panel, kind):
        listbox = panel._listbox
        for row in list(listbox.get_children()):
            listbox.remove(row)

        icon_theme = Gtk.IconTheme.get_default()
        entries = self._COMMON_FOLDERS if kind == 'folders' else self._COMMON_FILES

        for raw_path, icon_name, label in entries:
            real_path = os.path.expanduser(raw_path)
            if not os.path.exists(real_path):
                continue
            row = Gtk.ListBoxRow()
            row._picker_path = real_path
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            hbox.set_margin_top(6)
            hbox.set_margin_bottom(6)
            hbox.set_margin_start(10)
            hbox.set_margin_end(10)

            pix = None
            try:
                pix = icon_theme.load_icon(icon_name, 32, Gtk.IconLookupFlags.FORCE_SIZE)
            except Exception:
                pass
            if pix:
                img = Gtk.Image.new_from_pixbuf(pix)
            else:
                fallback = 'folder' if kind == 'folders' else 'text-x-generic'
                img = Gtk.Image.new_from_icon_name(fallback, Gtk.IconSize.DND)
            hbox.pack_start(img, False, False, 0)

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            name_lbl = Gtk.Label(label=label)
            name_lbl.set_halign(Gtk.Align.START)
            path_lbl = Gtk.Label(label=real_path)
            path_lbl.set_halign(Gtk.Align.START)
            path_lbl.get_style_context().add_class('dim-label')
            path_lbl.set_ellipsize(3)
            vbox.pack_start(name_lbl, False, False, 0)
            vbox.pack_start(path_lbl, False, False, 0)
            hbox.pack_start(vbox, True, True, 0)

            row.add(hbox)
            listbox.add(row)

        listbox.show_all()

    def _on_list_row_activated(self, listbox, row, kind):
        if row is None:
            return
        path = getattr(row, '_picker_path', None)
        if path:
            self._selected_path = path
            if self._selected_vbox is not None:
                self._selected_vbox.get_style_context().remove_class('essorafm-app-picker-selected')
            self._selected_vbox = None

    def _on_browse_panel_clicked(self, _btn, kind):
        if kind == 'folders':
            action = Gtk.FileChooserAction.SELECT_FOLDER
            title  = tr('select_folder')
        else:
            action = Gtk.FileChooserAction.OPEN
            title  = tr('browse')
        fc = Gtk.FileChooserDialog(title=title, transient_for=self, action=action)
        fc.add_buttons(tr('cancel'), Gtk.ResponseType.CANCEL,
                       tr('open'), Gtk.ResponseType.OK)
        fc.set_current_folder(os.path.expanduser('~'))
        if fc.run() == Gtk.ResponseType.OK:
            self._selected_path = fc.get_filename()
            fc.destroy()
            self.response(Gtk.ResponseType.OK)
        else:
            fc.destroy()


    def _load_apps(self):
        icon_theme = Gtk.IconTheme.get_default()
        apps = {}
        for d in self.APP_DIRS:
            if not os.path.isdir(d):
                continue
            for fname in sorted(os.listdir(d)):
                if not fname.endswith('.desktop'):
                    continue
                path = os.path.join(d, fname)
                entry = self._parse_desktop(path)
                if not entry:
                    continue
                key = fname.lower()
                if key not in apps:
                    apps[key] = (entry['name'], path, self._load_icon(icon_theme, entry.get('icon', '')))

        self._all_apps = sorted(apps.values(), key=lambda x: x[0].lower())
        self._filtered = list(self._all_apps)

    def _parse_desktop(self, path):
        try:
            kf = GLib.KeyFile()
            kf.load_from_file(path, GLib.KeyFileFlags.NONE)
            try:
                t = kf.get_string('Desktop Entry', 'Type')
                if t not in ('Application', 'Link'):
                    return None
            except Exception:
                pass
            try:
                no_display = kf.get_boolean('Desktop Entry', 'NoDisplay')
                if no_display:
                    return None
            except Exception:
                pass
            try:
                hidden = kf.get_boolean('Desktop Entry', 'Hidden')
                if hidden:
                    return None
            except Exception:
                pass
            name = ''
            try:
                name = kf.get_locale_string('Desktop Entry', 'Name', None) or ''
            except Exception:
                pass
            if not name:
                try:
                    name = kf.get_string('Desktop Entry', 'Name')
                except Exception:
                    return None
            icon = ''
            try:
                icon = kf.get_locale_string('Desktop Entry', 'Icon', None) or ''
            except Exception:
                pass
            if not icon:
                try:
                    icon = kf.get_string('Desktop Entry', 'Icon')
                except Exception:
                    pass
            return {'name': name.strip(), 'icon': icon.strip()}
        except Exception:
            return None

    def _load_icon(self, icon_theme, icon_name):
        if not icon_name:
            return self._fallback_pixbuf(icon_theme)
        if os.path.isabs(icon_name) and os.path.exists(icon_name):
            try:
                return GdkPixbuf.Pixbuf.new_from_file_at_size(icon_name, self.ICON_SIZE, self.ICON_SIZE)
            except Exception:
                pass
        for size in (self.ICON_SIZE, 48, 32):
            try:
                pix = icon_theme.load_icon(icon_name, size, Gtk.IconLookupFlags.FORCE_SIZE)
                if pix:
                    return pix
            except Exception:
                pass
        base = os.path.splitext(icon_name)[0]
        if base != icon_name:
            for size in (self.ICON_SIZE, 48, 32):
                try:
                    pix = icon_theme.load_icon(base, size, Gtk.IconLookupFlags.FORCE_SIZE)
                    if pix:
                        return pix
                except Exception:
                    pass
        return self._fallback_pixbuf(icon_theme)

    def _fallback_pixbuf(self, icon_theme):
        for name in ('application-x-executable', 'application-default-icon', 'gtk-execute'):
            try:
                pix = icon_theme.load_icon(name, self.ICON_SIZE, Gtk.IconLookupFlags.FORCE_SIZE)
                if pix:
                    return pix
            except Exception:
                pass
        return None


    def _rebuild_grid(self):
        """Vacía el FlowBox y lo repuebla con los apps filtrados."""
        for child in list(self._flowbox.get_children()):
            self._flowbox.remove(child)

        self._selected_vbox = None
        self._selected_path = None

        if not self._filtered:
            lbl = Gtk.Label(label=tr('app_picker_no_results'))
            lbl.set_margin_top(20)
            lbl.set_halign(Gtk.Align.CENTER)
            self._flowbox.add(lbl)
            self._flowbox.show_all()
            return

        for name, path, pixbuf in self._filtered:
            cell = self._make_cell(name, path, pixbuf)
            self._flowbox.add(cell)

        self._flowbox.show_all()

    def _make_cell(self, name, path, pixbuf):
        """Crea una celda clickeable: icono + nombre."""
        eb = Gtk.EventBox()
        eb.set_visible_window(False)
        eb.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        vbox.set_size_request(self.CELL_SIZE, self.CELL_SIZE + 30)
        vbox.set_halign(Gtk.Align.CENTER)
        vbox.set_margin_top(6)
        vbox.set_margin_bottom(6)
        vbox.set_margin_start(4)
        vbox.set_margin_end(4)

        if pixbuf:
            img = Gtk.Image.new_from_pixbuf(pixbuf)
        else:
            img = Gtk.Image.new_from_icon_name('application-x-executable', Gtk.IconSize.DIALOG)
        img.set_pixel_size(self.ICON_SIZE)
        img.set_halign(Gtk.Align.CENTER)
        vbox.pack_start(img, False, False, 0)

        lbl = Gtk.Label(label=name)
        lbl.set_max_width_chars(10)
        lbl.set_ellipsize(3)
        lbl.set_justify(Gtk.Justification.CENTER)
        lbl.set_line_wrap(True)
        lbl.set_lines(2)
        lbl.set_halign(Gtk.Align.CENTER)
        vbox.pack_start(lbl, False, False, 0)

        eb.add(vbox)
        eb.connect('button-press-event', self._on_cell_click, path, vbox)
        eb.set_tooltip_text(name)
        return eb

    def _on_cell_click(self, _widget, event, path, vbox):
        if event.button != 1:
            return False
        if self._selected_vbox is not None:
            self._selected_vbox.get_style_context().remove_class('essorafm-app-picker-selected')
        self._selected_path = path
        self._selected_vbox = vbox
        vbox.get_style_context().add_class('essorafm-app-picker-selected')
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            self.response(Gtk.ResponseType.OK)
        return True


    def _on_search_changed(self, entry):
        query = entry.get_text().strip().lower()
        if not query:
            self._filtered = list(self._all_apps)
        else:
            self._filtered = [(n, p, px) for n, p, px in self._all_apps if query in n.lower()]
        self._rebuild_grid()


    def get_selected_path(self):
        return self._selected_path


class EssoraDesktop(Gtk.Window):
    def __init__(self):
        super().__init__(title='EssoraFM Desktop')
        self.desktop_settings = DesktopDriveSettings()
        self.volume_service = VolumeService(parent_window=self)

        self.event_area = Gtk.EventBox()
        self.event_area.set_visible_window(True)
        self.event_area.set_above_child(False)
        self.event_area.set_can_focus(True)
        self.event_area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
        self.event_area.connect('button-press-event', self._on_desktop_button_press)
        self.event_area.connect('button-release-event', self._on_desktop_button_release)
        self.event_area.connect('draw', self._on_draw_wallpaper)

        self.fixed = Gtk.Fixed()
        self.fixed.set_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.fixed.connect('button-press-event', self._on_desktop_button_press)
        self.fixed.connect('button-release-event', self._on_desktop_button_release)
        self.event_area.add(self.fixed)
        self.add(self.event_area)

        self._wallpaper_pixbuf = None
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.connect('button-press-event', self._on_desktop_button_press)
        self.connect('button-release-event', self._on_desktop_button_release)
        self.connect('popup-menu', self._on_keyboard_popup_menu)
        self._reload_settings()
        self._configure_desktop_window()
        self._apply_css()

        for signal_name in (
            'mount-added', 'mount-removed', 'mount-changed', 'mount-pre-unmount',
            'volume-added', 'volume-removed', 'volume-changed',
            'drive-connected', 'drive-disconnected', 'drive-changed',
        ):
            try:
                self.volume_service.connect(signal_name, lambda *args: self._schedule_refresh(delay_ms=150))
            except Exception:
                pass

        self._drive_icons_process = None
        self._last_volume_signature = None
        self._configure_refresh_id = 0
        self.connect('destroy', self._on_destroy)
        self.connect('screen-changed', lambda *_: self._resize_to_screen())
        self.connect('configure-event', self._on_configure_event)
        self.connect('map-event', lambda *_: self._schedule_refresh(delay_ms=250))

        GLib.idle_add(self.refresh)
        GLib.timeout_add(600, self.refresh)
        GLib.timeout_add(1600, self.refresh)
        GLib.timeout_add_seconds(2, self._poll_volume_changes)

    def _reload_settings(self):
        self.desktop_settings.load()
        self.enabled = self.desktop_settings.get_bool('desktop_drive_icons', True)
        self.use_external_drive_icons = False
        self.show_internal = self.desktop_settings.get_bool('desktop_drive_show_internal', True)
        self.show_removable = self.desktop_settings.get_bool('desktop_drive_show_removable', True)
        self.show_network = self.desktop_settings.get_bool('desktop_drive_show_network', False)
        self.show_labels = self.desktop_settings.get_bool('ShowLabels', True)
        self.show_desktop_files = self.desktop_settings.get_bool('ShowDesktopFiles', True)
        self.icon_size = self.desktop_settings.get_int('desktop_drive_icon_size', 48)
        self.spacing_x = self.desktop_settings.get_int('SpacingX', 112)
        self.spacing_y = self.desktop_settings.get_int('SpacingY', 112)
        self.label_width = self.desktop_settings.get_int('LabelWidth', 12)
        self.xpos = self.desktop_settings.get_float('XPos', 0.010)
        self.ypos = self.desktop_settings.get_float('YPos', 0.990)
        self.xoffset = self.desktop_settings.get_int('XOffset', 0)
        self.yoffset = self.desktop_settings.get_int('YOffset', -40)
        self.label_lines = max(0, self.desktop_settings.get_int('NLines', 2))
        self.vertical = self.desktop_settings.get_bool('Vertical', False)
        self.reverse_pack = self.desktop_settings.get_bool('ReversePack', True)
        self.show_frame = self.desktop_settings.get_bool('ShowFrame', True)
        self.draw_shadow = self.desktop_settings.get_bool('DrawShadow', True)
        self.font_color = self.desktop_settings.get('FontColor', '#ffffffffffff') or '#ffffffffffff'
        self.shadow_color = self.desktop_settings.get('ShadowColor', '#000000000000') or '#000000000000'
        self.mount_action = "/usr/local/bin/essorafm '$dir'"
        self.umount_action = "/usr/local/bin/essorafm -D '$dir'"
        self.open_command = self.desktop_settings.get('OpenCommand', 'essorafm') or 'essorafm'
        self.pymenu_command = self.desktop_settings.get('PymenuCommand', '/usr/local/bin/pymenu') or '/usr/local/bin/pymenu'
        self.desktop_single_click = self.desktop_settings.get_bool('desktop_single_click', True)
        self.wallpaper = os.path.expanduser(self.desktop_settings.get('Wallpaper', '') or '')
        self.wallpaper_mode = self.desktop_settings.get('WallpaperMode', 'zoom') or 'zoom'
        self.wallpaper_directory = os.path.expanduser(self.desktop_settings.get('WallpaperDirectory', '/usr/share/backgrounds') or '/usr/share/backgrounds')
        self.desktop_dir = xdg_dir(XDG.DESKTOP)
        self.cell_w = max(96, self.icon_size + 58)
        self.cell_h = max(104, self.icon_size + 72)
        self.step_x = max(self.spacing_x, self.cell_w + 8)
        self.step_y = max(self.spacing_y, self.cell_h + 8)
        self.icon_loader = IconLoader(self.icon_size)
        self.sort_mode = self.desktop_settings.get('SortMode', 'name')
        self.sort_reverse = self.desktop_settings.get_bool('SortReverse', False)
        self.auto_arrange = self.desktop_settings.get_bool('AutoArrange', False)

    def _desktop_drive_icons_binary(self):
        return None

    def _ensure_drive_icons_config(self):
        self.desktop_settings.save()
        os.makedirs(CONFIG_DIR, exist_ok=True)

    def _sync_external_drive_icons(self):
        return False

    def _on_destroy(self, *_args):
        Gtk.main_quit()

    def _configure_desktop_window(self):
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_below(True)
        self.stick()
        self.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.set_app_paintable(True)
        self._resize_to_screen()

    def _resize_to_screen(self):
        screen = self.get_screen() or Gdk.Screen.get_default()
        if screen:
            self.move(0, 0)
            self.resize(screen.get_width(), screen.get_height())

    def _on_configure_event(self, *_args):
        self._schedule_refresh(delay_ms=120)
        return False

    def _schedule_refresh(self, delay_ms=250):
        if getattr(self, '_configure_refresh_id', 0):
            return False

        def _do_refresh():
            self._configure_refresh_id = 0
            self.refresh()
            return False

        self._configure_refresh_id = GLib.timeout_add(delay_ms, _do_refresh)
        return False

    def _poll_volume_changes(self):
        try:
            signature = self.volume_service.items_signature()
        except Exception:
            return True
        if signature != getattr(self, '_last_volume_signature', None):
            self._last_volume_signature = signature
            self.refresh()
        return True

    def _css_color(self, value, fallback):
        value = (value or '').strip()
        if value.startswith('#') and len(value) == 13:
            try:
                r = int(value[1:5], 16) // 257
                g = int(value[5:9], 16) // 257
                b = int(value[9:13], 16) // 257
                return f'#{r:02x}{g:02x}{b:02x}'
            except Exception:
                return fallback
        if value.startswith('#') and len(value) in (4, 7, 9):
            return value
        return fallback

    def _apply_css(self):
        font = self._css_color(getattr(self, 'font_color', '#ffffffffffff'), '#ffffff')
        shadow = self._css_color(getattr(self, 'shadow_color', '#000000000000'), '#000000')
        frame_css = 'background-color: rgba(0,0,0,0.30); border-radius: 5px; padding: 2px 4px;' if getattr(self, 'show_frame', True) else 'background-color: transparent; padding: 1px;'
        shadow_css = f'text-shadow: 1px 1px {shadow};' if getattr(self, 'draw_shadow', True) else ''
        css = f'''
        window {{ background-color: transparent; }}
        .essorafm-desktop-label {{ color: {font}; {shadow_css} {frame_css} }}
        eventbox:hover box {{ background-color: rgba(119,150,10,0.25); border-radius: 8px; }}
        .essorafm-eject-badge {{
            background-color: rgba(0, 0, 0, 0.65);
            color: #ffffff;
            border-radius: 999px;
            padding: 2px;
            border: 1px solid rgba(255, 255, 255, 0.55);
        }}
        .essorafm-app-picker-selected {{
            background-color: rgba(119,150,10,0.35);
            border-radius: 8px;
            border: 2px solid rgba(119,150,10,0.8);
        }}
        .essorafm-picker-listbox row {{
            border-radius: 6px;
            margin: 2px 4px;
        }}
        .essorafm-picker-listbox row:selected {{
            background-color: rgba(119,150,10,0.35);
        }}
        '''.encode('utf-8')
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _load_wallpaper(self):
        if not self.wallpaper or not os.path.exists(self.wallpaper):
            self._wallpaper_pixbuf = None
            return
        try:
            self._wallpaper_pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.wallpaper)
        except Exception:
            self._wallpaper_pixbuf = None

    def _sync_root_wallpaper(self):
        if not self.wallpaper or not os.path.exists(self.wallpaper):
            return
        commands = []
        if shutil.which('hsetroot'):
            commands.append(['hsetroot', '-fill', self.wallpaper])
        if shutil.which('feh'):
            commands.append(['feh', '--bg-fill', self.wallpaper])
        if shutil.which('xwallpaper'):
            commands.append(['xwallpaper', '--zoom', self.wallpaper])
        if shutil.which('nitrogen'):
            commands.append(['nitrogen', '--set-zoom-fill', self.wallpaper])
        for cmd in commands:
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                continue

    def _run_action(self, template, path):
        if not template or not path:
            return False
        command = template.replace('$dir', path).replace('$mountpoint', path)
        try:
            subprocess.Popen(shlex.split(command), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            try:
                subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except Exception:
                return False

    def _on_draw_wallpaper(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        if not self._wallpaper_pixbuf:
            cr.set_source_rgb(0.04, 0.05, 0.04)
            cr.rectangle(0, 0, width, height)
            cr.fill()
            return False
        pix = self._wallpaper_pixbuf
        pw, ph = pix.get_width(), pix.get_height()
        if pw <= 0 or ph <= 0 or width <= 0 or height <= 0:
            return False
        if self.wallpaper_mode == 'center':
            scaled = pix
            x = int((width - pw) / 2)
            y = int((height - ph) / 2)
        elif self.wallpaper_mode == 'stretch':
            scaled = pix.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
            x = y = 0
        else:
            scale = max(width / float(pw), height / float(ph))
            nw, nh = int(pw * scale), int(ph * scale)
            scaled = pix.scale_simple(nw, nh, GdkPixbuf.InterpType.BILINEAR)
            x = int((width - nw) / 2)
            y = int((height - nh) / 2)
        Gdk.cairo_set_source_pixbuf(cr, scaled, x, y)
        cr.paint()
        return False

    def _is_network_item(self, item):
        path = item.get('path') or ''
        uri = item.get('uri') or ''
        return uri.startswith(('smb:', 'ftp:', 'sftp:', 'dav:')) or path.startswith(('smb:', 'ftp:', 'sftp:', 'dav:'))

    def _is_removable_item(self, item):
        if item.get('removable') is True or item.get('is_usb') is True:
            return True
        volume = item.get('volume')
        try:
            drive = volume.get_drive() if volume else None
            if drive and (drive.is_media_removable() or drive.is_removable()):
                return True
        except Exception:
            pass
        name = (item.get('name') or '').lower()
        return any(word in name for word in ('usb', 'ventoy', 'pendrive', 'flash', 'sd card', 'removable'))

    def _is_technical_partition(self, item):
        if item.get('hidden_desktop') or item.get('hidden_sidebar'):
            return True
        fstype = (item.get('fstype') or '').lower()
        if fstype == 'swap':
            return True
        values_list = [item.get(k) for k in ('name', 'path', 'device', 'uuid', 'partlabel', 'parttype')]
        values = ' '.join(str(v or '').lower() for v in values_list)
        compact = ''.join(ch for ch in values if ch.isalnum())
        if 'vtoyefi' in compact:
            return True
        if '/boot/efi' in values or 'efi system' in values:
            return True
        for value in values_list:
            comp = ''.join(ch for ch in str(value or '').lower() if ch.isalnum())
            if comp in {'efi', 'esp', 'efisystempartition', 'vtoyefi', 'swap'}:
                return True
        if ' esp ' in f' {values} ':
            return True
        if (item.get('parttype') or '').lower() in (
            'c12a7328-f81f-11d2-ba4b-00a0c93ec93b',
            'ef00',
        ):
            return True
        return False

    def _filtered_items(self, items=None):
        if not self.enabled:
            return []
        if items is None:
            items = self.volume_service.list_sidebar_items()
        items = [i for i in items if i.get('kind') in ('mount', 'volume')]
        filtered = []
        for item in items:
            if item.get('hidden_desktop') or item.get('hidden_sidebar'):
                continue
            if self._is_technical_partition(item):
                continue
            is_network = self._is_network_item(item)
            is_removable = self._is_removable_item(item)
            if is_network and not self.show_network:
                continue
            if is_removable and not self.show_removable:
                continue
            if not is_network and not is_removable and not self.show_internal:
                continue
            filtered.append(item)
        return sorted(filtered, key=lambda item: (item.get('name') or '').lower())

    def _desktop_files(self):
        if not self.show_desktop_files or not os.path.isdir(self.desktop_dir):
            return []
        try:
            files = [
                os.path.join(self.desktop_dir, n)
                for n in os.listdir(self.desktop_dir)
                if not n.startswith('.')
            ]

            def sort_key(path):
                try:
                    if self.sort_mode == 'size':
                        return os.path.getsize(path)
                    if self.sort_mode == 'date':
                        return os.path.getmtime(path)
                    if self.sort_mode == 'type':
                        return os.path.splitext(path)[1].lower()
                    return os.path.basename(path).lower()
                except Exception:
                    return 0

            return sorted(files, key=sort_key, reverse=self.sort_reverse)
        except Exception:
            return []

    def _screen_size(self):
        screen = self.get_screen() or Gdk.Screen.get_default()
        screen_width = screen.get_width() if screen else 1024
        screen_height = screen.get_height() if screen else 768
        width = self.get_allocated_width()
        height = self.get_allocated_height()

        if width < 320:
            width = screen_width
        if height < 240:
            height = screen_height
        return max(1, width), max(1, height)

    def _desktop_anchor(self, width, height):
        """Return the top-left coordinate for the first drive icon cell.

        XPos/YPos are anchors like in the old desktop-drive-icons tool:
        0 = left/top and 1 = right/bottom.  Offsets are applied after anchoring.
        This makes XPos=0, YPos=1, YOffset=-40 place the first drive icon above
        the panel instead of clamping it on the bottom edge.
        """
        if self.xpos >= 0.5:
            base_x = width - self.cell_w + self.xoffset
        else:
            base_x = self.xoffset

        if self.ypos >= 0.5:
            base_y = height - self.cell_h + self.yoffset
        else:
            base_y = self.yoffset

        base_x = max(0, min(max(0, width - self.cell_w), base_x))
        base_y = max(0, min(max(0, height - self.cell_h), base_y))
        return base_x, base_y

    def _drive_position(self, index):
        width, height = self._screen_size()
        base_x, base_y = self._desktop_anchor(width, height)

        x_dir = -1 if self.xpos >= 0.5 else 1
        y_dir = -1 if self.ypos >= 0.5 else 1

        if self.vertical:
            available_y = (base_y + self.cell_h) if y_dir < 0 else (height - base_y)
            per_column = max(1, int(available_y // self.step_y))
            row = index % per_column
            col = index // per_column
            x = base_x + (col * self.step_x * x_dir)
            y = base_y + (row * self.step_y * y_dir)
        else:
            available_x = (base_x + self.cell_w) if x_dir < 0 else (width - base_x)
            per_row = max(1, int(available_x // self.step_x))
            col = index % per_row
            row = index // per_row
            x = base_x + (col * self.step_x * x_dir)
            y = base_y + (row * self.step_y * y_dir)

        x = max(0, min(max(0, width - self.cell_w), int(x)))
        y = max(0, min(max(0, height - self.cell_h), int(y)))
        return x, y

    def refresh(self):
        self._reload_settings()
        self._load_wallpaper()
        self._apply_css()
        self._sync_root_wallpaper()
        self.queue_draw()
        for child in list(self.fixed.get_children()):
            self.fixed.remove(child)

        sw, sh = self._screen_size()
        margin = 24

        rows_per_col = max(1, (sh - margin) // self.step_y)

        all_volume_items = self.volume_service.list_sidebar_items()
        self._last_volume_signature = self.volume_service.items_signature_from_items(all_volume_items)
        drive_items = self._filtered_items(all_volume_items)

        drive_cols_reserved = set()
        if drive_items:
            if self.xpos >= 0.5:
                total_cols = max(1, (sw - margin) // self.step_x)
                if self.vertical:
                    num_drives = len(drive_items)
                    cols_needed = max(1, (num_drives + rows_per_col - 1) // rows_per_col)
                    for c in range(total_cols - cols_needed, total_cols):
                        drive_cols_reserved.add(c)
                else:
                    drive_cols_reserved.add(total_cols - 1)

        def _all_grid_positions():
            positions = []
            col = 0
            while True:
                gx = margin + col * self.step_x
                if gx + self.cell_w > sw:
                    break
                if col not in drive_cols_reserved:
                    for row in range(rows_per_col):
                        gy = margin + row * self.step_y
                        if gy + self.cell_h <= sh:
                            positions.append((gx, gy))
                col += 1
            return positions

        grid_slots = _all_grid_positions()

        def _snap_to_slot(px, py):
            """Devuelve el índice del slot de grilla más cercano a (px, py)."""
            best_idx = 0
            best_dist = float('inf')
            for idx, (gx, gy) in enumerate(grid_slots):
                d = (px - gx) ** 2 + (py - gy) ** 2
                if d < best_dist:
                    best_dist = d
                    best_idx = idx
            return best_idx

        if self.auto_arrange:
            saved_pos = {}
        else:
            saved_pos = _load_icon_positions()
        desktop_files = list(self._desktop_files())

        occupied_slots = set()
        icon_assignments = {}  

        for path in desktop_files:
            key = os.path.basename(path)
            if key in saved_pos:
                ix, iy = saved_pos[key]
                ix = max(0, min(sw - self.cell_w, ix))
                iy = max(0, min(sh - self.cell_h, iy))
                icon_assignments[path] = (ix, iy)
                if grid_slots:
                    occupied_slots.add(_snap_to_slot(ix, iy))


        free_slots = [i for i in range(len(grid_slots)) if i not in occupied_slots]
        free_idx = 0
        for path in desktop_files:
            if path not in icon_assignments:
                if free_idx < len(free_slots):
                    slot = free_slots[free_idx]
                    free_idx += 1
                    icon_assignments[path] = grid_slots[slot]
                else:

                    if grid_slots:
                        lx, ly = grid_slots[-1]
                        icon_assignments[path] = (lx, ly + self.step_y * (free_idx - len(free_slots) + 1))
                    else:
                        icon_assignments[path] = (margin, margin)
                    free_idx += 1


        for path in desktop_files:
            icon = DesktopFileIcon(path, self)
            ix, iy = icon_assignments.get(path, (margin, margin))
            self.fixed.put(icon, int(ix), int(iy))
            icon.show_all()

        if self.reverse_pack:
            drive_items = list(reversed(drive_items))
        for idx, item in enumerate(drive_items):
            icon = DesktopDriveIcon(item, self)
            dx, dy = self._drive_position(idx)
            self.fixed.put(icon, dx, dy)
            icon.show_all()
        return False

    def open_desktop_file(self, path):
        target = self._resolve_desktop_link(path)

        if os.path.isdir(target):
            self.open_path(target)
            return

        try:
            app_info = Gio.DesktopAppInfo.new_from_filename(target)
            if app_info is not None:
                app_info.launch([], None)
                return
        except Exception:
            pass
        try:
            Gio.AppInfo.launch_default_for_uri(GLib.filename_to_uri(target, None), None)
        except Exception:
            try:
                subprocess.Popen(['xdg-open', target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as exc:
                self._error(str(exc))

    def _resolve_desktop_link(self, path):
        """Si el .desktop es Type=Link y URL apunta a otro .desktop existente
        o a una carpeta existente, devuelve esa ruta. En cualquier otro caso,
        devuelve la ruta original."""
        if not path.endswith('.desktop'):
            return path
        try:
            keyfile = GLib.KeyFile()
            keyfile.load_from_file(path, GLib.KeyFileFlags.NONE)
            try:
                entry_type = keyfile.get_string('Desktop Entry', 'Type')
            except Exception:
                entry_type = ''
            if entry_type != 'Link':
                return path
            try:
                url = keyfile.get_string('Desktop Entry', 'URL')
            except Exception:
                return path

            if url and os.path.isabs(url) and os.path.exists(url):
                if url.endswith('.desktop') or os.path.isdir(url):
                    return url
        except Exception:
            pass
        return path

    def popup_menu_for_desktop_file(self, path, event):
        menu = Gtk.Menu()
        open_item = Gtk.MenuItem(label=tr('open'))
        open_item.connect('activate', lambda *_: self.open_desktop_file(path))
        menu.append(open_item)
        remove_item = Gtk.MenuItem(label=tr('remove_desktop_icon'))
        remove_item.connect('activate', lambda *_: self._remove_desktop_icon(path))
        menu.append(remove_item)
        menu.append(Gtk.SeparatorMenuItem())
        refresh_item = Gtk.MenuItem(label=tr('refresh'))
        refresh_item.connect('activate', lambda *_: self.refresh())
        menu.append(refresh_item)
        menu.show_all()
        menu.popup_at_pointer(event)

    def _remove_desktop_icon(self, path):
        """Elimina un icono/archivo/carpeta/symlink del escritorio.

        - Symlinks (a carpetas o archivos): se elimina solo el symlink, nunca el target.
        - Archivos normales: se eliminan directamente.
        - Carpetas reales (no symlinks): se eliminan con shutil.rmtree solo si
          están dentro del directorio de escritorio, para no comprometer carpetas
          del sistema ni del home fuera del escritorio.
        """
        try:
            if os.path.islink(path):
                os.unlink(path)
                self.refresh()
                return

            if os.path.isdir(path):
                desktop_dir = os.path.realpath(self.desktop_dir)
                real_path   = os.path.realpath(path)
                if os.path.dirname(real_path) == desktop_dir:
                    shutil.rmtree(path)
                    self.refresh()
                else:
                    self._error(tr('remove_desktop_icon_folder_warning'))
                return

            os.remove(path)
            self.refresh()
        except Exception as exc:
            self._error(str(exc))

    def open_item(self, item):
        if item.get('mounted') and item.get('path'):
            self.open_path(item['path'])
            return
        self._mount_item(item, open_after=True)

    def _mount_item(self, item, open_after=False):
        if not item:
            return
        self.volume_service.mount_item(item, lambda ok, err: self._after_mount(ok, err, item, open_after=open_after))

    def open_path(self, path):
        if not path:
            return
        candidates = [
            '/usr/local/bin/essorafm',
            '/usr/local/essorafm/bin/essorafm',
            'python3 /usr/local/essorafm/essorafm.py',
            self.open_command,
        ]
        for cmd in candidates:
            try:
                if not cmd:
                    continue
                argv = shlex.split(cmd) if isinstance(cmd, str) else list(cmd)
                if not argv:
                    continue
                exe = argv[0]
                if os.path.isabs(exe) and not os.path.exists(exe):
                    continue
                subprocess.Popen(argv + [path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                continue
        try:
            Gio.AppInfo.launch_default_for_uri(GLib.filename_to_uri(path, None), None)
        except Exception:
            pass

    def _on_desktop_button_press(self, _widget, event):
        if getattr(event, 'button', 0) == 3:
            self.popup_desktop_menu(event)
            return True
        return False

    def _on_desktop_button_release(self, _widget, event):
        if getattr(event, 'button', 0) == 3:
            return True
        return False

    def _on_keyboard_popup_menu(self, _widget):
        self.popup_desktop_menu(None)
        return True

    def _set_sort_mode(self, _widget, mode):
        self.desktop_settings.update({'SortMode': mode})
        if self.auto_arrange:
            _clear_icon_positions()
        self.refresh()

    def _toggle_sort_reverse(self, _widget):
        new_val = not self.sort_reverse
        self.desktop_settings.update({'SortReverse': str(new_val).lower()})
        self.refresh()

    def _toggle_auto_arrange(self, _widget):
        new_val = not self.auto_arrange
        self.desktop_settings.update({'AutoArrange': str(new_val).lower()})
        if new_val:
            _clear_icon_positions()
        self.refresh()

    def popup_desktop_menu(self, event=None):
        menu = Gtk.Menu()
        applications = Gtk.MenuItem(label=tr('applications'))
        applications.connect('activate', lambda *_: self.launch_pymenu())
        menu.append(applications)
        menu.append(Gtk.SeparatorMenuItem())
        change_wallpaper = Gtk.MenuItem(label=tr('change_wallpaper'))
        change_wallpaper.connect('activate', lambda *_: self.choose_wallpaper())
        menu.append(change_wallpaper)
        add_icon = Gtk.MenuItem(label=tr('add_app_or_icon'))
        add_icon.connect('activate', lambda *_: self.add_icon_to_desktop())
        menu.append(add_icon)
        layout_item = Gtk.MenuItem(label=tr('desktop_icon_layout'))
        layout_item.connect('activate', lambda *_: self._show_layout_dialog())
        menu.append(layout_item)
        menu.append(Gtk.SeparatorMenuItem())

        sort_menu = Gtk.MenuItem(label=tr('desktop_sort_by'))
        submenu = Gtk.Menu()
        sort_options = [
            ('name', tr('desktop_sort_name')),
            ('size', tr('desktop_sort_size')),
            ('date', tr('desktop_sort_date')),
            ('type', tr('desktop_sort_type')),
        ]
        for mode, label in sort_options:
            item = Gtk.MenuItem(label=label)
            item.connect('activate', self._set_sort_mode, mode)
            submenu.append(item)
        sort_menu.set_submenu(submenu)
        menu.append(sort_menu)

        reverse_item = Gtk.CheckMenuItem(label=tr('desktop_sort_reverse'))
        reverse_item.set_active(self.sort_reverse)
        reverse_item.connect('toggled', self._toggle_sort_reverse)
        menu.append(reverse_item)

        auto_item = Gtk.CheckMenuItem(label=tr('desktop_auto_arrange'))
        auto_item.set_active(self.auto_arrange)
        auto_item.connect('toggled', self._toggle_auto_arrange)
        menu.append(auto_item)

        menu.append(Gtk.SeparatorMenuItem())
        refresh_item = Gtk.MenuItem(label=tr('refresh'))
        refresh_item.connect('activate', lambda *_: self.refresh())
        menu.append(refresh_item)
        menu.show_all()
        if event is not None:
            menu.popup_at_pointer(event)
        else:
            menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())

    def _show_layout_dialog(self):
        """Diálogo liviano con sliders para espaciado y tamaño de icono.

        Aplica los cambios en vivo mientras el usuario mueve los sliders y
        guarda al presionar Aplicar / cerrar con OK.  Cancelar restaura los
        valores anteriores.
        """

        orig = {
            'SpacingX':              self.desktop_settings.get_int('SpacingX', 112),
            'SpacingY':              self.desktop_settings.get_int('SpacingY', 112),
            'desktop_drive_icon_size': self.desktop_settings.get_int('desktop_drive_icon_size', 48),
        }
        DEFAULTS = {'SpacingX': 112, 'SpacingY': 112, 'desktop_drive_icon_size': 48}

        dialog = Gtk.Dialog(
            title=tr('desktop_layout_title'),
            transient_for=self,
            modal=True,
            use_header_bar=0,
        )
        dialog.set_default_size(420, 0)
        dialog.set_resizable(False)
        dialog.add_buttons(
            tr('cancel'),                Gtk.ResponseType.CANCEL,
            tr('desktop_layout_apply'),  Gtk.ResponseType.OK,
        )

        reset_btn = dialog.add_button(tr('desktop_layout_reset'), Gtk.ResponseType.REJECT)
        reset_btn.get_style_context().add_class('destructive-action')

        action_area = dialog.get_action_area()
        action_area.set_child_secondary(reset_btn, True)

        content = dialog.get_content_area()
        content.set_spacing(0)

        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(14)
        grid.set_margin_start(20)
        grid.set_margin_end(20)
        grid.set_margin_top(16)
        grid.set_margin_bottom(16)
        content.pack_start(grid, True, True, 0)

        def _make_row(label_text, key, min_val, max_val, step, row_idx):
            """Crea una fila: etiqueta | slider | valor en px."""
            lbl = Gtk.Label(label=label_text, xalign=0)
            lbl.get_style_context().add_class('dim-label')
            grid.attach(lbl, 0, row_idx, 1, 1)

            adj = Gtk.Adjustment(
                value=self.desktop_settings.get_int(key, DEFAULTS[key]),
                lower=min_val, upper=max_val,
                step_increment=step, page_increment=step * 4,
            )
            scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
            scale.set_hexpand(True)
            scale.set_draw_value(False)
            scale.set_round_digits(0)

            for mark in range(min_val, max_val + 1, step * 4):
                scale.add_mark(mark, Gtk.PositionType.BOTTOM, None)
            grid.attach(scale, 1, row_idx, 1, 1)

            val_lbl = Gtk.Label(label=f'{int(adj.get_value())} {tr("desktop_layout_px")}')
            val_lbl.set_width_chars(7)
            val_lbl.set_xalign(1)
            grid.attach(val_lbl, 2, row_idx, 1, 1)

            def _on_value_changed(adj, vl=val_lbl, k=key):
                v = int(adj.get_value())
                vl.set_text(f'{v} {tr("desktop_layout_px")}')
                self.desktop_settings.update({k: str(v)})
                self.refresh()

            adj.connect('value-changed', _on_value_changed)
            return adj

        adj_size = _make_row(
            tr('desktop_layout_icon_size'), 'desktop_drive_icon_size',
            min_val=24, max_val=96, step=8, row_idx=0,
        )

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(4)
        sep.set_margin_bottom(4)
        grid.attach(sep, 0, 1, 3, 1)

        adj_sx = _make_row(
            tr('desktop_layout_spacing_h'), 'SpacingX',
            min_val=80, max_val=240, step=8, row_idx=2,
        )
        adj_sy = _make_row(
            tr('desktop_layout_spacing_v'), 'SpacingY',
            min_val=80, max_val=240, step=8, row_idx=3,
        )

        content.show_all()

        def _apply_all():
            self.desktop_settings.update({
                'desktop_drive_icon_size': str(int(adj_size.get_value())),
                'SpacingX': str(int(adj_sx.get_value())),
                'SpacingY': str(int(adj_sy.get_value())),
            })
            self.refresh()

        def _reset_all():
            adj_size.set_value(DEFAULTS['desktop_drive_icon_size'])
            adj_sx.set_value(DEFAULTS['SpacingX'])
            adj_sy.set_value(DEFAULTS['SpacingY'])
            _apply_all()

        response = None

        def _on_response(dlg, resp):
            nonlocal response
            response = resp

        dialog.connect('response', _on_response)

        dialog.connect('response', lambda dlg, resp: _reset_all() if resp == Gtk.ResponseType.REJECT else None)

        while True:
            resp = dialog.run()
            if resp == Gtk.ResponseType.REJECT:
                continue
            break

        if resp == Gtk.ResponseType.OK:
            _apply_all()
        else:
            self.desktop_settings.update({k: str(v) for k, v in orig.items()})
            self.refresh()

        dialog.destroy()

    def launch_pymenu(self):
        try:
            if os.path.exists(self.pymenu_command) and os.access(self.pymenu_command, os.X_OK):
                subprocess.Popen([self.pymenu_command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(shlex.split(self.pymenu_command), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as exc:
            self._error(str(exc))

    def choose_wallpaper(self):
        wdir = self.wallpaper_directory
        if not os.path.isdir(wdir):
            wdir = '/usr/share/backgrounds'
        dialog = WallpaperCarouselDialog(
            parent=self,
            wallpaper_directory=wdir,
            current_wallpaper=self.wallpaper,
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            path = dialog.get_selected_path()
            new_dir = dialog.get_directory()
            if path:
                self.desktop_settings.update({
                    'Wallpaper': path,
                    'WallpaperMode': self.wallpaper_mode,
                    'WallpaperDirectory': new_dir,
                })
                self.refresh()
        dialog.destroy()

    def add_icon_to_desktop(self):
        dialog = AppPickerDialog(parent=self)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            src = dialog.get_selected_path()
            if src:
                try:
                    os.makedirs(self.desktop_dir, exist_ok=True)
                    dest_name = os.path.basename(src.rstrip('/'))
                    dest = os.path.join(self.desktop_dir, dest_name)
                    if os.path.exists(dest) or os.path.islink(dest):
                        base, ext = os.path.splitext(dest)
                        i = 1
                        while os.path.exists(f'{base}-{i}{ext}') or os.path.islink(f'{base}-{i}{ext}'):
                            i += 1
                        dest = f'{base}-{i}{ext}'
                    if os.path.isdir(src) and not src.endswith('.desktop'):
                        os.symlink(src, dest)
                    elif src.endswith('.desktop'):
                        self._write_link_desktop(src, dest)
                    else:
                        shutil.copy2(src, dest)
                    if dest.endswith('.desktop'):
                        os.chmod(dest, os.stat(dest).st_mode | 0o755)
                    self.refresh()
                except Exception as exc:
                    self._error(str(exc))
        dialog.destroy()

    def _write_link_desktop(self, source_desktop, dest_path):
        """Crea en el escritorio un .desktop tipo Link delegando al original.

        En lugar de copiar las 80+ líneas de Name[xx]/Comment[xx] del .desktop
        de /usr/share/applications/, escribimos solo el nombre, comentario e
        icono del idioma activo (con fallback al genérico) y apuntamos al
        archivo original con URL=. Pymenu y EssoraFM saben seguir esa URL
        para mostrar y lanzar la app correctamente.
        """
        keyfile = GLib.KeyFile()
        try:
            keyfile.load_from_file(source_desktop, GLib.KeyFileFlags.NONE)
        except Exception:
            shutil.copy2(source_desktop, dest_path)
            return

        def _get(key):
            try:
                value = keyfile.get_locale_string('Desktop Entry', key, None)
                if value:
                    return value
            except Exception:
                pass
            try:
                return keyfile.get_string('Desktop Entry', key)
            except Exception:
                return ''

        name = _get('Name') or os.path.splitext(os.path.basename(source_desktop))[0]
        comment = _get('Comment')
        icon = _get('Icon')

        lines = ['[Desktop Entry]', 'Type=Link', f'Name={name}']
        if comment:
            lines.append(f'Comment={comment}')
        if icon:
            lines.append(f'Icon={icon}')
        lines.append(f'URL={source_desktop}')
        lines.append('')

        with open(dest_path, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(lines))

    def popup_menu_for_item(self, item, event):
        menu = Gtk.Menu()
        if item.get('path'):
            open_item = Gtk.MenuItem(label=tr('open'))
            open_item.connect('activate', lambda *_: self.open_path(item['path']))
            menu.append(open_item)
        if item.get('kind') == 'volume' and (item.get('volume') or item.get('device') or item.get('can_mount')):
            mount_item = Gtk.MenuItem(label=tr('mount'))
            mount_item.connect('activate', lambda *_: self._mount_item(item, open_after=False))
            menu.append(mount_item)
        if item.get('kind') == 'mount':
            if item.get('can_unmount'):
                unmount_item = Gtk.MenuItem(label=tr('unmount'))
                unmount_item.connect('activate', lambda *_: self._unmount_item(item))
                menu.append(unmount_item)
            if item.get('can_eject') and item.get('volume'):
                eject_item = Gtk.MenuItem(label=tr('eject'))
                eject_item.connect('activate', lambda *_: self.volume_service.eject_volume(item['volume'], self._after_eject))
                menu.append(eject_item)
        menu.append(Gtk.SeparatorMenuItem())
        refresh_item = Gtk.MenuItem(label=tr('refresh'))
        refresh_item.connect('activate', lambda *_: self.refresh())
        menu.append(refresh_item)
        menu.show_all()
        menu.popup_at_pointer(event)

    def _unmount_item(self, item):
        if not item:
            return
        self._run_action(self.umount_action, item.get('path') or '')
        self.volume_service.unmount_item(item, self._after_unmount)

    def unmount_item(self, item):
        """Wrapper público invocado desde el badge de eject sobre el icono del
        escritorio. Delega en la lógica interna de desmontaje."""
        self._unmount_item(item)

    def _after_mount(self, ok, error_text, original_item=None, open_after=False):
        self.refresh()
        if ok and open_after:
            if error_text and isinstance(error_text, str) and error_text.startswith('/'):
                self.open_path(error_text)
                return
            GLib.timeout_add(700, lambda: self._open_after_mount(original_item))
        elif not ok and error_text:
            self._error(error_text)

    def _open_after_mount(self, original_item=None):
        original_name = original_item.get('name') if original_item else None
        original_device = original_item.get('device') if original_item else None
        original_uuid = original_item.get('uuid') if original_item else None
        self.refresh()
        for item in self.volume_service.list_sidebar_items():
            if not (item.get('mounted') and item.get('path')):
                continue
            if original_device and item.get('device') == original_device:
                self.open_path(item['path'])
                return False
            if original_uuid and item.get('uuid') == original_uuid:
                self.open_path(item['path'])
                return False
            if original_name and item.get('name') == original_name:
                self.open_path(item['path'])
                return False
        if original_name:
            user = os.environ.get('USER') or os.path.basename(os.path.expanduser('~'))
            for base in (f'/media/{user}', f'/run/media/{user}'):
                candidate = os.path.join(base, original_name)
                if os.path.isdir(candidate):
                    self.open_path(candidate)
                    return False
        return False

    def _after_unmount(self, ok, error_text):
        self.refresh()
        if not ok and error_text:
            self._error(error_text)

    def _after_eject(self, ok, error_text):
        self.refresh()
        if not ok and error_text:
            self._error(error_text)

    def _setting_label(self, key):
        labels = {
            'desktop_drive_icons': tr('desktop_drive_icons'),
            'desktop_drive_show_internal': tr('desktop_drive_show_internal'),
            'desktop_drive_show_removable': tr('desktop_drive_show_removable'),
            'desktop_drive_show_network': tr('desktop_drive_show_network'),
            'ShowLabels': tr('desktop_show_labels'),
            'ShowDesktopFiles': tr('desktop_show_files'),
            'ShowFrame': tr('desktop_show_frame'),
            'Vertical': tr('desktop_vertical'),
            'ReversePack': tr('desktop_reverse_pack'),
            'DrawShadow': tr('desktop_draw_shadow'),
            'desktop_orientation': tr('desktop_orientation'),
            'XPos': tr('desktop_xpos'),
            'YPos': tr('desktop_ypos'),
            'XOffset': tr('desktop_xoffset'),
            'YOffset': tr('desktop_yoffset'),
            'NLines': tr('desktop_nlines'),
            'desktop_drive_icon_size': tr('desktop_drive_icon_size'),
            'SpacingX': tr('desktop_spacing_x'),
            'SpacingY': tr('desktop_spacing_y'),
            'LabelWidth': tr('desktop_label_width'),
            'FontColor': tr('desktop_font_color'),
            'ShadowColor': tr('desktop_shadow_color'),
            'MountAction': tr('desktop_mount_action'),
            'UMountAction': tr('desktop_umount_action'),
            'PymenuCommand': tr('desktop_pymenu_command'),
            'WallpaperDirectory': tr('desktop_wallpaper_directory'),
            'desktop_single_click': tr('desktop_open_single_click'),
        }
        value = labels.get(key, key)
        return value if value != key else key

    def _edit_desktop_drive_config(self):
        self.desktop_settings.load()
        dialog = Gtk.Dialog(title=tr('desktop_drive_config'), transient_for=self, flags=0,
                            buttons=(tr('cancel'), Gtk.ResponseType.CANCEL, tr('save'), Gtk.ResponseType.OK))
        dialog.set_default_size(620, 560)
        content = dialog.get_content_area()
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        grid = Gtk.Grid(column_spacing=10, row_spacing=8, margin=12)
        scroll.add(grid)
        content.pack_start(scroll, True, True, 0)

        checks = {}
        entries = {}
        row = 0

        info_top = Gtk.Label(label=tr('desktop_internal_notice'), xalign=0)
        info_top.set_line_wrap(True)
        grid.attach(info_top, 0, row, 2, 1)
        row += 1

        check_keys = (
            'desktop_drive_icons',
            'desktop_drive_show_internal',
            'desktop_drive_show_removable',
            'desktop_drive_show_network',
            'ShowLabels',
            'ShowDesktopFiles',
            'ShowFrame',
            'ReversePack',
            'DrawShadow',
        )
        for key in check_keys:
            chk = Gtk.CheckButton(label=self._setting_label(key))
            chk.set_active(self.desktop_settings.get_bool(key, False))
            checks[key] = chk
            grid.attach(chk, 0, row, 2, 1)
            row += 1

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(6)
        sep.set_margin_bottom(2)
        grid.attach(sep, 0, row, 2, 1)
        row += 1
        click_label = Gtk.Label(label=tr('desktop_click_section'), xalign=0)
        click_label.get_style_context().add_class('dim-label')
        grid.attach(click_label, 0, row, 2, 1)
        row += 1
        chk_sc = Gtk.CheckButton(label=tr('desktop_open_single_click'))
        chk_sc.set_active(self.desktop_settings.get_bool('desktop_single_click', True))
        chk_sc.set_tooltip_text(tr('desktop_open_single_click'))
        checks['desktop_single_click'] = chk_sc
        grid.attach(chk_sc, 0, row, 2, 1)
        row += 1

        grid.attach(Gtk.Label(label=tr('desktop_orientation'), xalign=0), 0, row, 1, 1)
        orientation_combo = Gtk.ComboBoxText()
        orientation_combo.append('horizontal', tr('desktop_orientation_horizontal'))
        orientation_combo.append('vertical', tr('desktop_orientation_vertical'))
        orientation_combo.set_active_id('vertical' if self.desktop_settings.get_bool('Vertical', False) else 'horizontal')
        grid.attach(orientation_combo, 1, row, 1, 1)
        row += 1

        entry_keys = (
            'XPos', 'YPos', 'XOffset', 'YOffset', 'NLines',
            'desktop_drive_icon_size', 'SpacingX', 'SpacingY', 'LabelWidth',
            'FontColor', 'ShadowColor', 'MountAction', 'UMountAction',
            'PymenuCommand', 'WallpaperDirectory'
        )
        locked = {'MountAction', 'UMountAction'}
        for key in entry_keys:
            grid.attach(Gtk.Label(label=self._setting_label(key), xalign=0), 0, row, 1, 1)
            ent = Gtk.Entry()
            ent.set_text(str(self.desktop_settings.get(key, '')))
            if key in locked:
                ent.set_editable(False)
                ent.set_sensitive(False)
                ent.set_tooltip_text(tr('desktop_action_locked'))
            entries[key] = ent
            grid.attach(ent, 1, row, 1, 1)
            row += 1

        info = Gtk.Label(label=f"{tr('config_file')}: {DESKTOP_DRIVES_CONFIG}", xalign=0)
        info.set_selectable(True)
        info.set_line_wrap(True)
        grid.attach(info, 0, row, 2, 1)

        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            data = {key: str(widget.get_active()).lower() for key, widget in checks.items()}
            data['Vertical'] = 'true' if orientation_combo.get_active_id() == 'vertical' else 'false'
            for key, widget in entries.items():
                if key not in locked:
                    data[key] = widget.get_text()
            data['MountAction'] = "/usr/local/bin/essorafm '$dir'"
            data['UMountAction'] = "/usr/local/bin/essorafm -D '$dir'"
            self.desktop_settings.update(data)
            self.refresh()
        dialog.destroy()

    def _show_config_path(self):
        self._edit_desktop_drive_config()

    def _error(self, text):
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, text)
        dialog.run()
        dialog.destroy()


def run_desktop():
    log_dir = os.path.join(os.path.expanduser('~'), '.cache', 'essorafm')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'desktop-mode.log')
    try:
        with open(log_path, 'a', encoding='utf-8') as log:
            log.write('starting essorafm --desktop\\n')
    except Exception:
        pass

    win = EssoraDesktop()
    win.show_all()

    Gtk.main()
