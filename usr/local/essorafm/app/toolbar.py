# EssoraFM
# Author: josejp2424 and Nilsonmorales - GPL-3.0
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

from core.i18n import tr


TOOLBAR_STYLE_ICONS_ONLY  = 'icons_only'
TOOLBAR_STYLE_ICONS_FLAT  = 'icons_flat'
TOOLBAR_STYLE_TEXT_BELOW  = 'text_below'
TOOLBAR_STYLE_TEXT_RIGHT  = 'text_right'
TOOLBAR_STYLES = [
    (TOOLBAR_STYLE_ICONS_ONLY, 'toolbar_style_icons_only'),
    (TOOLBAR_STYLE_ICONS_FLAT, 'toolbar_style_icons_flat'),
    (TOOLBAR_STYLE_TEXT_BELOW, 'toolbar_style_text_below'),
    (TOOLBAR_STYLE_TEXT_RIGHT, 'toolbar_style_text_right'),
]

SORT_FIELDS = [
    ('name',     'sort_by_name'),
    ('size',     'sort_by_size'),
    ('modified', 'sort_by_modified'),
    ('type',     'sort_by_type'),
]


class Toolbar(Gtk.ScrolledWindow):
    def __init__(self, on_back, on_up, on_refresh, on_new_tab, on_new_folder,
                 on_toggle_hidden, on_preferences=None, on_duplicates=None,
                 on_view_mode=None, on_sort=None, settings_manager=None,
                 on_split_view=None, on_find_files=None):
        super().__init__()
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.set_shadow_type(Gtk.ShadowType.NONE)
        self.set_propagate_natural_height(True)
        self.set_margin_bottom(4)
        
        self.set_min_content_height(42)
        self.set_max_content_height(-1)

        self.on_toggle_hidden  = on_toggle_hidden
        self.on_view_mode      = on_view_mode
        self.on_sort           = on_sort
        self.on_split_view     = on_split_view
        self.settings_manager  = settings_manager
        self._syncing_hidden   = False
        self._syncing_view     = False
        self._syncing_split    = False

        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.box.get_style_context().add_class('essorafm-toolbar')
        self.add(self.box)
        self.box.set_margin_bottom(12)
        
        self._button_size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

        nav_actions = [
            ('go-previous-symbolic',   tr('back'),             on_back),
            ('go-up-symbolic',         tr('up'),               on_up),
            ('view-refresh-symbolic',  tr('refresh'),          on_refresh),
            ('tab-new-symbolic',       tr('new_tab_short'),    on_new_tab),
            ('folder-new-symbolic',    tr('new_folder_short'), on_new_folder),
            ('system-search-symbolic', tr('find_files_short'), on_find_files),
            ('edit-find-symbolic',     tr('duplicates_short'), on_duplicates),
        ]
        self._nav_buttons = []
        for icon_name, label, cb in nav_actions:
            btn = self._make_nav_button(icon_name, label, cb)
            self.box.pack_start(btn, False, False, 0)
            self._nav_buttons.append(btn)
            self._button_size_group.add_widget(btn)

        self.hidden_button = Gtk.ToggleButton()
        self.hidden_button.get_style_context().add_class('essorafm-toolbutton')
        self.hidden_button.set_tooltip_text(tr('show_hidden_toggle'))
        self.hidden_button._icon_name  = 'view-reveal-symbolic'
        self.hidden_button._label_text = tr('hidden')
        self.hidden_button.connect('toggled', self._on_hidden_toggled)
        self.box.pack_start(self.hidden_button, False, False, 0)
        self._button_size_group.add_widget(self.hidden_button)

        self.box.pack_start(self._sep(), False, False, 0)

        self.view_icons_btn = Gtk.RadioButton()
        self.view_icons_btn.get_style_context().add_class('essorafm-toolbutton')
        self.view_icons_btn.set_tooltip_text(tr('icons_view_option'))
        self.view_icons_btn.set_mode(False)
        self.view_icons_btn._icon_name  = 'view-grid-symbolic'
        self.view_icons_btn._label_text = tr('icons_view_option')
        self.view_icons_btn._is_radio = True

        self.view_list_btn = Gtk.RadioButton.new_from_widget(self.view_icons_btn)
        self.view_list_btn.get_style_context().add_class('essorafm-toolbutton')
        self.view_list_btn.set_tooltip_text(tr('list_view_option'))
        self.view_list_btn.set_mode(False)
        self.view_list_btn._icon_name  = 'view-list-symbolic'
        self.view_list_btn._label_text = tr('list_view_option')
        self.view_list_btn._is_radio = True

        self.box.pack_start(self.view_icons_btn, False, False, 0)
        self.box.pack_start(self.view_list_btn,  False, False, 0)
        self._button_size_group.add_widget(self.view_icons_btn)
        self._button_size_group.add_widget(self.view_list_btn)
        
        self.view_icons_btn.connect('toggled', self._on_view_toggled)
        self.view_list_btn.connect('toggled', self._on_view_toggled)

        self.split_btn = Gtk.ToggleButton()
        self.split_btn.get_style_context().add_class('essorafm-toolbutton')
        self.split_btn.set_tooltip_text(tr('split_view'))
        self.split_btn._icon_name  = 'view-dual-symbolic'
        self.split_btn._label_text = tr('split_view')
        self.split_btn.connect('toggled', self._on_split_toggled)
        self.box.pack_start(self.split_btn, False, False, 0)
        self._button_size_group.add_widget(self.split_btn)

        self.box.pack_start(self._sep(), False, False, 0)

        self.sort_btn = Gtk.MenuButton()
        self.sort_btn.get_style_context().add_class('essorafm-toolbutton')
        self.sort_btn.set_tooltip_text(tr('sort_by'))
        self.sort_btn._icon_name  = 'view-sort-ascending-symbolic'
        self.sort_btn._label_text = tr('sort_by')
        self._sort_menu = self._build_sort_menu()
        self.sort_btn.set_popup(self._sort_menu)
        self.box.pack_start(self.sort_btn, False, False, 0)
        self._button_size_group.add_widget(self.sort_btn)

        self.box.pack_start(self._sep(), False, False, 0)

        self.style_btn = Gtk.MenuButton()
        self.style_btn.get_style_context().add_class('essorafm-toolbutton')
        self.style_btn.set_tooltip_text(tr('toolbar_style'))
        self.style_btn._icon_name  = 'preferences-other-symbolic'
        self.style_btn._label_text = tr('toolbar_style')
        self._style_menu = self._build_style_menu()
        self.style_btn.set_popup(self._style_menu)
        self.box.pack_start(self.style_btn, False, False, 0)
        self._button_size_group.add_widget(self.style_btn)

        style = TOOLBAR_STYLE_TEXT_RIGHT
        if settings_manager:
            style = settings_manager.get('toolbar_style', TOOLBAR_STYLE_TEXT_RIGHT)
        self._current_style = style
        self._apply_style(style)


    def _sep(self):
        s = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        s.set_margin_start(4)
        s.set_margin_end(4)
        return s

    def _make_nav_button(self, icon_name, label_text, cb):
        btn = Gtk.Button()
        btn.get_style_context().add_class('essorafm-toolbutton')
        btn.set_tooltip_text(label_text)
        btn._icon_name   = icon_name
        btn._label_text  = label_text
        btn._is_radio = False
        btn.connect('clicked', lambda b, c=cb: c() if c else None)
        return btn


    def _build_sort_menu(self):
        menu = Gtk.Menu()
        self._sort_items = {}
        first = None
        for field, key in SORT_FIELDS:
            item = Gtk.RadioMenuItem(label=tr(key))
            if first is None:
                first = item
            else:
                item.join_group(first)
            item.connect('activate', self._on_sort_activated, field)
            menu.append(item)
            self._sort_items[field] = item
        menu.append(Gtk.SeparatorMenuItem())
        self._sort_asc  = Gtk.RadioMenuItem(label=tr('sort_asc'))
        self._sort_desc = Gtk.RadioMenuItem.new_from_widget(self._sort_asc)
        self._sort_desc.set_label(tr('sort_desc'))
        self._sort_asc.connect('activate',  self._on_sort_dir_activated, 'asc')
        self._sort_desc.connect('activate', self._on_sort_dir_activated, 'desc')
        menu.append(self._sort_asc)
        menu.append(self._sort_desc)
        menu.show_all()
        return menu

    def _build_style_menu(self):
        menu = Gtk.Menu()
        first = None
        self._style_items = {}
        for style_id, key in TOOLBAR_STYLES:
            item = Gtk.RadioMenuItem(label=tr(key))
            if first is None:
                first = item
            else:
                item.join_group(first)
            item.connect('activate', self._on_style_activated, style_id)
            menu.append(item)
            self._style_items[style_id] = item
        menu.show_all()
        return menu


    def _get_current_icon_size(self):
        """Obtiene el tamaño actual de iconos desde settings_manager."""
        if self.settings_manager:
            return self.settings_manager.get_int('toolbar_icon_size', 20)
        return 20

    def _build_btn_content(self, icon_name, label_text, style, icon_size=None):
        """Construye el contenido del botón con el tamaño de icono especificado."""
        if icon_size is None:
            icon_size = self._get_current_icon_size()
        
        if style == TOOLBAR_STYLE_ICONS_ONLY:
            img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DND)
            img.set_pixel_size(icon_size)
            return img
        elif style == TOOLBAR_STYLE_ICONS_FLAT:
            img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DND)
            img.set_pixel_size(icon_size)
            return img
        elif style == TOOLBAR_STYLE_TEXT_BELOW:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            box.set_halign(Gtk.Align.CENTER)
            img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DND)
            img.set_pixel_size(icon_size)
            lbl = Gtk.Label(label=label_text)
            lbl.set_single_line_mode(True)
            lbl.get_style_context().add_class('essorafm-toolbar-label')
            box.pack_start(img, False, False, 0)
            box.pack_start(lbl, False, False, 0)
            return box
        else:  
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            box.set_border_width(1)
            img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DND)
            img.set_pixel_size(icon_size)
            lbl = Gtk.Label(label=label_text)
            lbl.set_single_line_mode(True)
            lbl.get_style_context().add_class('essorafm-toolbar-label')
            box.pack_start(img, False, False, 0)
            box.pack_start(lbl, False, False, 0)
            return box

    def _refresh_button_child(self, btn, style, icon_size=None):
        """Actualiza el contenido de un botón individual."""
        icon_name  = getattr(btn, '_icon_name',  None)
        label_text = getattr(btn, '_label_text', None)
        if icon_name is None:
            return
        child = btn.get_child()
        if child:
            btn.remove(child)
        btn.add(self._build_btn_content(icon_name, label_text, style, icon_size))
        btn.show_all()

    def _apply_style(self, style, icon_size=None):
        """Aplica el estilo y tamaño de iconos a todos los botones."""
        self._current_style = style
        
        if icon_size is None:
            icon_size = self._get_current_icon_size()
        

        if hasattr(self, '_style_items') and style in self._style_items:
            item = self._style_items[style]
            if not item.get_active():
                item.handler_block_by_func(self._on_style_activated)
                item.set_active(True)
                item.handler_unblock_by_func(self._on_style_activated)

        all_btns = (
            self._nav_buttons +
            [self.hidden_button, self.view_icons_btn, self.view_list_btn,
             self.split_btn, self.sort_btn, self.style_btn]
        )
        for btn in all_btns:
            self._refresh_button_child(btn, style, icon_size)
            ctx = btn.get_style_context()
            if style == TOOLBAR_STYLE_ICONS_FLAT:
                ctx.add_class('flat')
            else:
                ctx.remove_class('flat')


        self.queue_resize()
        
        if self.settings_manager:
            self.settings_manager.set('toolbar_style', style)
            self.settings_manager.save()


    def _on_split_toggled(self, button):
        if self._syncing_split:
            return
        if self.on_split_view:
            self.on_split_view(button.get_active())

    def _on_hidden_toggled(self, _button):
        if self._syncing_hidden:
            return
        self.on_toggle_hidden()

    def _on_view_toggled(self, button):
        if self._syncing_view:
            return
        if button.get_active() and self.on_view_mode:
            self.on_view_mode('icons' if button is self.view_icons_btn else 'list')

    def _on_sort_activated(self, item, field):
        if item.get_active() and self.on_sort:
            direction = 'asc' if self._sort_asc.get_active() else 'desc'
            self.on_sort(field, direction)

    def _on_sort_dir_activated(self, item, direction):
        if item.get_active() and self.on_sort:
            field = next((f for f, i in self._sort_items.items() if i.get_active()), 'name')
            self.on_sort(field, direction)

    def _on_style_activated(self, item, style_id):
        if item.get_active():
            self._apply_style(style_id)


    def set_split_active(self, active):
        if self.split_btn.get_active() == active:
            return
        self._syncing_split = True
        try:
            self.split_btn.set_active(active)
        finally:
            self._syncing_split = False

    def set_hidden_active(self, active):
        if self.hidden_button.get_active() == active:
            return
        self._syncing_hidden = True
        try:
            self.hidden_button.set_active(active)
        finally:
            self._syncing_hidden = False

    def set_view_mode(self, mode):
        self._syncing_view = True
        try:
            self.view_icons_btn.handler_block_by_func(self._on_view_toggled)
            self.view_list_btn.handler_block_by_func(self._on_view_toggled)
            if mode == 'icons':
                self.view_icons_btn.set_active(True)
            else:
                self.view_list_btn.set_active(True)
        finally:
            self.view_icons_btn.handler_unblock_by_func(self._on_view_toggled)
            self.view_list_btn.handler_unblock_by_func(self._on_view_toggled)
            self._syncing_view = False

    def set_sort(self, field, direction):
        if field in self._sort_items:
            self._sort_items[field].set_active(True)
        if direction == 'desc':
            self._sort_desc.set_active(True)
        else:
            self._sort_asc.set_active(True)
            
    def refresh_all_buttons(self):
        """Reconstruye todos los botones con el tamaño actual de iconos."""
        icon_size = self._get_current_icon_size()
        self._apply_style(self._current_style, icon_size)
