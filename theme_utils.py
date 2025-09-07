from typing import Dict
from string import Template


CUSTOM_TEMPLATE = Template("""
/* Generated Custom Theme */

/* Global */
html, body, .q-page, .nicegui-content {
  background-color: $global_bg !important;
  color: $global_text !important;
}

/* Drawer */
.q-drawer {
  background-color: $drawer_bg !important;
  color: $global_text !important;
  border-right: 1px solid $border !important;
}
.q-drawer .q-item,
.q-drawer .q-item__section,
.q-drawer .q-item__label,
.q-drawer .material-symbols-outlined { color: $global_text !important; }

/* Cards & surfaces */
.q-card {
  background-color: $card_bg !important;
  color: $global_text !important;
  border: 1px solid $border !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.35), 0 4px 10px rgba(0, 0, 0, 0.25) !important;
}

/* Utility overrides */
.bg-neutral-900 { background-color: $global_bg !important; }
.text-gray-300 { color: $global_text !important; opacity: 0.9; }
.text-gray-400 { color: $global_text !important; opacity: 0.75; }
.text-gray-500 { color: $global_text !important; opacity: 0.6; }
.border-white { border-color: $border !important; }
.border-neutral-600 { border-color: $border !important; }
.border-[#ffdd00] { border-color: #ffdd00 !important; }

/* Buttons */
.drive-button, .drive-button * { color: $global_text !important; }
.drive-button.q-btn { border-color: $border !important; background-color: $global_bg !important; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.25) !important; }
.drive-button.q-btn:hover { background-color: $hover_bg !important; }
.q-btn--outline.text-white { color: $global_text !important; border-color: $number_border !important; background-color: transparent !important; }

/* Tables */
.q-table, .q-table th, .q-table td { color: $global_text !important; background-color: $global_bg !important; }
.q-table thead tr th { background-color: $card_bg !important; border-bottom: 1px solid $border !important; }
.q-table tbody tr td { border-bottom: 1px solid $border !important; }
.q-table tbody tr:nth-child(even) td { background-color: $zebra_even_bg !important; }
.q-table tbody tr:hover td { background-color: $hover_bg !important; }
.q-table__bottom { background-color: $table_footer_bg !important; color: $global_text !important; border-top: 1px solid $border !important; }

/* Separators */
.q-separator { background: $border !important; }

/* Labels and form controls */
label, .q-label, .q-field__label, .q-item__label, .q-btn__content, .q-banner__content { color: $global_text !important; }
.q-field__native, .q-field__control, .q-field__marginal { color: $global_text !important; }
.q-field__control, .q-select__dialog, .q-menu { background-color: $input_bg !important; border-color: $border !important; }
.number-input { background-color: $input_bg !important; color: $global_text !important; border-color: $number_border !important; }

/* Menus & dialogs */
.q-menu, .q-dialog__inner, .q-dialog-plugin, .q-panel, .q-banner, .q-list, .q-item {
  background-color: $menu_bg !important;
  color: $global_text !important;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.45), 0 6px 8px rgba(0, 0, 0, 0.35) !important;
}
.q-item:hover { background-color: $hover_bg !important; }

/* Rails and backplanes */
.pseudo-extend, .pseudo-extend-inverted {
  --base-color: $rail_base !important;
  --border-color: $rail_border !important;
  color: $global_text !important;
}
.f-shape, .f-shape::before, .f-shape::after,
.f-shape-rotated, .f-shape-rotated::before, .f-shape-rotated::after,
.extension-patch, .extension-patch-rotated { background-color: $fshape_bg !important; }
.f-shape, .f-shape-rotated { box-shadow: inset 0 0 0 1px $rail_border !important; }
.extension-patch::after, .extension-patch-rotated::after { background-color: $global_bg !important; }

/* Links & brand */
a, .q-link { color: $link_color !important; }
.text-yellowhako, .q-icon.text-yellowhako, .material-symbols-outlined.text-yellowhako {
  color: #ffdd00 !important;
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.25));
}
""")


def generate_custom_css(theme: Dict[str, str]) -> str:
    """Create CSS from a custom theme dict."""
    # Defensive: ensure all required keys exist with sane fallbacks
    defaults = {
        "global_bg": "#0f172a",
        "global_text": "#e5e7eb",
        "drawer_bg": "#0b1220",
        "card_bg": "#111827",
        "border": "#1f2937",
        "zebra_even_bg": "#0e1628",
        "hover_bg": "#162033",
        "table_footer_bg": "#111827",
        "input_bg": "#0f172a",
        "menu_bg": "#111827",
        "rail_base": "#0e1628",
        "rail_border": "#1f2937",
        "fshape_bg": "#1e2b48",
        "number_border": "#334155",
        "link_color": "#1d4ed8",
    }
    values = {**defaults, **{k: v for k, v in theme.items() if isinstance(v, str)}}
    return CUSTOM_TEMPLATE.safe_substitute(**values)


def write_custom_css(theme: Dict[str, str], path: str = "css/theme-custom.css") -> None:
    css = generate_custom_css(theme)
    with open(path, "w", encoding="utf-8") as f:
        f.write(css)
