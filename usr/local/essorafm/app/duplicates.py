# EssoraFM
# Author: josejp2424 - GPL-3.0
import hashlib
import os
import threading
from collections import defaultdict

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from core.i18n import tr


class DuplicateScannerDialog(Gtk.Dialog):
    COL_GROUP = 0
    COL_PATH = 1
    COL_SIZE = 2
    COL_KEEP = 3

    def __init__(self, parent, root_path):
        super().__init__(title=tr('duplicate_scanner'), transient_for=parent, modal=True)
        self.root_path = root_path
        self.cancelled = False
        self.set_default_size(780, 520)
        self.add_button(tr('close'), Gtk.ResponseType.CLOSE)
        self.delete_btn = self.add_button(tr('delete_selected'), Gtk.ResponseType.OK)
        self.delete_btn.set_sensitive(False)

        box = self.get_content_area()
        box.set_spacing(8)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(10)
        box.set_margin_end(10)

        self.info = Gtk.Label(label=tr('duplicate_scan_ready'), xalign=0)
        self.info.set_selectable(True)
        box.pack_start(self.info, False, False, 0)

        self.progress = Gtk.ProgressBar()
        box.pack_start(self.progress, False, False, 0)

        self.store = Gtk.ListStore(str, str, str, bool)
        self.tree = Gtk.TreeView(model=self.store)
        self.tree.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.tree.append_column(Gtk.TreeViewColumn(tr('group'), Gtk.CellRendererText(), text=self.COL_GROUP))
        path_col = Gtk.TreeViewColumn(tr('path'), Gtk.CellRendererText(), text=self.COL_PATH)
        path_col.set_expand(True)
        self.tree.append_column(path_col)
        self.tree.append_column(Gtk.TreeViewColumn(tr('size'), Gtk.CellRendererText(), text=self.COL_SIZE))
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.tree)
        box.pack_start(scroll, True, True, 0)

        hint = Gtk.Label(label=tr('duplicate_hint'), xalign=0)
        hint.set_line_wrap(True)
        box.pack_start(hint, False, False, 0)

        self.tree.get_selection().connect('changed', self._selection_changed)
        self.connect('response', self._on_response)
        self.show_all()
        self._start_scan()

    def _start_scan(self):
        thread = threading.Thread(target=self._scan_worker, daemon=True)
        thread.start()
        GLib.timeout_add(120, self._pulse)

    def _pulse(self):
        if self.cancelled:
            return False
        self.progress.pulse()
        return True

    def _scan_worker(self):
        try:
            GLib.idle_add(self.info.set_text, tr('duplicate_scanning'))
            by_size = defaultdict(list)
            for dirpath, dirnames, filenames in os.walk(self.root_path):
                if self.cancelled:
                    return
                dirnames[:] = [d for d in dirnames if d not in {'.git', '.cache', '__pycache__'}]
                for name in filenames:
                    path = os.path.join(dirpath, name)
                    try:
                        if os.path.islink(path):
                            continue
                        size = os.path.getsize(path)
                        if size <= 0:
                            continue
                        by_size[size].append(path)
                    except Exception:
                        continue
            candidates = {size: paths for size, paths in by_size.items() if len(paths) > 1}
            by_hash = defaultdict(list)
            total = sum(len(v) for v in candidates.values()) or 1
            done = 0
            for size, paths in candidates.items():
                for path in paths:
                    if self.cancelled:
                        return
                    digest = self._sha256(path)
                    done += 1
                    if digest:
                        by_hash[(size, digest)].append(path)
                    if done % 10 == 0:
                        GLib.idle_add(self.info.set_text, f"{tr('duplicate_hashing')} {done}/{total}")
            groups = [paths for paths in by_hash.values() if len(paths) > 1]
            GLib.idle_add(self._fill_results, groups)
        except Exception as exc:
            GLib.idle_add(self.info.set_text, str(exc))

    def _sha256(self, path):
        try:
            h = hashlib.sha256()
            with open(path, 'rb') as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b''):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return None

    def _human_size(self, size):
        value = float(size)
        for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
            if value < 1024 or unit == 'TB':
                return f'{value:.1f} {unit}' if unit != 'B' else f'{int(value)} B'
            value /= 1024

    def _fill_results(self, groups):
        self.cancelled = True
        self.progress.set_fraction(1.0)
        self.store.clear()
        count = 0
        for idx, paths in enumerate(groups, 1):
            for n, path in enumerate(sorted(paths)):
                try:
                    size = self._human_size(os.path.getsize(path))
                except Exception:
                    size = '?'
                self.store.append([str(idx), path, size, n == 0])
                count += 1
        if count:
            self.info.set_text(f"{tr('duplicate_found')} {len(groups)} {tr('duplicate_groups')}, {count} {tr('duplicate_files')}")
        else:
            self.info.set_text(tr('duplicate_none'))
        return False

    def _selection_changed(self, selection):
        model, paths = selection.get_selected_rows()
        self.delete_btn.set_sensitive(bool(paths))

    def selected_paths(self):
        model, rows = self.tree.get_selection().get_selected_rows()
        out = []
        for row in rows:
            it = model.get_iter(row)
            out.append(model.get_value(it, self.COL_PATH))
        return out

    def _on_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            paths = self.selected_paths()
            if not paths:
                return
            msg = tr('ask_delete_perm')
            confirm = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                                        buttons=Gtk.ButtonsType.OK_CANCEL, text=msg)
            resp = confirm.run()
            confirm.destroy()
            if resp != Gtk.ResponseType.OK:
                self.stop_emission_by_name('response')
                return
            for path in paths:
                try:
                    os.remove(path)
                except Exception:
                    pass
            self.destroy()
        else:
            self.cancelled = True
