# EssoraFM
# Author: josejp2424 - GPL-3.0
import gi

gi.require_version('Gio', '2.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, GLib, Gtk


class VolumeService:
    def __init__(self, parent_window=None):
        self.monitor = Gio.VolumeMonitor.get()
        self.parent_window = parent_window

    def _mount_operation(self):
        try:
            return Gtk.MountOperation.new(self.parent_window)
        except Exception:
            return None

    def connect(self, signal_name, callback):
        return self.monitor.connect(signal_name, callback)

    def list_sidebar_items(self):
        items = []
        seen = set()
        for mount in self.monitor.get_mounts():
            root = mount.get_root()
            path = root.get_path() or root.get_uri()
            uri = root.get_uri()
            key = path or mount.get_name()
            seen.add(key)
            items.append({
                'kind': 'mount', 'name': mount.get_name(), 'path': path, 'uri': uri,
                'mount': mount, 'volume': mount.get_volume(), 'icon': mount.get_icon(),
                'mounted': True, 'can_unmount': mount.can_unmount(), 'can_eject': mount.can_eject(),
            })

        for volume in self.monitor.get_volumes():
            mount = volume.get_mount()
            if mount is not None:
                continue
            activation_root = volume.get_activation_root()
            path = activation_root.get_path() if activation_root else None
            uri = activation_root.get_uri() if activation_root else None
            key = path or volume.get_name()
            if key in seen:
                continue
            items.append({
                'kind': 'volume', 'name': volume.get_name(), 'path': path, 'uri': uri,
                'mount': None, 'volume': volume, 'icon': volume.get_icon(),
                'mounted': False, 'can_mount': volume.can_mount(), 'can_eject': volume.can_eject(),
            })

        items.sort(key=lambda item: item['name'].lower())
        return items

    def mount_volume(self, volume, callback):
        def _done(obj, result, user_data=None):
            ok = True
            error_text = None
            try:
                volume.mount_finish(result)
            except GLib.Error as exc:
                ok = False
                error_text = exc.message
            GLib.idle_add(callback, ok, error_text)

        volume.mount(0, self._mount_operation(), None, _done, None)

    def unmount_mount(self, mount, callback):
        def _done(obj, result, user_data=None):
            ok = True
            error_text = None
            try:
                if hasattr(mount, 'unmount_with_operation_finish'):
                    mount.unmount_with_operation_finish(result)
                else:
                    mount.unmount_finish(result)
            except GLib.Error as exc:
                ok = False
                error_text = exc.message
            GLib.idle_add(callback, ok, error_text)

        if hasattr(mount, 'unmount_with_operation'):
            mount.unmount_with_operation(0, self._mount_operation(), None, _done, None)
        else:
            mount.unmount(0, None, _done, None)

    def eject_volume(self, volume, callback):
        def _done(obj, result, user_data=None):
            ok = True
            error_text = None
            try:
                if hasattr(volume, 'eject_with_operation_finish'):
                    volume.eject_with_operation_finish(result)
                else:
                    volume.eject_finish(result)
            except GLib.Error as exc:
                ok = False
                error_text = exc.message
            GLib.idle_add(callback, ok, error_text)

        if hasattr(volume, 'eject_with_operation'):
            volume.eject_with_operation(0, self._mount_operation(), None, _done, None)
        else:
            volume.eject(0, None, _done, None)
