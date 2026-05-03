<div align="center">

<img src="usr/local/essorafm/ui/icons/essorafm.svg" alt="EssoraFM logo" width="128" height="128">

# EssoraFM

**Modular GTK3 file manager for Essora Linux**

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL%203.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.4.23-green.svg)](https://github.com/josejp2424/essorafm/releases)
[![Platform](https://img.shields.io/badge/platform-Linux-lightgrey.svg)]()
[![Built with](https://img.shields.io/badge/built%20with-Python%203%20%2B%20GTK3-yellow.svg)]()
[![Init: OpenRC](https://img.shields.io/badge/init-OpenRC%20friendly-orange.svg)]()

A lightweight, init-system-agnostic file manager designed for [Essora Linux](https://sourceforge.net/projects/essora/) — a Devuan-based distribution with OpenRC. Works on any Linux without systemd dependencies.

</div>

---

## Table of contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Keyboard shortcuts](#keyboard-shortcuts)
- [Configuration](#configuration)
- [Themes](#themes)
- [GitHub integration (GitGUI)](#github-integration-gitgui)
- [Architecture](#architecture)
- [Internationalization](#internationalization)
- [Privilege escalation](#privilege-escalation)
- [Building from source](#building-from-source)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Credits](#credits)

---

## Features

### Core navigation
- **Tabbed browsing** with closable tabs and `Ctrl+T` / `Ctrl+W` shortcuts.
- **Sidebar with sections**: Quick access (favorites), Places (Home, Desktop, Documents, Downloads, Filesystem, Trash), Devices (auto-detected mounted volumes), and Network (SMB/FTP/SFTP/WebDAV bookmarks plus a built-in GitHub entry).
- **Path bar** with integrated search.
- **Multi-backend mount/unmount** for removable volumes, with automatic fallback through `udisksctl` → `gio mount` → `pkexec mount`.
- **Two view modes**: icons (grid) and list (with name, size, modified columns).
- **Hidden files toggle**: toolbar button, `Ctrl+H`, or context menu.
- **Configurable bar order and position**: choose whether toolbar sits above or below the address/search bar, and whether the whole bar block sits above or below the file area.

### File operations
- **Copy, paste, move to trash, restore, delete permanently** — all standard operations.
- **`rsync`-backed copying** when available for large transfers, falls back to Python `shutil`.
- **XDG-compliant trash** at `~/.local/share/Trash` with `.trashinfo` metadata.
- **Open with...** — submenu listing applications registered for the file's MIME type via `Gio.AppInfo`, plus an "Other application..." option that launches `Gtk.AppChooserDialog`.

### Preview panel
Optional side preview for the selected file. Toggleable from the toolbar and persisted across sessions.

| Format            | Backend                                          |
| ----------------- | ------------------------------------------------ |
| PNG, JPG, WEBP, BMP, GIF, TIFF, SVG | `GdkPixbuf` native loader |
| TXT, LOG, MD, CONF, INI, DESKTOP, SH, PY, JSON, XML, CSS | Python text reader (Cairo when available) |
| PDF (first page)  | `pdftoppm` from `poppler-utils`                  |
| EPUB (cover)      | Python `zipfile` extracting embedded cover image |

If a backend is missing, EssoraFM falls back gracefully to the standard file icon.

### Duplicate scanner
Built-in duplicate file finder accessible from the toolbar and right-click menu. Optimized for large folders: it first groups candidates by file size, and only then computes hashes for actual collision candidates.

### Network bookmarks
Connect to SMB, FTP, SFTP and WebDAV shares. Bookmarks are stored locally and reconnected on demand from the sidebar.

### Built-in desktop (`essorafm --desktop`)
EssoraFM includes its **own integrated desktop renderer** — no external dependencies required, the whole logic lives in `app/desktop.py`. It draws drive icons and `.desktop` shortcuts directly from the user's XDG Desktop folder, manages the wallpaper, and handles right-click menus for changing wallpaper, adding icons, and refreshing.

- **Mount-state visual feedback**: unmounted drives render at 50% opacity, mounted drives at 100%.
- **Eject badge**: a small clickable `media-eject` icon appears in the corner of mounted drive icons. Clicking it unmounts the drive without opening it.
- **`Add icon to desktop`** writes a clean `Type=Link` wrapper that delegates to the source `.desktop` (no more 80+ lines of `Name[xx]=` translations being copied to the desktop).
- **Wallpaper carousel**: pressing *Change wallpaper* opens a borderless modal showing thumbnails of every supported image (JPG, PNG, WEBP, BMP, TIFF, **SVG**) from the configured wallpaper directory. The selected image previews enlarged at the center, with the surrounding thumbnails scaling down progressively. Replaces the previous plain `Gtk.FileChooserDialog`.
- **Configurable**: drive icon size, label width and lines, font and shadow color, what types to show (internal / removable / network).
- **Send images to `/usr/share/backgrounds`** directly from the file manager's context menu.
- **Run files in a console** with one click.

### XDG-aware folder handling
EssoraFM resolves the user's standard folders (Desktop, Documents, Downloads, Pictures, Music, Videos) through `GLib.get_user_special_dir()`, which reads `~/.config/user-dirs.dirs`. This means it works correctly in any system language — `~/Descargas`, `~/Téléchargements`, `~/ダウンロード`, etc. — without hardcoding name lists. The sidebar Places section, the per-tab folder icon, and the `--desktop` mode all share this resolution.

### Themes
EssoraFM ships with seven themes, including the official **🌿 Essora** theme (olive green `#77960A` accent on dark gray `#1F2228`). Themes live as standalone `.theme` files in `/usr/local/essorafm/theme/` — drop a new file there and it appears automatically in Preferences. See [Themes](#themes) below.

### GitHub integration (GitGUI)
A clickable **GitHub** entry in the sidebar's Network section opens **GitGUI**, an embedded Git configuration tool that lives entirely under `/usr/local/essorafm/gitgui/`. It handles `git config --global` setup, SSH key generation for GitHub, and basic `clone` / `pull` / `push` actions — all running under the user's home, never as root. If `git` is not installed when launching, EssoraFM shows a localized dialog with the install command instead of opening a broken UI.

### Configurable interface
Persistent across sessions via `~/.config/essorafm/config.ini`:

- View mode (icons / list).
- Icon sizes for grid, list, sidebar and toolbar — independent.
- Single click to open.
- Show hidden files at startup.
- Show thumbnails (image previews in icon view).
- Window size — three presets (`640×480`, `880×550`, `1040×680`) and a fully custom width × height range (640–3840 × 480–2160).
- Sidebar layout (classic / compact).
- Bar order (toolbar above pathbar, or pathbar above toolbar).
- Bar block position (above or below the file content).
- Sort field (name / size / modified / type) and direction.
- Toolbar style (icons only, icons only flat, text below, text right).
- Application theme (any `.theme` file in `/usr/local/essorafm/theme/`).
- Rounded corners, card style, glassmorphism toggles.

### Internationalization
Full UI translations for **12 languages**: English, Spanish, Catalan, German, French, Italian, Portuguese, Hungarian, Japanese, Russian, Chinese, Arabic. Language is auto-detected from `$LANG` / system locale. The current build ships **274 translation keys per language**.

---

## Screenshots

<div align="center">

<table>
<tr>
<td align="center" width="50%">
<img src="assets/essorafm.png" alt="Main window"><br>
<sub><b>Main window</b></sub>
</td>
<td align="center" width="50%">
<img src="assets/essorafm2.png" alt="Preview panel"><br>
<sub><b>Preview panel</b></sub>
</td>
</tr>
<tr>
<td align="center" width="50%">
<img src="assets/essorafm3.png" alt="Preferences"><br>
<sub><b>Preferences</b></sub>
</td>
<td align="center" width="50%">
<img src="assets/essorafm4.png" alt="Duplicate scanner"><br>
<sub><b>Duplicate scanner</b></sub>
</td>
</tr>
<tr>
<td align="center" width="50%">
<img src="assets/essorafm5.png" alt="Network bookmarks"><br>
<sub><b>Network bookmarks</b></sub>
</td>
<td align="center" width="50%">
<img src="assets/essorafm6.png" alt="About dialog"><br>
<sub><b>About</b></sub>
</td>
</tr>
<tr>
<td align="center" colspan="2">
<img src="assets/wallpaper.png" alt="Wallpaper carousel"><br>
<sub><b>Wallpaper carousel (<code>essorafm --desktop</code> → right-click → Change wallpaper)</b></sub>
</td>
</tr>
</table>

</div>

---

## Requirements

### Runtime dependencies (Debian/Devuan package names)
- `python3` (≥ 3.8)
- `python3-gi`
- `python3-gi-cairo`
- `gir1.2-gtk-3.0`
- `gir1.2-gdkpixbuf-2.0`
- `gir1.2-glib-2.0`
- `gir1.2-pango-1.0`
- `udisks2`
- `samba` — required for SMB bookmarks
- `poppler-utils` — required for PDF previews
- `rclone` — used by the network mount fallback chain

### Recommended (not required)
- `git` — for GitGUI integration. EssoraFM detects its absence at launch and shows a localized prompt instead of failing.
- `openssh-client` — for GitGUI's SSH key generation tab.

### Optional dependencies
- `rsync` — accelerated copying with progress.
- `policykit-1` *or* `gksu` — privilege escalation for system-protected operations.
- `xdg-utils` — `xdg-open` fallback for "Open with default application".
- `librsvg` — provides SVG rendering for `GdkPixbuf` (already pulled in by GTK on Debian/Devuan). Without it, SVG wallpapers are skipped silently.

### Tested on
- Essora Linux (Devuan Excalibur base, OpenRC)
- Devuan Daedalus / Excalibur
- Debian 12 Bookworm

EssoraFM has **no systemd dependency**, so it runs equally well on systemd, OpenRC, runit or s6 systems.

---

## Installation

### Option 1 — `.deb` package (recommended)

Download the latest release from [Releases](https://github.com/josejp2424/essorafm/releases) or [SourceForge](https://sourceforge.net/projects/essora/) and install:

```bash
sudo dpkg -i essorafm_0.4.23-2_amd64.deb
sudo apt-get install -f   # resolve dependencies if needed
```

The `postinst` script seeds default config files into every real user's `~/.config/essorafm/` directory. Files that already exist are never overwritten — personal settings are preserved across upgrades.

### Option 2 — From the tar archive

```bash
tar -xzf essorafm-0_4_21-3_amd64_tar.gz
cd essorafm-0.4.23-2_amd64
sudo cp -rv usr/* /usr/

# Clean any old bytecode cache (important when upgrading)
sudo find /usr/local/essorafm -name '__pycache__' -type d -exec rm -rf {} +
sudo find /usr/local/essorafm -name '*.pyc' -delete
```

### Option 3 — From source

```bash
git clone https://github.com/josejp2424/essorafm.git
cd essorafm
sudo cp -rv usr/* /usr/
```

### Verify installation

```bash
which essorafm                       # → /usr/local/bin/essorafm
essorafm --version 2>/dev/null || essorafm
```

### Uninstall

```bash
sudo rm -rf /usr/local/essorafm
sudo rm -f /usr/local/bin/essorafm
sudo rm -f /usr/share/applications/essorafm.desktop
sudo rm -f /usr/share/applications/essorafm-desktop.desktop
```

User config at `~/.config/essorafm/` is preserved unless removed manually.

---

## Usage

### Launch
- From the application menu: *System → EssoraFM*
- From a terminal: `essorafm`
- With a starting path: `essorafm /home/user/Pictures`
- As a desktop renderer: `essorafm --desktop` (replaces the desktop wallpaper and renders drive icons + shortcuts)
- To unmount a path from the command line: `essorafm -D /media/user/disk`

### Right-click menu
On any file or folder you get:
- **Open** — uses the default application
- **Open with...** — submenu of every app registered for the MIME type, plus *Other application...*
- **Copy** — into the internal clipboard
- **Move to trash** / **Delete permanently**
- **Restore** (when inside trash)
- **Run in console** (when relevant)
- **Send to backgrounds** (for image files)
- **Paste here**, **New folder**, **Refresh**, **Show hidden** (always available on empty area)

---

## Keyboard shortcuts

| Shortcut         | Action                              |
| ---------------- | ----------------------------------- |
| `Ctrl+T`         | New tab                             |
| `Ctrl+W`         | Close current tab                   |
| `Ctrl+L`         | Focus the path bar                  |
| `Ctrl+H`         | Toggle hidden files                 |
| `Ctrl+,`         | Open Preferences                    |
| `Ctrl+C`         | Copy selected to internal clipboard |
| `Ctrl+V`         | Paste                               |
| `F5`             | Refresh current view                |
| `Delete`         | Move to trash                       |
| `Shift+Delete`   | Delete permanently                  |

---

## Configuration

EssoraFM stores its config at:

```
~/.config/essorafm/config.ini
```

Format:

```ini
[Main]
view_mode = icons
icon_size = 64
list_icon_size = 32
sidebar_icon_size = 32
toolbar_icon_size = 20
show_hidden = false
single_click = false
show_thumbnails = true
preview_enabled = true
window_width = 880
window_height = 550
sidebar_layout = classic
toolbar_first = true
bars_position = top
sort_field = name
sort_direction = asc
desktop_drive_icons = true
desktop_drive_icon_size = 48
desktop_drive_show_internal = true
desktop_drive_show_removable = true
desktop_drive_show_network = false
app_theme = default
theme_rounded = true
theme_cards = false
theme_glass = false
```

The file is created automatically on first run with sane defaults. All UI preferences are mirrored into it on save.

Network bookmarks are stored in:

```
~/.config/essorafm/network_bookmarks.json
```

---

## Themes

Themes are standalone INI files in `/usr/local/essorafm/theme/`. EssoraFM scans this folder at startup and exposes every `.theme` file in the Preferences combo. Two IDs are reserved (`default` and `gtk_system`) and handled internally.

### Bundled themes

| ID            | Display name      | Palette                                     |
| ------------- | ----------------- | ------------------------------------------- |
| `default`     | Default (dark)    | `#242424` background, olive green accent    |
| `gtk_system`  | System GTK theme  | Whatever GTK theme is installed system-wide |
| `essora`      | 🌿 Essora         | `#1F2228` + `#77960A` — official Essora     |
| `neon_cyber`  | ⚡ Neon Cyber     | `#050a0f` + electric blue `#00d4ff`         |
| `aurora`      | 🌌 Aurora         | `#0d0618` + violet `#7c3aed`                |
| `carbon`      | 🖤 Carbon         | `#1a1a1a` + silver `#9ca3af`                |
| `ocean_deep`  | 🌊 Ocean Deep     | `#0a1628` + cyan `#00b4d8`                  |
| `ember`       | 🔥 Ember          | `#0f0a06` + orange `#ff6b35`                |

### File format

Each theme is an INI file with a `[Theme]` metadata section and a `[CSS]` section:

```ini
[Theme]
Id = my_theme
Name = My theme
Name[es] = Mi tema
Name[ja] = マイテーマ
Description = Soft pastel palette
Description[es] = Paleta de pastel suave
Author = your-name
Version = 1.0
Emoji = 🎨

[CSS]
Code =
    window, .essorafm-root { background-color: #112233; }
    headerbar { background-color: #223344; color: #ffffff; }
    .essorafm-sidebar-tree.view { background-color: #1a2a3a; color: #ddeeff; }
    .essorafm-sidebar-tree.view:selected { background-color: #ff8800; color: #ffffff; }
```

`Name[xx]` and `Description[xx]` follow the same convention as `.desktop` files. EssoraFM picks the localized variant matching the system language and falls back to the unlocalized `Name=` / `Description=` if no match is found. See `/usr/local/essorafm/theme/README.md` for the full reference of CSS selectors that EssoraFM uses.

To install a new theme, drop its `.theme` file into `/usr/local/essorafm/theme/` and restart EssoraFM. To remove one, delete the file. The selected theme ID is persisted in `~/.config/essorafm/config.ini` under `app_theme`.

---

## GitHub integration (GitGUI)

EssoraFM ships with **GitGUI**, a small Git configuration GUI bundled under `/usr/local/essorafm/gitgui/`. It is reachable from the sidebar's Network section by clicking the **GitHub** entry.

GitGUI is launched as the **regular user**, never with `pkexec` or `sudo`, because it modifies `~/.gitconfig` and `~/.ssh/` — files that must live in the user's home, not in `/root/`.

What it does:
- Configure `git config --global user.name` / `user.email` / `core.editor`
- Generate an `ed25519` SSH key with `ssh-keygen` and copy the public key to clipboard for GitHub
- Clone repositories with progress feedback
- Run basic `pull` / `push` / `status` actions on a chosen working directory

If `git` is not installed when the user clicks the GitHub entry, EssoraFM detects this via `shutil.which('git')` and shows a localized dialog with the suggested install command — no broken GitGUI window opens. The same applies if `gitgui.py` is missing.

GitGUI's translations live separately in `/usr/local/essorafm/gitgui/translations.json` (11 languages, JSON-based) and are independent from EssoraFM's i18n.

---

## Architecture

```
/usr/local/essorafm/
├── essorafm.py              # entrypoint (--desktop, -D, normal)
├── app/
│   ├── window.py            # main window, layout, key bindings, theme loader
│   ├── tabs.py              # tab notebook, close buttons, XDG-aware tab icons
│   ├── fileview.py          # icon/list view + context menu
│   ├── sidebar.py           # quick access / places / devices / network sections
│   ├── pathbar.py           # path bar with integrated search
│   ├── toolbar.py           # top toolbar (icons / icons-flat / text-below / text-right)
│   ├── preview_panel.py     # right-side preview panel
│   ├── dialogs.py           # Preferences, Copy progress, About
│   ├── duplicates.py        # duplicate scanner UI
│   ├── network_dialog.py    # SMB/FTP/SFTP bookmarks UI
│   ├── wallpaper_carousel.py # wallpaper picker with thumbnail carousel
│   └── desktop.py           # built-in desktop renderer (--desktop mode)
├── core/
│   ├── settings.py          # paths, constants
│   ├── settings_manager.py  # config.ini read/write
│   ├── desktop_settings.py  # desktop-specific config
│   ├── filesystem.py        # directory listing, MIME detection
│   ├── copy_engine.py       # rsync + Python fallback
│   ├── privilege.py         # pkexec / gksu helper
│   ├── xdg.py               # XDG user-dirs.dirs resolution (any language)
│   └── i18n.py              # 12-language string table (274 keys each)
├── services/
│   ├── icon_loader.py       # GdkPixbuf icon caching
│   ├── thumbnailer.py       # async thumbnail generation
│   ├── previewer.py         # preview backends per format
│   ├── trash.py             # XDG-compliant trash
│   ├── volumes.py           # multi-backend mount/unmount (udisksctl/gio/pkexec)
│   ├── network_bookmarks.py # network bookmarks persistence
│   ├── favorites.py         # quick-access favorites persistence
│   └── themes.py            # .theme file loader
├── theme/
│   ├── README.md            # theme format reference
│   ├── essora.theme         # 🌿 Essora official
│   ├── neon_cyber.theme     # ⚡ Neon Cyber
│   ├── aurora.theme         # 🌌 Aurora
│   ├── carbon.theme         # 🖤 Carbon
│   ├── ocean_deep.theme     # 🌊 Ocean Deep
│   └── ember.theme          # 🔥 Ember
├── gitgui/
│   ├── gitgui.py            # GitGUI standalone Python/GTK app
│   └── translations.json    # 11-language strings
└── ui/
    ├── icons/               # SVG/PNG icon assets (essorafm, favorite, red, github)
    └── styles.css           # GTK CSS theming base
```

The codebase follows a **strict separation of concerns**:

- `app/` — GTK widgets and event handlers only.
- `core/` — pure logic, no GTK imports outside `Gio`/`GLib` data classes.
- `services/` — long-lived stateful helpers (icon caches, trash, thumbnails, theme loading).
- `theme/` — user-extendable theme files, no Python.
- `gitgui/` — self-contained sub-application launched on demand.

This allows individual modules to be tested or replaced without touching the UI layer.

---

## Internationalization

UI strings live in [`core/i18n.py`](core/i18n.py) under a `STRINGS` dict. The active language is detected from `$LANG`, falling back to English.

Supported languages out of the box:

| Code | Language    | Code | Language    |
| ---- | ----------- | ---- | ----------- |
| `en` | English     | `pt` | Portuguese  |
| `es` | Spanish     | `hu` | Hungarian   |
| `ca` | Catalan     | `ja` | Japanese    |
| `de` | German      | `ru` | Russian     |
| `fr` | French      | `zh` | Chinese     |
| `it` | Italian     | `ar` | Arabic      |

To add a new language, edit `core/i18n.py` and add an entry to the relevant string blocks (`GITHUB_STRINGS`, `THEME_TAB_STRINGS`, `BAR_POSITION_STRINGS`, `HARDCODED_FIX_STRINGS`, `TOOLBAR_FLAT_STRINGS`) with your translations. Spanish acts as the secondary fallback before English, so any missing key surfaces in Spanish first, then English.

To force a language regardless of system locale:

```bash
LANG=ja_JP.UTF-8 essorafm
```

Theme names and descriptions also follow the same `Name[xx]=` / `Description[xx]=` convention inside their `.theme` files. GitGUI carries its own JSON-based translation file at `/usr/local/essorafm/gitgui/translations.json` (11 languages).

User folder paths (Desktop, Documents, Downloads, Pictures, Music, Videos) are resolved via `core/xdg.py` which calls `GLib.get_user_special_dir()`. This makes EssoraFM work transparently on systems with localized XDG folders (`~/Descargas`, `~/Téléchargements`, `~/ダウンロード`, etc.) without hardcoding name lists.

---

## Privilege escalation

When an operation fails with `EPERM`/`EACCES` (e.g. deleting a file owned by root), EssoraFM transparently retries the action via `pkexec`. If `pkexec` is not available, it falls back to `gksu`. The user gets a single PolicyKit prompt and the operation continues.

This is implemented in [`core/privilege.py`](core/privilege.py) and triggered from:
- Move to trash
- Delete permanently
- Restore from trash
- Create folder
- Paste (copy)
- Mount/unmount when `udisksctl` and `gio mount` both fail (last fallback in `services/volumes.py`)

EssoraFM **never** requests elevated privileges preemptively — only when the kernel actually denies the operation.

---

## Building from source

To rebuild the `.deb` package:

```bash
# from the project root, where DEBIAN/control sits
fakeroot dpkg-deb --build --root-owner-group essorafm-0.4.23-2_amd64
```

To create a portable tarball:

```bash
tar -czf essorafm-0_4_21-3_amd64_tar.gz essorafm-0.4.23-2_amd64/
```

There is no compilation step — EssoraFM is pure Python.

---

## Troubleshooting

### Settings reset on every launch
Ensure `~/.config/essorafm/` is writable by the user. Delete `config.ini` to regenerate defaults:
```bash
rm ~/.config/essorafm/config.ini
```

### Thumbnails for PDF do not appear
Install Poppler:
```bash
sudo apt install poppler-utils
```

### SVG wallpapers do not show in the carousel
GdkPixbuf needs `librsvg` to render SVG. On Debian/Devuan it is installed by default with GTK, but if you ended up without it:
```bash
sudo apt install librsvg2-common
```

### Right-click context menu missing "Delete" or "Open with..."
Clear bytecode cache and restart:
```bash
sudo find /usr/local/essorafm -name '__pycache__' -type d -exec rm -rf {} +
sudo find /usr/local/essorafm -name '*.pyc' -delete
pkill -f essorafm
essorafm
```

### Volumes do not mount
EssoraFM tries `udisksctl`, then `gio mount`, then `pkexec mount`. If all three fail, install at least `udisks2`:
```bash
sudo apt install udisks2
udisksctl status
```

### USB drives do not show on the desktop
Open Preferences and check that **Show removable drives** is enabled. The setting persists in `~/.config/essorafm/config.ini` as `desktop_drive_show_removable=true`.

### Sidebar shows "Desktop"/"Documents" pointing to nothing on a non-English system
Resolved automatically since `0.4.21-2` via `core/xdg.py`. If you upgrade from an older build and the issue persists, run:
```bash
xdg-user-dirs-update --force
```
to regenerate `~/.config/user-dirs.dirs`, then restart EssoraFM.

### GitHub entry shows "Git is not installed"
Install Git:
```bash
sudo apt install git openssh-client
```

### Theme does not appear in Preferences
Verify the file ends in `.theme`, lives directly in `/usr/local/essorafm/theme/` (not in a subfolder), and parses as valid INI. EssoraFM silently skips malformed files. Check with:
```bash
python3 -c "import configparser; c=configparser.ConfigParser(); c.read('/usr/local/essorafm/theme/your.theme'); print(c.sections())"
```

### App locks up on a large folder
EssoraFM lists synchronously. Avoid running it on directories with hundreds of thousands of entries (e.g. `/proc`, mass-extracted archives). Use a terminal for those.

### Reset everything to defaults
```bash
rm -rf ~/.config/essorafm
```

---

## Contributing

Pull requests are welcome. The codebase is small enough to read end-to-end in an afternoon.

When opening a PR:
1. Keep changes surgical — modify only the files relevant to the issue.
2. Preserve the i18n layer — every new user-facing string must land in `core/i18n.py` for at least English and Spanish.
3. Avoid systemd-only APIs. EssoraFM ships on OpenRC distros.
4. Test on at least one Devuan or non-systemd Debian derivative when touching mount/unmount or autostart code.
5. New themes go as `.theme` files in `theme/` — never as hardcoded CSS in `window.py`.
6. Use `core.xdg.xdg_dir()` instead of `os.path.join(home, 'Downloads')` etc., so the change works in every locale.

Bug reports go in the [issue tracker](https://github.com/josejp2424/essorafm/issues). Please include:
- EssoraFM version (visible in *About*)
- Distribution and init system
- Output of `essorafm` from a terminal at the moment of the bug

---

## License

EssoraFM is released under the **GNU General Public License v3.0 or later**. See [LICENSE](LICENSE) for the full text.

```
Copyright (C) 2024–2026 josejp2424
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
```

---

## Credits

- **Author and maintainer**: josejp2424
- **Co-author**: Nilsonmorales [Woofshahenzup](https://github.com/Woofshahenzup) — UI polish, multi-backend mount, redesigned About dialog, flat toolbar style, wallpaper carousel, configurable bar order/position
- **GitGUI**: based on the original `git-seguro.sh` Bash script by [nilsonmorales](https://github.com/Woofshahenzup), rewritten as a GTK3 Python app for EssoraFM
- **Default styling**: adapted from the Catppuccin Mocha palette
- **Tested and shipped with**: [Essora Linux](https://sourceforge.net/projects/essora/)

---

<div align="center">

Made with patience and a lot of `Ctrl+R` for [Essora Linux](https://sourceforge.net/projects/essora/) ♥

</div>
