# EssoraFM themes

Each `.theme` file in this folder defines a theme that EssoraFM loads
automatically when the user opens Preferences. Drop a new file here, restart
EssoraFM, and the theme appears in the combo list.

## File format

The format is INI (parseable with Python's standard `configparser`). It has
two sections: `[Theme]` for metadata and `[CSS]` for the GTK CSS code.

### `[Theme]` section

| Key | Required | Description |
|-----|----------|-------------|
| `Id` | yes | Unique stable identifier. Lowercase, no spaces. Saved to `~/.config/essorafm/config.ini`. |
| `Name` | yes | Display name in English (fallback when no localized name matches). |
| `Name[xx]` | optional | Localized display name. `xx` is an ISO-639-1 code (`es`, `fr`, `ja`...). |
| `Description` | optional | Short description in English. |
| `Description[xx]` | optional | Localized description. |
| `Author` | optional | Theme author. |
| `Version` | optional | Theme version. |
| `Emoji` | optional | A single emoji shown next to the name in the combo. |

### `[CSS]` section

A single key `Code = ...` containing GTK 3 CSS. The value is multiline:
indent every continuation line with at least one space (standard
`configparser` behavior).

CSS classes used by EssoraFM that you can target:

- `window`, `.essorafm-root` — main window background.
- `headerbar` — top bar.
- `.essorafm-sidebar-box`, `.essorafm-sidebar`, `.essorafm-sidebar-tree` — sidebar containers.
- `.essorafm-sidebar-tree.view` — sidebar rows.
- `.essorafm-sidebar-tree.view:selected` — selected sidebar row.
- `.essorafm-content`, `.essorafm-toolbar` — main content area.
- `treeview.view` — file list rows.
- `.essorafm-tabs` — tab strip.
- `.essorafm-tabs tab` — individual tab.
- `.essorafm-tabs tab:checked` — active tab.

## Reserved IDs

`default` and `gtk_system` are reserved and handled internally — do NOT
create a `.theme` file with those IDs. They map to the styles.css base and
to the GTK system theme respectively.

## Minimal example

```ini
[Theme]
Id = my_theme
Name = My theme
Name[es] = Mi tema
Author = your-name

[CSS]
Code =
    window, .essorafm-root { background-color: #112233; }
    headerbar { background-color: #223344; color: #ffffff; }
    .essorafm-sidebar-tree.view { background-color: #1a2a3a; color: #ddeeff; }
```
