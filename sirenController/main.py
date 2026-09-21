import os
import sys
from pathlib import Path
import customtkinter as ctk
from playwright.sync_api import sync_playwright

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# 1. Locate files in local directory
folder = Path(__file__).parent.resolve()
target_file = folder / "index.html"
cd_logo_path = folder / "cd.png"

if not target_file.is_file():
    html_files = list(folder.glob("*.html"))
    if html_files:
        target_file = html_files[0]
    else:
        print(f"Error: No HTML file found in {folder}")
        sys.exit(1)

html_uri = target_file.as_uri()

# 2. Launch Playwright
p = sync_playwright().start()
# On most machines Playwright uses its own bundled Chromium. On ARM boards
# like the Raspberry Pi, Microsoft doesn't publish a prebuilt Chromium for
# Playwright, so install_dependencies.sh falls back to the Pi's system
# Chromium and points us at it via this environment variable.
system_chromium = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH") or None
browser = p.chromium.launch(headless=False, executable_path=system_chromium)
page = browser.new_page()

# The page shows a chain of startup popups the first time it loads in a
# fresh browser profile (Keep Effects On?, an update notice, a reset
# suggestion, then an audio tip after the first TEST press). Each one is
# normally dismissed permanently by its own "Don't show this again"
# checkbox, which just writes a flag to localStorage - so we write those
# same flags ourselves, before the page's scripts run, and every one of
# them is skipped. Since Playwright launches a fresh, throwaway browser
# profile each run, this has to happen on every launch, not just once.
# This only skips the prompts - it doesn't change what they'd have set
# (effects stay on, the default/recommended choice).
page.add_init_script("""
    try {
        localStorage.setItem('sirenosc_intro_seen', '1');
        localStorage.setItem('sirenosc_update_132_seen', '1');
        localStorage.setItem('sirenosc_reset_sug_132_seen', '1');
        localStorage.setItem('sirenosc_audio_tip_enabled', '0');
        var settings = JSON.parse(localStorage.getItem('sirenosc_ui_settings') || '{}');
        settings.startupPopups = false;
        settings.updateNotice132 = false;
        settings.resetSuggestion132 = false;
        settings.audioTipPopup = false;
        localStorage.setItem('sirenosc_ui_settings', JSON.stringify(settings));
    } catch (e) {}
""")

page.goto(html_uri)

# The page (SirenOsc) has stable element IDs for the real control buttons.
# Note the site's own typo: the brake button's id is "btnBreak", not "btnBrake".
SIREN_BUTTON_IDS = {
    'test': 'btnTest',
    'steady': 'btnSteady',
    'custom': 'btnCustom',
    'brake': 'btnBreak',
    'cancel': 'btnCancel',
}

def trigger_siren_action(action_name, state='press'):
    """
    Clicks (or presses/releases) the real siren control button on the page,
    targeted by its element id rather than by searching button text.

    Why by id: several buttons elsewhere on the page (reset/import/save
    dialogs) also render the text "CANCEL". A text search finds whichever
    one appears first in the page's HTML, which is one of those hidden
    dialog buttons rather than the actual btnCancel control - that's why
    CANCEL never did anything. Targeting the id sidesteps that entirely.

    TEST is the only "hold" control - the page listens for real
    mousedown/mouseup events on it. STEADY, CUSTOM, BRAKE and CANCEL are
    plain toggle buttons that respond to a single click, so they only
    need to act on 'press' and can ignore 'release'.
    """
    elem_id = SIREN_BUTTON_IDS.get(action_name.lower())
    if not elem_id:
        print(f"Unknown siren action: {action_name}")
        return

    try:
        button = page.locator(f"#{elem_id}")
        if action_name.lower() == 'test':
            if state == 'press':
                button.dispatch_event('mousedown')
            elif state == 'release':
                button.dispatch_event('mouseup')
        elif state == 'press':
            button.click()
    except Exception as e:
        print(f"Error triggering {action_name} ({state}): {e}")

# State tracking for indicator lights
steady_active = False
custom_active = False

# Button Handlers
def on_test_press(e=None): 
    light_amber.configure(fg_color="#FFB300")
    trigger_siren_action('test', 'press')

def on_test_release(e=None): 
    if not steady_active and not custom_active:
        light_amber.configure(fg_color="#553C00")
    trigger_siren_action('test', 'release')

def on_steady_click(): 
    global steady_active
    steady_active = True
    light_red.configure(fg_color="#FF1744")
    trigger_siren_action('steady', 'press')

def on_custom_click(): 
    global custom_active
    custom_active = True
    light_amber.configure(fg_color="#FFB300")
    trigger_siren_action('custom', 'press')

def on_cancel_click(): 
    global steady_active, custom_active
    steady_active = False
    custom_active = False
    light_amber.configure(fg_color="#553C00")
    light_red.configure(fg_color="#4A000B")
    
    # Exact same single-click execution as STEADY, CUSTOM, and BRAKE
    trigger_siren_action('cancel', 'press')

def on_brake_click():
    # BRAKE cancels STEADY/CUSTOM on the page too (see the site's own
    # btnBreak handler), so the indicator lights need to reset the same
    # way they do for CANCEL, or they'd go stale.
    global steady_active, custom_active
    steady_active = False
    custom_active = False
    light_amber.configure(fg_color="#553C00")
    light_red.configure(fg_color="#4A000B")
    trigger_siren_action('brake', 'press')

# --- GUI Setup ---
ctk.set_appearance_mode("Dark")

app = ctk.CTk()
app.title("WARNING SIGNAL CONTROL - MODEL AF")
app.geometry("520x480")
app.minsize(520, 480)
app.resizable(True, True)

cabinet = ctk.CTkFrame(app, fg_color="#DCA122", corner_radius=0)
cabinet.pack(fill="both", expand=True, padx=10, pady=10)

header_frame = ctk.CTkFrame(cabinet, fg_color="transparent")
header_frame.pack(pady=(15, 5))

if HAS_PIL and cd_logo_path.is_file():
    pil_img = Image.open(cd_logo_path)
    cd_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(90, 90))
    cd_badge = ctk.CTkLabel(header_frame, image=cd_image, text="")
else:
    cd_badge = ctk.CTkLabel(
        header_frame, 
        text="CD", 
        font=("Arial Black", 32, "bold"), 
        text_color="#C62828",
        fg_color="#1565C0",
        corner_radius=45,
        width=90,
        height=90
    )
cd_badge.pack()

lights_frame = ctk.CTkFrame(cabinet, fg_color="transparent")
lights_frame.pack(pady=10)

light_amber = ctk.CTkLabel(lights_frame, text="", width=18, height=18, corner_radius=9, fg_color="#553C00")
light_amber.pack(side="left", padx=20)

light_red = ctk.CTkLabel(lights_frame, text="", width=18, height=18, corner_radius=9, fg_color="#4A000B")
light_red.pack(side="left", padx=20)

panel = ctk.CTkFrame(cabinet, fg_color="#A81C1C", corner_radius=4, border_width=2, border_color="#D3D3D3")
panel.pack(fill="x", padx=20, pady=(10, 20))

title_label = ctk.CTkLabel(panel, text="WARNING SIGNAL CONTROL", font=("Impact", 22), text_color="#FFFFFF")
title_label.pack(pady=(12, 0))

sub_label = ctk.CTkLabel(panel, text="MODEL AF SERIES AII — OPEN SIREN SYNTHESIZER", font=("Arial", 9, "bold"), text_color="#E0E0E0")
sub_label.pack(pady=(0, 15))

btn_grid = ctk.CTkFrame(panel, fg_color="transparent")
btn_grid.pack(pady=(0, 15), padx=10)

press_event = "<ButtonPress-1>"
release_event = "<ButtonRelease-1>"

def create_panel_button(parent, text, col, press_cmd, release_cmd=None, btn_color="#2B2B2B", hover_color="#404040"):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.grid(row=0, column=col, padx=6)

    lbl = ctk.CTkLabel(frame, text=text, font=("Arial", 11, "bold"), text_color="#FFFFFF")
    lbl.pack(pady=(0, 5))

    btn = ctk.CTkButton(
        frame, 
        text="", 
        width=58, 
        height=58, 
        corner_radius=29,
        fg_color=btn_color,
        hover_color=hover_color,
        border_width=4,
        border_color="#C0C0C0"
    )
    btn.pack()

    if release_cmd:
        btn.bind(press_event, press_cmd)
        btn.bind(release_event, release_cmd)
    else:
        btn.configure(command=press_cmd)

    return btn

create_panel_button(btn_grid, "TEST", 0, on_test_press, on_test_release, "#3E3E3E", "#555555")
create_panel_button(btn_grid, "STEADY", 1, on_steady_click, None, "#1565C0", "#1E88E5")
create_panel_button(btn_grid, "CUSTOM", 2, on_custom_click, None, "#D84315", "#F4511E")
create_panel_button(btn_grid, "BRAKE", 3, on_brake_click, None, "#F9A825", "#FBC02D")
create_panel_button(btn_grid, "CANCEL", 4, on_cancel_click, None, "#212121", "#37474F")

def on_closing():
    browser.close()
    p.stop()
    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing)
app.mainloop()