# EssoraFM
# Author: josejp2424 - GPL-3.0
import os
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf

from core.copy_engine import CopyEngine
from core.settings import APP_NAME, ICON_PATH, ABOUT_ICON_PATH
from core.i18n import tr, LANG


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
        for size in (16, 20, 24, 28, 32):
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

        self.show_all()

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
        }


class AboutDialog(Gtk.AboutDialog):
    def __init__(self, parent):
        super().__init__(transient_for=parent, modal=True)
        self.set_program_name(APP_NAME)
        self.set_version('0.4.11')
        self.set_comments(tr('about_comments'))
        self.set_license_type(Gtk.License.GPL_3_0)
        self.set_website('https://sourceforge.net/projects/essora/')
        self.set_website_label('Essora')
        self.set_authors(['josejp2424 * Nilsonmorales'])
        self.set_copyright('GPL-3.0')
        target = ABOUT_ICON_PATH if os.path.exists(ABOUT_ICON_PATH) else ICON_PATH
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(target, 128, 128, True)
            self.set_logo(pix)
            self.set_icon(pix)
        except Exception:
            pass
