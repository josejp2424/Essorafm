#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# EssoraFM Desktop mode
# Original implementation for EssoraFM by josejp2424.
# Desktop control, wallpaper, desktop icons and drive icons.
# This uses GIO/GVolumeMonitor and EssoraFM's own config in ~/.config/essorafm/.
# EssoraFM
# Author: josejp2424 - GPL-3.0
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


class DesktopDriveIcon(Gtk.EventBox):
    def __init__(self, item, desktop):
        super().__init__()
        self.item = item
        self.desktop = desktop
        self.set_visible_window(False)
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.connect('button-press-event', self._on_button_press)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_size_request(self.desktop.cell_w, self.desktop.cell_h)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        self.add(box)

        pix = self.desktop.icon_loader._load_from_gicon(item.get('icon'), self.desktop.icon_size)
        image = Gtk.Image.new_from_pixbuf(pix) if pix else Gtk.Image.new_from_icon_name('drive-harddisk', Gtk.IconSize.DIALOG)
        image.set_pixel_size(self.desktop.icon_size)
        box.pack_start(image, False, False, 0)

        if self.desktop.show_labels:
            label = Gtk.Label(label=item.get('name') or 'Drive')
            label.set_line_wrap(True)
            label.set_justify(Gtk.Justification.CENTER)
            label.set_max_width_chars(self.desktop.label_width)
            label.set_ellipsize(3)
            label.get_style_context().add_class('essorafm-desktop-label')
            box.pack_start(label, False, False, 0)

        path = item.get('path') or ''
        self.set_tooltip_text(f"{item.get('name')}\n{path if item.get('mounted') and path else tr('not_mounted')}")

    def _on_button_press(self, _widget, event):
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and event.button == 1:
            self.desktop.open_item(self.item)
            return True
        if event.button == 3:
            self.desktop.popup_menu_for_item(self.item, event)
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
        label.set_justify(Gtk.Justification.CENTER)
        label.set_max_width_chars(self.desktop.label_width)
        label.set_ellipsize(3)
        label.get_style_context().add_class('essorafm-desktop-label')
        box.pack_start(label, False, False, 0)
        self.set_tooltip_text(path)

    def _display_name(self, path):
        name = os.path.basename(path)
        if name.endswith('.desktop'):
            try:
                keyfile = GLib.KeyFile()
                keyfile.load_from_file(path, GLib.KeyFileFlags.NONE)
                value = keyfile.get_locale_string('Desktop Entry', 'Name', None)
                if value:
                    return value
            except Exception:
                pass
            return name[:-8]
        return name

    def _gicon_for_path(self, path):
        if path.endswith('.desktop'):
            try:
                keyfile = GLib.KeyFile()
                keyfile.load_from_file(path, GLib.KeyFileFlags.NONE)
                icon = keyfile.get_string('Desktop Entry', 'Icon')
                if icon:
                    if os.path.isabs(icon) and os.path.exists(icon):
                        return Gio.FileIcon.new(Gio.File.new_for_path(icon))
                    return Gio.ThemedIcon.new(icon)
            except Exception:
                pass
        try:
            info = Gio.File.new_for_path(path).query_info('standard::icon', Gio.FileQueryInfoFlags.NONE, None)
            icon = info.get_icon()
            if icon:
                return icon
        except Exception:
            pass
        return Gio.ThemedIcon.new('text-x-generic')

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

        for signal_name in ('mount-added', 'mount-removed', 'volume-added', 'volume-removed', 'volume-changed', 'mount-changed'):
            self.volume_service.connect(signal_name, lambda *args: GLib.idle_add(self.refresh))

        self._drive_icons_process = None
        self.connect('destroy', self._on_destroy)
        self.connect('screen-changed', lambda *_: self._resize_to_screen())
        self.refresh()

    def _reload_settings(self):
        self.desktop_settings.load()
        self.enabled = self.desktop_settings.get_bool('Enabled', True)
        self.use_external_drive_icons = self.desktop_settings.get_bool('UseExternalDriveIcons', True)
        self.show_internal = self.desktop_settings.get_bool('ShowInternal', True)
        self.show_removable = self.desktop_settings.get_bool('ShowRemovable', True)
        self.show_network = self.desktop_settings.get_bool('ShowNetwork', False)
        self.show_labels = self.desktop_settings.get_bool('ShowLabels', True)
        self.show_desktop_files = self.desktop_settings.get_bool('ShowDesktopFiles', True)
        self.icon_size = self.desktop_settings.get_int('IconSize', 48)
        self.spacing_x = self.desktop_settings.get_int('SpacingX', 112)
        self.spacing_y = self.desktop_settings.get_int('SpacingY', 112)
        self.label_width = self.desktop_settings.get_int('LabelWidth', 12)
        self.xpos = self.desktop_settings.get_float('XPos', 0.010)
        self.ypos = self.desktop_settings.get_float('YPos', 0.990)
        self.xoffset = self.desktop_settings.get_int('XOffset', 0)
        self.yoffset = self.desktop_settings.get_int('YOffset', -40)
        self.nlines = max(1, self.desktop_settings.get_int('NLines', 2))
        self.vertical = self.desktop_settings.get_bool('Vertical', False)
        self.reverse_pack = self.desktop_settings.get_bool('ReversePack', True)
        self.show_frame = self.desktop_settings.get_bool('ShowFrame', True)
        self.draw_shadow = self.desktop_settings.get_bool('DrawShadow', True)
        self.font_color = self.desktop_settings.get('FontColor', '#ffffffffffff') or '#ffffffffffff'
        self.shadow_color = self.desktop_settings.get('ShadowColor', '#000000000000') or '#000000000000'
        self.mount_action = self.desktop_settings.get('MountAction', "essorafm '$dir'") or "essorafm '$dir'"
        self.umount_action = self.desktop_settings.get('UMountAction', "essorafm -D '$dir'") or "essorafm -D '$dir'"
        self.open_command = self.desktop_settings.get('OpenCommand', 'essorafm') or 'essorafm'
        self.pymenu_command = self.desktop_settings.get('PymenuCommand', '/usr/local/bin/pymenu') or '/usr/local/bin/pymenu'
        self.wallpaper = os.path.expanduser(self.desktop_settings.get('Wallpaper', '') or '')
        self.wallpaper_mode = self.desktop_settings.get('WallpaperMode', 'zoom') or 'zoom'
        self.wallpaper_directory = os.path.expanduser(self.desktop_settings.get('WallpaperDirectory', '/usr/share/backgrounds') or '/usr/share/backgrounds')
        self.desktop_dir = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.cell_w = max(96, self.spacing_x - 8)
        self.cell_h = max(96, self.spacing_y - 8)
        self.icon_loader = IconLoader(self.icon_size)

    def _desktop_drive_icons_binary(self):
        local_bin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bin', 'desktop_drive_icons')
        if os.path.exists(local_bin) and os.access(local_bin, os.X_OK):
            return local_bin
        system_bin = shutil.which('desktop_drive_icons')
        return system_bin

    def _ensure_drive_icons_config(self):
        self.desktop_settings.save()
        os.makedirs(CONFIG_DIR, exist_ok=True)

        old_dir = os.path.join(os.path.expanduser('~'), '.config', 'desktop_drive_icons')
        old_cfg = os.path.join(old_dir, 'config.ini')
        os.makedirs(old_dir, exist_ok=True)
        try:
            if os.path.islink(old_cfg):
                if os.readlink(old_cfg) != DESKTOP_DRIVES_CONFIG:
                    os.unlink(old_cfg)
            elif os.path.exists(old_cfg):
                backup = old_cfg + '.bak'
                if not os.path.exists(backup):
                    shutil.copy2(old_cfg, backup)
                os.remove(old_cfg)
            if not os.path.exists(old_cfg):
                os.symlink(DESKTOP_DRIVES_CONFIG, old_cfg)
        except Exception:
            try:
                shutil.copy2(DESKTOP_DRIVES_CONFIG, old_cfg)
            except Exception:
                pass

    def _sync_external_drive_icons(self):
        binary = self._desktop_drive_icons_binary()
        log_dir = os.path.join(os.path.expanduser('~'), '.cache', 'essorafm')
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, 'desktop-drive-icons.log')

        should_run = bool(self.enabled and self.use_external_drive_icons and binary)
        if not should_run:
            if self._drive_icons_process and self._drive_icons_process.poll() is None:
                try:
                    self._drive_icons_process.terminate()
                except Exception:
                    pass
            self._drive_icons_process = None
            try:
                with open(log_path, 'a', encoding='utf-8') as log:
                    log.write('disabled or binary missing: enabled=%s external=%s binary=%s\n' % (self.enabled, self.use_external_drive_icons, binary))
            except Exception:
                pass
            return

        if self._drive_icons_process and self._drive_icons_process.poll() is None:
            return

        self._ensure_drive_icons_config()
        env = os.environ.copy()
        env['PATH'] = '/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin:' + env.get('PATH', '')
        if not env.get('DISPLAY'):
            env['DISPLAY'] = ':0'
        if not env.get('XAUTHORITY'):
            xauth = os.path.join(os.path.expanduser('~'), '.Xauthority')
            if os.path.exists(xauth):
                env['XAUTHORITY'] = xauth

        try:
            log = open(log_path, 'a', encoding='utf-8')
            log.write('starting desktop_drive_icons: %s\n' % binary)
            log.write('settings: %s\n' % DESKTOP_DRIVES_CONFIG)
            log.flush()
            self._drive_icons_process = subprocess.Popen([binary], stdout=log, stderr=log, env=env, cwd=os.path.expanduser('~'), close_fds=True)
        except Exception as exc:
            self._drive_icons_process = None
            try:
                with open(log_path, 'a', encoding='utf-8') as log:
                    log.write('ERROR launching desktop_drive_icons: %s\n' % exc)
            except Exception:
                pass

    def _on_destroy(self, *_args):
        if self._drive_icons_process and self._drive_icons_process.poll() is None:
            try:
                self._drive_icons_process.terminate()
            except Exception:
                pass
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
        volume = item.get('volume')
        try:
            drive = volume.get_drive() if volume else None
            if drive and (drive.is_media_removable() or drive.is_removable()):
                return True
        except Exception:
            pass
        name = (item.get('name') or '').lower()
        return any(word in name for word in ('usb', 'pendrive', 'flash', 'sd card'))

    def _filtered_items(self):
        if not self.enabled:
            return []
        items = [i for i in self.volume_service.list_sidebar_items() if i.get('kind') in ('mount', 'volume')]
        filtered = []
        for item in items:
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

    def _drive_position(self, index):
        screen = Gdk.Screen.get_default()
        width = self.get_allocated_width() or (screen.get_width() if screen else 1024)
        height = self.get_allocated_height() or (screen.get_height() if screen else 768)
        base_x = int(width * self.xpos) + self.xoffset
        base_y = int(height * self.ypos) + self.yoffset
        line = index % self.nlines
        group = index // self.nlines
        if self.vertical:
            dx = group * self.spacing_x
            dy = line * self.spacing_y
        else:
            dx = line * self.spacing_x
            dy = group * self.spacing_y
        if self.reverse_pack:
            dx = -dx
            dy = -dy
        x = max(0, min(width - self.cell_w, base_x + dx))
        y = max(0, min(height - self.cell_h, base_y + dy))
        return x, y

    def refresh(self):
        self._reload_settings()
        self._sync_external_drive_icons()
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

        drive_items = [] if (self.use_external_drive_icons and self._desktop_drive_icons_binary()) else self._filtered_items()
        for idx, item in enumerate(drive_items):
            icon = DesktopDriveIcon(item, self)
            dx, dy = self._drive_position(idx)
            self.fixed.put(icon, dx, dy)
            icon.show_all()
        return False

    def open_desktop_file(self, path):
        try:
            Gio.AppInfo.launch_default_for_uri(GLib.filename_to_uri(path, None), None)
        except Exception:
            try:
                subprocess.Popen(['xdg-open', path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as exc:
                self._error(str(exc))

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
        volume = item.get('volume')
        if volume and item.get('can_mount', True):
            self.volume_service.mount_volume(volume, lambda ok, err: self._after_mount(ok, err, item, open_after=True))

    def open_path(self, path):
        if self._run_action(self.mount_action, path):
            return
        try:
            subprocess.Popen([self.open_command, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
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
        menu.append(Gtk.SeparatorMenuItem())
        config_item = Gtk.MenuItem(label=tr('desktop_drive_config'))
        config_item.connect('activate', lambda *_: self._edit_desktop_drive_config())
        menu.append(config_item)
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
        dialog = Gtk.FileChooserDialog(title=tr('change_wallpaper'), parent=self, action=Gtk.FileChooserAction.OPEN,
                                       buttons=(tr('cancel'), Gtk.ResponseType.CANCEL, tr('open'), Gtk.ResponseType.OK))
        filt = Gtk.FileFilter()
        filt.set_name('Images')
        for mime in ('image/png', 'image/jpeg', 'image/webp', 'image/bmp', 'image/svg+xml'):
            filt.add_mime_type(mime)
        dialog.add_filter(filt)
        if os.path.isdir(self.wallpaper_directory):
            dialog.set_current_folder(self.wallpaper_directory)
        elif os.path.isdir('/usr/share/backgrounds'):
            dialog.set_current_folder('/usr/share/backgrounds')
        if dialog.run() == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            self.desktop_settings.update({'Wallpaper': path, 'WallpaperMode': self.wallpaper_mode, 'WallpaperDirectory': os.path.dirname(path)})
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
                shutil.copy2(src, dest)
                if dest.endswith('.desktop'):
                    os.chmod(dest, os.stat(dest).st_mode | 0o755)
                self.refresh()
            except Exception as exc:
                self._error(str(exc))
        dialog.destroy()

    def popup_menu_for_item(self, item, event):
        menu = Gtk.Menu()
        if item.get('path'):
            open_item = Gtk.MenuItem(label=tr('open'))
            open_item.connect('activate', lambda *_: self.open_path(item['path']))
            menu.append(open_item)
        if item.get('kind') == 'volume' and item.get('volume') and item.get('can_mount', True):
            mount_item = Gtk.MenuItem(label=tr('mount'))
            mount_item.connect('activate', lambda *_: self.volume_service.mount_volume(item['volume'], lambda ok, err: self._after_mount(ok, err, item)))
            menu.append(mount_item)
        if item.get('kind') == 'mount' and item.get('mount'):
            if item.get('can_unmount'):
                unmount_item = Gtk.MenuItem(label=tr('unmount'))
                unmount_item.connect('activate', lambda *_: (self._run_action(self.umount_action, item.get('path') or ''), self.volume_service.unmount_mount(item['mount'], self._after_unmount)))
                menu.append(unmount_item)
            if item.get('can_eject') and item.get('volume'):
                eject_item = Gtk.MenuItem(label=tr('eject'))
                eject_item.connect('activate', lambda *_: self.volume_service.eject_volume(item['volume'], self._after_eject))
                menu.append(eject_item)
        menu.append(Gtk.SeparatorMenuItem())
        refresh_item = Gtk.MenuItem(label=tr('refresh'))
        refresh_item.connect('activate', lambda *_: self.refresh())
        menu.append(refresh_item)
        config_item = Gtk.MenuItem(label=tr('desktop_drive_config'))
        config_item.connect('activate', lambda *_: self._edit_desktop_drive_config())
        menu.append(config_item)
        menu.show_all()
        menu.popup_at_pointer(event)

    def _after_mount(self, ok, error_text, original_item=None, open_after=False):
        self.refresh()
        if ok and open_after:
            original_name = original_item.get('name') if original_item else None
            for item in self.volume_service.list_sidebar_items():
                if original_name and item.get('name') != original_name:
                    continue
                if item.get('mounted') and item.get('path'):
                    self.open_path(item['path'])
                    return
        elif not ok and error_text:
            self._error(error_text)

    def _after_unmount(self, ok, error_text):
        self.refresh()
        if not ok and error_text:
            self._error(error_text)

    def _after_eject(self, ok, error_text):
        self.refresh()
        if not ok and error_text:
            self._error(error_text)

    def _edit_desktop_drive_config(self):
        self.desktop_settings.load()
        dialog = Gtk.Dialog(title=tr('desktop_drive_config'), transient_for=self, flags=0,
                            buttons=(tr('cancel'), Gtk.ResponseType.CANCEL, tr('save'), Gtk.ResponseType.OK))
        dialog.set_default_size(560, 540)
        content = dialog.get_content_area()
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        grid = Gtk.Grid(column_spacing=10, row_spacing=8, margin=12)
        scroll.add(grid)
        content.pack_start(scroll, True, True, 0)

        checks = {}
        entries = {}
        row = 0
        for key in ('Enabled', 'UseExternalDriveIcons', 'ShowInternal', 'ShowRemovable', 'ShowNetwork', 'ShowLabels', 'ShowDesktopFiles', 'ShowFrame', 'Vertical', 'ReversePack', 'DrawShadow'):
            chk = Gtk.CheckButton(label=key)
            chk.set_active(self.desktop_settings.get_bool(key, False))
            checks[key] = chk
            grid.attach(chk, 0, row, 2, 1)
            row += 1

        for key in ('XPos', 'YPos', 'XOffset', 'YOffset', 'NLines', 'IconSize', 'SpacingX', 'SpacingY', 'LabelWidth', 'FontColor', 'ShadowColor', 'MountAction', 'UMountAction', 'PymenuCommand', 'WallpaperDirectory'):
            grid.attach(Gtk.Label(label=key, xalign=0), 0, row, 1, 1)
            ent = Gtk.Entry()
            ent.set_text(str(self.desktop_settings.get(key, '')))
            entries[key] = ent
            grid.attach(ent, 1, row, 1, 1)
            row += 1

        info = Gtk.Label(label=DESKTOP_DRIVES_CONFIG, xalign=0)
        info.set_selectable(True)
        grid.attach(info, 0, row, 2, 1)

        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            data = {key: str(widget.get_active()).lower() for key, widget in checks.items()}
            data.update({key: widget.get_text() for key, widget in entries.items()})
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

    GLib.idle_add(win._sync_external_drive_icons)

    Gtk.main()
