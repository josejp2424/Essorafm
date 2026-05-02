#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitGUI - Safe Git configuration + basic repository actions (GTK3)

Based on bash script "git-seguro.sh"
Original author (bash): nilsonmorales (GPL-3.0)
Python/GTK3 GUI + modifications: josejp2424 (GPL-3.0)

License: GPL-3.0-or-later
"""

import os
import sys
import json
import shutil
import subprocess
import threading
import locale

import re
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Gio, GLib
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import GdkPixbuf


ICON_PATH = "/usr/local/essorafm/ui/icons/github.svg"
SSH_CMD = 'ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new'



HEADER_ICON_SIZE = 24  
WINDOW_ICON_SIZE = 48  

def load_svg_pixbuf(path: str, size: int):
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
    except Exception:
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_size(path, size, size)
        except Exception:
            return None


def which(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _env_lang():
    for k in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        v = os.environ.get(k, "").strip()
        if v:
            return v
    return ""


def detect_lang(supported):
    raw = _env_lang() or (locale.getdefaultlocale()[0] if locale.getdefaultlocale() else "") or ""
    raw = raw.split(":")[0]
    raw = raw.replace("-", "_")
    base = raw.split(".")[0]
    code = base.split("_")[0].lower() if base else "en"
    if code not in supported:
        return "en"
    return code


class I18N:
    def __init__(self, translations_path: str):
        try:
            with open(translations_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception:
            self.data = {"en": {}}

        self.supported = set(self.data.keys()) if isinstance(self.data, dict) else {"en"}
        self.lang = detect_lang(self.supported)
        self.en = self.data.get("en", {}) if isinstance(self.data, dict) else {}

        if self.lang == "ar":
            Gtk.Widget.set_default_direction(Gtk.TextDirection.RTL)

    def t(self, key: str, **fmt):
        d = self.data.get(self.lang, {})
        s = d.get(key, self.en.get(key, key))
        if fmt:
            try:
                return s.format(**fmt)
            except Exception:
                return s
        return s


class GitGUIWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application, i18n: I18N):
        super().__init__(application=app)
        self._ = i18n.t
        self.set_title(self._("app_title"))

        sw, sh = 1024, 768
        try:
            display = Gdk.Display.get_default()
            if display:
                mon = display.get_primary_monitor() or display.get_monitor(0)
                if mon:
                    geo = mon.get_geometry()
                    sw, sh = int(geo.width), int(geo.height)
                else:
                    screen = Gdk.Screen.get_default()
                    if screen:
                        sw, sh = int(screen.get_width()), int(screen.get_height())
            else:
                screen = Gdk.Screen.get_default()
                if screen:
                    sw, sh = int(screen.get_width()), int(screen.get_height())
        except Exception:
            pass

        w = min(920, max(720, sw - 120))
        h = min(600, max(520, sh - 120))
        self.set_default_size(w, h)

        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(True)

        # Borderless
        self.set_decorated(False)

        if os.path.exists(ICON_PATH):
            try:
                pb = load_svg_pixbuf(ICON_PATH, WINDOW_ICON_SIZE)
                if pb:
                    self.set_icon(pb)
            except Exception:
                pass

        self._load_css()

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(root)

        header = self._build_headerbar(app)
        root.pack_start(header, False, False, 0)

        switcher_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        switcher_bar.get_style_context().add_class("switcher-bar")
        root.pack_start(switcher_bar, False, False, 0)

        self.stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT,
            transition_duration=180
        )
        self.stack.set_homogeneous(False)

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(self.stack)
        switcher.get_style_context().add_class("stack-switcher")
        switcher_bar.pack_start(switcher, True, True, 12)
        sc_content = Gtk.ScrolledWindow()
        sc_content.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root.pack_start(sc_content, True, True, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_border_width(12)
        sc_content.add(content)

        content.pack_start(self.stack, False, False, 0)

        # Pages
        self.page_identity = self._build_page_identity()
        self.page_ssh = self._build_page_ssh()
        self.page_clone = self._build_page_clone()
        self.page_repo = self._build_page_repo()

        self.stack.add_titled(self.page_identity, "identity", self._("tab_identity"))
        self.stack.add_titled(self.page_ssh, "ssh", self._("tab_ssh"))
        self.stack.add_titled(self.page_clone, "clone", self._("tab_clone"))
        self.stack.add_titled(self.page_repo, "repo", self._("tab_repo"))

        # Log
        self.log_view = Gtk.TextView(editable=False, cursor_visible=False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_buf = self.log_view.get_buffer()

        log_frame = Gtk.Frame()
        log_frame.set_label(self._("log_title"))
        log_frame.get_style_context().add_class("section-frame")

        sc = Gtk.ScrolledWindow()
        sc.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sc.set_min_content_height(140)
        sc.add(self.log_view)
        log_frame.add(sc)
        content.pack_start(log_frame, False, True, 0)

        if not which("git"):
            self._log(self._("git_missing"))
        else:
            self._log(self._("ready"))

        self.repo_path = None
        self.show_all()

    def _load_css(self):
        css = b"""
        .titlebar, headerbar { padding: 4px 8px; }
        .header-root { background: rgba(40, 44, 52, 0.92); }
        .switcher-bar { background: rgba(40, 44, 52, 0.82); padding: 4px 0px; }
        .stack-switcher button { border-radius: 10px; padding: 8px 14px; }
        .section-frame { border-radius: 12px; }
        .big-action button { padding: 10px 14px; border-radius: 12px; }
        .window-controls button { padding: 6px 10px; border-radius: 10px; }
        .mono { font-family: monospace; }
        .dim-label { opacity: 0.75; font-size: 90%; }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    def _build_headerbar(self, app: Gtk.Application) -> Gtk.Widget:
        header_box = Gtk.EventBox()
        header_box.get_style_context().add_class("header-root")
        header_box.set_visible_window(True)
        header_box.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)

        hb = Gtk.HeaderBar()
        hb.set_show_close_button(False)
        hb.get_style_context().add_class("titlebar")

        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        if os.path.exists(ICON_PATH):
            pb = load_svg_pixbuf(ICON_PATH, HEADER_ICON_SIZE)
            if pb:
                img = Gtk.Image.new_from_pixbuf(pb)
                title_box.pack_start(img, False, False, 0)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        lbl_title = Gtk.Label()
        lbl_title.set_xalign(0)
        lbl_title.set_markup(f"<b>{self._('app_title')}</b>")

        lbl_sub = Gtk.Label(label=self._("app_subtitle"))
        lbl_sub.set_xalign(0)
        lbl_sub.get_style_context().add_class("dim-label")

        labels.pack_start(lbl_title, False, False, 0)
        labels.pack_start(lbl_sub, False, False, 0)

        title_box.pack_start(labels, False, False, 0)
        hb.set_custom_title(title_box)

        # Menu
        menu_btn = Gtk.MenuButton()
        menu_btn.set_image(Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON))
        menu_btn.set_relief(Gtk.ReliefStyle.NONE)

        model = Gio.Menu()
        model.append(self._("menu_about"), "app.about")
        model.append(self._("menu_quit"), "app.quit")

        try:
            menu_btn.set_menu_model(model)
        except Exception:
            pop = Gtk.Popover.new(menu_btn)
            vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            b1 = Gtk.ModelButton(label=self._("menu_about"))
            b1.connect("clicked", lambda *_: app.activate_action("about", None) or pop.popdown())
            b2 = Gtk.ModelButton(label=self._("menu_quit"))
            b2.connect("clicked", lambda *_: app.activate_action("quit", None) or pop.popdown())
            vb.pack_start(b1, False, False, 0)
            vb.pack_start(b2, False, False, 0)
            vb.show_all()
            pop.add(vb)
            menu_btn.set_popover(pop)

        # Window controls — orden visual: ⋮  −  ✕
        btn_min = Gtk.Button()
        btn_min.set_relief(Gtk.ReliefStyle.NONE)
        btn_min.set_image(Gtk.Image.new_from_icon_name("window-minimize-symbolic", Gtk.IconSize.BUTTON))
        btn_min.connect("clicked", lambda *_: self.iconify())

        btn_close = Gtk.Button()
        btn_close.set_relief(Gtk.ReliefStyle.NONE)
        btn_close.set_image(Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.BUTTON))
        btn_close.connect("clicked", lambda *_: self.close())

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        controls.get_style_context().add_class("window-controls")
        controls.pack_start(menu_btn, False, False, 0)
        controls.pack_start(btn_min, False, False, 0)
        controls.pack_start(btn_close, False, False, 0)

        hb.pack_end(controls)

        def on_drag(_w, event):
            if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
                self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
                return True
            return False

        header_box.connect("button-press-event", on_drag)
        header_box.add(hb)
        return header_box

    def _card(self, title: str, child: Gtk.Widget) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.set_label(title)
        frame.get_style_context().add_class("section-frame")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(12)
        box.pack_start(child, True, True, 0)
        frame.add(box)
        return frame

    def _log(self, text: str):
        end = self.log_buf.get_end_iter()
        self.log_buf.insert(end, text)
        GLib.idle_add(self._scroll_log)

    def _scroll_log(self):
        parent = self.log_view.get_parent()
        if hasattr(parent, "get_vadjustment"):
            vadj = parent.get_vadjustment()
            vadj.set_value(vadj.get_upper() - vadj.get_page_size())
        return False

    def _run(self, cmd, cwd=None, env=None, no_stdin=False):
        try:
            p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             env=env, stdin=(subprocess.DEVNULL if no_stdin else None))
            return p.returncode, p.stdout
        except Exception as e:
            return 999, str(e)

    def _https_env_for_git(self):
        """Build env to provide HTTPS credentials via GIT_ASKPASS (session-only)."""
        user = (self.auth_user.get_text().strip() if hasattr(self, "auth_user") else "")
        token = (self.auth_token.get_text().strip() if hasattr(self, "auth_token") else "")
        if not user or not token:
            return None

        path = "/tmp/gitgui-askpass.sh"
        script = '''#!/bin/sh
    case "$1" in
    *sername*|*Username*) echo "$GITGUI_USER" ;;
    *) echo "$GITGUI_TOKEN" ;;
    esac
    '''
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(script)
            os.chmod(path, 0o700)
        except Exception:
            return None

        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_ASKPASS"] = path
        env["GITGUI_USER"] = user
        env["GITGUI_TOKEN"] = token
        return env

    def _run_git(self, args, repo=None, env=None, no_stdin=False):
        if not which("git"):
            return 127, "git missing"
        if repo:
            cmd = ["git", "-C", repo] + args
        else:
            cmd = ["git"] + args
        return self._run(cmd, env=env, no_stdin=no_stdin)

    # ---------------- Pages: Identity / SSH / Clone ----------------

    def _build_page_identity(self) -> Gtk.Widget:
        grid = Gtk.Grid(column_spacing=10, row_spacing=10)

        self.entry_name = Gtk.Entry()
        self.entry_email = Gtk.Entry()
        self.entry_editor = Gtk.Entry()
        self.entry_editor.set_text("geany")

        if which("git"):
            self.entry_name.set_text(self._git_get("user.name") or "")
            self.entry_email.set_text(self._git_get("user.email") or "")
            self.entry_editor.set_text(self._git_get("core.editor") or "geany")

        grid.attach(Gtk.Label(label=self._("lbl_name")), 0, 0, 1, 1)
        grid.attach(self.entry_name,                     1, 0, 1, 1)
        grid.attach(Gtk.Label(label=self._("lbl_email")),0, 1, 1, 1)
        grid.attach(self.entry_email,                    1, 1, 1, 1)
        grid.attach(Gtk.Label(label=self._("lbl_editor")),0, 2, 1, 1)
        grid.attach(self.entry_editor,                   1, 2, 1, 1)

        btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btns.get_style_context().add_class("big-action")

        btn_defaults = Gtk.Button(label=self._("btn_recommended"))
        btn_defaults.connect("clicked", self.on_apply_recommended)

        btn_apply = Gtk.Button(label=self._("btn_apply"))
        btn_apply.connect("clicked", self.on_apply_identity)

        btns.pack_start(btn_defaults, True, True, 0)
        btns.pack_start(btn_apply, True, True, 0)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.pack_start(self._card(self._("section_identity"), grid), False, False, 0)
        box.pack_start(btns, False, False, 0)
        return box

    def _build_page_ssh(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        info = Gtk.Label(label=self._("ssh_help"))
        info.set_xalign(0)
        box.pack_start(info, False, False, 0)

        self.pubkey_view = Gtk.TextView(editable=False, cursor_visible=False)
        self.pubkey_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.pubkey_buf = self.pubkey_view.get_buffer()

        sc = Gtk.ScrolledWindow()
        sc.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sc.set_min_content_height(150)
        sc.add(self.pubkey_view)

        btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btns.get_style_context().add_class("big-action")

        btn_gen = Gtk.Button(label=self._("btn_gen_key"))
        btn_gen.connect("clicked", self.on_generate_or_show_ssh)

        btn_copy = Gtk.Button(label=self._("btn_copy"))
        btn_copy.connect("clicked", self.on_copy_pubkey)

        btns.pack_start(btn_gen, True, True, 0)
        btns.pack_start(btn_copy, True, True, 0)

        box.pack_start(self._card(self._("section_ssh"), sc), False, True, 0)
        box.pack_start(btns, False, False, 0)
        return box

    def _build_page_clone(self) -> Gtk.Widget:
        grid = Gtk.Grid(column_spacing=10, row_spacing=10)
    
        self.entry_repo = Gtk.Entry()
        self.entry_repo.set_placeholder_text(self._("ph_repo"))
    
        self.folder_btn = Gtk.FileChooserButton(title=self._("lbl_dest"),
                                                action=Gtk.FileChooserAction.SELECT_FOLDER)
        self.folder_btn.set_current_folder(os.path.expanduser("~"))
    
        grid.attach(Gtk.Label(label=self._("lbl_repo_url")), 0, 0, 1, 1)
        grid.attach(self.entry_repo,                         1, 0, 1, 1)
        grid.attach(Gtk.Label(label=self._("lbl_dest")),     0, 1, 1, 1)
        grid.attach(self.folder_btn,                         1, 1, 1, 1)
    
        btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btns.get_style_context().add_class("big-action")
    
        btn_clone = Gtk.Button(label=self._("btn_clone"))
        btn_clone.connect("clicked", self.on_clone)
    
        btn_clear = Gtk.Button(label=self._("btn_clear") if self._("btn_clear") != "btn_clear" else "Reset")
        btn_clear.connect("clicked", self._reset_clone_form)
    
        btns.pack_start(btn_clone, True, True, 0)
        btns.pack_start(btn_clear, True, True, 0)
    
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.pack_start(self._card(self._("section_clone"), grid), False, False, 0)
        box.pack_start(btns, False, False, 0)
        return box

    # ---------------- Page: Repository ----------------

    def _build_page_repo(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        top = Gtk.Grid(column_spacing=10, row_spacing=10)
        self.repo_btn = Gtk.FileChooserButton(
            title=self._("lbl_repo_folder"),
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        self.repo_btn.set_current_folder(os.path.expanduser("~"))
        self.repo_btn.connect("file-set", self.on_repo_selected)

        self.branch_label = Gtk.Label(label="")
        self.branch_label.set_xalign(0)

        top.attach(Gtk.Label(label=self._("lbl_repo_folder")), 0, 0, 1, 1)
        top.attach(self.repo_btn, 1, 0, 1, 1)
        top.attach(self.branch_label, 1, 1, 1, 1)

        outer.pack_start(self._card(self._("section_repo"), top), False, False, 0)


        # Authentication 
        auth_grid = Gtk.Grid(column_spacing=10, row_spacing=10)

        self.auth_mode = Gtk.ComboBoxText()
        self.auth_mode.append_text(self._("auth_mode_ssh"))
        self.auth_mode.append_text(self._("auth_mode_https"))
        self.auth_mode.set_active(0)

        self.auth_user = Gtk.Entry()
        self.auth_user.set_placeholder_text(self._("ph_username"))

        self.auth_token = Gtk.Entry()
        self.auth_token.set_visibility(False)
        self.auth_token.set_placeholder_text(self._("ph_token"))

        auth_help = Gtk.Label(label=self._("auth_help"))
        auth_help.set_xalign(0)
        auth_help.set_line_wrap(True)

        auth_grid.attach(Gtk.Label(label=self._("auth_mode")), 0, 0, 1, 1)
        auth_grid.attach(self.auth_mode, 1, 0, 1, 1)
        auth_grid.attach(Gtk.Label(label=self._("lbl_username")), 0, 1, 1, 1)
        auth_grid.attach(self.auth_user, 1, 1, 1, 1)
        auth_grid.attach(Gtk.Label(label=self._("lbl_token")), 0, 2, 1, 1)
        auth_grid.attach(self.auth_token, 1, 2, 1, 1)
        auth_grid.attach(auth_help, 1, 3, 1, 1)
        ssh_help_lbl = Gtk.Label(label=self._("ssh_help"))
        ssh_help_lbl.set_xalign(0)
        ssh_help_lbl.set_line_wrap(True)
        auth_grid.attach(ssh_help_lbl, 1, 4, 1, 1)

        btn_test = Gtk.Button(label=self._("btn_test_auth"))
        btn_test.connect("clicked", self.on_test_auth)

        row_auth = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row_auth.pack_start(btn_test, False, False, 0)
        btn_switch = Gtk.Button(label=self._("btn_switch_ssh"))
        btn_switch.connect("clicked", self.on_switch_ssh)

        btn_test_ssh = Gtk.Button(label=self._("btn_test_ssh"))
        btn_test_ssh.connect("clicked", self.on_test_ssh)

        row_auth.pack_start(btn_switch, False, False, 0)
        row_auth.pack_start(btn_test_ssh, False, False, 0)

        auth_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        auth_box.pack_start(auth_grid, False, False, 0)
        auth_box.pack_start(row_auth, False, False, 0)

        outer.pack_start(self._card(self._("section_auth"), auth_box), False, False, 0)

        def _toggle_auth_fields(*_a):
            https = self.auth_mode.get_active() == 1
            self.auth_user.set_sensitive(https)
            self.auth_token.set_sensitive(https)
            try:
                ssh_help_lbl.set_visible(not https)
            except Exception:
                pass
            return False
        self.auth_mode.connect("changed", _toggle_auth_fields)
        _toggle_auth_fields()

        # Status list
        self.status_store = Gtk.ListStore(str, str) 

        self.status_tree = Gtk.TreeView(model=self.status_store)
        renderer = Gtk.CellRendererText()
        col1 = Gtk.TreeViewColumn("St", renderer, text=0)
        col2 = Gtk.TreeViewColumn("File", renderer, text=1)
        self.status_tree.append_column(col1)
        self.status_tree.append_column(col2)

        sel = self.status_tree.get_selection()
        sel.set_mode(Gtk.SelectionMode.MULTIPLE)

        sc = Gtk.ScrolledWindow()
        sc.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sc.set_min_content_height(220)
        sc.add(self.status_tree)

        outer.pack_start(self._card(self._("status_header"), sc), True, True, 0)

        # Actions row 1
        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row1.get_style_context().add_class("big-action")

        btn_refresh = Gtk.Button(label=self._("btn_refresh"))
        btn_refresh.connect("clicked", lambda *_: self.refresh_status())

        btn_stage = Gtk.Button(label=self._("btn_stage"))
        btn_stage.connect("clicked", self.on_stage)

        btn_stage_all = Gtk.Button(label=self._("btn_stage_all"))
        btn_stage_all.connect("clicked", self.on_stage_all)

        btn_unstage = Gtk.Button(label=self._("btn_unstage"))
        btn_unstage.connect("clicked", self.on_unstage)

        btn_discard = Gtk.Button(label=self._("btn_discard"))
        btn_discard.connect("clicked", self.on_discard)

        btn_diff = Gtk.Button(label=self._("btn_diff"))
        btn_diff.connect("clicked", self.on_diff)

        row1.pack_start(btn_refresh, True, True, 0)
        row1.pack_start(btn_stage, True, True, 0)
        row1.pack_start(btn_stage_all, True, True, 0)
        row1.pack_start(btn_unstage, True, True, 0)
        row1.pack_start(btn_discard, True, True, 0)
        row1.pack_start(btn_diff, True, True, 0)

        outer.pack_start(row1, False, False, 0)

        # Commit 
        grid2 = Gtk.Grid(column_spacing=10, row_spacing=10)
        self.commit_entry = Gtk.Entry()
        self.commit_entry.set_placeholder_text(self._("ph_commit_msg"))

        grid2.attach(Gtk.Label(label=self._("lbl_commit_msg")), 0, 0, 1, 1)
        grid2.attach(self.commit_entry, 1, 0, 1, 1)

        btn_commit = Gtk.Button(label=self._("btn_commit"))
        btn_commit.connect("clicked", self.on_commit)

        btn_pull = Gtk.Button(label=self._("btn_pull"))
        btn_pull.connect("clicked", self.on_pull)

        btn_push = Gtk.Button(label=self._("btn_push"))
        btn_push.connect("clicked", self.on_push)

        btn_log = Gtk.Button(label=self._("btn_show_log"))
        btn_log.connect("clicked", self.on_show_log)

        btn_remote = Gtk.Button(label=self._("btn_show_remote"))
        btn_remote.connect("clicked", self.on_show_remote)

        row2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row2.get_style_context().add_class("big-action")
        row2.pack_start(btn_commit, True, True, 0)
        row2.pack_start(btn_pull, True, True, 0)
        row2.pack_start(btn_push, True, True, 0)
        row2.pack_start(btn_log, True, True, 0)
        row2.pack_start(btn_remote, True, True, 0)

        outer.pack_start(self._card(self._("lbl_commit_msg"), grid2), False, False, 0)
        outer.pack_start(row2, False, False, 0)

        return outer

    def _selected_files(self):
        model, paths = self.status_tree.get_selection().get_selected_rows()
        files = []
        for p in paths:
            it = model.get_iter(p)
            code = model.get_value(it, 0)
            path = model.get_value(it, 1)
            files.append((code, path))
        return files

    def on_repo_selected(self, *_):
        path = self.repo_btn.get_filename()
        if not path:
            self.repo_path = None
            return
        self.repo_path = path
        self.refresh_status()

    def _is_git_repo(self, path: str) -> bool:
        rc, out = self._run_git(["rev-parse", "--is-inside-work-tree"], repo=path)
        return rc == 0 and out.strip() == "true"

    def refresh_status(self):
        if not self.repo_path:
            self._log(self._("repo_none"))
            return
        if not self._is_git_repo(self.repo_path):
            self._log(self._("repo_not_git"))
            return

        rc, out = self._run_git(["status", "--porcelain=v1", "-b"], repo=self.repo_path)
        if rc != 0:
            self._log(out + "\n")
            return

        self.status_store.clear()

        lines = [l.rstrip("\n") for l in out.splitlines()]
        branch = ""
        extra = ""
        for l in lines:
            if l.startswith("## "):

                branch = l[3:]
                extra = ""
                if "..." in branch:
                    branch, rest = branch.split("...", 1)
                    extra = f" ({rest})"
                break

        self.branch_label.set_text(self._("branch_label", branch=branch or "?", extra=extra))

        for l in lines:
            if not l or l.startswith("## "):
                continue
            code = l[:2]
            path = l[3:]
            self.status_store.append([code, path])

    def _ensure_repo(self):
        if not self.repo_path:
            self._log(self._("repo_none"))
            return False
        if not self._is_git_repo(self.repo_path):
            self._log(self._("repo_not_git"))
            return False
        return True

    def on_stage(self, *_):
        if not self._ensure_repo():
            return
        items = self._selected_files()
        if not items:
            self._log(self._("nothing_selected"))
            return
        paths = [p for _, p in items]
        rc, out = self._run_git(["add", "--"] + paths, repo=self.repo_path)
        self._log(out + "\n")
        self._log(self._("stage_ok") if rc == 0 else out + "\n")
        self.refresh_status()

    def on_stage_all(self, *_):
        if not self._ensure_repo():
            return
        rc, out = self._run_git(["add", "-A"], repo=self.repo_path)
        self._log(out + "\n")
        if rc == 0:
            self._log(self._("stage_all_ok"))
        else:
            self._log(self._("stage_all_fail"))
        self.refresh_status()

    def on_unstage(self, *_):
        if not self._ensure_repo():
            return
        items = self._selected_files()
        if not items:
            self._log(self._("nothing_selected"))
            return
        paths = [p for _, p in items]

        rc, out = self._run_git(["restore", "--staged", "--"] + paths, repo=self.repo_path)
        if rc != 0:
            rc, out = self._run_git(["reset", "HEAD", "--"] + paths, repo=self.repo_path)

        self._log(out + "\n")
        if rc == 0:
            self._log(self._("unstage_ok"))
        self.refresh_status()

    def on_discard(self, *_):
        if not self._ensure_repo():
            return
        items = self._selected_files()
        if not items:
            self._log(self._("nothing_selected"))
            return
        paths = [p for _, p in items]

        rc, out = self._run_git(["restore", "--"] + paths, repo=self.repo_path)
        if rc != 0:
            rc, out = self._run_git(["checkout", "--"] + paths, repo=self.repo_path)

        self._log(out + "\n")
        if rc == 0:
            self._log(self._("discard_ok"))
        self.refresh_status()

    def on_diff(self, *_):
        if not self._ensure_repo():
            return
        items = self._selected_files()
        if not items:
            self._log(self._("nothing_selected"))
            return
        path = items[0][1]
        rc, out = self._run_git(["diff", "--", path], repo=self.repo_path)
        self._show_text_dialog(self._("diff_title", path=path), out if out.strip() else "(no diff)")

    def _show_text_dialog(self, title: str, text: str):
        dlg = Gtk.Dialog(title=title, transient_for=self, modal=True)
        dlg.set_default_size(820, 420)

        box = dlg.get_content_area()
        tv = Gtk.TextView(editable=False, cursor_visible=False)
        tv.get_style_context().add_class("mono")
        tv.set_wrap_mode(Gtk.WrapMode.NONE)
        buf = tv.get_buffer()
        buf.set_text(text)

        sc = Gtk.ScrolledWindow()
        sc.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sc.add(tv)
        box.add(sc)

        dlg.add_button(self._("dialog_close"), Gtk.ResponseType.CLOSE)
        dlg.show_all()
        dlg.run()
        dlg.destroy()

    def on_commit(self, *_):
        if not self._ensure_repo():
            return
        msg = self.commit_entry.get_text().strip()
        if not msg:
            self._log(self._("msg_empty"))
            return

        rc, out = self._run_git(["commit", "-m", msg], repo=self.repo_path)
        self._log(out + "\n")
        if rc == 0:
            self._log(self._("commit_ok"))
            self.commit_entry.set_text("")
        else:
            self._log(self._("commit_fail"))
        self.refresh_status()

    def _run_bg(self, label_start: str, args, ok_msg: str, fail_msg: str, env=None, no_stdin=False):
        if not self._ensure_repo():
            return

        self._log(label_start)

        def worker():
            rc, out = self._run_git(args, repo=self.repo_path, env=env, no_stdin=no_stdin)
            GLib.idle_add(self._log, out + "\n")
            GLib.idle_add(self._log, ok_msg if rc == 0 else fail_msg)
            GLib.idle_add(self.refresh_status)

        threading.Thread(target=worker, daemon=True).start()


    def on_pull(self, *_):
        if not self._ensure_repo():
            return
        if hasattr(self, "auth_mode") and self.auth_mode.get_active() == 0:
            if not self._ensure_origin_ssh(self.repo_path):
                self._log(self._("ssh_need_switch"))
                return
            env = os.environ.copy()
            env["GIT_SSH_COMMAND"] = SSH_CMD
            env["GIT_TERMINAL_PROMPT"] = "0"
            self._run_bg(self._("pull_start"), ["pull"], self._("pull_ok"), self._("pull_fail"), env=env, no_stdin=True)
            return
        env = self._https_env_for_git()
        if not env:
            self._log(self._("auth_missing"))
            return
        self._run_bg(self._("pull_start"), ["pull"], self._("pull_ok"), self._("pull_fail"), env=env, no_stdin=True)
    def on_push(self, *_):
        if not self._ensure_repo():
            return
        if hasattr(self, "auth_mode") and self.auth_mode.get_active() == 0:
            if not self._ensure_origin_ssh(self.repo_path):
                self._log(self._("ssh_need_switch"))
                return
            env = os.environ.copy()
            env["GIT_SSH_COMMAND"] = SSH_CMD
            env["GIT_TERMINAL_PROMPT"] = "0"
            self._run_bg(self._("push_start"), ["push"], self._("push_ok"), self._("push_fail"), env=env, no_stdin=True)
            return
        env = self._https_env_for_git()
        if not env:
            self._log(self._("auth_missing"))
            return
        self._run_bg(self._("push_start"), ["push"], self._("push_ok"), self._("push_fail"), env=env, no_stdin=True)

    def on_show_remote(self, *_):
        if not self._ensure_repo():
            return
        rc, out = self._run_git(["remote", "-v"], repo=self.repo_path)
        self._show_text_dialog("Remotes", out)

    def on_show_log(self, *_):
        if not self._ensure_repo():
            return
        rc, out = self._run_git(["log", "--oneline", "--decorate", "-n", "50"], repo=self.repo_path)
        self._show_text_dialog("Log", out)

    # ---------------- Git config actions ----------------


    def _to_ssh_url(self, url: str):
        if not url:
            return None
        u = url.strip()
        if u.endswith("/"):
            u = u[:-1]
        m = re.match(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", u, re.IGNORECASE)
        if m:
            owner, repo = m.group(1), m.group(2)
            return f"git@github.com:{owner}/{repo}.git"
        if u.startswith("git@github.com:"):
            return u
        return None

    def _ensure_origin_ssh(self, repo_path: str):
        """Ensure origin uses SSH for GitHub (avoids HTTPS username/token prompts)."""
        rc, out = self._run_git(["remote", "get-url", "origin"], repo=repo_path)
        if rc != 0:
            self._log(out + "\n")
            return False
        origin = out.strip()
        if origin.startswith("git@github.com:"):
            return True
        ssh_url = self._to_ssh_url(origin)
        if not ssh_url:
            return False
        rc2, out2 = self._run_git(["remote", "set-url", "origin", ssh_url], repo=repo_path)
        if rc2 == 0:
            self._log(self._("ssh_switched"))
            return True
        self._log(out2 + "\n")
        return False

    def on_switch_ssh(self, *_):
        if not self._ensure_repo():
            return
        rc, out = self._run_git(["remote", "get-url", "origin"], repo=self.repo_path)
        if rc != 0:
            self._log(out + "\n")
            self._log(self._("ssh_switch_fail"))
            return
        origin = out.strip()
        ssh_url = self._to_ssh_url(origin)
        if not ssh_url:
            self._log(self._("ssh_url_fail"))
            return
        rc2, out2 = self._run_git(["remote", "set-url", "origin", ssh_url], repo=self.repo_path)
        if rc2 == 0:
            self._log(self._("ssh_switch_ok", url=ssh_url))
        else:
            self._log(out2 + "\n")
            self._log(self._("ssh_switch_fail"))

    def on_test_ssh(self, *_):
        cmd = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", "-T", "git@github.com"]
        rc, out = self._run(cmd, cwd=None)
        self._log(out + "\n")
        ok = ("successfully authenticated" in out.lower()) or ("hi " in out.lower() and "github" in out.lower())
        if ok:
            self._log(self._("ssh_test_ok"))
        else:
            self._log(self._("ssh_test_fail"))

    def on_test_auth(self, *_):
        if not self._ensure_repo():
            return

        rc, out = self._run_git(["remote", "get-url", "origin"], repo=self.repo_path)
        if rc != 0:
            self._log(out + "\n")
            self._log(self._("auth_test_fail"))
            return

        https = hasattr(self, "auth_mode") and (self.auth_mode.get_active() == 1)
        env = None
        no_stdin = False
        if https:
            env = self._https_env_for_git()
            if not env:
                self._log(self._("auth_missing"))
                return
            no_stdin = True

        rc2, out2 = self._run_git(["ls-remote", "--heads", "origin"], repo=self.repo_path, env=env, no_stdin=no_stdin)
        self._log(out2 + "\n")
        self._log(self._("auth_test_ok") if rc2 == 0 else self._("auth_test_fail"))

    def _git_get(self, key: str):
        rc, out = self._run_git(["config", "--global", "--get", key])
        return out.strip() if rc == 0 else None

    def _git_set(self, key: str, value: str):
        return self._run_git(["config", "--global", key, value])

    def on_apply_identity(self, *_):
        if not which("git"):
            self._log(self._("git_missing"))
            return

        name = self.entry_name.get_text().strip()
        email = self.entry_email.get_text().strip()
        editor = self.entry_editor.get_text().strip() or "geany"

        if name:
            rc, out = self._git_set("user.name", name)
            self._log(self._("set_name", value=name, out=out))
        if email:
            rc, out = self._git_set("user.email", email)
            self._log(self._("set_email", value=email, out=out))

        rc, out = self._git_set("core.editor", editor)
        self._log(self._("set_editor", value=editor, out=out))
        self._log(self._("ok_identity"))

    def on_apply_recommended(self, *_):
        if not which("git"):
            self._log(self._("git_missing"))
            return

        recommended = {
            "color.ui": "auto",
            "init.defaultBranch": "main",
            "push.default": "simple",
            "pull.rebase": "false",
            "credential.helper": "cache --timeout=3600",
            "alias.st": "status",
            "alias.co": "checkout",
            "alias.br": "branch",
            "alias.cm": "commit",
            "alias.lg": "log --oneline --decorate --graph",
        }

        for k, v in recommended.items():
            rc, out = self._git_set(k, v)
            if out.strip():
                self._log(f"{k} -> {v}\n{out}\n")
            else:
                self._log(f"{k} -> {v}\n")

        self._log(self._("ok_recommended"))

    # ---------------- SSH ----------------

    def on_generate_or_show_ssh(self, *_):
        home = os.path.expanduser("~")
        pub = os.path.join(home, ".ssh", "id_ed25519.pub")
        priv = os.path.join(home, ".ssh", "id_ed25519")

        os.makedirs(os.path.join(home, ".ssh"), exist_ok=True)

        if not which("ssh-keygen"):
            self._log(self._("sshkeygen_missing"))
            return

        if not os.path.exists(pub) or not os.path.exists(priv):
            email = self.entry_email.get_text().strip() or "git@local"
            self._log(self._("gen_key_start"))
            rc, out = self._run(["ssh-keygen", "-t", "ed25519", "-C", email, "-f", priv, "-N", ""])
            self._log(out + "\n")
            if rc != 0:
                self._log(self._("keygen_failed"))
                return

        try:
            with open(pub, "r", encoding="utf-8") as f:
                key = f.read().strip() + "\n"
        except Exception as e:
            self._log(self._("read_pub_failed", path=pub, err=str(e)))
            return

        self.pubkey_buf.set_text(key)
        self._log(self._("key_ready"))

    def on_copy_pubkey(self, *_):
        start, end = self.pubkey_buf.get_bounds()
        txt = self.pubkey_buf.get_text(start, end, True).strip()
        if not txt:
            self._log(self._("no_key_to_copy"))
            return
        cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        cb.set_text(txt, -1)
        cb.store()
        self._log(self._("copied"))

    # ---------------- Clone ----------------

    def on_clone(self, *_):
        if not which("git"):
            self._log(self._("git_missing"))
            return
        repo = self.entry_repo.get_text().strip()
        dest = self.folder_btn.get_filename()
        if not repo:
            self._log(self._("repo_empty"))
            return
        if not dest or not os.path.isdir(dest):
            self._log(self._("dest_invalid"))
            return
        self._log(self._("clone_start", dest=dest, repo=repo))
        def worker():
            repo_url = repo
            if hasattr(self, "auth_mode") and self.auth_mode.get_active() == 0:
                ssh_repo = self._to_ssh_url(repo_url)
                if ssh_repo:
                    repo_url = ssh_repo
            if hasattr(self, "auth_mode") and self.auth_mode.get_active() == 0:
                rc, out = self._run(["git", "-c", f"core.sshCommand={SSH_CMD}", "clone", repo_url], cwd=dest)
            else:
                rc, out = self._run(["git", "clone", repo_url], cwd=dest)
            GLib.idle_add(self._log, out + "\n")
            if rc == 0:
                GLib.idle_add(self._log, self._("clone_ok"))
                repo_name = repo_url.rstrip("/").split("/")[-1]
                if repo_name.endswith(".git"):
                    repo_name = repo_name[:-4]
                candidate = os.path.join(dest, repo_name)
                def _set_repo():
                    try:
                        self.repo_btn.set_filename(candidate)
                        self.repo_path = candidate
                        try:
                            if hasattr(self, 'auth_mode') and self.auth_mode.get_active() == 0:
                                self._ensure_origin_ssh(candidate)
                        except Exception:
                            pass
                        self._log(self._("auto_repo_set", path=candidate))
                        GLib.idle_add(self._reset_clone_form)
                        self.stack.set_visible_child_name("repo")
                        self.refresh_status()
                    except Exception:
                        pass
                    return False
                GLib.idle_add(_set_repo)
            else:
                GLib.idle_add(self._log, self._("clone_fail"))
        threading.Thread(target=worker, daemon=True).start()
    
    def _reset_clone_form(self, *_):
        self.entry_repo.set_text("")
        self.folder_btn.unselect_all()
        self.folder_btn.set_current_folder(os.path.expanduser("~"))   


class GitGUIApplication(Gtk.Application):
    def __init__(self, translations_path: str):
        super().__init__(application_id="org.essora.gitgui", flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.i18n = I18N(translations_path)

        act_about = Gio.SimpleAction.new("about", None)
        act_about.connect("activate", self.on_about)
        self.add_action(act_about)

        act_quit = Gio.SimpleAction.new("quit", None)
        act_quit.connect("activate", lambda *_: self.quit())
        self.add_action(act_quit)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = GitGUIWindow(self, self.i18n)
        win.present()

    def on_about(self, *_):
        _ = self.i18n.t
        win = self.props.active_window
        about = Gtk.AboutDialog(transient_for=win, modal=True)
    
        about.set_program_name(_("app_title"))
        about.set_version("2.0")
        about.set_comments(_("about_comments"))
        about.set_authors(self.i18n.data.get(self.i18n.lang, {}).get("about_authors", ["josejp2424"]))
        about.set_copyright(_("about_credit"))
        about.set_license_type(Gtk.License.GPL_3_0)
    
        if os.path.exists(ICON_PATH):
            try:
                img = Gtk.Image.new_from_file(ICON_PATH)
                pb = img.get_pixbuf()
                if pb:
                    about.set_logo(pb)
            except Exception:
                pass
    
        about.connect("response", lambda d, *_: d.destroy())
        about.present()


def find_translations():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "translations.json"),
        "/usr/local/essorafm/gitgui/translations.json",
        os.path.join(os.path.expanduser("~"), ".config", "gitgui", "translations.json"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]


def main():
    tpath = find_translations()
    app = GitGUIApplication(tpath)
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
