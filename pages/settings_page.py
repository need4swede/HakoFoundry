from nicegui import ui
import json
import re
import logging
from authentication import require_auth
import globals
import page_layout

@require_auth
def settingsPage():
    """Settings page for chassis layout and powerboard information."""

    # Use a mutable object to store the flag so it can be accessed in nested functions
    state_flags = {'ignoring_change': False}

    # Store UI element references
    ui_refs = {'model_switch': None, 'sn_switch': None}

    # Ensure at least one switch is on during initialization
    if not globals.layoutState.get_model_display() and not globals.layoutState.get_sn_display():
        # If both are off, turn on model display by default
        globals.layoutState.set_model_display(True)

    def change_product(new_product):
        """Change the chassis product and reset layout."""
        globals.layoutState.reset_chassis()
        globals.layoutState.set_product(new_product)

    def change_model_display(value):
        # If turning off model display, ensure SN display is on
        if not value and not globals.layoutState.get_sn_display():
            globals.layoutState.set_sn_display(True)
            # Update the SN switch UI
            if ui_refs['sn_switch']:
                ui_refs['sn_switch'].set_value(True)
        globals.layoutState.set_model_display(value)

    def swap_powerboard_positions():
        """Swap the positions of powerboard 1 and 2 in powerboardDict."""
        pb1 = globals.powerboardDict.get(1)
        pb2 = globals.powerboardDict.get(2)

        if pb1 and pb2:
            # Swap the Powerboard objects in the dictionary
            globals.powerboardDict[1], globals.powerboardDict[2] = globals.powerboardDict[2], globals.powerboardDict[1]

            ui.notify("Powerboard positions swapped!",
                     position='bottom-right', type='positive', group=False)
            # Refresh the powerboard information table
            powerboard_container.clear()
            with powerboard_container:
                create_powerboard_table()
        elif pb1 or pb2:
            ui.notify("Only one powerboard detected, cannot swap.",
                     position='bottom-right', type='warning', group=False)
        else:
            ui.notify("No powerboards detected, cannot swap.",
                     position='bottom-right', type='warning', group=False)

    def change_sn_display(value):
        # If turning off SN display, ensure model display is on
        if not value and not globals.layoutState.get_model_display():
            globals.layoutState.set_model_display(True)
            # Update the model switch UI
            if ui_refs['model_switch']:
                ui_refs['model_switch'].set_value(True)
        globals.layoutState.set_sn_display(value)

    def handle_product_change(e):
        """Handle product selection change."""
        # Ignore programmatic changes
        if state_flags['ignoring_change']:
            return

        current_product = globals.layoutState.get_product()
        new_product = e.value

        # Only show dialog if actually changing to a different product
        if new_product != current_product:
            reset_dialog(new_product)

    def reset_dialog(new_product):
        """Show confirmation dialog when changing chassis layout."""
        def on_no():
            # Set flag to ignore the change event when resetting value
            state_flags['ignoring_change'] = True
            product_select.set_value(globals.layoutState.get_product())
            state_flags['ignoring_change'] = False
            dialog.close()

        with ui.dialog().props('persistent') as dialog, ui.card():
            ui.label('Changing layouts will reset backplanes and drives. Continue?')
            with ui.row().classes('w-full justify-center'):
                ui.button('Yes', on_click=lambda: (change_product(new_product), dialog.close())).classes('border-solid border-2 border-[#ffdd00]').props('flat color="white"')
                ui.button('No', on_click=on_no).classes('border-solid border-2 border-[#ffdd00]').props('flat color="white"')
        dialog.open()

    def get_powerboard_info():
        """Get powerboard information for table display."""
        powerboard_data = []

        for position in [1, 2]:
            if position in globals.powerboardDict:
                pb = globals.powerboardDict[position]
                try:
                    # Get connection port info
                    port = getattr(pb, '_serial_instance', None)
                    port_name = port.port if port and hasattr(port, 'port') else 'Unknown'

                    powerboard_data.append({
                        'port': port_name,
                        'hardware_rev': pb.hardware_revision if hasattr(pb, 'hardware_revision') else 'Unknown',
                        'firmware_ver': pb.firmware_version if hasattr(pb, 'firmware_version') else 'Unknown',
                        'location': pb.location if hasattr(pb, 'location') else 'Unknown'
                    })
                except Exception as e:
                    # Fallback for any errors accessing powerboard properties
                    powerboard_data.append({
                        'port': 'Error',
                        'hardware_rev': 'Error',
                        'firmware_ver': 'Error',
                        'location': 'Error'
                    })

        return powerboard_data

    def create_powerboard_table():
        """Create and return powerboard information table."""
        powerboard_data = get_powerboard_info()

        if not powerboard_data:
            return ui.label('No powerboards detected.').classes('text-gray-500 italic')

        # Define table columns
        columns = [
            {'name': 'port', 'label': 'Serial Port', 'field': 'port', 'required': True, 'align': 'left'},
            {'name': 'hardware_rev', 'label': 'Hardware Rev', 'field': 'hardware_rev', 'required': True, 'align': 'center'},
            {'name': 'firmware_ver', 'label': 'Firmware Ver', 'field': 'firmware_ver', 'required': True, 'align': 'center'},
            {'name': 'location', 'label': 'Location', 'field': 'location', 'required': True, 'align': 'center'}
        ]

        return ui.table(
            columns=columns,
            rows=powerboard_data,
            row_key='location'
        ).classes('w-full')

    def get_pwm_values():
        """Get current saved PWM values from powerboards."""
        pwm_data = {}

        # Get powerboard 1 PWM values
        if 1 in globals.powerboardDict:
            pb1_pwm = globals.powerboardDict[1].get_saved_fan_pwm()
            pwm_data['pb1'] = {
                'row1': pb1_pwm[0],
                'row2': pb1_pwm[1],
                'row3': pb1_pwm[2]
            }

        # Get powerboard 2 PWM values
        if 2 in globals.powerboardDict:
            pb2_pwm = globals.powerboardDict[2].get_saved_fan_pwm()
            pwm_data['pb2'] = {
                'aux': pb2_pwm[2]  # Use third value for auxiliary
            }

        return pwm_data

    def create_pwm_settings():
        """Create PWM settings interface."""
        pwm_data = get_pwm_values()

        if not pwm_data:
            return ui.label('No powerboards detected for PWM settings.').classes('text-gray-500 italic')

        # Store PWM input references
        pwm_inputs = {}

        async def apply_pwm_settings():
            """Apply the PWM settings using fan control service."""
            try:
                # Get values from inputs
                pb1_values = [0, 0, 0]
                pb2_aux = 100

                if 'pb1' in pwm_data:
                    pb1_values[0] = int(pwm_inputs['pb1_row1'].value)
                    pb1_values[1] = int(pwm_inputs['pb1_row2'].value)
                    pb1_values[2] = int(pwm_inputs['pb1_row3'].value)

                if 'pb2' in pwm_data:
                    pb2_aux = int(pwm_inputs['pb2_aux'].value)

                # Use fan control service to set the speeds
                await globals.fan_control_service.set_fan_speed(
                    pb1_values[0], pb1_values[1], pb1_values[2], pb2_aux
                )

                ui.notify("PWM settings applied successfully!",
                         position='bottom-right', type='positive', group=False)

            except Exception as e:
                ui.notify(f"Error applying PWM settings: {str(e)}",
                         position='bottom-right', type='negative', group=False)

        with ui.column().classes('w-full gap-4'):
            # Powerboard 1 settings
            if 'pb1' in pwm_data:
                with ui.card().classes('w-full'):
                    ui.label('Powerboard 1 - Fan Rows').classes('text-lg font-semibold mb-2')
                    with ui.grid(columns=3).classes('gap-4 w-full'):
                        with ui.column().classes('items-center gap-2'):
                            ui.label('Row 1 PWM')
                            pwm_inputs['pb1_row1'] = ui.slider(
                                min=0, max=100, step=1,
                                value=int(pwm_data['pb1']['row1'])
                            ).classes('w-32')
                            ui.label().bind_text_from(pwm_inputs['pb1_row1'], 'value', lambda v: f'{int(v)}%')

                        with ui.column().classes('items-center gap-2'):
                            ui.label('Row 2 PWM')
                            pwm_inputs['pb1_row2'] = ui.slider(
                                min=0, max=100, step=1,
                                value=int(pwm_data['pb1']['row2'])
                            ).classes('w-32')
                            ui.label().bind_text_from(pwm_inputs['pb1_row2'], 'value', lambda v: f'{int(v)}%')

                        with ui.column().classes('items-center gap-2'):
                            ui.label('Row 3 PWM')
                            pwm_inputs['pb1_row3'] = ui.slider(
                                min=0, max=100, step=1,
                                value=int(pwm_data['pb1']['row3'])
                            ).classes('w-32')
                            ui.label().bind_text_from(pwm_inputs['pb1_row3'], 'value', lambda v: f'{int(v)}%')

            # Powerboard 2 settings (show only if exists)
            if 'pb2' in pwm_data:
                with ui.card().classes('w-full'):
                    ui.label('Powerboard 2 - Auxiliary Fans').classes('text-lg font-semibold mb-2')
                    with ui.column().classes('items-center gap-2 w-full'):
                        ui.label('Auxiliary PWM')
                        pwm_inputs['pb2_aux'] = ui.slider(
                            min=0, max=100, step=1,
                            value=int(pwm_data['pb2']['aux'])
                        ).classes('w-64')
                        ui.label().bind_text_from(pwm_inputs['pb2_aux'], 'value', lambda v: f'{int(v)}%')

            # Apply button
            with ui.row().classes('justify-center w-full mt-4'):
                ui.button(
                    'Apply PWM Settings',
                    on_click=apply_pwm_settings
                ).classes('border-solid border-2 border-[#ffdd00] text-white px-6 py-2').props('flat')

    # Main settings UI
    with page_layout.frame('Settings'):
        with ui.element('div').classes('w-full max-w-5xl mx-auto px-4'):
            with ui.card().classes('w-full'):
                ui.label('Settings').classes('text-xl font-bold mb-2')
                with ui.tabs().classes('w-full') as tabs:
                    general_tab = ui.tab('General')
                    themes_tab = ui.tab('Themes')
                    backplanes_tab = ui.tab('Backplanes')
                    powerboard_tab = ui.tab('Powerboard')
                    pwm_tab = ui.tab('PWM')

                with ui.tab_panels(tabs, value=general_tab).classes('w-full'):
                    with ui.tab_panel(general_tab):
                        with ui.grid(columns=2).classes('gap-3 w-full items-center').style('grid-auto-rows: auto;'):
                            ui.label('Chassis Layout:').classes('justify-start items-center')
                            product_select = ui.select(
                                ['Hako-Core', 'Hako-Core Mini'],
                                value=globals.layoutState.get_product(),
                                on_change=handle_product_change
                            )

                            ui.label('Show drive model:')
                            ui_refs['model_switch'] = ui.switch(value=globals.layoutState.get_model_display(), on_change=lambda e: change_model_display(e.value))

                            ui.label('Show drive serial #:')
                            ui_refs['sn_switch'] = ui.switch(value=globals.layoutState.get_sn_display(), on_change=lambda e: change_sn_display(e.value))

                            ui.label('Invert chassis orientation:')
                            orientation_switch = ui.switch(
                                value=globals.layoutState.chassis_is_inverted(),
                                on_change=lambda e: globals.layoutState.set_chassis_inverted(e.value)
                            )
                            orientation_switch.tooltip('Toggle if your chassis is physically mounted inverted')

                            ui.label('Temperature Units:')
                            unit_options = {'Celsius (C°)': 'C', 'Fahrenheit (F°)': 'F'}
                            current_unit = globals.layoutState.get_units()
                            current_display = next((k for k, v in unit_options.items() if v == current_unit), 'Celsius (C°)')
                            ui.select(
                                list(unit_options.keys()),
                                value=current_display,
                                on_change=lambda e: globals.layoutState.set_units(unit_options[e.value])
                            )

                    with ui.tab_panel(themes_tab):
                        # Theme selection + preview actions
                        with ui.row().classes('w-full items-end gap-3'):
                            ui.label('Theme').classes('text-lg font-semibold')
                            theme_map = {
                                'Dark': 'dark', 'Light': 'light', 'Blue': 'blue',
                                'Emerald': 'emerald', 'Purple': 'purple', 'Amber': 'amber', 'Custom': 'custom'
                            }
                            current_theme_display = next((k for k, v in theme_map.items() if v == globals.layoutState.get_theme()), 'Dark')
                            async def _on_theme_change(e):
                                value = theme_map[e.value]
                                globals.layoutState.set_theme(value)
                                # Remove any live preview style when switching away from custom
                                if value != 'custom':
                                    ui.run_javascript("""
                                    (() => { const el = document.getElementById('custom-theme-preview'); if (el) el.remove(); })();
                                    """)
                                else:
                                    # When switching to custom, immediately reflect current builder values in the iframe
                                    try:
                                        await _apply_live_from_current()
                                    except Exception:
                                        pass
                                ui.notify('Theme updated. Reload to apply.', position='bottom-right', type='info', group=False)
                            theme_select = ui.select(list(theme_map.keys()), value=current_theme_display, on_change=_on_theme_change)

                            # Quick preview button for current theme selection
                            def preview_current():
                                ui.notify('Switch to Custom and use Preview for live CSS.', position='bottom-right', type='info', group=False)
                            ui.button('Preview', on_click=preview_current).props('flat')

                        # Custom builder (only when Custom) — reveal immediately without extra expansion
                        with ui.column().bind_visibility_from(globals.layoutState, 'theme', backward=lambda t: t == 'custom').classes('w-full mt-2'):
                            ui.label('Custom Theme Builder').classes('text-md font-semibold mb-1')
                            logger = logging.getLogger('foundry_logger')
                            ct = globals.layoutState.get_custom_theme() or {}
                            # Working copy that event handlers update in real time
                            current = {**ct}
                            current.setdefault('menus_bg', ct.get('menu_bg', ct.get('card_bg', '#1d1d1d')))

                            with ui.grid(columns=2).classes('gap-4 w-full').style('grid-auto-rows: auto;'):
                                with ui.column().classes('gap-2'):
                                    ui.label('Base & Text').classes('text-sm text-gray-400')
                                    dm = ui.switch('Dark base', value=bool(ct.get('dark_mode', True)))
                                    async def _on_dm_change(_):
                                        await _apply_live_from_current()
                                    dm.on('change', _on_dm_change)

                                    def color_picker(label_text, key, default):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.label(label_text).classes('w-44')
                                            val = current.get(key, default)
                                            txt = ui.input(value=val, placeholder='#RRGGBB').classes('w-28')
                                            swatch = ui.input(value=val).props('type=color').classes('w-12')

                                            hex_re = re.compile(r'^#?(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')

                                            async def on_txt_change(e):
                                                v = (txt.value or '').strip()
                                                if not hex_re.match(v):
                                                    return
                                                if not v.startswith('#'):
                                                    v = '#' + v
                                                v = '#' + v[1:].lower()
                                                if len(v) == 4:
                                                    v = '#' + ''.join(ch*2 for ch in v[1:])
                                                swatch.set_value(v)
                                                txt.set_value(v)
                                                current[key] = v
                                                await _apply_live_from_current()

                                            async def on_swatch_change(e):
                                                v = (swatch.value or '').strip()
                                                if not v.startswith('#'):
                                                    v = '#' + v
                                                v = '#' + v[1:].lower()
                                                if len(v) == 4:
                                                    v = '#' + ''.join(ch*2 for ch in v[1:])
                                                txt.set_value(v)
                                                current[key] = v
                                                await _apply_live_from_current()

                                            # Sync both ways on both 'input' (live) and 'change' (finalize)
                                            txt.on('input', on_txt_change)
                                            txt.on('change', on_txt_change)
                                            swatch.on('input', on_swatch_change)
                                            swatch.on('change', on_swatch_change)

                                            def _reset():
                                                txt.set_value(default)
                                                swatch.set_value(default)
                                                current[key] = default
                                                ui.notify(f"Reset '{label_text}'", position='bottom-right', type='info', group=False)
                                            ui.button('Reset', on_click=_reset).props('flat dense size=sm').classes('q-ml-sm')
                                            return txt

                                    inputs = {}
                                    inputs['global_bg'] = color_picker('Background', 'global_bg', '#121212')
                                    inputs['global_text'] = color_picker('Text Color', 'global_text', '#e0e0e0')
                                    inputs['drawer_bg'] = color_picker('Drawer background', 'drawer_bg', '#1b1b1b')
                                    inputs['menus_bg'] = color_picker('Menus background', 'menus_bg', '#1d1d1d')
                                    inputs['border'] = color_picker('Border', 'border', '#2a2a2a')
                                    inputs['input_bg'] = color_picker('Input background', 'input_bg', '#1d1d1d')
                                    # menu_bg comes from unified 'menus_bg' on save

                                with ui.column().classes('gap-2'):
                                    ui.label('Tables & Rails').classes('text-sm text-gray-400')
                                    inputs['zebra_even_bg'] = color_picker('Table zebra (even)', 'zebra_even_bg', '#171717')
                                    inputs['hover_bg'] = color_picker('Hover background', 'hover_bg', '#2a2a2a')
                                    inputs['table_footer_bg'] = color_picker('Table footer bg', 'table_footer_bg', '#1d1d1d')
                                    inputs['rail_base'] = color_picker('Rail base', 'rail_base', '#303030')
                                    inputs['rail_border'] = color_picker('Rail border', 'rail_border', '#2a2a2a')
                                    inputs['fshape_bg'] = color_picker('Backplane (F-shape)', 'fshape_bg', '#232323')
                                    inputs['number_border'] = color_picker('Number border', 'number_border', '#333333')
                                    inputs['link_color'] = color_picker('Link color', 'link_color', '#ffffff')

                            def _collect_theme_data():
                                # Start from our live-updated working copy
                                data = {k: current.get(k, inp.value) for k, inp in inputs.items()}
                                # Validate hex values (#RGB or #RRGGBB)
                                invalid = [k for k, v in data.items() if not isinstance(v, str) or not re.fullmatch(r'#?(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})', (v or ''))]
                                if invalid:
                                    raise ValueError(f"Invalid hex value for: {', '.join(invalid)} (use #RGB or #RRGGBB)")
                                # Normalize to #lowercase
                                for k, v in list(data.items()):
                                    if not v.startswith('#'):
                                        v = '#' + v
                                    v = '#' + v[1:].lower()
                                    if len(v) == 4:
                                        v = '#' + ''.join(ch*2 for ch in v[1:])
                                    data[k] = v
                                # Map unified menus color to both required keys for theme utils
                                if 'menus_bg' in data:
                                    mv = data.pop('menus_bg')
                                    data['card_bg'] = mv
                                    data['menu_bg'] = mv
                                data['dark_mode'] = bool(dm.value)
                                try:
                                    logger.info(f"[ThemeBuilder] Collected theme: {json.dumps(data)}")
                                except Exception:
                                    pass
                                return data

                            def _populate_editor(data: dict):
                                try:
                                    dm.set_value(bool(data.get('dark_mode', True)))
                                    # Set unified menus background from existing theme values
                                    v_menus = data.get('menu_bg', data.get('card_bg'))
                                    if v_menus and 'menus_bg' in inputs:
                                        inputs['menus_bg'].set_value(v_menus)
                                        current['menus_bg'] = v_menus
                                    for k, inp in inputs.items():
                                        if k in data:
                                            inp.set_value(data[k])
                                            current[k] = data[k]
                                except Exception:
                                    pass

                            async def _apply_live_from_current():
                                try:
                                    data = {k: current.get(k, inp.value) for k, inp in inputs.items()}
                                    # Map unified menus to card/menu
                                    if 'menus_bg' in data:
                                        mv = data['menus_bg']
                                        data['card_bg'] = mv
                                        data['menu_bg'] = mv
                                    data['dark_mode'] = bool(dm.value)
                                    from theme_utils import generate_custom_css
                                    css = generate_custom_css(data)
                                    css_json = json.dumps(css)
                                    dark_val = 'true' if data['dark_mode'] else 'false'
                                    # Live apply ONLY inside the preview iframe; do not alter current page
                                    await ui.run_javascript(f"""
                                    (() => {{
                                      const css = {css_json};
                                      const id = 'custom-theme-preview';
                                      const iframe = document.getElementById('theme-preview-iframe');
                                      if (iframe && iframe.contentDocument) {{
                                        let s2 = iframe.contentDocument.getElementById(id);
                                        if (!s2) {{ s2 = iframe.contentDocument.createElement('style'); s2.id = id; iframe.contentDocument.head.appendChild(s2); }}
                                        s2.textContent = css;
                                        try {{ iframe.contentWindow.Quasar.Dark.set({dark_val}); }} catch(e) {{}}
                                      }}
                                    }})();
                                    """)
                                except Exception as _:
                                    pass

                            with ui.row().classes('w-full items-center gap-3 mt-2'):
                                def save_custom_theme():
                                    data = _collect_theme_data()
                                    try:
                                        logger.info("[ThemeBuilder] Saving custom theme...")
                                        globals.layoutState.set_custom_theme(data)
                                        if hasattr(globals.layoutState, 'set_custom_theme_enabled'):
                                            globals.layoutState.set_custom_theme_enabled(True)
                                        from theme_utils import write_custom_css
                                        write_custom_css(data, path='css/theme-custom.css')
                                        logger.info("[ThemeBuilder] Wrote css/theme-custom.css")
                                        ui.notify('Custom theme saved. Select Custom and reload to apply.', position='bottom-right', type='positive', group=False)
                                    except Exception as ex:
                                        ui.notify(f'Failed to save custom theme: {ex}', position='bottom-right', type='negative', group=False)
                                ui.button('Save', on_click=save_custom_theme).props('color=primary')

                                async def set_active():
                                    data = _collect_theme_data()
                                    try:
                                        logger.info("[ThemeBuilder] Set Active with data from builder")
                                        globals.layoutState.set_custom_theme(data)
                                        globals.layoutState.set_theme('custom')
                                        if hasattr(globals.layoutState, 'set_custom_theme_enabled'):
                                            globals.layoutState.set_custom_theme_enabled(True)
                                        from theme_utils import write_custom_css, generate_custom_css
                                        write_custom_css(data, path='css/theme-custom.css')
                                        # Live inject CSS for current session
                                        css = generate_custom_css(data)
                                        css_json = json.dumps(css)
                                        await ui.run_javascript(f"""
                                        (() => {{
                                          const id = 'custom-theme-preview';
                                          let style = document.getElementById(id);
                                          if (!style) {{
                                            style = document.createElement('style');
                                            style.id = id;
                                            document.head.appendChild(style);
                                          }}
                                          style.textContent = {css_json};
                                        }})();
                                        """)
                                        try:
                                            theme_select.set_value('Custom')
                                        except Exception:
                                            pass
                                        ui.notify('Custom theme set active. Reload to persist across sessions.', position='bottom-right', type='positive', group=False)
                                    except Exception as ex:
                                        ui.notify(f'Failed to activate custom theme: {ex}', position='bottom-right', type='negative', group=False)
                                ui.button('Set Active', on_click=set_active)

                                async def preview():
                                    # Apply the current builder theme to the embedded overview iframe
                                    await _apply_live_from_current()
                                    ui.notify('Preview applied in the embedded overview.', position='bottom-right', type='info', group=False)
                                ui.button('Preview', on_click=preview).props('flat')

                            ui.separator().classes('my-2')

                            # Live embedded Overview preview
                            ui.label('Live Overview Preview').classes('text-sm text-gray-400')
                            preview_iframe = ui.element('iframe').props('src=/overview').style('width: 100%; height: 600px; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; background: transparent;').classes('w-full').props('loading=eager').props('id=theme-preview-iframe')

                            async def sync_from_preview():
                                js = """
                                (() => {
                                  const rgbToHex = (c) => {
                                    if (!c) return '';
                                    const m = c.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
                                    if (!m) return '';
                                    const toHex = (n) => ('0'+parseInt(n,10).toString(16)).slice(-2);
                                    return '#' + toHex(m[1]) + toHex(m[2]) + toHex(m[3]);
                                  };
                                  const iframe = document.getElementById('theme-preview-iframe');
                                  if (!iframe || !iframe.contentDocument) return null;
                                  const d = iframe.contentDocument;
                                  const pickBG = (sel) => { const el = d.querySelector(sel); return el ? rgbToHex(getComputedStyle(el).backgroundColor) : ''; };
                                  const pickColor = (sel) => { const el = d.querySelector(sel); return el ? rgbToHex(getComputedStyle(el).color) : ''; };
                                  const pickBorder = (sel) => { const el = d.querySelector(sel); return el ? rgbToHex(getComputedStyle(el).borderTopColor) : ''; };
                                  const pickVar = (sel, v) => { const el = d.querySelector(sel); return el ? (getComputedStyle(el).getPropertyValue(v) || '').trim() : ''; };
                                  const firstNonEmpty = (...vals) => vals.find(v => v && v.length>0) || '';

                                  const global_bg = firstNonEmpty(pickBG('.q-page'), pickBG('body'));
                                  const global_text = firstNonEmpty(pickColor('body'), '#e0e0e0');
                                  const drawer_bg = firstNonEmpty(pickBG('.q-drawer'), '#1b1b1b');
                                  const menus_bg = firstNonEmpty(pickBG('.q-card'), '#1d1d1d');
                                  const border = firstNonEmpty(pickBorder('.q-card'), pickBG('.q-separator'), '#2a2a2a');
                                  const input_bg = firstNonEmpty(pickBG('.q-field__control'), menus_bg);
                                  const zebra_even_bg = firstNonEmpty(pickBG('.q-table tbody tr:nth-child(even) td'), menus_bg);
                                  const hover_bg = firstNonEmpty(pickBG('.q-item:hover'), border, '#2a2a2a');
                                  const table_footer_bg = firstNonEmpty(pickBG('.q-table__bottom'), menus_bg);
                                  const rail_base = firstNonEmpty(pickVar('.pseudo-extend','--base-color'), '#303030');
                                  const rail_border = firstNonEmpty(pickVar('.pseudo-extend','--border-color'), '#252525');
                                  const fshape_bg = firstNonEmpty(pickBG('.f-shape'), '#171717');
                                  const number_border = firstNonEmpty(pickBorder('.number-input'), border);
                                  const link_color = firstNonEmpty(pickColor('.q-page a'), '#1d4ed8');

                                  return JSON.stringify({
                                    global_bg, global_text, drawer_bg,
                                    card_bg: menus_bg, menu_bg: menus_bg,
                                    border, input_bg, zebra_even_bg,
                                    hover_bg, table_footer_bg,
                                    rail_base, rail_border, fshape_bg,
                                    number_border, link_color
                                  });
                                })();
                                """
                                try:
                                    res = await ui.run_javascript(js, timeout=5.0)
                                    if not res:
                                        ui.notify('Could not read colors from preview.', position='bottom-right', type='warning', group=False)
                                        return
                                    data = json.loads(res)
                                    # Populate unified menus from card/menu
                                    if 'card_bg' in data:
                                        m = data['card_bg']
                                        if 'menus_bg' in inputs:
                                            inputs['menus_bg'].set_value(m)
                                            current['menus_bg'] = m
                                    # Update all matching inputs and current working copy
                                    for k, v in data.items():
                                        if k in inputs:
                                            inputs[k].set_value(v)
                                        current[k] = v
                                    await _apply_live_from_current()
                                    ui.notify('Captured colors from preview.', position='bottom-right', type='positive', group=False)
                                except Exception as ex:
                                    ui.notify(f'Preview capture failed: {ex}', position='bottom-right', type='negative', group=False)

                            with ui.row().classes('w-full justify-end my-2'):
                                ui.button('Use colors from preview', on_click=sync_from_preview).props('flat')

                            # One-time seed of builder fields from the default (unset) dark theme
                            # Only runs if active theme is plain 'dark' to avoid capturing overlay colors
                            seeded_in_session = {'done': False}

                            async def _seed_from_unset_dark():
                                if seeded_in_session['done']:
                                    return
                                try:
                                    theme_name = getattr(globals.layoutState, 'get_theme', lambda: 'dark')()
                                    if theme_name == 'dark':
                                        await sync_from_preview()  # populate inputs/current only; no persistence
                                        seeded_in_session['done'] = True
                                except Exception:
                                    # Best-effort: ignore if iframe not ready yet
                                    pass

                            # Give the iframe a moment to load before capturing
                            ui.timer(1.0, _seed_from_unset_dark, once=True)

                            # If the active theme is already custom, reflect it in the iframe once it loads
                            async def _ensure_preview_matches_current_theme():
                                try:
                                    theme_name = getattr(globals.layoutState, 'get_theme', lambda: 'dark')()
                                    if theme_name == 'custom':
                                        await _apply_live_from_current()
                                except Exception:
                                    pass

                            ui.timer(1.0, _ensure_preview_matches_current_theme, once=True)

                            with ui.row().classes('w-full items-center gap-3'):
                                name_input = ui.input(placeholder='Theme name').classes('w-60')
                                saved_select = ui.select(options=globals.layoutState.list_themes(), value=None, label='Saved themes').classes('w-60')

                                def refresh_saved_options():
                                    saved_select.set_options(globals.layoutState.list_themes())

                                def save_as_named():
                                    name = (name_input.value or '').strip()
                                    if not name:
                                        return ui.notify('Please enter a theme name', position='bottom-right', type='warning', group=False)
                                    data = _collect_theme_data()
                                    try:
                                        logger.info(f"[ThemeBuilder] Save As named theme '{name}'")
                                        globals.layoutState.save_named_theme(name, data)
                                        refresh_saved_options()
                                        saved_select.set_value(name)
                                        ui.notify(f"Saved theme '{name}'", position='bottom-right', type='positive', group=False)
                                    except Exception as ex:
                                        ui.notify(f'Failed to save theme: {ex}', position='bottom-right', type='negative', group=False)

                                async def load_selected():
                                    name = saved_select.value
                                    if not name:
                                        return ui.notify('Select a saved theme', position='bottom-right', type='info', group=False)
                                    data = globals.layoutState.get_named_theme(name)
                                    if not data:
                                        return ui.notify('Theme not found', position='bottom-right', type='negative', group=False)
                                    _populate_editor(data)
                                    try:
                                        logger.info(f"[ThemeBuilder] Loaded named theme '{name}' into editor")
                                    except Exception:
                                        pass
                                    ui.notify(f"Loaded '{name}' into editor", position='bottom-right', type='info', group=False)
                                    # Ensure the iframe reflects what we just loaded
                                    try:
                                        await _apply_live_from_current()
                                    except Exception:
                                        pass

                                def delete_selected():
                                    name = saved_select.value
                                    if not name:
                                        return ui.notify('Select a theme to delete', position='bottom-right', type='warning', group=False)
                                    try:
                                        globals.layoutState.delete_named_theme(name)
                                        refresh_saved_options()
                                        saved_select.set_value(None)
                                        ui.notify(f"Deleted theme '{name}'", position='bottom-right', type='positive', group=False)
                                    except Exception as ex:
                                        ui.notify(f'Failed to delete theme: {ex}', position='bottom-right', type='negative', group=False)

                                def export_selected():
                                    name = saved_select.value
                                    if not name:
                                        return ui.notify('Select a theme to export', position='bottom-right', type='warning', group=False)
                                    data = globals.layoutState.get_named_theme(name)
                                    if not data:
                                        return ui.notify('Theme not found', position='bottom-right', type='negative', group=False)
                                    payload = json.dumps({"name": name, "theme": data}, indent=2)
                                    ui.download(payload, filename=f"{name}.json")

                                def on_import(e):
                                    try:
                                        content = e.content.read().decode('utf-8')
                                        obj = json.loads(content)
                                        name = obj.get('name') if isinstance(obj, dict) else None
                                        data = obj.get('theme') if isinstance(obj, dict) and 'theme' in obj else obj
                                        if not isinstance(data, dict):
                                            raise ValueError('Invalid theme file')
                                        if not name:
                                            name = f"Imported Theme {len(globals.layoutState.list_themes())+1}"
                                        globals.layoutState.save_named_theme(name, data)
                                        refresh_saved_options()
                                        saved_select.set_value(name)
                                        ui.notify(f"Imported theme '{name}'", position='bottom-right', type='positive', group=False)
                                    except Exception as ex:
                                        ui.notify(f'Import failed: {ex}', position='bottom-right', type='negative', group=False)

                                ui.button('Save As', on_click=save_as_named)
                                ui.button('Load to Editor', on_click=load_selected)
                                ui.button('Delete', on_click=delete_selected)
                                ui.button('Export', on_click=export_selected)
                                ui.upload(on_upload=on_import).props('accept=.json').classes('')

                    with ui.tab_panel(backplanes_tab):
                        ui.label('Backplanes').classes('text-lg font-semibold mb-2')
                        with ui.row().classes('w-full items-center gap-3'):
                            def clear_all_backplanes():
                                def on_confirm():
                                    globals.layoutState.clear_all_backplanes()
                                    ui.notify("All backplanes cleared successfully!", position='bottom-right', type='positive', group=False)
                                    confirm_dialog.close()
                                def on_cancel():
                                    confirm_dialog.close()
                                with ui.dialog().props('persistent') as confirm_dialog, ui.card().classes('p-6'):
                                    ui.label('Clear All Backplanes?').classes('text-xl font-bold mb-4')
                                    ui.label('This will remove all backplanes and their drive assignments. This action cannot be undone.').classes('text-sm text-gray-400 mb-4')
                                    with ui.row().classes('w-full justify-center gap-4'):
                                        ui.button('Yes, Clear All', on_click=on_confirm).classes('border-solid border-2 border-red-500 text-red-500 px-6 py-2').props('flat')
                                        ui.button('Cancel', on_click=on_cancel).classes('border-solid border-2 border-[#ffdd00] text-white px-6 py-2').props('flat')
                                confirm_dialog.open()
                            ui.button('Clear All Backplanes', on_click=clear_all_backplanes, icon='delete_sweep').classes('bg-red-500 text-white px-6 py-2').props('flat')
                            ui.label('Remove all backplanes and drive assignments').classes('text-xs text-gray-500 self-center')

                    with ui.tab_panel(powerboard_tab):
                        ui.label('Powerboard Information').classes('text-lg font-semibold mb-2')
                        with ui.column().classes('w-full') as powerboard_container:
                            create_powerboard_table()
                        if 2 in globals.powerboardDict:
                            with ui.row().classes('w-full items-center gap-2 mt-2'):
                                ui.label('Swap powerboard positions:')
                                ui_refs['pb_swap_switch'] = ui.switch(value=globals.layoutState.get_pb_swap(), on_change=lambda e: (globals.layoutState.set_pb_swap(e.value), swap_powerboard_positions()))

                    with ui.tab_panel(pwm_tab):
                        ui.label('Default Fan Speed').classes('text-lg font-semibold mb-2')
                        ui.label('These will be used when the system starts and persist between power cycles.').classes('text-sm text-gray-500 mb-2')
                        create_pwm_settings()

            ui.space().classes('h-2')
