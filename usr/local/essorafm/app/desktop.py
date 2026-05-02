#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# EssoraFM Desktop mode
# Original implementation for EssoraFM by josejp2424.
# Desktop control, wallpaper, desktop icons and drive icons.
# This uses GIO/GVolumeMonitor and EssoraFM's own config in ~/.config/essorafm/.
# EssoraFM
# Author: josejp2424 and Nilsonmorales - GPL-3.0
import os
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
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and event.button == 1:
            self.desktop.open_item(self.item)
            return True
        return False

    def _on_button_release(self, _widget, event):
        if event.button == 1:
            self.desktop.open_item(self.item)
            return True
        return False


class DesktopFileIcon(Gtk.EventBox):
    def __init__(self, path, desktop):
        super().__init__()
        self.path = path
        self.desktop = desktop
        self.set_visible_window(False)
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.connect('button-press-event', self._on_button_press)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_size_request(self.desktop.cell_w, self.desktop.cell_h)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        self.add(box)

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
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and event.button == 1:
            self.desktop.open_desktop_file(self.path)
            return True
        if event.button == 3:
            self.desktop.popup_menu_for_desktop_file(self.path, event)
            return True
        return False


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
        self.wallpaper = os.path.expanduser(self.desktop_settings.get('Wallpaper', '') or '')
        self.wallpaper_mode = self.desktop_settings.get('WallpaperMode', 'zoom') or 'zoom'
        self.wallpaper_directory = os.path.expanduser(self.desktop_settings.get('WallpaperDirectory', '/usr/share/backgrounds') or '/usr/share/backgrounds')
        self.desktop_dir = xdg_dir(XDG.DESKTOP)
        self.cell_w = max(96, self.icon_size + 58)
        self.cell_h = max(104, self.icon_size + 72)
        self.step_x = max(self.spacing_x, self.cell_w + 8)
        self.step_y = max(self.spacing_y, self.cell_h + 8)
        self.icon_loader = IconLoader(self.icon_size)

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
            return sorted([os.path.join(self.desktop_dir, n) for n in os.listdir(self.desktop_dir) if not n.startswith('.')], key=lambda p: os.path.basename(p).lower())
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

        x, y = 24, 24
        max_h = (self.get_allocated_height() or 768) - self.spacing_y
        for path in self._desktop_files():
            icon = DesktopFileIcon(path, self)
            self.fixed.put(icon, x, y)
            icon.show_all()
            y += self.spacing_y
            if y > max_h:
                y = 24
                x += self.spacing_x

        all_volume_items = self.volume_service.list_sidebar_items()
        self._last_volume_signature = self.volume_service.items_signature_from_items(all_volume_items)
        drive_items = self._filtered_items(all_volume_items)
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
        """Si el .desktop es Type=Link y URL apunta a otro .desktop existente,
        devuelve la ruta del .desktop apuntado. En cualquier otro caso,
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
            if url and url.endswith('.desktop') and os.path.isabs(url) and os.path.exists(url):
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
        try:
            if os.path.isdir(path):
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

    def popup_desktop_menu(self, event=None):
        menu = Gtk.Menu()
        applications = Gtk.MenuItem(label=tr('applications'))
        applications.connect('activate', lambda *_: self.launch_pymenu())
        menu.append(applications)
        menu.append(Gtk.SeparatorMenuItem())
        change_wallpaper = Gtk.MenuItem(label=tr('change_wallpaper'))
        change_wallpaper.connect('activate', lambda *_: self.choose_wallpaper())
        menu.append(change_wallpaper)
        add_icon = Gtk.MenuItem(label=tr('add_desktop_icon'))
        add_icon.connect('activate', lambda *_: self.add_icon_to_desktop())
        menu.append(add_icon)
        refresh_item = Gtk.MenuItem(label=tr('refresh'))
        refresh_item.connect('activate', lambda *_: self.refresh())
        menu.append(refresh_item)
        menu.show_all()
        if event is not None:
            menu.popup_at_pointer(event)
        else:
            menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())

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
        dialog = Gtk.FileChooserDialog(title=tr('add_desktop_icon'), parent=self, action=Gtk.FileChooserAction.OPEN,
                                       buttons=(tr('cancel'), Gtk.ResponseType.CANCEL, tr('open'), Gtk.ResponseType.OK))
        if os.path.isdir('/usr/share/applications'):
            dialog.set_current_folder('/usr/share/applications')
        if dialog.run() == Gtk.ResponseType.OK:
            src = dialog.get_filename()
            try:
                os.makedirs(self.desktop_dir, exist_ok=True)
                dest = os.path.join(self.desktop_dir, os.path.basename(src))
                if os.path.exists(dest):
                    base, ext = os.path.splitext(dest)
                    i = 1
                    while os.path.exists(f'{base}-{i}{ext}'):
                        i += 1
                    dest = f'{base}-{i}{ext}'
                if src.endswith('.desktop'):
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
