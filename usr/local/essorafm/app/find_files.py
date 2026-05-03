#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# EssoraFM - Find Files dialog
# Author: josejp2424 - GPL-3.0
"""Diálogo de búsqueda de archivos al estilo SpaceFM.

Permite buscar archivos en una o más carpetas filtrando por:
  - Patrón de nombre (glob: *.txt, foto*.jpg)
  - Sensibilidad a mayúsculas
  - Tipo de archivo (todos, texto, imagen, audio, video)
  - Tamaño mínimo y máximo (KB, MB, GB)
  - Fecha de modificación (último día, semana, mes, año, rango)
  - Archivos ocultos sí/no
  - Incluir subcarpetas sí/no

La búsqueda corre en un thread separado para no bloquear la UI. Se puede
detener en cualquier momento. Doble-click en un resultado abre la carpeta
contenedora en EssoraFM.
"""

import os
import re
import fnmatch
import threading
import time
import datetime
import mimetypes
import subprocess
import shlex

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Gdk, GLib, Gio, Pango

from core.i18n import tr
from core.xdg import xdg_dir, XDG

_SIZE_UNITS = {
    'KB': 1024,
    'MB': 1024 * 1024,
    'GB': 1024 * 1024 * 1024,
}

_FILE_TYPES = {
    'all':   None,
    'text':  ('text/', ['.txt', '.md', '.log', '.conf', '.ini', '.py', '.sh',
                        '.json', '.xml', '.html', '.css', '.js', '.c', '.h',
                        '.cpp', '.rs', '.go', '.rb', '.lua']),
    'image': ('image/', ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif',
                         '.tiff', '.tif', '.svg', '.ico', '.heic']),
    'audio': ('audio/', ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.opus',
                         '.aac', '.wma']),
    'video': ('video/', ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv',
                         '.m4v', '.ogv', '.ts', '.wmv', '.3gp']),
}

_DATE_LIMITS = {
    'any':       None,
    'today':     1,
    'week':      7,
    'month':     30,
    'year':      365,
}


class FindFilesDialog(Gtk.Window):
    """Ventana de búsqueda independiente (no Gtk.Dialog, así puede quedar
    abierta mientras el usuario navega EssoraFM)."""

    def __init__(self, parent_window, initial_dirs=None):
        super().__init__(title=tr('find_files_title'))
        self.parent_window = parent_window
        self.set_default_size(820, 600)
        self.set_transient_for(parent_window)
        try:
            self.set_icon_name('system-search')
        except Exception:
            pass

        # Estado
        self._search_thread = None
        self._cancel_event = threading.Event()
        self._results_count = 0
        self._search_start_time = 0

        # Layout principal
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_vbox)

        # Notebook con dos tabs: Search / Results
        self._notebook = Gtk.Notebook()
        self._notebook.set_margin_start(8)
        self._notebook.set_margin_end(8)
        self._notebook.set_margin_top(8)
        main_vbox.pack_start(self._notebook, True, True, 0)

        # Tab 1: criterios de búsqueda
        criteria_page = self._build_criteria_page(initial_dirs)
        self._notebook.append_page(criteria_page, Gtk.Label(label=tr('find_files_tab_search')))

        # Tab 2: resultados
        results_page = self._build_results_page()
        self._notebook.append_page(results_page, Gtk.Label(label=tr('find_files_tab_results')))

        # Barra inferior con botones y status
        button_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_bar.set_margin_start(8)
        button_bar.set_margin_end(8)
        button_bar.set_margin_top(6)
        button_bar.set_margin_bottom(8)
        main_vbox.pack_start(button_bar, False, False, 0)

        self._status_label = Gtk.Label(label='', xalign=0)
        self._status_label.set_hexpand(True)
        self._status_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        button_bar.pack_start(self._status_label, True, True, 0)

        self._stop_btn = Gtk.Button(label=tr('find_files_stop'))
        self._stop_btn.connect('clicked', self._on_stop_clicked)
        self._stop_btn.set_sensitive(False)
        button_bar.pack_start(self._stop_btn, False, False, 0)

        self._search_btn = Gtk.Button(label=tr('find_files_start'))
        self._search_btn.get_style_context().add_class('suggested-action')
        self._search_btn.connect('clicked', self._on_search_clicked)
        button_bar.pack_start(self._search_btn, False, False, 0)

        # Atajos
        self.connect('key-press-event', self._on_key_press)
        self.connect('destroy', self._on_destroy)

        self.show_all()


    def _build_criteria_page(self, initial_dirs):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_start(12)
        outer.set_margin_end(12)
        outer.set_margin_top(12)
        outer.set_margin_bottom(12)
        scroll.add(outer)

        frame_name = Gtk.Frame(label=tr('find_files_name'))
        nb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        nb.set_margin_start(10); nb.set_margin_end(10)
        nb.set_margin_top(10);   nb.set_margin_bottom(10)
        frame_name.add(nb)

        self.fn_entry = Gtk.Entry()
        self.fn_entry.set_placeholder_text(tr('find_files_name_placeholder'))
        self.fn_entry.set_tooltip_text(tr('find_files_name_tooltip'))
        self.fn_entry.connect('activate', lambda *_: self._on_search_clicked(None))
        nb.pack_start(self.fn_entry, False, False, 0)

        self.fn_case = Gtk.CheckButton(label=tr('find_files_case_sensitive'))
        nb.pack_start(self.fn_case, False, False, 0)

        outer.pack_start(frame_name, False, False, 0)

        frame_type = Gtk.Frame(label=tr('find_files_type'))
        tb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        tb.set_margin_start(10); tb.set_margin_end(10)
        tb.set_margin_top(10);   tb.set_margin_bottom(10)
        frame_type.add(tb)

        self.type_radios = {}
        radio_group = None
        for key, label_key in (
            ('all',   'find_files_type_all'),
            ('text',  'find_files_type_text'),
            ('image', 'find_files_type_image'),
            ('audio', 'find_files_type_audio'),
            ('video', 'find_files_type_video'),
        ):
            radio = Gtk.RadioButton.new_with_label_from_widget(radio_group, tr(label_key))
            if radio_group is None:
                radio_group = radio
                radio.set_active(True)
            tb.pack_start(radio, False, False, 0)
            self.type_radios[key] = radio

        outer.pack_start(frame_type, False, False, 0)

        frame_meta = Gtk.Frame(label=tr('find_files_size_date'))
        mg = Gtk.Grid(column_spacing=10, row_spacing=8)
        mg.set_margin_start(10); mg.set_margin_end(10)
        mg.set_margin_top(10);   mg.set_margin_bottom(10)
        frame_meta.add(mg)

        self.size_min_chk = Gtk.CheckButton(label=tr('find_files_size_min'))
        mg.attach(self.size_min_chk, 0, 0, 1, 1)
        self.size_min_spin = Gtk.SpinButton.new_with_range(0, 100000, 1)
        self.size_min_spin.set_value(0)
        mg.attach(self.size_min_spin, 1, 0, 1, 1)
        self.size_min_unit = Gtk.ComboBoxText()
        for u in ('KB', 'MB', 'GB'):
            self.size_min_unit.append(u, u)
        self.size_min_unit.set_active_id('KB')
        mg.attach(self.size_min_unit, 2, 0, 1, 1)

        self.size_max_chk = Gtk.CheckButton(label=tr('find_files_size_max'))
        mg.attach(self.size_max_chk, 0, 1, 1, 1)
        self.size_max_spin = Gtk.SpinButton.new_with_range(0, 100000, 1)
        self.size_max_spin.set_value(100)
        mg.attach(self.size_max_spin, 1, 1, 1, 1)
        self.size_max_unit = Gtk.ComboBoxText()
        for u in ('KB', 'MB', 'GB'):
            self.size_max_unit.append(u, u)
        self.size_max_unit.set_active_id('MB')
        mg.attach(self.size_max_unit, 2, 1, 1, 1)

        # Fecha
        date_label = Gtk.Label(label=tr('find_files_date'), xalign=0)
        mg.attach(date_label, 0, 2, 1, 1)
        self.date_combo = Gtk.ComboBoxText()
        self.date_combo.append('any',   tr('find_files_date_any'))
        self.date_combo.append('today', tr('find_files_date_today'))
        self.date_combo.append('week',  tr('find_files_date_week'))
        self.date_combo.append('month', tr('find_files_date_month'))
        self.date_combo.append('year',  tr('find_files_date_year'))
        self.date_combo.set_active_id('any')
        mg.attach(self.date_combo, 1, 2, 2, 1)

        outer.pack_start(frame_meta, False, False, 0)

        frame_places = Gtk.Frame(label=tr('find_files_places'))
        pb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        pb.set_margin_start(10); pb.set_margin_end(10)
        pb.set_margin_top(10);   pb.set_margin_bottom(10)
        frame_places.add(pb)

        # Lista de carpetas
        places_scroll = Gtk.ScrolledWindow()
        places_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        places_scroll.set_min_content_height(120)
        places_scroll.set_shadow_type(Gtk.ShadowType.IN)

        self.places_store = Gtk.ListStore(str)
        self.places_view = Gtk.TreeView(model=self.places_store)
        self.places_view.set_headers_visible(False)
        col = Gtk.TreeViewColumn('', Gtk.CellRendererText(), text=0)
        self.places_view.append_column(col)
        places_scroll.add(self.places_view)
        pb.pack_start(places_scroll, True, True, 0)

        # Botones add/remove
        place_btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        add_btn = Gtk.Button(label=tr('find_files_add_folder'))
        add_btn.connect('clicked', self._on_add_folder)
        place_btns.pack_start(add_btn, False, False, 0)

        remove_btn = Gtk.Button(label=tr('find_files_remove_folder'))
        remove_btn.connect('clicked', self._on_remove_folder)
        place_btns.pack_start(remove_btn, False, False, 0)

        # Atajos rápidos
        home_btn = Gtk.Button(label=tr('find_files_add_home'))
        home_btn.connect('clicked', lambda *_: self._add_place(os.path.expanduser('~')))
        place_btns.pack_start(home_btn, False, False, 0)

        desktop_btn = Gtk.Button(label=tr('find_files_add_desktop'))
        desktop_btn.connect('clicked', lambda *_: self._add_place(xdg_dir(XDG.DESKTOP)))
        place_btns.pack_start(desktop_btn, False, False, 0)

        pb.pack_start(place_btns, False, False, 0)

        # Opciones por defecto
        self.include_sub = Gtk.CheckButton(label=tr('find_files_include_sub'))
        self.include_sub.set_active(True)
        pb.pack_start(self.include_sub, False, False, 0)

        self.include_hidden = Gtk.CheckButton(label=tr('find_files_include_hidden'))
        pb.pack_start(self.include_hidden, False, False, 0)

        outer.pack_start(frame_places, True, True, 0)

        # Llenar con carpetas iniciales
        if initial_dirs:
            for d in initial_dirs:
                if d and os.path.isdir(d):
                    self._add_place(d)
        else:
            self._add_place(os.path.expanduser('~'))

        return scroll


    def _build_results_page(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.results_store = Gtk.ListStore(str, str, str, str, str, str)
        self.results_view = Gtk.TreeView(model=self.results_store)
        self.results_view.set_rules_hint(True)
        self.results_view.connect('row-activated', self._on_result_activated)
        self.results_view.connect('button-press-event', self._on_result_button_press)

        # Icono
        col_icon = Gtk.TreeViewColumn('')
        cr_icon = Gtk.CellRendererPixbuf()
        col_icon.pack_start(cr_icon, False)
        col_icon.add_attribute(cr_icon, 'icon-name', 0)
        self.results_view.append_column(col_icon)

        # Nombre
        col_name = Gtk.TreeViewColumn(tr('find_files_col_name'), Gtk.CellRendererText(), text=1)
        col_name.set_sort_column_id(1)
        col_name.set_resizable(True)
        col_name.set_min_width(180)
        self.results_view.append_column(col_name)

        # Carpeta contenedora
        col_dir = Gtk.TreeViewColumn(tr('find_files_col_folder'), Gtk.CellRendererText(), text=2)
        col_dir.set_sort_column_id(2)
        col_dir.set_resizable(True)
        col_dir.set_expand(True)
        self.results_view.append_column(col_dir)

        # Tamaño
        col_size = Gtk.TreeViewColumn(tr('find_files_col_size'), Gtk.CellRendererText(), text=3)
        col_size.set_sort_column_id(3)
        col_size.set_resizable(True)
        self.results_view.append_column(col_size)

        # Modificado
        col_mtime = Gtk.TreeViewColumn(tr('find_files_col_modified'), Gtk.CellRendererText(), text=4)
        col_mtime.set_sort_column_id(4)
        col_mtime.set_resizable(True)
        self.results_view.append_column(col_mtime)

        scroll.add(self.results_view)
        return scroll

    def _add_place(self, path):
        if not path or not os.path.isdir(path):
            return
        for row in self.places_store:
            if row[0] == path:
                return
        self.places_store.append([path])

    def _on_add_folder(self, _btn):
        dialog = Gtk.FileChooserDialog(
            title=tr('find_files_add_folder'),
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(tr('cancel'), Gtk.ResponseType.CANCEL,
                           tr('open'), Gtk.ResponseType.OK)
        dialog.set_current_folder(os.path.expanduser('~'))
        if dialog.run() == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            if path:
                self._add_place(path)
        dialog.destroy()

    def _on_remove_folder(self, _btn):
        sel = self.places_view.get_selection()
        model, treeiter = sel.get_selected()
        if treeiter is not None:
            model.remove(treeiter)


    def _on_search_clicked(self, _btn):
        if self._search_thread is not None and self._search_thread.is_alive():
            return

        # Recolectar criterios
        criteria = self._collect_criteria()
        if criteria is None:
            return

        # Limpiar resultados
        self.results_store.clear()
        self._results_count = 0
        self._cancel_event.clear()
        self._search_start_time = time.time()

        # Cambiar a tab de resultados
        self._notebook.set_current_page(1)

        # Update UI state
        self._search_btn.set_sensitive(False)
        self._stop_btn.set_sensitive(True)
        self._set_status(tr('find_files_searching'))

        # Lanzar thread
        self._search_thread = threading.Thread(
            target=self._search_worker, args=(criteria,), daemon=True
        )
        self._search_thread.start()

    def _on_stop_clicked(self, _btn):
        self._cancel_event.set()
        self._set_status(tr('find_files_stopping'))

    def _collect_criteria(self):
        # Carpetas
        dirs = [row[0] for row in self.places_store]
        if not dirs:
            self._set_status(tr('find_files_no_places'))
            return None

        # Tipo
        type_key = 'all'
        for key, radio in self.type_radios.items():
            if radio.get_active():
                type_key = key
                break

        # Tamaño
        size_min = None
        if self.size_min_chk.get_active():
            unit = self.size_min_unit.get_active_id() or 'KB'
            size_min = int(self.size_min_spin.get_value()) * _SIZE_UNITS[unit]

        size_max = None
        if self.size_max_chk.get_active():
            unit = self.size_max_unit.get_active_id() or 'MB'
            size_max = int(self.size_max_spin.get_value()) * _SIZE_UNITS[unit]

        # Fecha
        date_key = self.date_combo.get_active_id() or 'any'
        date_after = None
        if _DATE_LIMITS.get(date_key) is not None:
            days = _DATE_LIMITS[date_key]
            date_after = time.time() - (days * 86400)

        return {
            'dirs': dirs,
            'pattern': self.fn_entry.get_text().strip(),
            'case_sensitive': self.fn_case.get_active(),
            'type': type_key,
            'size_min': size_min,
            'size_max': size_max,
            'date_after': date_after,
            'include_sub': self.include_sub.get_active(),
            'include_hidden': self.include_hidden.get_active(),
        }

    def _search_worker(self, criteria):
        """Corre en thread separado. Usa GLib.idle_add para actualizar la UI."""
        pattern = criteria['pattern']
        case_sensitive = criteria['case_sensitive']

        if pattern:
            if not case_sensitive:
                pattern_lower = pattern.lower()
            else:
                pattern_lower = pattern
        else:
            pattern_lower = '*'

        type_filter = _FILE_TYPES.get(criteria['type'])
        size_min = criteria['size_min']
        size_max = criteria['size_max']
        date_after = criteria['date_after']
        include_sub = criteria['include_sub']
        include_hidden = criteria['include_hidden']

        for root_dir in criteria['dirs']:
            if self._cancel_event.is_set():
                break
            try:
                self._walk_directory(
                    root_dir, pattern_lower, case_sensitive, type_filter,
                    size_min, size_max, date_after, include_sub, include_hidden,
                )
            except Exception as exc:
                print(f'find_files: error walking {root_dir}: {exc}')

        # Notificar fin
        GLib.idle_add(self._on_search_done)

    def _walk_directory(self, root_dir, pattern, case_sensitive, type_filter,
                        size_min, size_max, date_after, include_sub, include_hidden):
        if not include_sub:
            try:
                entries = os.listdir(root_dir)
            except (PermissionError, OSError):
                return
            for name in entries:
                if self._cancel_event.is_set():
                    return
                if not include_hidden and name.startswith('.'):
                    continue
                full = os.path.join(root_dir, name)
                if os.path.isfile(full):
                    self._test_and_add(full, name, pattern, case_sensitive,
                                       type_filter, size_min, size_max, date_after)
            return

        for current, subdirs, files in os.walk(root_dir, followlinks=False):
            if self._cancel_event.is_set():
                return

            if not include_hidden:
                subdirs[:] = [d for d in subdirs if not d.startswith('.')]

            for fname in files:
                if self._cancel_event.is_set():
                    return
                if not include_hidden and fname.startswith('.'):
                    continue
                full = os.path.join(current, fname)
                self._test_and_add(full, fname, pattern, case_sensitive,
                                   type_filter, size_min, size_max, date_after)

    def _test_and_add(self, full_path, name, pattern, case_sensitive,
                      type_filter, size_min, size_max, date_after):
        if pattern and pattern != '*':
            test_name = name if case_sensitive else name.lower()
            if not fnmatch.fnmatch(test_name, pattern):
                return

        if type_filter is not None:
            mime_prefix, exts = type_filter
            ext = os.path.splitext(name)[1].lower()
            if ext not in exts:
                mime, _ = mimetypes.guess_type(full_path)
                if not mime or not mime.startswith(mime_prefix):
                    return

        try:
            st = os.stat(full_path)
        except (PermissionError, OSError):
            return

        if size_min is not None and st.st_size < size_min:
            return
        if size_max is not None and st.st_size > size_max:
            return
        if date_after is not None and st.st_mtime < date_after:
            return

        info = {
            'full_path': full_path,
            'name': name,
            'dirname': os.path.dirname(full_path),
            'size': st.st_size,
            'mtime': st.st_mtime,
        }
        GLib.idle_add(self._add_result_row, info)

    def _add_result_row(self, info):
        mime, _ = mimetypes.guess_type(info['full_path'])
        if mime:
            icon_name = self._mime_to_icon(mime)
        else:
            icon_name = 'text-x-generic'

        size_str = self._format_size(info['size'])
        mtime_str = datetime.datetime.fromtimestamp(info['mtime']).strftime('%Y-%m-%d %H:%M')

        self.results_store.append([
            icon_name,
            info['name'],
            info['dirname'],
            size_str,
            mtime_str,
            info['full_path'],
        ])
        self._results_count += 1

        if self._results_count % 50 == 0:
            self._set_status(tr('find_files_found_count').format(n=self._results_count))
        return False

    def _on_search_done(self):
        elapsed = time.time() - self._search_start_time
        msg = tr('find_files_done').format(
            n=self._results_count, t=f'{elapsed:.1f}'
        )
        self._set_status(msg)
        self._search_btn.set_sensitive(True)
        self._stop_btn.set_sensitive(False)
        return False


    def _on_result_activated(self, _view, path, _column):
        """Doble-click en un resultado → abre la carpeta contenedora en EssoraFM
        seleccionando el archivo."""
        treeiter = self.results_store.get_iter(path)
        full_path = self.results_store.get_value(treeiter, 5)
        if not full_path:
            return
        target = os.path.dirname(full_path) if os.path.isfile(full_path) else full_path
        self._open_in_essorafm(target)

    def _on_result_button_press(self, view, event):
        if event.button != 3:
            return False
        path_info = view.get_path_at_pos(int(event.x), int(event.y))
        if path_info is None:
            return False
        path, _, _, _ = path_info
        view.get_selection().select_path(path)
        treeiter = self.results_store.get_iter(path)
        full_path = self.results_store.get_value(treeiter, 5)
        if not full_path:
            return False

        menu = Gtk.Menu()

        item_open = Gtk.MenuItem(label=tr('open'))
        item_open.connect('activate', lambda *_: self._open_file_with_default(full_path))
        menu.append(item_open)

        item_open_dir = Gtk.MenuItem(label=tr('find_files_open_folder'))
        item_open_dir.connect('activate',
                              lambda *_: self._open_in_essorafm(os.path.dirname(full_path)))
        menu.append(item_open_dir)

        item_copy = Gtk.MenuItem(label=tr('find_files_copy_path'))
        item_copy.connect('activate', lambda *_: self._copy_path_to_clipboard(full_path))
        menu.append(item_copy)

        menu.show_all()
        menu.popup_at_pointer(event)
        return True

    def _open_in_essorafm(self, path):
        if not path:
            return
        candidates = [
            '/usr/local/bin/essorafm',
            '/usr/local/essorafm/bin/essorafm',
        ]
        for cmd in candidates:
            if os.path.exists(cmd):
                try:
                    subprocess.Popen([cmd, path],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                    return
                except Exception:
                    continue
        try:
            Gio.AppInfo.launch_default_for_uri(GLib.filename_to_uri(path, None), None)
        except Exception:
            pass

    def _open_file_with_default(self, path):
        try:
            Gio.AppInfo.launch_default_for_uri(GLib.filename_to_uri(path, None), None)
        except Exception:
            try:
                subprocess.Popen(['xdg-open', path],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    def _copy_path_to_clipboard(self, path):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(path, -1)
        clipboard.store()


    def _set_status(self, text):
        self._status_label.set_text(text)

    def _format_size(self, n):
        for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
            if n < 1024:
                return f'{n:.1f} {unit}' if unit != 'B' else f'{n} {unit}'
            n /= 1024
        return f'{n:.1f} PB'

    def _mime_to_icon(self, mime):
        if mime.startswith('text/'):
            return 'text-x-generic'
        if mime.startswith('image/'):
            return 'image-x-generic'
        if mime.startswith('audio/'):
            return 'audio-x-generic'
        if mime.startswith('video/'):
            return 'video-x-generic'
        if mime == 'application/pdf':
            return 'application-pdf'
        if mime.startswith('application/'):
            return 'application-x-generic'
        return 'text-x-generic'

    def _on_key_press(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self._search_thread is not None and self._search_thread.is_alive():
                self._cancel_event.set()
            else:
                self.destroy()
            return True
        return False

    def _on_destroy(self, *_args):
        self._cancel_event.set()
