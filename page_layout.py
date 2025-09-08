from contextlib import contextmanager
from nicegui import ui, app
import globals
import authentication
import os
import logging
from theme_utils import write_custom_css, generate_custom_css
import time
""" The main layout for every page. Left drawer mainly."""
@contextmanager
def frame(navtitle: str):

    def toggleLeftDrawer():
        left_drawer.props.update(mini=not left_drawer.props.get('mini'))
        left_drawer.update()

    # Set up static file serving for CSS
    app.add_static_files('/css', 'css')

    # Add CSS file reference for layout styles
    ui.add_head_html('<link rel="stylesheet" type="text/css" href="/css/layout.css">')

    # Conditionally add light theme overrides on top of existing styles
    try:
        if globals.layoutState and getattr(globals.layoutState, 'get_theme', None):
            theme = globals.layoutState.get_theme()
            logging.getLogger('foundry_logger').info(f"[Layout] Applying theme: {theme}")
            if theme == 'light':
                # Disable Quasar dark mode and apply our light overrides
                ui.dark_mode().disable()
                ui.add_head_html('<link rel="stylesheet" type="text/css" href="/css/theme-light.css">')
            elif theme == 'blue':
                # Ensure dark mode base and apply modern slate overrides
                ui.dark_mode().enable()
                ui.add_head_html('<link rel="stylesheet" type="text/css" href="/css/theme-blue.css">')
            elif theme == 'emerald':
                ui.dark_mode().enable()
                ui.add_head_html('<link rel="stylesheet" type="text/css" href="/css/theme-emerald.css">')
            elif theme == 'purple':
                ui.dark_mode().enable()
                ui.add_head_html('<link rel="stylesheet" type="text/css" href="/css/theme-purple.css">')
            elif theme == 'amber':
                ui.dark_mode().enable()
                ui.add_head_html('<link rel="stylesheet" type="text/css" href="/css/theme-amber.css">')
            elif theme == 'custom':
                # Load custom theme; only inject CSS if explicitly enabled
                ct = getattr(globals.layoutState, 'get_custom_theme', lambda: {})() or {}
                logging.getLogger('foundry_logger').info(f"[Layout] Custom theme settings: {ct}")
                dark_mode = bool(ct.get('dark_mode', True))
                if dark_mode:
                    ui.dark_mode().enable()
                else:
                    ui.dark_mode().disable()
                if getattr(globals.layoutState, 'is_custom_theme_enabled', lambda: False)():
                    try:
                        os.makedirs('css', exist_ok=True)
                        write_custom_css(ct, path='css/theme-custom.css')
                        logging.getLogger('foundry_logger').info("[Layout] Wrote css/theme-custom.css")
                    except Exception:
                        # Fallback: inject as <style> if writing fails
                        css = generate_custom_css(ct)
                        ui.add_head_html(f'<style>{css}</style>')
                        logging.getLogger('foundry_logger').warning("[Layout] Failed to write theme-custom.css, injected <style> fallback")
                    else:
                        # Cache-bust to ensure latest edits load
                        try:
                            v = int(os.path.getmtime('css/theme-custom.css'))
                        except Exception:
                            v = int(time.time())
                        ui.add_head_html(f'<link rel="stylesheet" type="text/css" href="/css/theme-custom.css?v={v}">')
                        logging.getLogger('foundry_logger').info(f"[Layout] Injected theme-custom.css?v={v}")
    except Exception:
        # Fail silently if theme is unavailable
        pass

    # Initializing defaults
    ui.icon.default_props('color=yellowhako')
    ui.item_label.default_style('color:white')
    ui.separator.default_props('dark')

    # LEFT
    with ui.left_drawer(bordered=True, top_corner=True).props('mini mini-to-overlay width="300" breakpoint="0"').style('background-color: #1b1b1b; height: 100vh; display: flex; flex-direction: column;').classes('w-full px-0 p-0').on('mouseenter', lambda: toggleLeftDrawer()).on('mouseleave', lambda: toggleLeftDrawer()) as left_drawer:
        with ui.list().classes('w-full px-0 p-0').style('flex: 1; display: flex; flex-direction: column;'):
            with ui.item():
                with ui.item_section().props('avatar'):
                    ui.image('res/Hako_Logo.png').classes('w-6')
                with ui.item_section():
                    ui.item_label('HAKOFORGE FOUNDRY').classes('text-nowrap')

            ui.separator()

            with ui.item().props('clickable v-ripple').on_click(lambda: ui.navigate.to('/overview')):
                with ui.item_section().props('avatar'):
                    ui.icon('storage').classes('material-symbols-outlined')
                with ui.item_section():
                    ui.item_label('System Overview').classes('text-nowrap')


            with ui.item().props('clickable v-ripple').on_click(lambda: ui.navigate.to('/curves')):
                with ui.item_section().props('avatar'):
                    ui.icon('timeline').classes('material-symbols-outlined')
                with ui.item_section():
                    ui.item_label('Fan Curves').classes('text-nowrap')
            ui.separator()

            with ui.item().props('clickable').on_click(lambda: ui.navigate.to('/settings')):
                with ui.item_section().props('avatar'):
                    ui.icon('settings').classes('material-symbols-outlined')
                with ui.item_section():
                    ui.item_label('Settings').classes('text-nowrap')

            with ui.item().props('clickable').on_click(lambda: ui.navigate.to('https://docs.hakoforge.com/', new_tab=True)):
                with ui.item_section().props('avatar'):
                    ui.icon('help').classes('material-symbols-outlined')
                with ui.item_section():
                    ui.item_label('Support').classes('text-nowrap')

            # Spacer to push user info to bottom
            ui.space()

            ui.separator()
            if authentication.get_current_user() == 'Guest':
                with ui.item().props('clickable v-ripple'):
                    with ui.item_section().props('avatar'):
                        ui.icon('person').classes('material-symbols-outlined')
                    with ui.item_section():
                        ui.item_label(f'{authentication.get_current_user()}').classes('text-nowrap')
            else:
                with ui.item().props('clickable v-ripple').on_click(lambda: (authentication.logout_session(), ui.navigate.to('/'))):
                    with ui.item_section().props('avatar'):
                        ui.icon('person').classes('material-symbols-outlined')
                    with ui.item_section():
                        ui.item_label(f'Log Out {authentication.get_current_user()}').classes('text-nowrap')

    yield
