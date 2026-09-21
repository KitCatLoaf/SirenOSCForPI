#!/usr/bin/env bash
# Installs everything main.py needs to run:
#   - customtkinter  (the control panel GUI)
#   - playwright     (drives the browser showing index.html)
#   - Pillow         (optional - only used to show cd.png as the badge image;
#                      the script falls back to a plain "CD" badge without it)
# and a Chromium browser for Playwright to drive.

set -e  # stop on the first error instead of limping on with a broken install

echo "== Checking for Python 3 and pip =="
if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. Install Python 3 first (e.g. from python.org), then re-run this script."
    exit 1
fi

PYTHON=python3
PIP="$PYTHON -m pip"

# customtkinter is built on top of Tkinter, which on Linux/Raspberry Pi OS
# has to come from the system package manager - pip can't install it.
if command -v apt-get >/dev/null 2>&1; then
    echo "== Installing system packages (python3-tk) =="
    sudo apt-get update
    sudo apt-get install -y python3-tk
fi

echo "== Upgrading pip =="
$PIP install --upgrade pip

echo "== Installing Python packages =="
$PIP install customtkinter playwright Pillow

echo "== Installing a Chromium browser for Playwright =="
if $PYTHON -m playwright install chromium; then
    echo "Playwright's own Chromium installed successfully."
else
    echo
    echo "Playwright couldn't download its own Chromium build. This is expected"
    echo "on ARM boards like the Raspberry Pi - Microsoft doesn't publish"
    echo "prebuilt Chromium binaries for ARM. Falling back to the system's"
    echo "Chromium package instead."
    echo

    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get install -y chromium-browser || sudo apt-get install -y chromium
        CHROMIUM_PATH="$(command -v chromium-browser || command -v chromium || true)"

        if [ -n "$CHROMIUM_PATH" ]; then
            echo "Installed system Chromium at: $CHROMIUM_PATH"
            if ! grep -q "PLAYWRIGHT_CHROMIUM_PATH" "$HOME/.bashrc" 2>/dev/null; then
                echo "export PLAYWRIGHT_CHROMIUM_PATH=\"$CHROMIUM_PATH\"" >> "$HOME/.bashrc"
            fi
            echo "Added PLAYWRIGHT_CHROMIUM_PATH=$CHROMIUM_PATH to ~/.bashrc so main.py"
            echo "uses it automatically. Open a new terminal (or run 'source ~/.bashrc')"
            echo "before running main.py."
        else
            echo "Could not find an installed chromium binary. Install one manually"
            echo "and set PLAYWRIGHT_CHROMIUM_PATH to its path before running main.py,"
            echo "e.g.: export PLAYWRIGHT_CHROMIUM_PATH=/usr/bin/chromium-browser"
        fi
    else
        echo "No apt-get found to install a fallback Chromium automatically."
        echo "Install a Chromium/Chrome build manually and set PLAYWRIGHT_CHROMIUM_PATH"
        echo "to its path before running main.py."
    fi
fi

echo
echo "All done. You can now run: python3 main.py"