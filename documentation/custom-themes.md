# Custom Themes

This project supports layered, additive themes. The base UI renders with the existing dark styling. A theme file loads on top of those styles to override colors and contrast without changing layout or the original CSS.

Included themes
- `css/theme-light.css` (light base; disables dark mode)
- `css/theme-blue.css` (dark base overlay)
- `css/theme-emerald.css` (dark base overlay)
- `css/theme-purple.css` (dark base overlay)
- `css/theme-amber.css` (dark base overlay)

## How Themes Load

- Base CSS always loads (layout + component CSS)
  - `css/layout.css`
  - `css/f-shape.css`, `css/f-shape-rotated.css`, `css/pseudo-extend.css`, and other component styles
- A theme file loads after base styles and overrides specific selectors.
- For the built-in Light theme, Quasar dark mode is disabled in the layout and `css/theme-light.css` is injected on top of the base styles.

Relevant code
- `page_layout.py` serves static CSS and injects `layout.css`. It then checks the selected theme and injects the matching theme CSS, enabling or disabling Quasar dark mode accordingly.
- `foundry_state.py` stores the current theme (persisted to `config/layout_config.json`) and validates allowed theme names.
- `pages/settings_page.py` provides the Theme selector and saves the user's choice.

## What To Override

Aim to change color/contrast only. Avoid altering dimensions or layout.

Global surfaces
- `html, body, .q-page, .nicegui-content`: base background and text color.

Navigation
- `.q-drawer`: left drawer background, text color, right border, and inner shadow.
- `.q-drawer .q-item`, `.q-item__label`, `.material-symbols-outlined` for drawer items and icons.

Cards & panels
- `.q-card`: surface color, border color, and optional box-shadow for depth.

Typography
- `.text-white`: in dark mode many components force white text; override for legibility.
- `label, .q-label, .q-item__label, .q-btn__content, .q-banner__content` for general text.

Buttons
- `.q-btn` family as needed.
- `.q-btn--outline.text-white`: outline buttons that request white text in dark mode.
- `.drive-button` and `.drive-button *`: ensures labels inside drive buttons are readable.

Inputs
- `.q-field__native, .q-field__control, .q-field__marginal`: input text and background.
- `.number-input`: local class used for numeric controls.

Tables
- `.q-table, .q-table th, .q-table td`: base table surface and text.
- `.q-table thead tr th`: header band and divider line.
- `.q-table tbody tr td`: row separators, zebra striping, hover state.
- `.q-table__bottom`: footer band.

Separators
- `.q-separator`: horizontal rule color.

Notifications & menus
- `.q-notification`: surface, border.
- `.q-menu, .q-dialog__inner, .q-dialog-plugin, .q-list, .q-item`: surfaces and text; add shadows for elevation; hover state on `.q-item:hover`.

Chassis rails and backplanes
- `.pseudo-extend`, `.pseudo-extend-inverted`: use CSS variables to control side-rail backgrounds and borders
  - `--base-color`: rail fill
  - `--border-color`: rail border
- `.f-shape` and `.f-shape-rotated` (plus their `::before` and `::after`): the main backplane grid “F” surfaces.
- `.extension-patch`, `.extension-patch-rotated` and their `::after` scoop element (the scoop often matches the page background).

Brand accents
- `.text-yellowhako`: keep the brand yellow, add `text-shadow`/`filter: drop-shadow(...)` in light themes for contrast instead of changing to black.

## Design Tokens (Recommended)

Even though base styles are not variable-driven, you can structure your theme with a few logical tokens for consistency:

- Surface tokens: `--surface`, `--surface-muted`, `--surface-elevated`
- Text tokens: `--text`, `--text-muted`
- Border token: `--border`
- Accent tokens: `--accent`, `--accent-contrast`

Usage pattern in your theme file:

```css
:root {
  --surface: #ffffff;
  --surface-muted: #f6f7fb;
  --surface-elevated: #ffffff;
  --text: #111827;
  --text-muted: #6b7280;
  --border: #d1d5db;
  --accent: #ffdd00;
}

.q-card { background: var(--surface); color: var(--text); border-color: var(--border); }
.q-separator { background: var(--border); }
```

## Create Your Own Theme

1) Copy the example and adjust
- Create `css/theme-yourname.css` and start from `css/theme-light.css` as a template.
- Keep overrides additive. Prefer using `!important` only when necessary to win over Quasar/Tailwind inline styles.

2) Override the key selectors
- Use the list above as a checklist: Global → Drawer → Cards → Buttons/Inputs → Tables → Menus/Dialogs → Rails/Backplanes → Brand accents.

3) Load your theme
- Quick test: temporarily add an `elif` in `page_layout.py` pointing to your file.
- Production: wire it in three places:
  - Add your theme file under `css/theme-yourname.css`.
  - Extend the theme selector mapping in `pages/settings_page.py` (display → value).
  - Update validation in `foundry_state.py` to allow your theme value.

Example injection (conceptual):

```python
# page_layout.py
theme = globals.layoutState.get_theme()
if theme == 'light':
    ui.dark_mode().disable()
    ui.add_head_html('<link rel="stylesheet" type="text/css" href="/css/theme-light.css">')
elif theme == 'mytheme':
    ui.dark_mode().enable()  # keep dark base for overlays
    ui.add_head_html('<link rel="stylesheet" type="text/css" href="/css/theme-yourname.css">')
```

4) Test interactions
- Verify hover, focus, disabled, and selected states where applicable.
- Check table header/body/footer and zebra rows.
- Confirm the drive buttons, rails, and F-shape surfaces have sufficient contrast.

## Contrast & Accessibility Tips

- Use at least a 3:1 contrast ratio for non-text UI elements and 4.5:1 for small text when possible.
- Separate adjacent surfaces with either a border (`--border`) or a subtle shadow.
- Preserve brand accents (yellow) and use shadows to ensure legibility on light backgrounds.

## Minimal Theme Skeleton (Dark Overlay)

```css
/* css/theme-yourname.css */

/* Global */
html, body, .q-page, .nicegui-content { background: #0f172a !important; color: #e5e7eb !important; }

/* Navigation */
.q-drawer { background: #0b1220 !important; color: #e5e7eb !important; border-right: 1px solid #1f2937 !important; }

/* Cards */
.q-card { background: #111827 !important; color: #e5e7eb !important; border: 1px solid #1f2937 !important; }

/* Tables */
.q-table, .q-table th, .q-table td { background: #0f172a !important; color: #e5e7eb !important; }
.q-table thead tr th { background: #111827 !important; border-bottom: 1px solid #1f2937 !important; }

/* Inputs */
.q-field__control { background: #0f172a !important; }

/* Rails / Backplanes */
.pseudo-extend, .pseudo-extend-inverted { --base-color: #0e1628 !important; --border-color: #1f2937 !important; }
.f-shape, .f-shape::before, .f-shape::after, .f-shape-rotated, .f-shape-rotated::before, .f-shape-rotated::after { background: #1e2b48 !important; }

/* Brand */
.text-yellowhako { color: #ffdd00 !important; filter: drop-shadow(0 1px 1px rgba(0,0,0,0.25)); }
```

For a light-base theme, swap the background and text colors accordingly (see `css/theme-light.css`) and remember to disable dark mode in `page_layout.py` for that theme.
```

## Checklist

- Global background and text
- Drawer and icons
- Cards and panels
- Buttons (regular, outline) and drive buttons
- Inputs (text, number, select)
- Tables (header/body/footer, hover, zebra)
- Separators and notifications
- Menus/dialogs and list items
- Chassis rails (`.pseudo-extend`) and backplane F-shapes
- Brand yellow contrast handling

With these guidelines, you can create cohesive themes that layer cleanly on top of the existing UI without changing the layout or original CSS.
