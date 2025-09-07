from nicegui import ui
import json
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
        with ui.element('div').classes('flex w-full').style('justify-content: safe center;'):
            with ui.card():
                # Chassis Layout Section
                ui.label('Chassis Configuration').classes('text-xl font-bold mb-4')
                with ui.grid(columns=2).classes('gap-0 w-full').style('grid-auto-rows: auto;'):
                    ui.label('Chassis Layout:').classes('flex justify-start items-center')
                    product_select = ui.select(
                        ['Hako-Core', 'Hako-Core Mini'],
                        value=globals.layoutState.get_product(),
                        on_change=handle_product_change
                    )

                    ui.label('Show drive model:').classes('flex justify-start items-center ')
                    ui_refs['model_switch'] = ui.switch(value=globals.layoutState.get_model_display(), on_change=lambda e: change_model_display(e.value)).style('justify-content:end;')

                    ui.label('Show drive serial #:').classes('flex justify-start items-center')
                    ui_refs['sn_switch'] = ui.switch(value=globals.layoutState.get_sn_display(), on_change=lambda e: change_sn_display(e.value)).style('justify-content:end;')

                    ui.label('Invert chassis orientation:').classes('flex justify-start items-center')
                    orientation_switch = ui.switch(
                        value=globals.layoutState.chassis_is_inverted(),
                        on_change=lambda e: globals.layoutState.set_chassis_inverted(e.value)
                    ).style('justify-content:end;')
                    orientation_switch.tooltip('Toggle if your chassis is physically mounted inverted')

                    ui.label('Temperature Units:').classes('flex justify-start items-center')
                    # Map display names to backend values
                    unit_options = {'Celsius (C°)': 'C', 'Fahrenheit (F°)': 'F'}
                    current_unit = globals.layoutState.get_units()
                    # Find the display name for the current value
                    current_display = next((k for k, v in unit_options.items() if v == current_unit), 'Celsius (C°)')

                    ui.select(
                        list(unit_options.keys()),
                        value=current_display,
                        on_change=lambda e: globals.layoutState.set_units(unit_options[e.value])
                    ).style('justify-content:end;')

                    # Theme selection
                    ui.label('Theme:').classes('flex justify-start items-center')
                    theme_map = {
                        'Dark': 'dark',
                        'Light': 'light',
                        'Blue': 'blue',
                        'Emerald': 'emerald',
                        'Purple': 'purple',
                        'Amber': 'amber',
                        'Custom': 'custom',
                    }
                    current_theme_display = next((k for k, v in theme_map.items() if v == globals.layoutState.get_theme()), 'Dark')
                    def _on_theme_change(e):
                        globals.layoutState.set_theme(theme_map[e.value])
                        ui.notify('Theme updated. Reload to apply.', position='bottom-right', type='info', group=False)

                    ui.select(
                        list(theme_map.keys()),
                        value=current_theme_display,
                        on_change=_on_theme_change
                    ).style('justify-content:end;')

                    # Custom theme editor - shown when 'Custom' is selected
                    def show_custom_editor():
                        return globals.layoutState.get_theme() == 'custom'

                    with ui.expansion('Custom Theme Builder').bind_visibility_from(globals.layoutState, 'theme', backward=lambda t: t == 'custom').props('dense').classes('w-full mt-2').style('grid-column: 1 / -1;'):
                        ct = globals.layoutState.get_custom_theme() or {}

                        def color_row(label_text, key, default):
                            with ui.row().classes('w-full items-center'):
                                ui.label(label_text).classes('w-48 text-right pr-2')
                                val = ct.get(key, default)
                                i = ui.input(value=val).props('type=color').classes('w-24')
                                return i

                        # Dark mode toggle for custom theme
                        dm = ui.switch('Dark base', value=bool(ct.get('dark_mode', True)))

                        inputs = {}
                        inputs['global_bg'] = color_row('Global background', 'global_bg', '#0f172a')
                        inputs['global_text'] = color_row('Global text', 'global_text', '#e5e7eb')
                        inputs['drawer_bg'] = color_row('Drawer background', 'drawer_bg', '#0b1220')
                        inputs['card_bg'] = color_row('Card background', 'card_bg', '#111827')
                        inputs['border'] = color_row('Border', 'border', '#1f2937')
                        inputs['zebra_even_bg'] = color_row('Table zebra (even)', 'zebra_even_bg', '#0e1628')
                        inputs['hover_bg'] = color_row('Hover background', 'hover_bg', '#162033')
                        inputs['table_footer_bg'] = color_row('Table footer bg', 'table_footer_bg', '#111827')
                        inputs['input_bg'] = color_row('Input background', 'input_bg', '#0f172a')
                        inputs['menu_bg'] = color_row('Menu/dialog background', 'menu_bg', '#111827')
                        inputs['rail_base'] = color_row('Rail base', 'rail_base', '#0e1628')
                        inputs['rail_border'] = color_row('Rail border', 'rail_border', '#1f2937')
                        inputs['fshape_bg'] = color_row('Backplane (F-shape)', 'fshape_bg', '#1e2b48')
                        inputs['number_border'] = color_row('Number border', 'number_border', '#334155')
                        inputs['link_color'] = color_row('Link color', 'link_color', '#1d4ed8')

                        def _collect_theme_data():
                            data = {k: inp.value for k, inp in inputs.items()}
                            data['dark_mode'] = bool(dm.value)
                            return data

                        def _populate_editor(data: dict):
                            try:
                                dm.set_value(bool(data.get('dark_mode', True)))
                                for k, inp in inputs.items():
                                    if k in data:
                                        inp.set_value(data[k])
                            except Exception:
                                pass

                        def save_custom_theme():
                            data = _collect_theme_data()
                            try:
                                globals.layoutState.set_custom_theme(data)
                                # Also write a css file for static serving
                                from theme_utils import write_custom_css
                                write_custom_css(data, path='css/theme-custom.css')
                                ui.notify('Custom theme saved. Select Custom and reload to apply.', position='bottom-right', type='positive', group=False)
                            except Exception as ex:
                                ui.notify(f'Failed to save custom theme: {ex}', position='bottom-right', type='negative', group=False)

                        with ui.row().classes('w-full items-center gap-3 mt-3'):
                            ui.button('Save Custom Theme', on_click=save_custom_theme).props('color=primary')
                            def set_active():
                                data = _collect_theme_data()
                                try:
                                    globals.layoutState.set_custom_theme(data)
                                    globals.layoutState.set_theme('custom')
                                    from theme_utils import write_custom_css
                                    write_custom_css(data, path='css/theme-custom.css')
                                    ui.notify('Custom theme set active. Reload to apply.', position='bottom-right', type='positive', group=False)
                                except Exception as ex:
                                    ui.notify(f'Failed to activate custom theme: {ex}', position='bottom-right', type='negative', group=False)
                            ui.button('Set as Active Theme', on_click=set_active)
                            def preview():
                                data = _collect_theme_data()
                                from theme_utils import generate_custom_css
                                css = generate_custom_css(data)
                                # Add a style tag to preview without reload; latest added wins in cascade
                                ui.add_head_html(f'<style id="custom-theme-preview">{css}</style>')
                                ui.notify('Preview applied (not persisted).', position='bottom-right', type='info', group=False)
                            ui.button('Preview', on_click=preview).props('flat')

                        ui.separator().classes('my-2')

                        # Named themes management
                        with ui.row().classes('w-full items-center gap-3'):
                            name_input = ui.input(placeholder='Theme name').classes('w-60')
                            saved_select = ui.select(options=globals.layoutState.list_themes(), value=None, label='Saved themes').classes('w-60')

                            def refresh_saved_options():
                                saved_select.set_options(globals.layoutState.list_themes())

                            def save_as_named():
                                name = (name_input.value or '').strip()
                                if not name:
                                    ui.notify('Please enter a theme name', position='bottom-right', type='warning', group=False)
                                    return
                                data = _collect_theme_data()
                                try:
                                    globals.layoutState.save_named_theme(name, data)
                                    refresh_saved_options()
                                    saved_select.set_value(name)
                                    ui.notify(f"Saved theme '{name}'", position='bottom-right', type='positive', group=False)
                                except Exception as ex:
                                    ui.notify(f'Failed to save theme: {ex}', position='bottom-right', type='negative', group=False)

                            def load_selected():
                                name = saved_select.value
                                if not name:
                                    ui.notify('Select a saved theme', position='bottom-right', type='info', group=False)
                                    return
                                data = globals.layoutState.get_named_theme(name)
                                if not data:
                                    ui.notify('Theme not found', position='bottom-right', type='negative', group=False)
                                    return
                                _populate_editor(data)
                                ui.notify(f"Loaded '{name}' into editor", position='bottom-right', type='info', group=False)

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
                                    # Support either {name, theme} or just theme dict
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

                ui.separator().classes('my-4')

                # Clear All Backplanes Section
                with ui.row().classes('w-full justify-center'):
                    def clear_all_backplanes():
                        """Clear all backplanes with confirmation dialog."""
                        def on_confirm():
                            globals.layoutState.clear_all_backplanes()
                            ui.notify("All backplanes cleared successfully!",
                                     position='bottom-right', type='positive', group=False)
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

                    ui.button(
                        'Clear All Backplanes',
                        on_click=clear_all_backplanes,
                        icon='delete_sweep'
                    ).classes('bg-red-500 text-white px-6 py-2').props('flat')
                    ui.label('Remove all backplanes and drive assignments').classes('text-xs text-gray-500 ml-2 self-center')

                ui.separator().classes('mb-6')

                # Powerboard Information Section
                with ui.column().classes('w-full') as powerboard_container:
                    ui.label('Powerboard Information').classes('text-xl font-bold mb-4')
                    create_powerboard_table()
                if 2 in globals.powerboardDict:
                    with ui.row().classes('w-full justify-center'):
                        ui.label('Swap powerboard positions:').classes('flex justify-start items-center ')
                        ui_refs['pb_swap_switch'] = ui.switch(value=globals.layoutState.get_pb_swap(), on_change=lambda e: (globals.layoutState.set_pb_swap(e.value), swap_powerboard_positions())).style('justify-content:end;')


                ui.separator().classes('mb-6')

                # PWM Settings Section
                with ui.column().classes('w-full') as pwm_container:
                    ui.label('Default Fan Speed').classes('text-xl font-bold mb-4')
                    ui.label('These will be used when the system starts and persist between power cycles.').classes('text-sm text-gray-500 mb-2')
                    create_pwm_settings()

                # Additional spacing
                ui.space().classes('h-2')
