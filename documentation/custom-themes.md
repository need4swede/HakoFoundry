# Custom Themes

This project supports layered, additive themes. The base UI renders with the existing dark styling. A theme file can load on top of those styles to override colors and contrast without changing layout or the original CSS.

The included `css/theme-light.css` demonstrates this approach.

## How Themes Load

- Base CSS always loads (layout + component CSS)
  - `css/layout.css`
  - `css/f-shape.css`, `css/f-shape-rotated.css`, `css/pseudo-extend.css`, and other component styles
- A theme file loads after base styles and overrides specific selectors.
- For the built-in Light theme, Quasar dark mode is disabled in the layout and `css/theme-light.css` is injected on top of the base styles.

Relevant code
- `page_layout.py:17` sets up static files.
- `page_layout.py:21` injects `layout.css` and, when the selected theme is `light`, disables dark mode and layers `theme-light.css`.
- `foundry_state.py:450` defines `self.theme` with persistence to `config/layout_config.json`.
- `pages/settings_page.py:296` adds a Theme selector that saves the user's choice.

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
- Quick test: temporarily swap the Light CSS link in `page_layout.py` to your file name.
- Production: extend the theme selection to include your theme name and add a conditional link injection in `page_layout.py` similar to the Light theme.

Example injection (conceptual):

```python
# page_layout.py
if globals.layoutState.get_theme() == 'mytheme':
    ui.dark_mode().disable()  # or enable() depending on your base
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

## Minimal Theme Skeleton

```css
/* css/theme-yourname.css */

/* Global */
html, body, .q-page, .nicegui-content { background: #fafafa !important; color: #111827 !important; }

/* Navigation */
.q-drawer { background: #f5f5f5 !important; color: #111827 !important; border-right: 1px solid #d1d5db !important; }

/* Cards */
.q-card { background: #ffffff !important; color: #111827 !important; border: 1px solid #d1d5db !important; }

/* Tables */
.q-table, .q-table th, .q-table td { background: #ffffff !important; color: #111827 !important; }
.q-table thead tr th { background: #f8fafc !important; border-bottom: 1px solid #d1d5db !important; }

/* Inputs */
.q-field__control { background: #ffffff !important; }

/* Rails / Backplanes */
.pseudo-extend, .pseudo-extend-inverted { --base-color: #f3f4f6 !important; --border-color: #cbd5e1 !important; }
.f-shape, .f-shape::before, .f-shape::after, .f-shape-rotated, .f-shape-rotated::before, .f-shape-rotated::after { background: #e5e7eb !important; }

/* Brand */
.text-yellowhako { color: #ffdd00 !important; text-shadow: 0 1px 2px rgba(0,0,0,0.45); }
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
