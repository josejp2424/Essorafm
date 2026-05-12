# EssoraFM
# Author: josejp2424 and Nilsonmorales - GPL-3.0
import json
import os
import subprocess
import threading
import gi

gi.require_version('Gio', '2.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, GLib, Gtk

from core.i18n import tr


class VolumeService:
    """Unified volume service for EssoraFM.

    EssoraFM uses this service both in the sidebar and in the desktop mode.
    The important point is that USB/internal detection is based on the real
    block device data from lsblk, not on the mount path.  Internal partitions
    mounted under /media must not receive the USB icon, while real USB devices
    such as Ventoy must appear on the desktop and refresh automatically.
    """

    TECHNICAL_PARTTYPES = {
        'c12a7328-f81f-11d2-ba4b-00a0c93ec93b',  
        'ef00',
    }

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

    def _themed_icon(self, names):
        if isinstance(names, str):
            names = [names]
        try:
            return Gio.ThemedIcon.new_from_names(names)
        except Exception:
            try:
                return Gio.ThemedIcon.new(names[0])
            except Exception:
                return None

    def removable_icon(self):
        return self._themed_icon([
            'media-removable-symbolic',
            'drive-removable-media-symbolic',
            'drive-removable-media-usb-symbolic',
            'drive-removable-media-usb',
            'drive-removable-media',
        ])

    def harddisk_icon(self):
        return self._themed_icon([
            'drive-harddisk-symbolic',
            'drive-harddisk',
            'drive-multidisk-symbolic',
            'drive-multidisk',
        ])

    def _volume_identifier(self, volume, kind):
        if not volume:
            return None
        try:
            value = volume.get_identifier(kind)
            return value or None
        except Exception:
            return None

    def _volume_device(self, volume):
        for kind in ('unix-device', 'unix_device', 'device'):
            value = self._volume_identifier(volume, kind)
            if value:
                return value
        return None

    def _volume_uuid(self, volume):
        for kind in ('uuid', 'filesystem-uuid'):
            value = self._volume_identifier(volume, kind)
            if value:
                return value
        return None

    def _volume_drive(self, volume):
        try:
            return volume.get_drive() if volume else None
        except Exception:
            return None

    def _drive_is_removable(self, drive):
        if not drive:
            return False
        try:
            if drive.is_removable() or drive.is_media_removable():
                return True
        except Exception:
            pass
        try:
            name = (drive.get_name() or '').lower()
            if any(word in name for word in ('usb', 'ventoy', 'flash', 'pendrive', 'removable')):
                return True
        except Exception:
            pass
        return False

    def _volume_is_removable(self, volume):
        return self._drive_is_removable(self._volume_drive(volume))

    def _first_mountpoint(self, value):
        if value is None:
            return None
        if isinstance(value, list):
            for item in value:
                if item and str(item).startswith('/'):
                    return item
            return None
        value = str(value).strip()
        if not value:
            return None
        for part in value.split('\n'):
            part = part.strip()
            if part and part.startswith('/'):
                return part
        return None

    def _compact(self, value):
        return ''.join(ch for ch in str(value or '').lower() if ch.isalnum())

    def _is_technical_data(self, name=None, path=None, device=None, uuid=None,
                           fstype=None, partlabel=None, parttype=None):
        fstype_l = (fstype or '').lower().strip()
        if fstype_l == 'swap':
            return True
        parttype_l = (parttype or '').lower().strip()
        if parttype_l in self.TECHNICAL_PARTTYPES:
            return True

        values = [name, path, device, uuid, partlabel, parttype]
        text = ' '.join(str(v or '').lower() for v in values)
        compact = self._compact(text)

        if 'vtoyefi' in compact:
            return True
        if '/boot/efi' in text:
            return True
        if 'efi system' in text:
            return True
        for value in values:
            comp = self._compact(value)
            if comp in {'efi', 'esp', 'efisystempartition', 'vtoyefi', 'swap'}:
                return True
        if ' esp ' in f' {text} ':
            return True
        return False

    def _name_looks_removable(self, name):
        name_l = (name or '').lower()
        return any(word in name_l for word in (
            'usb', 'ventoy', 'pendrive', 'flash', 'removable', 'sd card', 'memory card'
        ))

    def _boolish(self, value):
        return str(value or '').strip().lower() in {'1', 'true', 'yes', 'y'}

    def _lsblk_nodes(self, nodes, parent=None):
        for node in nodes or []:
            merged = dict(node)
            if parent:
                for key in ('rm', 'tran', 'model', 'hotplug'):
                    if merged.get(key) in (None, '', False) and parent.get(key) not in (None, ''):
                        merged[key] = parent.get(key)
                merged['_parent_path'] = parent.get('path') or parent.get('name')
                merged['_parent_name'] = parent.get('name') or parent.get('path')
            yield merged
            for child in self._lsblk_nodes(node.get('children') or [], merged):
                yield child

    def _load_lsblk(self):
        if not (os.path.exists('/bin/lsblk') or os.path.exists('/usr/bin/lsblk')):
            return []
        try:
            proc = subprocess.run(
                ['lsblk', '-J', '-p', '-o', 'NAME,PATH,LABEL,UUID,FSTYPE,MOUNTPOINTS,RM,TYPE,TRAN,MODEL,PARTLABEL,PARTTYPE,HOTPLUG,SIZE'],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=5,
            )
            if proc.returncode != 0 or not proc.stdout.strip():
                return []
            data = json.loads(proc.stdout)
            return list(self._lsblk_nodes(data.get('blockdevices', [])))
        except Exception:
            return []

    def _lsblk_is_removable(self, node):
        tran = (node.get('tran') or '').lower()
        return (
            self._boolish(node.get('rm')) or
            self._boolish(node.get('hotplug')) or
            tran in {'usb', 'mmc', 'sd'} or
            self._name_looks_removable(node.get('label')) or
            self._name_looks_removable(node.get('partlabel')) or
            self._name_looks_removable(node.get('model'))
        )

    def _key_values(self, *values):
        keys = []
        for value in values:
            if value is None:
                continue
            value = str(value).strip()
            if not value:
                continue
            keys.append(value)
            keys.append(value.lower())
        return keys

    def _gio_mount_records(self):
        records = []
        for mount in self.monitor.get_mounts():
            try:
                root = mount.get_root()
                path = root.get_path() or None
                uri = root.get_uri() or None
            except Exception:
                path = uri = None
            volume = None
            try:
                volume = mount.get_volume()
            except Exception:
                pass
            device = self._volume_device(volume)
            uuid = self._volume_uuid(volume)
            name = None
            try:
                name = mount.get_name()
            except Exception:
                pass
            records.append({
                'kind': 'mount', 'name': name, 'path': path, 'uri': uri,
                'mount': mount, 'volume': volume, 'device': device, 'uuid': uuid,
                'removable': self._volume_is_removable(volume),
                'gio_icon': mount.get_icon() if hasattr(mount, 'get_icon') else None,
            })
        for volume in self.monitor.get_volumes():
            try:
                if volume.get_mount() is not None:
                    continue
            except Exception:
                pass
            activation_root = None
            try:
                activation_root = volume.get_activation_root()
            except Exception:
                pass
            path = activation_root.get_path() if activation_root else None
            uri = activation_root.get_uri() if activation_root else None
            device = self._volume_device(volume)
            uuid = self._volume_uuid(volume)
            name = None
            try:
                name = volume.get_name()
            except Exception:
                pass
            records.append({
                'kind': 'volume', 'name': name, 'path': path, 'uri': uri,
                'mount': None, 'volume': volume, 'device': device, 'uuid': uuid,
                'removable': self._volume_is_removable(volume),
                'gio_icon': volume.get_icon() if hasattr(volume, 'get_icon') else None,
            })
        return records

    def _gio_index(self, records):
        index = {}
        for rec in records:
            for key in self._key_values(rec.get('device'), rec.get('uuid'), rec.get('path'), rec.get('uri'), rec.get('name')):
                index.setdefault(key, rec)
        return index

    def _match_gio(self, index, *, device=None, uuid=None, label=None, partlabel=None, mountpoint=None):
        for key in self._key_values(device, uuid, mountpoint, label, partlabel):
            if key in index:
                return index[key]
        return None

    def _volume_display_name(self, node, device):
        label = node.get('label') or None
        partlabel = node.get('partlabel') or None
        if label:
            return label
        if partlabel:
            return partlabel
        size = (node.get('size') or '').strip()
        if size:
            return f"Volume de {size}"
        return os.path.basename(str(device or 'Volume'))

    def _lsblk_item_from_node(self, node, gio_index, seen):
        typ = (node.get('type') or '').lower()
        if typ in {'loop', 'zram', 'ram'}:
            return None
        device = node.get('path') or node.get('name')
        if not device or not str(device).startswith('/dev/'):
            return None

        fstype = (node.get('fstype') or '').strip()
        mountpoint = self._first_mountpoint(node.get('mountpoints'))
        uuid = node.get('uuid') or None
        label = node.get('label') or None
        partlabel = node.get('partlabel') or None
        parttype = node.get('parttype') or None
        removable = self._lsblk_is_removable(node)

        if typ not in {'part', 'crypt', 'lvm', 'rom'} and not (fstype or mountpoint):
            return None
        if not (fstype or mountpoint or removable):
            return None

        hidden = self._is_technical_data(
            name=label or partlabel or node.get('model') or os.path.basename(device),
            path=mountpoint,
            device=device,
            uuid=uuid,
            fstype=fstype,
            partlabel=partlabel,
            parttype=parttype,
        )

        gio = self._match_gio(gio_index, device=device, uuid=uuid, label=label, partlabel=partlabel, mountpoint=mountpoint)
        if gio:
            if gio.get('path'):
                mountpoint = gio.get('path')
            removable = removable or bool(gio.get('removable'))

        name = self._volume_display_name(node, device)
        if gio and gio.get('name') and not (label or partlabel):
            name = gio.get('name')

        mounted = bool(mountpoint)
        icon = self.removable_icon() if removable else self.harddisk_icon()
        item = {
            'kind': 'mount' if mounted else 'volume',
            'name': name,
            'path': mountpoint,
            'uri': GLib.filename_to_uri(mountpoint, None) if mountpoint else None,
            'mount': gio.get('mount') if gio else None,
            'volume': gio.get('volume') if gio else None,
            'icon': icon,
            'mounted': mounted,
            'can_mount': not mounted,
            'can_unmount': mounted,
            'can_eject': removable,
            'device': device,
            'uuid': uuid,
            'fstype': fstype,
            'partlabel': partlabel,
            'parttype': parttype,
            'removable': removable,
            'is_usb': removable,
            'hidden_desktop': hidden,
            'hidden_sidebar': hidden,
            'source': 'lsblk',
        }

        identity_values = set(self._key_values(device, uuid, mountpoint, label, partlabel, item.get('uri'), name))
        if identity_values & seen:
            return None
        seen.update(identity_values)
        return item

    def _gio_only_item(self, rec, seen):
        identity_values = set(self._key_values(rec.get('device'), rec.get('uuid'), rec.get('path'), rec.get('uri'), rec.get('name')))
        if identity_values & seen:
            return None
        hidden = self._is_technical_data(name=rec.get('name'), path=rec.get('path'), device=rec.get('device'), uuid=rec.get('uuid'))
        removable = bool(rec.get('removable')) or self._name_looks_removable(rec.get('name'))
        mounted = rec.get('kind') == 'mount' and bool(rec.get('path'))
        icon = self.removable_icon() if removable else (rec.get('gio_icon') or self.harddisk_icon())
        item = {
            'kind': 'mount' if mounted else 'volume',
            'name': rec.get('name') or 'Volume',
            'path': rec.get('path'),
            'uri': rec.get('uri'),
            'mount': rec.get('mount'),
            'volume': rec.get('volume'),
            'icon': icon,
            'mounted': mounted,
            'can_mount': not mounted,
            'can_unmount': mounted,
            'can_eject': removable,
            'device': rec.get('device'),
            'uuid': rec.get('uuid'),
            'removable': removable,
            'is_usb': removable,
            'hidden_desktop': hidden,
            'hidden_sidebar': hidden,
            'source': 'gio',
        }
        seen.update(identity_values)
        return item

    def list_sidebar_items(self):
        items = []
        seen = set()
        gio_records = self._gio_mount_records()
        gio_index = self._gio_index(gio_records)

        for node in self._load_lsblk():
            item = self._lsblk_item_from_node(node, gio_index, seen)
            if item is not None:
                items.append(item)

        for rec in gio_records:
            item = self._gio_only_item(rec, seen)
            if item is not None:
                items.append(item)

        items = [item for item in items if not item.get('hidden_sidebar')]
        items.sort(key=lambda item: (0 if item.get('removable') else 1, (item.get('name') or '').lower()))
        return items

    def items_signature_from_items(self, items):
        rows = []
        for item in items or []:
            rows.append((
                item.get('kind'), item.get('name'), item.get('device'),
                item.get('uuid'), item.get('path'), bool(item.get('mounted')),
                bool(item.get('removable')), bool(item.get('hidden_sidebar')),
            ))
        return tuple(sorted(rows))

    def items_signature(self):
        return self.items_signature_from_items(self.list_sidebar_items())

    def _run_async(self, func):
        threading.Thread(target=func, daemon=True).start()

    def _parse_udisks_mount_path(self, text):
        text = (text or '').strip()
        marker = ' at '
        if marker in text:
            path = text.split(marker, 1)[1].strip()
            if path.endswith('.'):
                path = path[:-1]
            if path:
                return path
        return None

    def _which(self, cmd):
        """Return full path of cmd if found in PATH, else None."""
        try:
            result = subprocess.run(['which', cmd], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            path = result.stdout.strip()
            return path if path else None
        except Exception:
            return None

    def _run_udisksctl_mount(self, item, callback):
        device = item.get('device') if isinstance(item, dict) else None
        if not device:
            volume = item.get('volume') if isinstance(item, dict) else item
            device = self._volume_device(volume)
        if not device or not os.path.exists(device):
            GLib.idle_add(callback, False, 'No block device found for this volume')
            return

        def worker():
            if self._which('udisksctl'):
                try:
                    proc = subprocess.run(
                        ['udisksctl', 'mount', '-b', device],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
                    output = (proc.stdout or proc.stderr or '').strip()
                    if proc.returncode == 0:
                        mount_path = self._parse_udisks_mount_path(output)
                        GLib.idle_add(callback, True, mount_path)
                        return
                except Exception:
                    pass

            if self._which('gio'):
                try:
                    uri = 'file://' + device
                    proc = subprocess.run(
                        ['gio', 'mount', uri],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
                    if proc.returncode == 0:
                        GLib.idle_add(callback, True, None)
                        return
                except Exception:
                    pass

            if self._which('pkexec') and self._which('mount'):
                try:
                    import tempfile, re
                    label = os.path.basename(device)
                    mount_dir = os.path.join('/media', os.environ.get('USER', 'user'), label)
                    os.makedirs(mount_dir, exist_ok=True)
                    proc = subprocess.run(
                        ['pkexec', 'mount', device, mount_dir],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
                    if proc.returncode == 0:
                        GLib.idle_add(callback, True, mount_dir)
                        return
                    else:
                        err = (proc.stderr or proc.stdout or '').strip()
                        GLib.idle_add(callback, False, err or 'pkexec mount failed')
                        return
                except Exception as exc:
                    GLib.idle_add(callback, False, str(exc))
                    return

            GLib.idle_add(callback, False, tr('volumes_no_backend'))
        self._run_async(worker)

    def _run_udisksctl_unmount(self, item, callback):
        device = item.get('device') if isinstance(item, dict) else None
        if not device or not os.path.exists(device):
            GLib.idle_add(callback, False, 'No block device found for this volume')
            return

        def worker():
            if self._which('udisksctl'):
                try:
                    proc = subprocess.run(
                        ['udisksctl', 'unmount', '-b', device],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
                    if proc.returncode == 0:
                        GLib.idle_add(callback, True, None)
                        return
                    else:
                        err = (proc.stderr or proc.stdout or 'udisksctl unmount failed').strip()

                except Exception:
                    pass

            if self._which('gio'):
                try:
                    uri = 'file://' + device
                    proc = subprocess.run(
                        ['gio', 'mount', '--unmount', uri],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
                    if proc.returncode == 0:
                        GLib.idle_add(callback, True, None)
                        return
                except Exception:
                    pass

            if self._which('pkexec') and self._which('umount'):
                try:
                    proc = subprocess.run(
                        ['pkexec', 'umount', device],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
                    if proc.returncode == 0:
                        GLib.idle_add(callback, True, None)
                        return
                    else:
                        err = (proc.stderr or proc.stdout or '').strip()
                        GLib.idle_add(callback, False, err or 'pkexec umount failed')
                        return
                except Exception as exc:
                    GLib.idle_add(callback, False, str(exc))
                    return

            GLib.idle_add(callback, False, tr('volumes_no_backend'))
        self._run_async(worker)

    def mount_item(self, item, callback):
        if not item:
            GLib.idle_add(callback, False, 'Invalid volume')
            return
        volume = item.get('volume') if isinstance(item, dict) else item
        if volume and getattr(volume, 'can_mount', lambda: False)():
            def done(ok, result):
                if ok:
                    callback(True, result)
                else:
                    self._run_udisksctl_mount(item, callback)
            self.mount_volume(volume, done)
        else:
            self._run_udisksctl_mount(item, callback)

    def mount_volume(self, volume, callback):
        def _done(obj, result, user_data=None):
            ok = True
            result_text = None
            try:
                volume.mount_finish(result)
                try:
                    mount = volume.get_mount()
                    if mount:
                        root = mount.get_root()
                        result_text = root.get_path() or root.get_uri()
                except Exception:
                    result_text = None
            except GLib.Error as exc:
                ok = False
                result_text = exc.message
            GLib.idle_add(callback, ok, result_text)
        volume.mount(0, self._mount_operation(), None, _done, None)

    def unmount_item(self, item, callback):
        mount = item.get('mount') if isinstance(item, dict) else item
        if mount:
            self.unmount_mount(mount, callback)
        else:
            self._run_udisksctl_unmount(item, callback)

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
        if not volume:
            GLib.idle_add(callback, False, 'No volume object available')
            return
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
