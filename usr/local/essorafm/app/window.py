# EssoraFM
# Author: josejp2424 and Nilsonmorales - GPL-3.0
import configparser
import os
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib

from core.settings import APP_ID, APP_NAME, ICON_PATH, GTK3_SETTINGS_INI, DEFAULT_START_DIR, ABOUT_GREEN
from core.settings_manager import SettingsManager
from core.i18n import tr
from app.sidebar import Sidebar
from app.pathbar import PathBar
from app.tabs import Tabs
from app.toolbar import Toolbar
from app.preview_panel import PreviewPanel
from app.dialogs import PreferencesDialog, AboutDialog
from services import themes as theme_service


class EssoraFMApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.window = None
        self.start_path = None

    def do_activate(self):
        if self.window is None:
            self.window = MainWindow(self)
        self.window.present()

    def run(self, argv):
        cleaned = [argv[0]] if argv else []
        for arg in argv[1:]:
            if not arg.startswith('-') and os.path.exists(arg):
                self.start_path = os.path.abspath(arg)
                continue
            cleaned.append(arg)
        return super().run(cleaned)


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=APP_NAME)
        self.settings_manager = SettingsManager()
        self._apply_theme_from_settings_ini()
        self._apply_local_css()
        win_w = self.settings_manager.get_int('window_width', 940)
        win_h = self.settings_manager.get_int('window_height', 600)
        win_w = max(760, min(win_w, 1600))
        win_h = max(520, min(win_h, 1000))
        self.set_default_size(win_w, win_h)
        self.set_position(Gtk.WindowPosition.CENTER)
        if os.path.exists(ICON_PATH):
            try:
                self.set_icon_from_file(ICON_PATH)
            except Exception:
                pass

        self.root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.root.get_style_context().add_class('essorafm-root')
        self.add(self.root)

        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        if os.path.exists(ICON_PATH):
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(ICON_PATH, 18, 18, True)
                header.pack_start(Gtk.Image.new_from_pixbuf(pix))
            except Exception:
                pass
        title = Gtk.Label(label=APP_NAME)
        title.get_style_context().add_class('essorafm-title')
        header.set_custom_title(title)

        prefs_btn = Gtk.Button()
        prefs_btn.get_style_context().add_class('essorafm-header-button')
        prefs_btn.add(Gtk.Image.new_from_icon_name('preferences-system-symbolic', Gtk.IconSize.BUTTON))
        prefs_btn.set_tooltip_text(tr('preferences'))
        prefs_btn.connect('clicked', self.show_preferences)
        header.pack_end(prefs_btn)

        about_btn = Gtk.Button()
        about_btn.get_style_context().add_class('essorafm-header-button')
        about_btn.add(Gtk.Image.new_from_icon_name('help-about-symbolic', Gtk.IconSize.BUTTON))
        about_btn.set_tooltip_text(tr('about'))
        about_btn.connect('clicked', self.show_about)
        header.pack_end(about_btn)
        self.set_titlebar(header)

        self.toolbar = Toolbar(self.go_back, self.go_up, self.refresh_current,
                               self.new_tab, self.new_folder, self.toggle_hidden,
                               self.show_preferences, self.open_duplicate_scanner,
                               on_view_mode=self._on_view_mode_changed,
                               on_sort=self._on_sort_changed,
                               on_split_view=self._on_split_view_toggled,
                               on_find_files=self.open_find_files,
                               settings_manager=self.settings_manager)
        self.pathbar = PathBar(self.open_path, on_search_changed=self._on_search_changed)

        self.preview_toggle = Gtk.ToggleButton(label=tr('preview'))
        self.preview_toggle.set_active(self.settings_manager.get_bool('preview_enabled', True))
        self.preview_toggle.connect('toggled', self._on_preview_toggled)

        self.sidebar = Sidebar(self.open_path, self.show_message, None, None,
                               self.settings_manager)

        # Bottom sidebar artwork - requested by josejp2424
        self.sidebar_art_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.sidebar_art_box.get_style_context().add_class('essorafm-sidebar-art-box')
        self.sidebar_art_box.set_halign(Gtk.Align.CENTER)
        self.sidebar_art_box.set_valign(Gtk.Align.END)
        self.sidebar_art = Gtk.Image()
        self.sidebar_art.get_style_context().add_class('essorafm-sidebar-art')
        self._load_sidebar_art()
        self.sidebar_art_box.pack_start(self.sidebar_art, False, False, 0)

        self._split_active = False
        self._split_paned  = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        self._split_paned.get_style_context().add_class('essorafm-split-paned')
        self.tabs = Tabs(self.show_message, self.update_pathbar, self.settings_manager)
        self.tabs_right = Tabs(self.show_message, self._on_right_panel_changed,
                               self.settings_manager)
        self._split_paned.add1(self.tabs)
        self._split_paned.add2(self.tabs_right)
        self.tabs_right.set_no_show_all(True)
        self.tabs_right.hide()
        
        self._active_panel = 'left'

        self.content_paned = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        self.preview_panel = PreviewPanel()
        self.content_paned.add1(self._split_paned)
        self.content_paned.add2(self.preview_panel)
        self.content_paned.set_position(max(420, win_w - 430))

        self.status = Gtk.Label(label=tr('ready'), xalign=0)
        self.status.get_style_context().add_class('essorafm-status')
        self._permanent_status_text = tr('ready')
        self._status_restore_id = None

        self._layout_container = None
        self._build_layout()

        self.tabs.add_tab(app.start_path or DEFAULT_START_DIR)
        self._sync_preview_callback()
        self.update_pathbar()
        self.connect('key-press-event', self._on_key_press)
        
        self._connect_panel_click_events()
        
        self.tabs.connect('switch-page', self._on_tab_switched)
        self.tabs_right.connect('switch-page', self._on_tab_switched)
        
        self.show_all()
        self._apply_app_theme()
        self._sync_hidden_button()

        current_view = self.current_view()
        if current_view:
            self.toolbar.set_view_mode(current_view.view_mode)
        
        self.toolbar.set_sort(
            self.settings_manager.get('sort_field', 'name'),
            self.settings_manager.get('sort_direction', 'asc'),
        )
        
        self._apply_preview_visibility(self.preview_toggle.get_active())
        
        self._update_panel_style()
        
        GLib.idle_add(self.update_status_from_active_view)

    def update_status_from_active_view(self):
        """Actualiza la barra de estado desde la vista activa."""
        view = self.current_view()
        if view and hasattr(view, 'update_status'):
            view.update_status()

    def _on_tab_switched(self, notebook, page, page_num):
        """Cuando se cambia de pestaña, actualizar la barra de estado."""
        self.update_status_from_active_view()

    def _connect_panel_click_events(self):
        """Conecta eventos de clic para detectar qué panel está activo."""
        self.tabs.connect('button-press-event', self._on_panel_click, 'left')
        self.tabs.connect('focus-in-event', self._on_panel_focus, 'left')
        
        self.tabs_right.connect('button-press-event', self._on_panel_click, 'right')
        self.tabs_right.connect('focus-in-event', self._on_panel_focus, 'right')
        
        self._connect_fileview_events(self.tabs, 'left')
        self._connect_fileview_events(self.tabs_right, 'right')
        
        self.tabs.connect('page-added', self._on_tab_added, 'left')
        self.tabs_right.connect('page-added', self._on_tab_added, 'right')

    def _connect_fileview_events(self, tabs_widget, panel_name):
        """Conecta eventos a los FileView dentro de un panel."""
        for idx in range(tabs_widget.get_n_pages()):
            view = tabs_widget.get_nth_page(idx)
            if view:
                view.connect('button-press-event', self._on_fileview_click, panel_name)
                view.connect('focus-in-event', self._on_fileview_focus, panel_name)

    def _on_tab_added(self, tabs_widget, child, page_num, panel_name):
        """Cuando se agrega una nueva pestaña, conectar sus eventos."""
        if child:
            child.connect('button-press-event', self._on_fileview_click, panel_name)
            child.connect('focus-in-event', self._on_fileview_focus, panel_name)

    def _on_panel_click(self, widget, event, panel_name):
        """Cuando se hace clic en un panel, activarlo."""
        if self._active_panel != panel_name:
            self._active_panel = panel_name
            self.update_pathbar()
            self._sync_hidden_button()
            self._update_panel_style()
            
            view = self.current_view()
            if view:
                self.toolbar.set_view_mode(view.view_mode)
                self.update_status_from_active_view()
        return False

    def _on_panel_focus(self, widget, event, panel_name):
        """Cuando un panel recibe foco, activarlo."""
        if self._active_panel != panel_name:
            self._active_panel = panel_name
            self.update_pathbar()
            self._sync_hidden_button()
            self._update_panel_style()
            view = self.current_view()
            if view:
                self.toolbar.set_view_mode(view.view_mode)
                self.update_status_from_active_view()
        return False

    def _on_fileview_click(self, widget, event, panel_name):
        """Cuando se hace clic en un FileView, activar su panel."""
        if self._active_panel != panel_name:
            self._active_panel = panel_name
            self.update_pathbar()
            self._sync_hidden_button()
            self._update_panel_style()
            view = self.current_view()
            if view:
                self.toolbar.set_view_mode(view.view_mode)
                self.update_status_from_active_view()
        return False

    def _on_fileview_focus(self, widget, event, panel_name):
        """Cuando un FileView recibe foco, activar su panel."""
        if self._active_panel != panel_name:
            self._active_panel = panel_name
            self.update_pathbar()
            self._sync_hidden_button()
            self._update_panel_style()
            view = self.current_view()
            if view:
                self.toolbar.set_view_mode(view.view_mode)
                self.update_status_from_active_view()
        return False

    def _apply_local_css(self):
        """Aplica CSS profesional con barra de acento para panel activo."""
        css = f"""
        button.about-green, button.about-green label {{ color: {ABOUT_GREEN}; }}
        
        /* Estilo profesional para panel activo - barra de acento superior */
        .panel-underline {{
            box-shadow: inset 0 2px 0 0 @selected_bg_color;
            border-radius: 6px 6px 0 0;
            transition: all 0.1s ease;
        }}
        
        /* Estilo para panel inactivo - sin barra */
        .panel-inactive {{
            box-shadow: none;
        }}
        
        /* ============================================
           ESTILOS COMPACTOS PARA PESTAÑAS
           ============================================ */
        .essorafm-tabs tab {{
            padding: 4px 8px;
            min-width: 150px;
        }}
        
        .essorafm-tab-label label {{
            font-size: 14px;
            margin: 0 4px;
        }}
        
        .essorafm-tab-close {{
            padding: 2px;
            min-width: 20px;
            min-height: 20px;
            border-radius: 10px;
        }}
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), 
            provider, 
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _update_panel_style(self):
        """Aplica barra de acento superior al panel activo (estilo profesional)."""
        for panel in [self.tabs, self.tabs_right]:
            panel.get_style_context().remove_class('panel-underline')
            panel.get_style_context().remove_class('panel-inactive')
        
        if self._split_active:
            if self._active_panel == 'left':
                self.tabs.get_style_context().add_class('panel-underline')
                self.tabs_right.get_style_context().add_class('panel-inactive')
            else:
                self.tabs_right.get_style_context().add_class('panel-underline')
                self.tabs.get_style_context().add_class('panel-inactive')
        else:
            self.tabs.get_style_context().add_class('panel-underline')

    def get_active_panel(self):
        """Retorna el widget del panel activo."""
        if not self._split_active:
            return self.tabs
        
        if self._active_panel == 'right' and self.tabs_right.get_visible():
            return self.tabs_right
        return self.tabs

    def current_view(self):
        """Obtiene la vista activa actual (del panel activo)."""
        active_panel = self.get_active_panel()
        return active_panel.current_view() if active_panel else None

    def _make_left_box(self):
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left_box.get_style_context().add_class('essorafm-sidebar-box')
        left_box.set_size_request(205, -1)
        left_box.pack_start(self.sidebar, True, True, 0)
        left_box.pack_end(self.sidebar_art_box, False, False, 0)
        return left_box

    def _make_pathbar_row(self):
        """Barra unificada: pathbar (con búsqueda integrada) + toggle vista previa."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        row.pack_start(self.pathbar, True, True, 0)
        row.pack_start(self.preview_toggle, False, False, 0)
        return row

    def _make_bars_box(self):
        """Construye el bloque toolbar + pathbar respetando el orden configurado."""
        bars = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        toolbar_first = self.settings_manager.get_bool('toolbar_first', True)
        if toolbar_first:
            bars.pack_start(self.toolbar, False, False, 0)
            bars.pack_start(self._make_pathbar_row(), False, False, 0)
        else:
            bars.pack_start(self._make_pathbar_row(), False, False, 0)
            bars.pack_start(self.toolbar, False, False, 0)
        return bars

    def _make_outer_paned(self, left_widget, right_widget):
        outer = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        outer.get_style_context().add_class('essorafm-paned')
        try:
            outer.set_wide_handle(True)
        except Exception:
            pass
        outer.add1(left_widget)
        outer.add2(right_widget)
        outer.set_position(205)
        return outer

    def _build_layout(self):
        layout = self.settings_manager.get('sidebar_layout', 'classic')
        container = self._assemble_layout(layout)
        self.root.pack_start(container, True, True, 0)
        self._layout_container = container

    def _rebuild_layout(self):
        for widget in (self.toolbar, self.pathbar,
                       self.preview_toggle, self.sidebar, self.sidebar_art_box,
                       self.content_paned, self.status):
            parent = widget.get_parent()
            if parent:
                parent.remove(widget)
        if self._layout_container:
            self.root.remove(self._layout_container)
            self._layout_container.destroy()
            self._layout_container = None

        layout = self.settings_manager.get('sidebar_layout', 'classic')
        container = self._assemble_layout(layout)
        self.root.pack_start(container, True, True, 0)
        self._layout_container = container
        self.root.show_all()
        self.update_pathbar()
        self._sync_hidden_button()

    def _assemble_layout(self, layout):
        if layout == 'top_bar':
            return self._assemble_top_bar_layout()
        else:
            return self._assemble_classic_layout()

    def _assemble_classic_layout(self):
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right_box.get_style_context().add_class('essorafm-content')
        right_box.set_border_width(8)
        bars_bottom = self.settings_manager.get('bars_position', 'top') == 'bottom'
        if not bars_bottom:
            right_box.pack_start(self._make_bars_box(), False, False, 0)
        right_box.pack_start(self.content_paned, True, True, 0)
        right_box.pack_start(self.status, False, False, 0)
        if bars_bottom:
            right_box.pack_start(self._make_bars_box(), False, False, 0)
        return self._make_outer_paned(self._make_left_box(), right_box)

    def _assemble_top_bar_layout(self):
        wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        bars_bottom = self.settings_manager.get('bars_position', 'top') == 'bottom'

        bars_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        bars_widget.get_style_context().add_class('essorafm-topbar')
        bars_widget.set_border_width(6)
        inner = self._make_bars_box()
        bars_widget.pack_start(inner, False, False, 0)

        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        right_box.get_style_context().add_class('essorafm-content')
        right_box.set_border_width(6)
        right_box.pack_start(self.content_paned, True, True, 0)
        right_box.pack_start(self.status, False, False, 0)

        inner_paned = self._make_outer_paned(self._make_left_box(), right_box)

        if not bars_bottom:
            wrapper.pack_start(bars_widget, False, False, 0)
            sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            wrapper.pack_start(sep, False, False, 0)
            wrapper.pack_start(inner_paned, True, True, 0)
        else:
            wrapper.pack_start(inner_paned, True, True, 0)
            sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            wrapper.pack_start(sep, False, False, 0)
            wrapper.pack_start(bars_widget, False, False, 0)
        return wrapper

    def _load_sidebar_art(self):
        image_path = '/usr/local/essorafm/ui/icons/essorafm-about.png'
        fallback_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ui', 'icons', 'essorafm-about.png')
        if not os.path.exists(image_path) and os.path.exists(fallback_path):
            image_path = fallback_path
        if not os.path.exists(image_path):
            return
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(image_path, 185, 145, True)
            self.sidebar_art.set_from_pixbuf(pix)
        except Exception:
            pass

    def _apply_theme_from_settings_ini(self):
        settings = Gtk.Settings.get_default()
        if settings is None or not os.path.exists(GTK3_SETTINGS_INI):
            return
        parser = configparser.ConfigParser()
        try:
            parser.read(GTK3_SETTINGS_INI, encoding='utf-8')
        except Exception:
            return
        if not parser.has_section('Settings'):
            return
        section = parser['Settings']
        theme = section.get('gtk-theme-name', '').strip()
        icon_theme = section.get('gtk-icon-theme-name', '').strip()
        prefer_dark = section.get('gtk-application-prefer-dark-theme', '').strip().lower()
        if theme:
            try:
                settings.set_property('gtk-theme-name', theme)
            except Exception:
                pass
        if icon_theme:
            try:
                settings.set_property('gtk-icon-theme-name', icon_theme)
            except Exception:
                pass
        if prefer_dark in {'1', 'true', 'yes', 'on'}:
            settings.set_property('gtk-application-prefer-dark-theme', True)
        elif prefer_dark in {'0', 'false', 'no', 'off'}:
            settings.set_property('gtk-application-prefer-dark-theme', False)

    _BUILTIN_THEMES = {
        'default': '',         
        'gtk_system': '__SYSTEM__',  
    }


    _theme_provider = None

    def _apply_app_theme(self):
        """Aplica el tema seleccionado inyectando CSS como provider global."""
        from gi.repository import Gdk as _Gdk
        screen = _Gdk.Screen.get_default()
        theme_id = self.settings_manager.get('app_theme', 'default')
        rounded  = self.settings_manager.get_bool('theme_rounded', True)
        cards    = self.settings_manager.get_bool('theme_cards', False)


        if MainWindow._theme_provider is not None:
            try:
                Gtk.StyleContext.remove_provider_for_screen(screen, MainWindow._theme_provider)
            except Exception:
                pass
            MainWindow._theme_provider = None

        if theme_id == 'gtk_system':
            return

        if theme_id in MainWindow._BUILTIN_THEMES:
            css_base = MainWindow._BUILTIN_THEMES[theme_id]
        else:
            theme = theme_service.get_theme(theme_id)
            css_base = theme['css'] if theme else ''

        extra = ""
        if rounded:
            extra += """
            /* ── Sidebar scroll container ── */
            .essorafm-sidebar-scroll {
                border-radius: 10px;
                margin: 6px 4px 6px 6px;
            }
            /* El treeview del sidebar */
            .essorafm-sidebar-tree.view {
                border-radius: 10px;
            }
            /* ── Panel de archivos ── */
            .essorafm-fileview-scroll {
                border-radius: 10px;
                margin: 4px 6px 4px 4px;
            }
            .essorafm-fileview-scroll treeview.view,
            .essorafm-fileview-scroll .essorafm-iconview {
                border-radius: 10px;
            }
            /* quitar sombra/borde que corta las esquinas */
            .essorafm-sidebar-scroll undershoot,
            .essorafm-sidebar-scroll overshoot,
            .essorafm-fileview-scroll undershoot,
            .essorafm-fileview-scroll overshoot {
                background: none;
                border: none;
            }
            """
        if cards:
            extra += """
            .essorafm-fileview-scroll {
                border-radius: 14px;
                margin: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.4);
            }
            """

        full_css = css_base + extra
        if not full_css.strip():
            return

        provider = Gtk.CssProvider()
        try:
            provider.load_from_data(full_css.encode('utf-8'))
        except Exception as e:
            print(f"[EssoraFM] CSS theme error: {e}")
            return

        Gtk.StyleContext.add_provider_for_screen(
            screen, provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1  
        )
        MainWindow._theme_provider = provider

    def _sync_preview_callback(self):
        try:
            for idx in range(self.tabs.get_n_pages()):
                view = self.tabs.get_nth_page(idx)
                if view:
                    view.preview_callback = self.preview_panel.set_file
            for idx in range(self.tabs_right.get_n_pages()):
                view = self.tabs_right.get_nth_page(idx)
                if view:
                    view.preview_callback = self.preview_panel.set_file
        except Exception:
            pass

    def _on_search_changed(self, text):
        """Llamado por PathBar cuando cambia el texto de búsqueda."""
        view = self.current_view()
        if view and hasattr(view, 'set_search_query'):
            view.set_search_query(text)

    def _on_split_view_toggled(self, active):
        """Activa o desactiva el panel dividido."""
        self._split_active = active
        if active:
            if self.tabs_right.get_n_pages() == 0:
                view = self.tabs.current_view()
                path = view.current_path if view else DEFAULT_START_DIR
                self.tabs_right.add_tab(path)
            self.tabs_right.set_no_show_all(False)
            self.tabs_right.show_all()
            self._connect_fileview_events(self.tabs_right, 'right')
            GLib.idle_add(self._equalize_split)
            GLib.idle_add(self.update_status_from_active_view)
        else:
            self.tabs_right.hide()
            self._active_panel = 'left'
            self._update_panel_style()
            self.update_status_from_active_view()
        self.toolbar.set_split_active(active)

    def _equalize_split(self):
        total = self._split_paned.get_allocation().width
        if total > 10:
            self._split_paned.set_position(total // 2)
        return False

    def _on_right_panel_changed(self, *_args):
        """Callback del panel derecho."""
        self._sync_preview_callback()
        if self._active_panel == 'right':
            self.update_pathbar()
            self._sync_hidden_button()
            GLib.idle_add(self.update_status_from_active_view)

    def _on_view_mode_changed(self, mode):
        """Llamado por el toolbar al cambiar el modo de vista (iconos/lista)."""
        view = self.current_view()
        if view and view.view_mode != mode:
            self.settings_manager.set('view_mode', mode)
            self.settings_manager.save()
            view.view_mode = mode

    def _on_sort_changed(self, field, direction):
        """Llamado por el toolbar al seleccionar un nuevo criterio de orden."""
        view = self.current_view()
        if view and hasattr(view, 'apply_sort'):
            view.apply_sort(field, direction)
        self.toolbar.set_sort(field, direction)

    def _on_preview_toggled(self, button):
        """Handler del toggle del usuario: aplica el cambio visual y persiste."""
        visible = button.get_active()
        self._apply_preview_visibility(visible)
        try:
            self.settings_manager.set('preview_enabled', 'true' if visible else 'false')
            self.settings_manager.save()
        except Exception as e:
            print(f"Error saving preview state: {e}")
        self.show_message(tr('preview_on') if visible else tr('preview_off'))

    def _apply_preview_visibility(self, visible):
        """Aplica visualmente el estado del panel sin tocar la config."""
        try:
            self.preview_panel.set_visible(visible)
        except Exception as e:
            print(f"Error toggling preview: {e}")

    def open_path(self, path):
        view = self.current_view()
        if view:
            view.load_path(path)
            self.update_pathbar()
            self._sync_hidden_button()

    def update_pathbar(self, *_args, is_status=False):
        self._sync_preview_callback()
        view = self.current_view()
        if view:
            self.pathbar.set_path(view.current_path)
            self._sync_hidden_button()
            if not is_status:
                GLib.idle_add(self.update_status_from_active_view)

    def go_up(self):
        view = self.current_view()
        if view:
            view.go_up()
            self.update_pathbar()

    def refresh_current(self):
        view = self.current_view()
        if view:
            view.refresh()
            self.update_pathbar()

    def new_tab(self):
        view = self.current_view()
        path = view.current_path if view else DEFAULT_START_DIR
        active_panel = self.get_active_panel()
        active_panel.add_tab(path)
        self.update_pathbar()

    def new_folder(self):
        view = self.current_view()
        if view:
            view.create_folder_dialog()

    def toggle_hidden(self, *_args):
        view = self.current_view()
        if view:
            view.toggle_hidden()
            self._sync_hidden_button()
            self.show_message(tr('show_hidden_visible') if view.show_hidden else tr('show_hidden_hidden'))

    def _sync_hidden_button(self):
        view = self.current_view()
        if view:
            self.toolbar.set_hidden_active(view.show_hidden)

    def go_back(self):
        view = self.current_view()
        if view:
            if not view.go_back():
                self.show_message(tr('no_prev_folder'))
            self.update_pathbar()

    def open_duplicate_scanner(self, *_args):
        view = self.current_view()
        if view:
            view.open_duplicate_scanner()
            self.update_pathbar()

    def open_find_files(self, *_args):
        """Abre el diálogo de búsqueda de archivos. Si hay una vista activa,
        usa su carpeta actual como punto de partida; si no, usa $HOME."""
        from app.find_files import FindFilesDialog
        view = self.current_view()
        initial = []
        if view and getattr(view, 'current_path', None):
            initial.append(view.current_path)
        FindFilesDialog(self, initial_dirs=initial or None)

    def show_message(self, text, is_status=False):
        """Muestra un mensaje en la barra de estado.

        is_status=True  -> mensaje permanente (conteo de archivos/carpetas).
                           Se guarda como estado base y no desaparece.
        is_status=False -> notificacion temporal (copia, borrado, etc.).
                           Se muestra 3 s y luego restaura el estado base.
        """
        self.status.set_text(text)
        if is_status:
            self._permanent_status_text = text
            if self._status_restore_id is not None:
                GLib.source_remove(self._status_restore_id)
                self._status_restore_id = None
        else:
            if self._status_restore_id is not None:
                GLib.source_remove(self._status_restore_id)
            self._status_restore_id = GLib.timeout_add(3000, self._restore_status)

    def _restore_status(self):
        """Restaura el texto de estado permanente tras una notificacion temporal."""
        self._status_restore_id = None
        self.status.set_text(self._permanent_status_text)
        return False

    _LEGACY_DRIVE_ICONS_AUTOSTART = '/etc/xdg/autostart/essorafm_desktop_drive_icons.desktop'

    def _sync_autostart_desktop(self, enabled=None):
        """Remove the old external desktop_drive_icons autostart.

        Drive icons are now handled only by essorafm --desktop. The preference
        desktop_drive_icons controls whether the internal icons are drawn; it
        must not install or start the old standalone binary anymore.
        """
        import os
        from core.privilege import run_privileged

        dst = self._LEGACY_DRIVE_ICONS_AUTOSTART
        if not os.path.exists(dst):
            return
        try:
            run_privileged(['/bin/rm', '-f', '--', dst])
            self.show_message(tr('legacy_external_drive_icons_removed'))
        except RuntimeError as exc:
            self.show_message(f"{tr('autostart_error')} {exc}")

    def apply_ui_settings(self):
        self.tabs.apply_preferences_all()
        self.tabs_right.apply_preferences_all()
        preview_enabled = self.settings_manager.get_bool('preview_enabled', True)
        self.preview_toggle.handler_block_by_func(self._on_preview_toggled)
        self.preview_toggle.set_active(preview_enabled)
        self.preview_toggle.handler_unblock_by_func(self._on_preview_toggled)
        self.preview_panel.set_visible(preview_enabled)
        self.sidebar.apply_preferences()
        if hasattr(self.toolbar, 'refresh_all_buttons'):
            self.toolbar.refresh_all_buttons()
        self.show_message(tr('settings_applied'))

    def show_preferences(self, *_args):
        dialog = PreferencesDialog(self, self.settings_manager)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_values = dialog.values()
            new_drive_icons_str = new_values.get('desktop_drive_icons', 'true').strip().lower()
            new_drive_icons = new_drive_icons_str in ('1', 'true', 'yes', 'on')

            old_layout = self.settings_manager.get('sidebar_layout', 'classic')
            new_layout = new_values.get('sidebar_layout', 'classic')
            old_toolbar_first = self.settings_manager.get('toolbar_first', 'true')
            new_toolbar_first = new_values.get('toolbar_first', 'true')
            old_bars_position = self.settings_manager.get('bars_position', 'top')
            new_bars_position = new_values.get('bars_position', 'top')

            self.settings_manager.update(new_values)

            self._sync_autostart_desktop(new_drive_icons)

            try:
                from core.desktop_settings import DesktopDriveSettings
                DesktopDriveSettings().update({
                    'desktop_drive_icons': self.settings_manager.get('desktop_drive_icons', 'true'),
                    'desktop_drive_icon_size': self.settings_manager.get('desktop_drive_icon_size', '48'),
                    'desktop_drive_show_internal': self.settings_manager.get('desktop_drive_show_internal', 'true'),
                    'desktop_drive_show_removable': self.settings_manager.get('desktop_drive_show_removable', 'true'),
                    'desktop_drive_show_network': self.settings_manager.get('desktop_drive_show_network', 'false'),
                })
            except Exception:
                pass

            self.sidebar.apply_preferences()
            self.tabs.apply_preferences_all()
            self.tabs_right.apply_preferences_all()

            needs_rebuild = (old_layout != new_layout or
                             old_toolbar_first != new_toolbar_first or
                             old_bars_position != new_bars_position)
            if needs_rebuild:
                self._rebuild_layout()
            else:
                if hasattr(self.toolbar, 'refresh_all_buttons'):
                    self.toolbar.refresh_all_buttons()

            new_w = self.settings_manager.get_int('window_width', 940)
            new_h = self.settings_manager.get_int('window_height', 600)
            new_w = max(640, min(new_w, 3840))
            new_h = max(480, min(new_h, 2160))
            self.resize(new_w, new_h)
            
            self.apply_ui_settings()
            self._apply_app_theme()
            self.show_message(tr('saved_preferences'))
        dialog.destroy()

    def show_about(self, *_args):
        dialog = AboutDialog(self)
        dialog.run()
        dialog.destroy()

    def _on_key_press(self, _widget, event):
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)
        if ctrl and event.keyval == Gdk.KEY_t:
            self.new_tab()
            return True
        if ctrl and event.keyval == Gdk.KEY_w:
            view = self.current_view()
            if view:
                active_panel = self.get_active_panel()
                active_panel.close_tab(view)
            return True
        if ctrl and event.keyval == Gdk.KEY_l:
            self.pathbar.entry.grab_focus()
            self.pathbar.entry.select_region(0, -1)
            return True
        if ctrl and event.keyval == Gdk.KEY_h:
            self.toggle_hidden()
            return True
        if ctrl and event.keyval == Gdk.KEY_comma:
            self.show_preferences()
            return True
        if ctrl and event.keyval == Gdk.KEY_f:
            self.open_find_files()
            return True
        if event.keyval == Gdk.KEY_Tab and ctrl:
            if self._split_active:
                if self._active_panel == 'left':
                    self._active_panel = 'right'
                else:
                    self._active_panel = 'left'
                self._update_panel_style()
                self.update_pathbar()
                self._sync_hidden_button()
                view = self.current_view()
                if view:
                    self.toolbar.set_view_mode(view.view_mode)
                    self.update_status_from_active_view()
            return True
        return False
