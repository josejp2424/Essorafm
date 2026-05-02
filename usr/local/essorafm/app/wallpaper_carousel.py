# EssoraFM - Wallpaper Carousel
# Author: josejp2424 and Nilsonmorales - GPL-3.0
import os
import threading

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

from core.i18n import tr

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif', '.svg'}

THUMB_W = 320
THUMB_H = 200

VISIBLE = 5


def _is_image(path):
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS


def _collect_images(directory):
    try:
        entries = sorted(os.listdir(directory))
    except OSError:
        return []
    return [os.path.join(directory, e) for e in entries if _is_image(e)]


class WallpaperCarouselDialog(Gtk.Window):
    """
    Ventana sin decoracion, centrada en pantalla.
    Muestra solo las miniaturas en carrusel + barra superior + botones.
    """

    def __init__(self, parent, wallpaper_directory, current_wallpaper=None):
        super().__init__()

        self._parent        = parent
        self._directory     = wallpaper_directory
        self._current       = current_wallpaper or ''
        self._images        = []
        self._index         = 0
        self._pixbuf_cache  = {}
        self._loading       = set()
        self._selected_path = None
        self._result        = Gtk.ResponseType.CANCEL

        self.set_decorated(False)
        self.set_modal(True)
        self.set_transient_for(parent)
        self.set_skip_taskbar_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)

        card_sizes = [THUMB_W, int(THUMB_W * 0.70), int(THUMB_W * 0.52)]
        total_width = (card_sizes[0] + card_sizes[1]*2 + card_sizes[2]*2) + (VISIBLE - 1) * 10 + 100
        
        nav_btn_width = 50  
        margin = 40  
        
        win_w = total_width + nav_btn_width * 2 + margin
        win_h = THUMB_H + 150
        
        screen = Gdk.Screen.get_default()
        sw = screen.get_width()
        sh = screen.get_height()
        

        win_w = min(win_w, sw - 40)
        win_h = min(win_h, sh - 40)
        
        self.set_default_size(win_w, win_h)
        self.set_resizable(False)


        x_pos = (sw - win_w) // 2
        y_pos = (sh - win_h) // 2
        self.move(x_pos, y_pos)

        self._build_css()
        self._build_ui()
        self._load_images()
        self.connect('key-press-event', self._on_key)
        self.connect('delete-event', lambda *_: self._close(Gtk.ResponseType.CANCEL))



    def _build_css(self):
        css = b"""
        .wp-root {
            background-color: #1a1a1a;
        }
        .wp-topbar {
            background-color: #111111;
        }
        .wp-card-inner {
            border-radius: 8px;
            background-color: #1a1a1a;
            border: 2px solid transparent;
        }
        .wp-card-selected .wp-card-inner {
            border: 3px solid #7f961a;
        }
        .wp-card-side {
            opacity: 0.5;
        }
        .wp-nav-btn {
            background-color: rgba(30,30,30,0.9);
            border-radius: 50%;
            min-width: 40px;
            min-height: 40px;
            border: 1px solid #3a3a3a;
            color: #ffffff;
            padding: 0;
        }
        .wp-nav-btn:hover {
            background-color: rgba(127,150,26,0.8);
            border-color: #7f961a;
        }
        .wp-dir-btn {
            color: #aaaaaa;
            font-size: 18px;
            background: transparent;
            border: 1px solid #3a3a3a;
            border-radius: 5px;
            padding: 2px 8px;
        }
        .wp-dir-btn:hover {
            color: #b8d400;
            border-color: #7f961a;
        }
        .wp-counter {
            color: #666666;
            font-size: 18px;
        }
        .wp-apply-btn {
            background-color: #7f961a;
            color: #ffffff;
            border-radius: 7px;
            padding: 5px 22px;
            font-weight: bold;
            border: none;
        }
        .wp-apply-btn:hover {
            background-color: #96b020;
        }
        .wp-cancel-btn {
            background-color: #333333;
            color: #cccccc;
            border-radius: 7px;
            padding: 5px 18px;
            border: 1px solid #444;
        }
        .wp-cancel-btn:hover {
            background-color: #444444;
            color: #ffffff;
        }
        .wp-filename {
            color: #b8d400;
            font-size: 18px;
            font-weight: bold;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 10
        )


    def _build_ui(self):
            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            root.get_style_context().add_class('wp-root')
            self.add(root)
    
            topbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            topbar.get_style_context().add_class('wp-topbar')
            topbar.set_margin_top(8); topbar.set_margin_bottom(8)
            topbar.set_margin_start(14); topbar.set_margin_end(14)
    
            self._counter_label = Gtk.Label()
            self._counter_label.get_style_context().add_class('wp-counter')
            topbar.pack_start(self._counter_label, False, False, 0)
    
            spacer = Gtk.Box()
            topbar.pack_start(spacer, True, True, 0)
    
            self._dir_btn = Gtk.Button()
            self._dir_btn.get_style_context().add_class('wp-dir-btn')
            self._dir_btn.connect('clicked', self._on_change_dir)
            
            self._dir_btn_label = Gtk.Label()
            self._dir_btn_label.set_ellipsize(3)
            self._dir_btn_label.set_max_width_chars(30)
            self._dir_btn.add(self._dir_btn_label)
            
            topbar.pack_end(self._dir_btn, False, False, 0)
            root.pack_start(topbar, False, False, 0)
    
            main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            main_box.set_vexpand(True)
            main_box.set_valign(Gtk.Align.CENTER)
            main_box.set_halign(Gtk.Align.CENTER)
    
            self._btn_prev = self._make_nav_btn('go-previous-symbolic')
            self._btn_prev.connect('clicked', lambda *_: self._move(-1))
    
            self._cards_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            self._cards_box.set_valign(Gtk.Align.CENTER)
    
            self._btn_next = self._make_nav_btn('go-next-symbolic')
            self._btn_next.connect('clicked', lambda *_: self._move(1))
    
            main_box.pack_start(self._btn_prev, False, False, 0)
            main_box.pack_start(self._cards_box, False, False, 0)
            main_box.pack_start(self._btn_next, False, False, 0)
            root.pack_start(main_box, True, True, 0)
    
            bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            bottom.set_halign(Gtk.Align.CENTER)
            bottom.set_margin_top(10); bottom.set_margin_bottom(12)
    
            self._cancel_btn = Gtk.Button(label=tr('cancel'))
            self._cancel_btn.get_style_context().add_class('wp-cancel-btn')
            self._cancel_btn.connect('clicked', lambda *_: self._close(Gtk.ResponseType.CANCEL))
            bottom.pack_start(self._cancel_btn, False, False, 0)
    
            self._apply_btn = Gtk.Button(label=tr('wallpaper_apply'))
            self._apply_btn.get_style_context().add_class('wp-apply-btn')
            self._apply_btn.connect('clicked', self._on_apply)
            bottom.pack_start(self._apply_btn, False, False, 0)
            root.pack_start(bottom, False, False, 0)
    
            self._card_widgets = []
            for _ in range(VISIBLE):
                card = self._make_card_widget()
                self._cards_box.pack_start(card['outer'], False, False, 0)
                self._card_widgets.append(card)
    
            self.show_all()

    def _make_nav_btn(self, icon_name):
        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.add(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR))
        btn.get_style_context().add_class('wp-nav-btn')
        btn.set_valign(Gtk.Align.CENTER)
        return btn

    def _make_card_widget(self):
            outer = Gtk.EventBox()
            outer.get_style_context().add_class('wp-card-outer')
    
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            inner.get_style_context().add_class('wp-card-inner')
            inner.set_valign(Gtk.Align.CENTER)
            outer.add(inner)
    
            img = Gtk.Image()
            img.set_margin_top(5)
            img.set_margin_bottom(5)
            img.set_margin_start(5)
            img.set_margin_end(5)
            inner.pack_start(img, False, False, 0)
    
            lbl = Gtk.Label(label='')
            lbl.get_style_context().add_class('wp-filename')
            lbl.set_ellipsize(3)
            lbl.set_max_width_chars(20)
            lbl.set_margin_bottom(5)
            inner.pack_start(lbl, False, False, 0)
    
            return {'outer': outer, 'inner': inner, 'image': img, 'label': lbl, '_path': None}


    def _load_images(self):
        self._images = _collect_images(self._directory)
        if self._current and self._current in self._images:
            self._index = self._images.index(self._current)
        else:
            self._index = 0
        self._selected_path = self._images[self._index] if self._images else None
        self._refresh_ui()

    def _refresh_ui(self):
            n = len(self._images)
    
            short = self._directory
            home = os.path.expanduser('~')
            if short.startswith(home):
                short = '~' + short[len(home):]
            self._dir_btn_label.set_text('📁  ' + short)
    
            self._counter_label.set_text(
                str(self._index + 1) + ' / ' + str(n) if n else '0 / 0')
    
            self._btn_prev.set_sensitive(n > 1)
            self._btn_next.set_sensitive(n > 1)
            self._apply_btn.set_sensitive(n > 0)
    
            half  = VISIBLE // 2
            slots = [self._index + (i - half) for i in range(VISIBLE)]
    
            for slot_i, abs_i in enumerate(slots):
                card      = self._card_widgets[slot_i]
                is_center = (abs_i == self._index)
                is_valid  = 0 <= abs_i < n
    
                outer_ctx = card['outer'].get_style_context()
                outer_ctx.remove_class('wp-card-selected')
                outer_ctx.remove_class('wp-card-side')
    
                dist  = abs(slot_i - half)
                scale = 1.0 if dist == 0 else (0.70 if dist == 1 else 0.52)
                tw = int(THUMB_W * scale)
                th = int(THUMB_H * scale)
    
                if not is_valid:
                    card['image'].set_from_pixbuf(self._blank_pixbuf(tw, th))
                    card['label'].set_text("")
                    card['outer'].set_sensitive(False)
                    continue
    
                path = self._images[abs_i]
                card['_path'] = path
                card['outer'].set_sensitive(True)
                
                card['label'].set_text(os.path.basename(path))
                card['label'].set_opacity(1.0 if is_center else 0.6)
    
                if is_center:
                    outer_ctx.add_class('wp-card-selected')
                else:
                    outer_ctx.add_class('wp-card-side')
    
                try: card['outer'].disconnect_by_func(self._on_card_clicked)
                except: pass
                card['outer'].connect('button-press-event', lambda _w, _e, ai=abs_i: self._on_card_clicked(ai))
    
                pix = self._get_thumb(path, tw, th)
                if pix:
                    card['image'].set_from_pixbuf(pix)
                else:
                    card['image'].set_from_pixbuf(self._blank_pixbuf(tw, th))
                    if self._cache_key(path, tw, th) not in self._pixbuf_cache:
                        self._request_thumb(path, tw, th)
    
            self._cards_box.show_all()

    def _blank_pixbuf(self, w, h):
        pix = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8,
                                    max(1, w), max(1, h))
        pix.fill(0x1a1a1aff)
        return pix


    def _cache_key(self, path, w, h):
        return (path, w, h)

    def _get_thumb(self, path, w, h):
        return self._pixbuf_cache.get(self._cache_key(path, w, h))

    def _request_thumb(self, path, w, h):
        key = self._cache_key(path, w, h)
        if key in self._loading:
            return
        self._loading.add(key)
        threading.Thread(target=self._load_thumb_thread,
                         args=(path, w, h, key), daemon=True).start()

    def _load_thumb_thread(self, path, w, h, key):
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, w, h, True)
        except Exception:
            pix = None
        GLib.idle_add(self._thumb_ready, key, pix)

    def _thumb_ready(self, key, pix):
        self._loading.discard(key)
        self._pixbuf_cache[key] = pix
        self._refresh_ui()
        return False


    def _move(self, delta):
        if not self._images:
            return
        self._index = (self._index + delta) % len(self._images)
        self._selected_path = self._images[self._index]
        self._refresh_ui()

    def _on_card_clicked(self, abs_i):
        if abs_i == self._index:
            self._on_apply()
        else:
            self._index = abs_i
            self._selected_path = self._images[self._index]
            self._refresh_ui()

    def _on_key(self, _w, event):
        k = event.keyval
        if k in (Gdk.KEY_Left, Gdk.KEY_KP_Left):
            self._move(-1); return True
        if k in (Gdk.KEY_Right, Gdk.KEY_KP_Right):
            self._move(1);  return True
        if k in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self._on_apply(); return True
        if k == Gdk.KEY_Escape:
            self._close(Gtk.ResponseType.CANCEL); return True
        return False

    def _on_change_dir(self, *_):
        chooser = Gtk.FileChooserDialog(
            title=tr('select_folder'),
            transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        chooser.add_buttons(tr('cancel'), Gtk.ResponseType.CANCEL,
                            tr('open'),   Gtk.ResponseType.OK)
        chooser.set_current_folder(self._directory)
        if chooser.run() == Gtk.ResponseType.OK:
            self._directory = chooser.get_filename()
            self._index = 0
            self._pixbuf_cache.clear()
            self._load_images()
        chooser.destroy()

    def _on_apply(self, *_):
        if self._selected_path:
            self._close(Gtk.ResponseType.OK)

    def _close(self, result):
        self._result = result
        Gtk.main_quit()


    def run(self):
        self.show()
        Gtk.main()
        return self._result

    def destroy(self):
        super().destroy()

    def get_selected_path(self):
        return self._selected_path

    def get_directory(self):
        return self._directory
