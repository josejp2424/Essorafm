# EssoraFM
# Author: josejp2424 and Nilsonmorales - GPL-3.0
import os
import subprocess
import urllib.parse
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GdkPixbuf, GLib

from core.filesystem import FileSystemService
from core.privilege import run_privileged, find_escalator
from services.icon_loader import IconLoader
from services.trash import TrashService
from services.thumbnailer import Thumbnailer
from app.duplicates import DuplicateScannerDialog
from app.dialogs import CopyProgressDialog
from core.i18n import tr

_ESSORAFM_BIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bin')
_RUN_IN_TERMINAL = os.path.join(_ESSORAFM_BIN, 'run_in_terminal')
_SEND_TO_BACKGROUNDS = os.path.join(_ESSORAFM_BIN, 'Send-to Backgrounds')

_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.svg', '.webp', '.bmp', '.gif', '.tiff', '.tif'}


class FileView(Gtk.Box):
    COL_PIXBUF = 0
    COL_NAME = 1
    COL_SIZE = 2
    COL_MODIFIED = 3
    COL_PATH = 4
    COL_IS_DIR = 5

    DND_TARGET_URI_LIST = 0
    DND_TARGET_TEXT = 1

    def __init__(self, on_path_changed, show_message, settings_manager):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.on_path_changed = on_path_changed
        self.show_message = show_message
        self.settings_manager = settings_manager
        self.current_path = os.path.expanduser('~')
        self.history = []
        self.show_hidden = settings_manager.get_bool('show_hidden', False)
        self.single_click = settings_manager.get_bool('single_click', False)
        saved_mode = settings_manager.get('view_mode', 'icons')
        self._view_mode = saved_mode
        self.fs = FileSystemService()
        self.trash = TrashService()
        self.icon_loader = IconLoader(settings_manager.get_int('icon_size', 64))
        self.show_thumbnails = settings_manager.get_bool('show_thumbnails', True)
        self.thumbnailer = Thumbnailer(self.icon_loader, self.show_thumbnails)
        self.clipboard_paths = []
        self.search_query = ""
        self.preview_callback = None
        self._hover_preview_id = None
        self._hover_preview_path = None
        self.sort_field     = settings_manager.get('sort_field', 'name')
        self.sort_direction = settings_manager.get('sort_direction', 'asc')

        self.store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str, str, str, bool)
        self.stack = Gtk.Stack()
        self.pack_start(self.stack, True, True, 0)

        self.tree = Gtk.TreeView(model=self.store)
        self.tree.set_headers_visible(True)
        self.tree.set_enable_search(True)
        self.tree.connect('row-activated', self._on_row_activated_tree)
        self.tree.connect('button-press-event', self._on_button_press)
        self.tree.connect('key-press-event', self._on_key_press)
        self.tree.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.tree.connect('motion-notify-event', self._on_motion_preview_tree)
        self.tree.get_selection().connect('changed', self._on_selection_preview_changed)
        self.tree.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self._setup_drag_source(self.tree)
        self._build_tree_columns()

        tree_scroll = Gtk.ScrolledWindow()
        tree_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        tree_scroll.get_style_context().add_class('essorafm-fileview-scroll')
        tree_scroll.add(self.tree)
        self.stack.add_named(tree_scroll, 'list')
        self.icon_view = Gtk.IconView.new_with_model(self.store)
        self.icon_view.set_item_width(110)
        self.icon_view.set_item_orientation(Gtk.Orientation.VERTICAL)
        self.icon_view.set_columns(-1)
        self.icon_view.set_margin(8)
        self.icon_view.set_row_spacing(4)
        self.icon_view.set_column_spacing(4)
        self.icon_view.set_spacing(2)

        self._cr_pixbuf = Gtk.CellRendererPixbuf()
        self._cr_pixbuf.set_alignment(0.5, 0.5)
        self.icon_view.pack_start(self._cr_pixbuf, False)
        self.icon_view.add_attribute(self._cr_pixbuf, 'pixbuf', self.COL_PIXBUF)


        self._cr_text = Gtk.CellRendererText()
        self._cr_text.set_property('alignment', 1)   
        self._cr_text.set_property('wrap-mode', 2)  
        self._cr_text.set_property('wrap-width', 100)
        self._cr_text.set_property('xalign', 0.5)
        self._cr_text.set_property('yalign', 0.0)
        self.icon_view.pack_end(self._cr_text, True)
        self.icon_view.add_attribute(self._cr_text, 'text', self.COL_NAME)
        self.icon_view.set_activate_on_single_click(self.single_click)
        self.icon_view.connect('item-activated', self._on_row_activated_icon)
        self.icon_view.connect('button-press-event', self._on_button_press_icon)
        self.icon_view.connect('key-press-event', self._on_key_press)
        self.icon_view.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.icon_view.connect('motion-notify-event', self._on_motion_preview_icon)
        self.icon_view.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.icon_view.connect('selection-changed', self._on_selection_preview_changed)
        self._setup_drag_source(self.icon_view)
        self.icon_view.get_style_context().add_class('essorafm-iconview')
        self._apply_icon_view_css()

        icon_scroll = Gtk.ScrolledWindow()
        icon_scroll.set_policy(Gtk.PolicyType.ALWAYS, Gtk.PolicyType.AUTOMATIC)
        icon_scroll.set_hexpand(True)
        icon_scroll.set_vexpand(True)
        icon_scroll.get_style_context().add_class('essorafm-fileview-scroll')
        icon_scroll.add(self.icon_view)
        self.stack.add_named(icon_scroll, 'icons')

        self._apply_icon_size_only()
        
        self.load_path(self.current_path, add_to_history=False)

        self.stack.connect('realize', self._on_stack_realize)
        self.icon_view.connect('map', self._on_icon_view_mapped)
        
        self._setup_drop_destination()

    
    def _setup_drop_destination(self):
        """Configura el FileView para recibir archivos arrastrados."""
        targets = [
            Gtk.TargetEntry.new('text/uri-list', 0, 0),
            Gtk.TargetEntry.new('text/plain', 0, 1),
        ]
        
        actions = Gdk.DragAction.COPY | Gdk.DragAction.MOVE
        
        self.drag_dest_set(Gtk.DestDefaults.ALL, targets, actions)
        self.connect('drag-data-received', self._on_drag_data_received)
        self.connect('drag-motion', self._on_drag_motion)
        self.connect('drag-leave', self._on_drag_leave)
        
        self.tree.drag_dest_set(Gtk.DestDefaults.ALL, targets, actions)
        self.tree.connect('drag-data-received', self._on_drag_data_received)
        self.tree.connect('drag-motion', self._on_drag_motion)
        
        self.icon_view.drag_dest_set(Gtk.DestDefaults.ALL, targets, actions)
        self.icon_view.connect('drag-data-received', self._on_drag_data_received)
        self.icon_view.connect('drag-motion', self._on_drag_motion)

    def _on_drag_motion(self, widget, drag_context, x, y, time):
        """Resalta el widget cuando se arrastra algo sobre él."""
        Gdk.drag_status(drag_context, Gdk.DragAction.COPY, time)
        return True

    def _on_drag_leave(self, widget, drag_context, time):
        """Restaura el widget cuando el cursor sale."""
        pass

    def _on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        """Recibe archivos arrastrados y los copia/mueve a la carpeta actual."""
        uris = data.get_uris()
        if not uris:
            Gtk.drag_finish(drag_context, False, False, time)
            return
        
        paths = []
        for uri in uris:
            if uri.startswith('file://'):
                path = uri[7:]
                path = urllib.parse.unquote(path)
                if os.path.exists(path):
                    paths.append(path)
        
        if not paths:
            Gtk.drag_finish(drag_context, False, False, time)
            return
        
        dlg = CopyProgressDialog(self.get_toplevel(), paths, self.current_path, 
                                 lambda ok, err: self._after_drag_drop(ok, err, drag_context, time))
        dlg.present()

    def _after_drag_drop(self, ok, error_text, drag_context, time):
        """Callback después de completar la copia/movimiento."""
        if ok:
            self.refresh()
            self.show_message(tr('copy_done'))
            Gtk.drag_finish(drag_context, True, False, time)
        else:
            self.show_message(error_text or tr('copy_fail'))
            Gtk.drag_finish(drag_context, False, False, time)

    def format_size(self, size_bytes):
        """Formatea el tamaño en bytes a una unidad legible."""
        if size_bytes == 0:
            return "0 B"
        elif size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def get_folder_stats(self):
        """Obtiene estadísticas de la carpeta actual."""
        try:
            items = list(self.fs.list_directory(self.current_path, show_hidden=self.show_hidden))
            total_items = len(items)
            folders = sum(1 for i in items if i.get('is_dir', False))
            files = total_items - folders
            total_size_bytes = 0
            for item in items:
                if not item.get('is_dir', False):
                    total_size_bytes += item.get('size_bytes', 0)
            return {
                'total': total_items,
                'folders': folders,
                'files': files,
                'size': self.format_size(total_size_bytes),
                'size_bytes': total_size_bytes
            }
        except Exception:
            return {'total': 0, 'folders': 0, 'files': 0, 'size': '0 B', 'size_bytes': 0}

    def update_status(self):
        """Actualiza la barra de estado con informacion de la carpeta o seleccion."""
        def _do_update():
            try:
                selected = self.selected_paths()

                if selected:
                    total = len(selected)
                    folders = sum(1 for p in selected if os.path.isdir(p))
                    files = total - folders

                    size_bytes = 0
                    for p in selected:
                        if os.path.isfile(p):
                            try:
                                size_bytes += os.path.getsize(p)
                            except Exception:
                                pass

                    size = self.format_size(size_bytes)

                    if total == 1:
                        name = os.path.basename(selected[0])
                        if folders == 1:
                            msg = f"\U0001f4c1 {name}"
                        else:
                            msg = f"\U0001f4c4 {name} \u2022 {size}"
                    else:
                        if files == 0:
                            msg = f"\U0001f4c1 {total} {tr('folders')}"
                        elif folders == 0:
                            msg = f"\U0001f4c4 {total} {tr('files')} \u2022 {size}"
                        else:
                            msg = f"\U0001f4c4 {files} {tr('files')} \u2022 \U0001f4c1 {folders} {tr('folders')}"
                else:
                    stats = self.get_folder_stats()
                    if stats['total'] == 0:
                        msg = tr('empty_folder')
                    else:
                        if stats['files'] == 0:
                            msg = f"\U0001f4c1 {stats['total']} {tr('folders')}"
                        elif stats['folders'] == 0:
                            msg = f"\U0001f4c4 {stats['total']} {tr('files')} \u2022 {stats['size']}"
                        else:
                            msg = f"\U0001f4c1 {stats['folders']} {tr('folders')} \u2022 \U0001f4c4 {stats['files']} {tr('files')} \u2022 {stats['size']}"

                self.show_message(msg, is_status=True)
            except Exception as e:
                print(f"Error updating status: {e}")
            return False

        GLib.idle_add(_do_update)

    def _on_stack_realize(self, widget):
        """Se llama justo después de show_all(). Aplica el modo de vista guardado
        porque show_all() resetea el visible child del Gtk.Stack."""
        self.stack.set_visible_child_name('icons' if self._view_mode == 'icons' else 'list')
        widget.disconnect_by_func(self._on_stack_realize)

    def _on_icon_view_mapped(self, widget):
        """Se llama una sola vez cuando el IconView aparece en pantalla por primera vez.
        Es el momento correcto para forzar la orientación vertical (texto debajo de iconos)."""
        self._fix_icon_view_orientation()
        widget.disconnect_by_func(self._on_icon_view_mapped)

    def _apply_icon_view_css(self):
        """Aplica CSS para forzar que el texto esté debajo de los iconos."""
        css = b"""
        .icon-view-vertical cell {
            -GtkIconView-cell-padding: 4px;
        }
        .icon-view-vertical cell:selected {
            background-color: @selected_bg_color;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        self.icon_view.get_style_context().add_class('icon-view-vertical')

    def _apply_icon_size_only(self):
        """Aplica solo el tamaño de iconos sin cambiar el modo de vista."""
        icon_size = self.settings_manager.get_int('icon_size', 64)
        self.icon_loader = IconLoader(icon_size)
        self.show_thumbnails = self.settings_manager.get_bool('show_thumbnails', True)
        self.thumbnailer = Thumbnailer(self.icon_loader, self.show_thumbnails)
        
        item_width = max(icon_size + 30, 110)
        self.icon_view.set_item_width(item_width)
        if hasattr(self, '_cr_text'):
            self._cr_text.set_property('wrap-width', item_width - 10)
        self.icon_view.set_activate_on_single_click(self.single_click)

    @property
    def view_mode(self):
        return self._view_mode

    @view_mode.setter
    def view_mode(self, value):
        """Cambia el modo de vista y lo guarda en settings_manager."""
        if self._view_mode == value:
            return
        self._view_mode = value
        self.stack.set_visible_child_name('icons' if value == 'icons' else 'list')
        
        if self.settings_manager:
            self.settings_manager.set('view_mode', value)
            self.settings_manager.save()
        
        if value == 'icons':
            GLib.idle_add(self._fix_icon_view_orientation)

    def _fix_icon_view_orientation(self):
        """Fuerza un redibujado del IconView para que aplique el layout vertical."""
        if hasattr(self, 'icon_view') and self.icon_view:
            self.icon_view.set_item_orientation(Gtk.Orientation.VERTICAL)
            self.icon_view.queue_draw()
        return False

    def _setup_drag_source(self, widget):
        targets = [
            Gtk.TargetEntry.new('text/uri-list', 0, self.DND_TARGET_URI_LIST),
            Gtk.TargetEntry.new('text/plain', 0, self.DND_TARGET_TEXT),
            Gtk.TargetEntry.new('STRING', 0, self.DND_TARGET_TEXT),
        ]
        actions = Gdk.DragAction.COPY | Gdk.DragAction.MOVE | Gdk.DragAction.LINK
        try:
            widget.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, targets, actions)
        except TypeError:
            widget.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, targets, actions)
        widget.connect('drag-data-get', self._on_drag_data_get)
        widget.connect('drag-begin', self._on_drag_begin)

    def _paths_to_uris(self, paths):
        uris = []
        for path in paths:
            try:
                if path and os.path.exists(path):
                    uris.append(Gio.File.new_for_path(path).get_uri())
            except Exception:
                pass
        return uris

    def _on_drag_begin(self, widget, drag_context):
        try:
            paths = self.selected_paths()
            if not paths:
                return
            first = paths[0]
            for row in self.store:
                if row[self.COL_PATH] == first:
                    pixbuf = row[self.COL_PIXBUF]
                    if pixbuf:
                        Gtk.drag_set_icon_pixbuf(drag_context, pixbuf, 0, 0)
                    break
        except Exception:
            pass

    def _on_drag_data_get(self, widget, drag_context, selection_data, info, time):
        paths = self.selected_paths()
        if not paths:
            return
        if info == self.DND_TARGET_URI_LIST:
            uris = self._paths_to_uris(paths)
            if uris:
                selection_data.set_uris(uris)
            return
        text = '\n'.join(paths)
        try:
            selection_data.set_text(text, -1)
        except Exception:
            selection_data.set(selection_data.get_target(), 8, text.encode('utf-8'))

    def _build_tree_columns(self):
        self.tree.append_column(Gtk.TreeViewColumn('', Gtk.CellRendererPixbuf(), pixbuf=self.COL_PIXBUF))
        renderer = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn(tr('name'), renderer, text=self.COL_NAME)
        col.set_expand(True)
        col.set_resizable(True)
        self.tree.append_column(col)
        self.tree.append_column(Gtk.TreeViewColumn(tr('size'), Gtk.CellRendererText(), text=self.COL_SIZE))
        self.tree.append_column(Gtk.TreeViewColumn(tr('modified'), Gtk.CellRendererText(), text=self.COL_MODIFIED))

    def apply_preferences(self):
        """Aplica todas las preferencias respetando el modo de vista actual."""
        self.show_hidden = self.settings_manager.get_bool('show_hidden', False)
        self.single_click = self.settings_manager.get_bool('single_click', False)
        
        self._apply_icon_size_only()
        
        self.refresh()
        
        GLib.idle_add(self._fix_icon_view_orientation)

    def active_widget(self):
        return self.icon_view if self._view_mode == 'icons' else self.tree

    def _sort_key(self, item):
        """Clave de ordenamiento según self.sort_field y self.sort_direction."""
        field = self.sort_field or 'name'

        is_file = 0 if item.get('is_dir') else 1
        if field == 'size':
            try:
                raw = item.get('size_bytes', 0) or 0
                key = (is_file, int(raw))
            except Exception:
                key = (is_file, 0)
        elif field == 'modified':
            key = (is_file, item.get('mtime', 0) or 0)
        elif field == 'type':
            ext = os.path.splitext(item.get('name', ''))[1].lower()
            key = (is_file, ext, item.get('name', '').lower())
        else:  
            key = (is_file, item.get('name', '').lower())
        return key

    def apply_sort(self, field, direction):
        """Cambiar el ordenamiento activo y refrescar."""
        self.sort_field = field
        self.sort_direction = direction
        self.settings_manager.set('sort_field', field)
        self.settings_manager.set('sort_direction', direction)
        self.settings_manager.save()
        self.refresh()

    def load_path(self, path, add_to_history=True):
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(path):
            self.show_message(f"{tr('invalid_folder')} {path}")
            return
        if add_to_history and path != self.current_path:
            self.history.append(self.current_path)
        self.current_path = path
        self.store.clear()
        size = self.settings_manager.get_int('icon_size', 64) if self._view_mode == 'icons' else self.settings_manager.get_int('list_icon_size', 24)
        try:
            query = (self.search_query or '').strip().lower()
            items = list(self.fs.list_directory(path, show_hidden=self.show_hidden))
            if query:
                items = [i for i in items if query in i['name'].lower()]

            reverse = (self.sort_direction == 'desc')
            items.sort(key=self._sort_key, reverse=reverse)
            for item in items:
                pix = self.thumbnailer.thumbnail_for(item['path'], item['gio_file'], item['file_info'], size)
                self.store.append([pix, item['name'], item['size_text'], item['modified_text'], item['path'], item['is_dir']])
            try:
                self.on_path_changed(path)
            except TypeError:
                self.on_path_changed(path, False)
            self.update_status()
        except Exception as exc:
            self.show_message(str(exc))

    def _is_icons_view_active(self):
        try:
            visible = self.stack.get_visible_child_name()
            return visible == 'icons'
        except Exception:
            return self._view_mode == 'icons'

    def selected_paths(self):
        selected = []
        if self._is_icons_view_active():
            for tree_path in self.icon_view.get_selected_items():
                it = self.store.get_iter(tree_path)
                selected.append(self.store.get_value(it, self.COL_PATH))
        else:
            model, paths = self.tree.get_selection().get_selected_rows()
            for tree_path in paths:
                it = model.get_iter(tree_path)
                selected.append(model.get_value(it, self.COL_PATH))
        if not selected:
            if self._is_icons_view_active():
                model, paths = self.tree.get_selection().get_selected_rows()
                for tree_path in paths:
                    it = model.get_iter(tree_path)
                    selected.append(model.get_value(it, self.COL_PATH))
            else:
                for tree_path in self.icon_view.get_selected_items():
                    it = self.store.get_iter(tree_path)
                    selected.append(self.store.get_value(it, self.COL_PATH))
        return selected

    def set_search_query(self, query):
        self.search_query = (query or '').strip()
        self.refresh()

    def _preview_path(self, path):
        if path and self.preview_callback:
            try:
                self.preview_callback(path)
            except Exception:
                pass

    def _on_selection_preview_changed(self, *_args):
        selected = self.selected_paths()
        if selected:
            self._preview_path(selected[0])
        self.update_status()

    def _schedule_hover_preview(self, path):
        if not path or os.path.isdir(path):
            return
        self._hover_preview_path = path
        if self._hover_preview_id:
            GLib.source_remove(self._hover_preview_id)
        self._hover_preview_id = GLib.timeout_add(420, self._do_hover_preview)

    def _do_hover_preview(self):
        self._hover_preview_id = None
        self._preview_path(self._hover_preview_path)
        return False

    def _on_motion_preview_icon(self, widget, event):
        hit = self.icon_view.get_path_at_pos(int(event.x), int(event.y))
        if hit is not None:
            try:
                it = self.store.get_iter(hit)
                self._schedule_hover_preview(self.store.get_value(it, self.COL_PATH))
            except Exception:
                pass
        return False

    def _on_motion_preview_tree(self, widget, event):
        hit = self.tree.get_path_at_pos(int(event.x), int(event.y))
        if hit:
            try:
                it = self.store.get_iter(hit[0])
                self._schedule_hover_preview(self.store.get_value(it, self.COL_PATH))
            except Exception:
                pass
        return False

    def go_up(self):
        parent = os.path.dirname(self.current_path.rstrip('/')) or '/'
        self.load_path(parent)

    def go_back(self):
        if not self.history:
            return False
        previous = self.history.pop()
        self.load_path(previous, add_to_history=False)
        return True

    def toggle_hidden(self):
        self.show_hidden = not self.show_hidden
        self.refresh()

    def refresh(self):
        self.load_path(self.current_path, add_to_history=False)
        if self._view_mode == 'icons':
            GLib.idle_add(self._fix_icon_view_orientation)

    def open_file(self, path):
        try:
            Gio.AppInfo.launch_default_for_uri(f'file://{path}', None)
        except Exception:
            subprocess.Popen(['xdg-open', path])

    def _open_selected_path(self, target, is_dir):
        if is_dir:
            self.load_path(target)
        else:
            self.open_file(target)

    def _on_row_activated_tree(self, tree, path, _column):
        it = tree.get_model().get_iter(path)
        self._open_selected_path(tree.get_model().get_value(it, self.COL_PATH), tree.get_model().get_value(it, self.COL_IS_DIR))

    def _on_row_activated_icon(self, icon_view, path):
        it = self.store.get_iter(path)
        self._open_selected_path(self.store.get_value(it, self.COL_PATH), self.store.get_value(it, self.COL_IS_DIR))

    def _pick_clicked_path(self, event):
        if self._is_icons_view_active():
            hit = self.icon_view.get_path_at_pos(int(event.x), int(event.y))
            if hit is not None:
                if not self.icon_view.path_is_selected(hit):
                    self.icon_view.unselect_all()
                    self.icon_view.select_path(hit)
                try:
                    it = self.store.get_iter(hit)
                    return self.store.get_value(it, self.COL_PATH)
                except Exception:
                    return None
            return None
        hit = self.tree.get_path_at_pos(int(event.x), int(event.y))
        if hit:
            tree_path, _column, _cell_x, _cell_y = hit
            selection = self.tree.get_selection()
            if not selection.path_is_selected(tree_path):
                selection.unselect_all()
                selection.select_path(tree_path)
            try:
                it = self.store.get_iter(tree_path)
                return self.store.get_value(it, self.COL_PATH)
            except Exception:
                return None
        return None

    def _on_button_press_icon(self, _widget, event):
        if event.button == 3:
            hit = self._pick_clicked_path(event)
            self.show_context_menu(event, clicked_hit=hit)
            return True
        return False

    def _on_button_press(self, _widget, event):
        if event.button == 3:
            hit = self._pick_clicked_path(event)
            self.show_context_menu(event, clicked_hit=hit)
            return True
        return False

    def _on_key_press(self, _widget, event):
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(event.state & Gdk.ModifierType.SHIFT_MASK)
        if ctrl and event.keyval in (Gdk.KEY_c, Gdk.KEY_C):
            self._copy_selected()
            return True
        if ctrl and event.keyval in (Gdk.KEY_v, Gdk.KEY_V):
            self.paste_into_current()
            return True
        if ctrl and event.keyval in (Gdk.KEY_h, Gdk.KEY_H):
            self.toggle_hidden()
            return True
        if event.keyval == Gdk.KEY_F5:
            self.refresh()
            return True
        if event.keyval == Gdk.KEY_Delete:
            if shift:
                self.delete_selected(permanent=True)
            else:
                self.delete_selected(permanent=False)
            return True
        return False

    def paste_into_current(self):
        if not self.clipboard_paths:
            self.show_message(tr('no_copied_files'))
            return
        dlg = CopyProgressDialog(self.get_toplevel(), self.clipboard_paths, self.current_path, self._after_copy)
        dlg.present()

    def _after_copy(self, ok, error_text):
        if ok:
            self.show_message(tr('copy_done'))
            self.refresh()
        else:
            self.show_message(error_text or tr('copy_fail'))

    def create_folder_dialog(self):
        dialog = Gtk.Dialog(title=tr('new_folder_title'), transient_for=self.get_toplevel(), modal=True)
        dialog.add_buttons('Cancelar', Gtk.ResponseType.CANCEL, 'Crear', Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        box.set_spacing(8)
        entry = Gtk.Entry()
        entry.set_activates_default(True)
        box.pack_start(Gtk.Label(label=tr('folder_name'), xalign=0), False, False, 8)
        box.pack_start(entry, False, False, 8)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.show_all()
        resp = dialog.run()
        name = entry.get_text().strip()
        dialog.destroy()
        if resp == Gtk.ResponseType.OK and name:
            try:
                self.fs.create_folder(self.current_path, name)
                self.refresh()
            except Exception as exc:
                self.show_message(str(exc))

    def is_trash_view(self):
        return self.trash.is_in_trash(self.current_path) or os.path.realpath(self.current_path) == os.path.realpath(self.trash.trash_path())

    def delete_selected(self, permanent=False):
        selected = self.selected_paths()
        if not selected:
            self.show_message(tr('no_selection'))
            return
        if permanent or self.is_trash_view():
            text = tr('ask_delete_perm')
        else:
            text = tr('ask_move_trash')
        dlg = Gtk.MessageDialog(transient_for=self.get_toplevel(), modal=True, message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.OK_CANCEL, text=text)
        resp = dlg.run()
        dlg.destroy()
        if resp != Gtk.ResponseType.OK:
            return
        try:
            if permanent or self.is_trash_view():
                self.trash.delete_permanently(selected)
                self.show_message(tr('trash_deleted'))
            else:
                self.trash.move_to_trash(selected)
                self.show_message(tr('trash_moved'))
            self.refresh()
        except Exception as exc:
            self.show_message(str(exc))

    def restore_selected(self):
        selected = self.selected_paths()
        if not selected:
            self.show_message(tr('no_selection'))
            return
        try:
            for path in selected:
                self.trash.restore_from_trash(path)
            self.show_message(tr('trash_restored'))
            self.refresh()
        except Exception as exc:
            self.show_message(str(exc))

    def _resolve_selection(self, clicked_path):
        selected = self.selected_paths()
        if selected:
            return selected
        if clicked_path:
            return [clicked_path]
        return []

    def _build_open_with_submenu(self, path):
        submenu = Gtk.Menu()
        try:
            content_type, _uncertain = Gio.content_type_guess(path, None)
            apps = Gio.AppInfo.get_all_for_type(content_type) if content_type else []
        except Exception:
            apps = []

        default_app = None
        try:
            if content_type:
                default_app = Gio.AppInfo.get_default_for_type(content_type, False)
        except Exception:
            default_app = None

        added_ids = set()
        if default_app:
            self._append_app_to_menu(submenu, default_app, path)
            added_ids.add(default_app.get_id())
            if apps:
                submenu.append(Gtk.SeparatorMenuItem())

        for app in apps:
            if app.get_id() in added_ids:
                continue
            self._append_app_to_menu(submenu, app, path)
            added_ids.add(app.get_id())

        if added_ids:
            submenu.append(Gtk.SeparatorMenuItem())

        other_item = Gtk.MenuItem()
        other_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        try:
            other_icon = Gtk.Image.new_from_icon_name('application-x-executable', Gtk.IconSize.MENU)
            other_box.pack_start(other_icon, False, False, 0)
        except Exception:
            pass
        other_box.pack_start(Gtk.Label(label=tr('open_with_other'), xalign=0), True, True, 0)
        other_item.add(other_box)
        other_item.connect('activate', lambda *_: self._show_app_chooser(path))
        submenu.append(other_item)

        return submenu

    def _append_app_to_menu(self, menu, app, path):
        item = Gtk.MenuItem()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        try:
            icon = app.get_icon()
            if icon:
                image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.MENU)
                box.pack_start(image, False, False, 0)
        except Exception:
            pass
        label = Gtk.Label(label=app.get_display_name() or app.get_name() or '?', xalign=0)
        box.pack_start(label, True, True, 0)
        item.add(box)
        item.connect('activate', lambda *_: self._launch_with_app(app, path))
        menu.append(item)

    def _launch_with_app(self, app, path):
        try:
            gfile = Gio.File.new_for_path(path)
            app.launch([gfile], None)
        except Exception as exc:
            self.show_message(str(exc))

    def _show_app_chooser(self, path):
        try:
            gfile = Gio.File.new_for_path(path)
            dialog = Gtk.AppChooserDialog(parent=self.get_toplevel(), modal=True, gfile=gfile)
            dialog.set_title(tr('open_with_other'))
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                app = dialog.get_app_info()
                if app:
                    self._launch_with_app(app, path)
            dialog.destroy()
        except Exception as exc:
            self.show_message(str(exc))

    def _make_menu_item(self, label, icon_name=None):
        item = Gtk.MenuItem()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        chosen = None
        if icon_name:
            candidates = [icon_name] if isinstance(icon_name, str) else list(icon_name)
            try:
                theme = Gtk.IconTheme.get_default()
                for cand in candidates:
                    if theme.has_icon(cand):
                        chosen = cand
                        break
                if chosen is None and candidates:
                    chosen = candidates[0]
            except Exception:
                chosen = candidates[0] if candidates else None

        if chosen:
            try:
                image = Gtk.Image.new_from_icon_name(chosen, Gtk.IconSize.MENU)
                box.pack_start(image, False, False, 0)
            except Exception:
                pass
        lbl = Gtk.Label(label=label, xalign=0)
        box.pack_start(lbl, True, True, 0)
        item.add(box)
        return item

    def show_context_menu(self, event, clicked_hit=None):
        menu = Gtk.Menu()
        selected = self._resolve_selection(clicked_hit)
        in_trash = self.is_trash_view()

        if selected:
            open_item = self._make_menu_item(tr('open'), 'document-open')
            open_item.connect('activate', lambda *_: self._open_first_selected_paths(selected))
            menu.append(open_item)

            if len(selected) >= 1:
                open_with_item = self._make_menu_item(tr('open_with'), 'document-open-symbolic')
                open_with_item.set_submenu(self._build_open_with_submenu(selected[0]))
                menu.append(open_with_item)

            if any(os.path.isfile(p) for p in selected):
                run_term_item = self._make_menu_item(tr('run_in_terminal'), ('utilities-terminal', 'terminal', 'gnome-terminal'))
                run_term_item.connect('activate', lambda *_: self._run_in_terminal(selected))
                menu.append(run_term_item)

            if any(self._is_image(p) for p in selected):
                send_bg_item = self._make_menu_item(tr('send_to_backgrounds'), ('preferences-desktop-wallpaper', 'preferences-desktop', 'image-x-generic'))
                send_bg_item.connect('activate', lambda *_: self._send_to_backgrounds(selected))
                menu.append(send_bg_item)

            menu.append(Gtk.SeparatorMenuItem())

            copy_item = self._make_menu_item(tr('copy'), 'edit-copy')
            copy_item.connect('activate', lambda *_: self._copy_paths(selected))
            menu.append(copy_item)

            if in_trash:
                restore_item = self._make_menu_item(tr('restore'), 'edit-undo')
                restore_item.connect('activate', lambda *_: self.restore_selected())
                menu.append(restore_item)

            delete_label = tr('delete_permanent') if in_trash else tr('move_to_trash')
            delete_icon = 'edit-delete' if in_trash else 'user-trash'
            delete_item = self._make_menu_item(delete_label, delete_icon)
            delete_item.connect('activate', lambda *_: self._delete_paths(selected, permanent=in_trash))
            menu.append(delete_item)

            if not in_trash:
                delete_perm_item = self._make_menu_item(tr('delete_permanent'), 'edit-delete')
                delete_perm_item.connect('activate', lambda *_: self._delete_paths(selected, permanent=True))
                menu.append(delete_perm_item)

            menu.append(Gtk.SeparatorMenuItem())

        paste_item = self._make_menu_item(tr('paste_here'), 'edit-paste')
        paste_item.connect('activate', lambda *_: self.paste_into_current())
        paste_item.set_sensitive(bool(self.clipboard_paths) and not in_trash)
        menu.append(paste_item)

        new_folder_item = self._make_menu_item(tr('new_folder'), ('folder-new', 'folder'))
        new_folder_item.connect('activate', lambda *_: self.create_folder_dialog())
        new_folder_item.set_sensitive(not in_trash)
        menu.append(new_folder_item)

        duplicates_item = self._make_menu_item(tr('duplicate_scanner'), ('edit-find', 'system-search'))
        duplicates_item.connect('activate', lambda *_: self.open_duplicate_scanner())
        duplicates_item.set_sensitive(not in_trash)
        menu.append(duplicates_item)

        refresh_item = self._make_menu_item(tr('refresh_menu'), 'view-refresh')
        refresh_item.connect('activate', lambda *_: self.refresh())
        menu.append(refresh_item)

        show_hidden_item = Gtk.CheckMenuItem(label=tr('show_hidden_menu'))
        show_hidden_item.set_active(self.show_hidden)
        show_hidden_item.connect('toggled', lambda *_: self.toggle_hidden())
        menu.append(show_hidden_item)

        menu.show_all()
        menu.popup_at_pointer(event)

    def open_duplicate_scanner(self):
        dialog = DuplicateScannerDialog(self.get_toplevel(), self.current_path)
        dialog.run()
        dialog.destroy()
        self.refresh()

    def _open_first_selected_paths(self, paths):
        if not paths:
            return
        path = paths[0]
        self._open_selected_path(path, os.path.isdir(path))

    def _copy_paths(self, paths):
        self.clipboard_paths = list(paths)
        self.show_message(f"{len(self.clipboard_paths)} {tr('copied_items')}")

    def _delete_paths(self, paths, permanent=False):
        if not paths:
            self.show_message(tr('no_selection'))
            return
        if permanent or self.is_trash_view():
            text = tr('ask_delete_perm')
        else:
            text = tr('ask_move_trash')
        dialog = Gtk.MessageDialog(transient_for=self.get_toplevel(), modal=True,
                                   message_type=Gtk.MessageType.QUESTION,
                                   buttons=Gtk.ButtonsType.OK_CANCEL, text=text)
        resp = dialog.run()
        dialog.destroy()
        if resp != Gtk.ResponseType.OK:
            return
        try:
            if permanent or self.is_trash_view():
                self.trash.delete_permanently(paths)
                self.show_message(tr('trash_deleted'))
            else:
                self.trash.move_to_trash(paths)
                self.show_message(tr('trash_moved'))
            self.refresh()
        except Exception as exc:
            self.show_message(str(exc))

    def _open_first_selected(self):
        selected = self.selected_paths()
        if not selected:
            return
        path = selected[0]
        self._open_selected_path(path, os.path.isdir(path))

    def _copy_selected(self):
        self.clipboard_paths = self.selected_paths()
        self.show_message(f"{len(self.clipboard_paths)} {tr('copied_items')}")

    def _is_image(self, path):
        try:
            if not os.path.isfile(path):
                return False
            ext = os.path.splitext(path)[1].lower()
            return ext in _IMAGE_EXTS
        except Exception:
            return False

    def _run_in_terminal(self, paths):
        if not paths:
            return
        if not os.path.isfile(_RUN_IN_TERMINAL):
            self.show_message(f"{tr('run_failed')} {_RUN_IN_TERMINAL}")
            return
        for path in paths:
            if not os.path.isfile(path):
                continue
            try:
                subprocess.Popen([_RUN_IN_TERMINAL, path],
                                 cwd=os.path.dirname(path) or self.current_path)
            except Exception as exc:
                self.show_message(f"{tr('run_failed')} {exc}")

    def _send_to_backgrounds(self, paths):
        images = [p for p in paths if self._is_image(p)]
        if not images:
            return
        if not find_escalator():
            self.show_message(f"{tr('send_failed')} pkexec / gksu")
            return
        try:
            run_privileged(['/bin/cp', '-rf', '--'] + images + ['/usr/share/backgrounds'])
            self.show_message(tr('sent_to_backgrounds'))
        except Exception as exc:
            self.show_message(f"{tr('send_failed')} {exc}")
