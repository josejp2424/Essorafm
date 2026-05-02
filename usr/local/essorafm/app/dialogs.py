# EssoraFM
# Author: josejp2424 and Nilsonmorales - GPL-3.0
import os
import subprocess
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf

from core.copy_engine import CopyEngine
from core.settings import APP_NAME, ICON_PATH, ABOUT_ICON_PATH
from core.i18n import tr, LANG
from services import themes as theme_service


class CopyProgressDialog(Gtk.Dialog):
    """Diálogo compacto de progreso de copia con porcentaje visible."""

    def __init__(self, parent, sources, destination, on_done, title=None):
        super().__init__(title=title or 'Copiando archivos', transient_for=parent, modal=True)
        self.set_default_size(380, -1)
        self.set_resizable(False)
        self.engine = CopyEngine()
        self.on_done = on_done

        area = self.get_content_area()
        area.set_margin_top(10)
        area.set_margin_bottom(4)
        area.set_margin_start(12)
        area.set_margin_end(12)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        area.add(box)

        self.label = Gtk.Label(label=tr('preparing'), xalign=0)
        self.label.set_max_width_chars(48)
        self.label.set_ellipsize(3)  
        box.pack_start(self.label, False, False, 0)

        bar_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.progress = Gtk.ProgressBar()
        self.progress.set_hexpand(True)
        self.progress.set_valign(4)  
        bar_row.pack_start(self.progress, True, True, 0)

        self.pct_label = Gtk.Label(label='0%')
        self.pct_label.set_width_chars(5)
        self.pct_label.set_xalign(1.0)
        bar_row.pack_start(self.pct_label, False, False, 0)
        box.pack_start(bar_row, False, False, 0)

        self.add_button(tr('cancel_button'), Gtk.ResponseType.CANCEL)
        self.connect('response', self._on_response)
        self.show_all()

        self.engine.copy(sources, destination, self.update_progress, self.copy_finished)

    def update_progress(self, message, fraction):
        self.label.set_text(message)
        frac = max(0.0, min(fraction, 1.0))
        if frac <= 0:
            self.progress.pulse()
            self.pct_label.set_text('...')
        else:
            self.progress.set_fraction(frac)
            self.pct_label.set_text(f'{int(frac * 100)}%')
        return False

    def copy_finished(self, ok, error_text):
        self.destroy()
        self.on_done(ok, error_text)
        return False

    def _on_response(self, _dialog, response_id):
        if response_id == Gtk.ResponseType.CANCEL:
            self.engine.cancel()


class PreferencesDialog(Gtk.Dialog):
    def __init__(self, parent, settings_manager):
        super().__init__(title=tr('preferences'), transient_for=parent, modal=True)
        self.settings_manager = settings_manager
        self.set_default_size(700, 480)
        self.add_buttons(tr('cancel'), Gtk.ResponseType.CANCEL, tr('save'), Gtk.ResponseType.OK)

        area = self.get_content_area()
        area.set_margin_top(12)
        area.set_margin_bottom(12)
        area.set_margin_start(12)
        area.set_margin_end(12)

        main = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        area.add(main)

        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        stack.set_transition_duration(200)

        sidebar = Gtk.StackSidebar()
        sidebar.set_stack(stack)
        sidebar.set_size_request(160, -1)
        main.pack_start(sidebar, False, False, 0)
        main.pack_start(stack, True, True, 0)

        page_general = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14, margin=6)
        frame1 = Gtk.Frame(label=tr('interface'))
        grid1 = Gtk.Grid(column_spacing=12, row_spacing=10, margin=12)
        frame1.add(grid1)
        page_general.pack_start(frame1, False, False, 0)

        self.view_combo = Gtk.ComboBoxText()
        self.view_combo.append('icons', tr('icons_view_option'))
        self.view_combo.append('list', tr('list_view_option'))
        self.view_combo.set_active_id(settings_manager.get('view_mode', 'icons'))
        grid1.attach(Gtk.Label(label=tr('view_mode'), xalign=0), 0, 0, 1, 1)
        grid1.attach(self.view_combo, 1, 0, 1, 1)

        self.single_click = Gtk.CheckButton(label=tr('single_click'))
        self.single_click.set_active(settings_manager.get_bool('single_click', False))
        grid1.attach(self.single_click, 0, 1, 2, 1)

        self.show_hidden = Gtk.CheckButton(label=tr('show_hidden_start'))
        self.show_hidden.set_active(settings_manager.get_bool('show_hidden', False))
        grid1.attach(self.show_hidden, 0, 2, 2, 1)

        self.show_thumbnails = Gtk.CheckButton(label=tr('show_thumbnails'))
        self.show_thumbnails.set_active(settings_manager.get_bool('show_thumbnails', True))
        grid1.attach(self.show_thumbnails, 0, 3, 2, 1)

        self.preview_enabled = Gtk.CheckButton(label=tr('preview_enabled') if tr('preview_enabled') != 'preview_enabled' else 'Mostrar panel de vista previa')
        self.preview_enabled.set_active(settings_manager.get_bool('preview_enabled', True))
        grid1.attach(self.preview_enabled, 0, 4, 2, 1)

        self.desktop_drive_icons = Gtk.CheckButton(label=tr('desktop_drive_icons'))
        self.desktop_drive_icons.set_active(settings_manager.get_bool('desktop_drive_icons', True))
        grid1.attach(self.desktop_drive_icons, 0, 5, 2, 1)

        _sl_label_text = tr('sidebar_layout') if tr('sidebar_layout') != 'sidebar_layout' else 'Diseño del panel'
        _sl_classic     = tr('sidebar_layout_classic') if tr('sidebar_layout_classic') != 'sidebar_layout_classic' else 'Clásico (sidebar a la par)'
        _sl_top         = tr('sidebar_layout_top_bar') if tr('sidebar_layout_top_bar') != 'sidebar_layout_top_bar' else 'Compacto (barra arriba)'
        grid1.attach(Gtk.Label(label=_sl_label_text, xalign=0), 0, 6, 1, 1)
        self.sidebar_layout_combo = Gtk.ComboBoxText()
        self.sidebar_layout_combo.append('classic', _sl_classic)
        self.sidebar_layout_combo.append('top_bar', _sl_top)
        self.sidebar_layout_combo.set_active_id(settings_manager.get('sidebar_layout', 'classic'))
        grid1.attach(self.sidebar_layout_combo, 1, 6, 1, 1)

        _tf_label = tr('toolbar_first')
        _tf_toolbar_first = tr('toolbar_first_option')
        _tf_pathbar_first = tr('pathbar_first_option')
        grid1.attach(Gtk.Label(label=_tf_label, xalign=0), 0, 7, 1, 1)
        self.toolbar_first_combo = Gtk.ComboBoxText()
        self.toolbar_first_combo.append('true', _tf_toolbar_first)
        self.toolbar_first_combo.append('false', _tf_pathbar_first)
        self.toolbar_first_combo.set_active_id(
            'true' if settings_manager.get_bool('toolbar_first', True) else 'false')
        grid1.attach(self.toolbar_first_combo, 1, 7, 1, 1)

        _bp_label = tr('bars_position')
        _bp_top = tr('bars_position_top')
        _bp_bottom = tr('bars_position_bottom')
        grid1.attach(Gtk.Label(label=_bp_label, xalign=0), 0, 8, 1, 1)
        self.bars_position_combo = Gtk.ComboBoxText()
        self.bars_position_combo.append('top', _bp_top)
        self.bars_position_combo.append('bottom', _bp_bottom)
        self.bars_position_combo.set_active_id(settings_manager.get('bars_position', 'top'))
        grid1.attach(self.bars_position_combo, 1, 8, 1, 1)

        stack.add_titled(page_general, 'general', tr('general'))

        page_view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14, margin=6)
        frame2 = Gtk.Frame(label=tr('icons'))
        grid2 = Gtk.Grid(column_spacing=12, row_spacing=10, margin=12)
        frame2.add(grid2)
        page_view.pack_start(frame2, False, False, 0)

        self.icon_combo = Gtk.ComboBoxText()
        for size in (32, 48, 64, 72, 96, 128):
            self.icon_combo.append(str(size), f'{size}x{size}')
        self.icon_combo.set_active_id(str(settings_manager.get_int('icon_size', 64)))
        grid2.attach(Gtk.Label(label=tr('large_icons'), xalign=0), 0, 0, 1, 1)
        grid2.attach(self.icon_combo, 1, 0, 1, 1)

        self.list_icon_combo = Gtk.ComboBoxText()
        for size in (16, 20, 24, 32, 40):
            self.list_icon_combo.append(str(size), f'{size}x{size}')
        self.list_icon_combo.set_active_id(str(settings_manager.get_int('list_icon_size', 24)))
        grid2.attach(Gtk.Label(label=tr('small_icons'), xalign=0), 0, 1, 1, 1)
        grid2.attach(self.list_icon_combo, 1, 1, 1, 1)

        self.sidebar_icon_combo = Gtk.ComboBoxText()
        for size in (16, 20, 24, 28, 32, 40, 48):
            self.sidebar_icon_combo.append(str(size), f'{size}x{size}')
        self.sidebar_icon_combo.set_active_id(str(settings_manager.get_int('sidebar_icon_size', 20)))
        grid2.attach(Gtk.Label(label=tr('sidebar_icons'), xalign=0), 0, 2, 1, 1)
        grid2.attach(self.sidebar_icon_combo, 1, 2, 1, 1)

        self.desktop_drive_icon_combo = Gtk.ComboBoxText()
        for size in (32, 48, 64, 72, 96):
            self.desktop_drive_icon_combo.append(str(size), f'{size}x{size}')
        self.desktop_drive_icon_combo.set_active_id(str(settings_manager.get_int('desktop_drive_icon_size', 48)))
        grid2.attach(Gtk.Label(label=tr('desktop_drive_icon_size'), xalign=0), 0, 3, 1, 1)
        grid2.attach(self.desktop_drive_icon_combo, 1, 3, 1, 1)

        self.toolbar_icon_combo = Gtk.ComboBoxText()
        for size in (16, 18, 20, 22, 24, 28, 32):
            self.toolbar_icon_combo.append(str(size), f'{size}x{size}')
        self.toolbar_icon_combo.set_active_id(str(settings_manager.get_int('toolbar_icon_size', 20)))
        grid2.attach(Gtk.Label(label=tr('toolbar_icon_size'), xalign=0), 0, 4, 1, 1)
        grid2.attach(self.toolbar_icon_combo, 1, 4, 1, 1)

        stack.add_titled(page_view, 'view', tr('visualization'))

        page_layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14, margin=6)
        frame3 = Gtk.Frame(label=tr('window_size'))
        grid3 = Gtk.Grid(column_spacing=12, row_spacing=10, margin=12)
        frame3.add(grid3)
        page_layout.pack_start(frame3, False, False, 0)

        self.window_presets = [
            ('640x480', tr('preset_compact'), 640, 480),
            ('880x550', tr('preset_medium'), 880, 550),
            ('1040x680', tr('preset_large'), 1040, 680),
            ('custom', tr('preset_custom'), None, None),
        ]
        current_w = settings_manager.get_int('window_width', 880)
        current_h = settings_manager.get_int('window_height', 550)

        self.window_preset_combo = Gtk.ComboBoxText()
        for preset_id, label, _w, _h in self.window_presets:
            self.window_preset_combo.append(preset_id, label)

        active_preset = 'custom'
        for preset_id, _label, w, h in self.window_presets:
            if w == current_w and h == current_h:
                active_preset = preset_id
                break
        self.window_preset_combo.set_active_id(active_preset)
        grid3.attach(Gtk.Label(label=tr('preset'), xalign=0), 0, 0, 1, 1)
        grid3.attach(self.window_preset_combo, 1, 0, 2, 1)

        self.window_width_spin = Gtk.SpinButton.new_with_range(640, 3840, 10)
        self.window_width_spin.set_value(current_w)
        grid3.attach(Gtk.Label(label=tr('width'), xalign=0), 0, 1, 1, 1)
        grid3.attach(self.window_width_spin, 1, 1, 1, 1)

        self.window_height_spin = Gtk.SpinButton.new_with_range(480, 2160, 10)
        self.window_height_spin.set_value(current_h)
        grid3.attach(Gtk.Label(label=tr('height'), xalign=0), 0, 2, 1, 1)
        grid3.attach(self.window_height_spin, 1, 2, 1, 1)

        self.window_preset_combo.connect('changed', self._on_preset_changed)
        self.window_width_spin.connect('value-changed', self._on_window_size_spin_changed)
        self.window_height_spin.connect('value-changed', self._on_window_size_spin_changed)
        self._sync_spins_with_preset()

        stack.add_titled(page_layout, 'layout', tr('layout'))

        page_themes = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14, margin=6)

        frame_theme = Gtk.Frame(label=tr('themes_app_section'))
        grid_theme = Gtk.Grid(column_spacing=12, row_spacing=10, margin=12)
        frame_theme.add(grid_theme)
        page_themes.pack_start(frame_theme, False, False, 0)

        grid_theme.attach(Gtk.Label(label=tr('themes_theme'), xalign=0), 0, 0, 1, 1)
        self.theme_combo = Gtk.ComboBoxText()
        self.theme_combo.append('default',    tr('themes_default'))
        self.theme_combo.append('gtk_system', tr('themes_gtk_system'))
        self._theme_descriptions = {
            'default':    tr('themes_default_desc'),
            'gtk_system': tr('themes_gtk_system_desc'),
        }
        for t in theme_service.list_themes():
            label = f"{t['emoji']} {t['name']}".strip() if t['emoji'] else t['name']
            self.theme_combo.append(t['id'], label)
            self._theme_descriptions[t['id']] = (
                f"{t['emoji']} {t['description']}".strip()
                if t['emoji'] else t['description']
            )
        self.theme_combo.set_active_id(settings_manager.get('app_theme', 'default'))
        grid_theme.attach(self.theme_combo, 1, 0, 1, 1)

        frame_preview = Gtk.Frame(label=tr('themes_preview'))
        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=12)
        frame_preview.add(preview_box)
        page_themes.pack_start(frame_preview, True, True, 0)

        self._theme_preview_label = Gtk.Label(xalign=0)
        self._theme_preview_label.set_line_wrap(True)
        preview_box.pack_start(self._theme_preview_label, False, False, 0)

        frame_style = Gtk.Frame(label=tr('themes_style_options'))
        grid_style = Gtk.Grid(column_spacing=12, row_spacing=8, margin=12)
        frame_style.add(grid_style)
        page_themes.pack_start(frame_style, False, False, 0)

        self.rounded_corners = Gtk.CheckButton(label=tr('themes_rounded'))
        self.rounded_corners.set_active(settings_manager.get_bool('theme_rounded', True))
        grid_style.attach(self.rounded_corners, 0, 0, 2, 1)

        self.card_style = Gtk.CheckButton(label=tr('themes_card_style'))
        self.card_style.set_active(settings_manager.get_bool('theme_cards', False))
        grid_style.attach(self.card_style, 0, 1, 2, 1)

        self.glassmorphism = Gtk.CheckButton(label=tr('themes_glass'))
        self.glassmorphism.set_active(settings_manager.get_bool('theme_glass', False))
        grid_style.attach(self.glassmorphism, 0, 2, 2, 1)

        self.theme_combo.connect('changed', self._on_theme_combo_changed)
        self._update_theme_preview()

        _themes_label = tr('themes_tab')
        stack.add_titled(page_themes, 'themes', _themes_label)

        self.show_all()

    def _on_theme_combo_changed(self, _combo):
        self._update_theme_preview()

    def _update_theme_preview(self):
        tid = self.theme_combo.get_active_id() or 'default'
        text = self._theme_descriptions.get(tid, '')
        self._theme_preview_label.set_text(text)

    def _sync_spins_with_preset(self):
        active = self.window_preset_combo.get_active_id()
        is_custom = (active == 'custom')
        self.window_width_spin.set_sensitive(is_custom)
        self.window_height_spin.set_sensitive(is_custom)

    def _on_preset_changed(self, _combo):
        active = self.window_preset_combo.get_active_id()
        for preset_id, _label, w, h in self.window_presets:
            if preset_id == active and w is not None:
                self.window_width_spin.handler_block_by_func(self._on_window_size_spin_changed)
                self.window_height_spin.handler_block_by_func(self._on_window_size_spin_changed)
                self.window_width_spin.set_value(w)
                self.window_height_spin.set_value(h)
                self.window_width_spin.handler_unblock_by_func(self._on_window_size_spin_changed)
                self.window_height_spin.handler_unblock_by_func(self._on_window_size_spin_changed)
                break
        self._sync_spins_with_preset()

    def _on_window_size_spin_changed(self, _spin):
        if self.window_preset_combo.get_active_id() != 'custom':
            self.window_preset_combo.handler_block_by_func(self._on_preset_changed)
            self.window_preset_combo.set_active_id('custom')
            self.window_preset_combo.handler_unblock_by_func(self._on_preset_changed)
            self._sync_spins_with_preset()

    def values(self):
        return {
            'view_mode': self.view_combo.get_active_id() or 'icons',
            'icon_size': self.icon_combo.get_active_id() or '64',
            'list_icon_size': self.list_icon_combo.get_active_id() or '24',
            'sidebar_icon_size': self.sidebar_icon_combo.get_active_id() or '20',
            'toolbar_icon_size': self.toolbar_icon_combo.get_active_id() or '20',
            'show_hidden': str(self.show_hidden.get_active()).lower(),
            'single_click': str(self.single_click.get_active()).lower(),
            'show_thumbnails': str(self.show_thumbnails.get_active()).lower(),
            'preview_enabled': str(self.preview_enabled.get_active()).lower(),
            'desktop_drive_icons': str(self.desktop_drive_icons.get_active()).lower(),
            'desktop_drive_icon_size': self.desktop_drive_icon_combo.get_active_id() or '48',
            'window_width': str(int(self.window_width_spin.get_value())),
            'window_height': str(int(self.window_height_spin.get_value())),
            'sidebar_layout': self.sidebar_layout_combo.get_active_id() or 'classic',
            'toolbar_first': self.toolbar_first_combo.get_active_id() or 'true',
            'bars_position': self.bars_position_combo.get_active_id() or 'top',
            'app_theme': self.theme_combo.get_active_id() or 'default',
            'theme_rounded': str(self.rounded_corners.get_active()).lower(),
            'theme_cards': str(self.card_style.get_active()).lower(),
            'theme_glass': str(self.glassmorphism.get_active()).lower(),
        }


class AboutDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(transient_for=parent, modal=True)
        self.set_title(f'About {APP_NAME}')
        self.set_resizable(False)
        self.set_default_size(600, -1)
        self.set_border_width(0)

        css = b"""
        .about-title   { font-size: 18pt; font-weight: bold; }
        .about-version { font-size: 12pt; }
        .about-label   { font-size: 12pt; }
        .about-link    { font-size: 12pt; }
        .about-created { font-size: 11pt; font-style: italic; }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(24)
        self.get_content_area().add(box)

        target = ABOUT_ICON_PATH if os.path.exists(ABOUT_ICON_PATH) else ICON_PATH
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(target, 64, 64, True)
            img = Gtk.Image.new_from_pixbuf(pix)
            img.set_halign(Gtk.Align.CENTER)
            box.pack_start(img, False, False, 0)
        except Exception:
            pass

        name_lbl = Gtk.Label(label=APP_NAME)
        name_lbl.get_style_context().add_class('about-title')
        name_lbl.set_halign(Gtk.Align.CENTER)
        box.pack_start(name_lbl, False, False, 0)

        ver_lbl = Gtk.Label(label='Version 0.4.20')
        ver_lbl.get_style_context().add_class('about-version')
        ver_lbl.set_halign(Gtk.Align.CENTER)
        box.pack_start(ver_lbl, False, False, 0)

        box.pack_start(Gtk.Separator(), False, False, 4)

        desc = Gtk.Label(label=tr('about_comments'))
        desc.get_style_context().add_class('about-label')
        desc.set_line_wrap(True)
        desc.set_max_width_chars(38)
        desc.set_justify(Gtk.Justification.CENTER)
        desc.set_halign(Gtk.Align.CENTER)
        box.pack_start(desc, False, False, 0)

        created = Gtk.Label(label='Created by')
        created.get_style_context().add_class('about-created')
        created.set_halign(Gtk.Align.CENTER)
        box.pack_start(created, False, False, 0)

        for username, url in [
            ('josejp2424',    'https://github.com/josejp2424'),
            ('woofshahenzup', 'https://github.com/woofshahenzup'),
        ]:
            btn = Gtk.LinkButton.new_with_label(url, username)
            btn.get_style_context().add_class('about-link')
            btn.set_halign(Gtk.Align.CENTER)
            btn.connect('activate-link', self._open_url)
            box.pack_start(btn, False, False, 0)

        box.pack_start(Gtk.Separator(), False, False, 4)

        site_btn = Gtk.LinkButton.new_with_label(
            'https://sourceforge.net/projects/essora/', 'Essora on SourceForge'
        )
        site_btn.get_style_context().add_class('about-link')
        site_btn.set_halign(Gtk.Align.CENTER)
        site_btn.connect('activate-link', self._open_url)
        box.pack_start(site_btn, False, False, 0)

        lic = Gtk.Label(label='License: GPL-3.0')
        lic.get_style_context().add_class('about-created')
        lic.set_halign(Gtk.Align.CENTER)
        box.pack_start(lic, False, False, 0)

        self.add_button('Close', Gtk.ResponseType.CLOSE)
        self.connect('response', lambda d, _r: d.destroy())
        self.show_all()

    def _open_url(self, btn):
        try:
            subprocess.Popen(['xdg-open', btn.get_uri()])
        except Exception:
            pass
        return True
