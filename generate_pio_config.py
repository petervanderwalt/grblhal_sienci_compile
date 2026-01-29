#!/usr/bin/env python3

import json
import subprocess
import sys
import textwrap
from pathlib import Path
import urllib.request
import re

PROFILE_URL = (
    "https://raw.githubusercontent.com/Sienci-Labs/"
    "grblhal-profiles/main/profiles/altmill.json"
)

OUTPUT_INI = Path("platformio.ini")

# --- FIXED: Added all common build flags, libs, and extra dirs from your working file ---
BASE_ENV = """
[platformio]
default_envs = {default_envs}
include_dir = Inc
src_dir = Src

[env]
platform = ststm32
platform_packages = framework-stm32cubef4
framework = stm32cube
lib_archive = no
lib_ldf_mode = off
board = genericSTM32F412VG
upload_protocol = dfu
board_build.ldscript = STM32F412VGTX_FLASH.ld

; Common Build Flags from your original [common] section
build_flags =
  -I .
  -I boards
  -I FatFs
  -I FatFs/STM
  -I Drivers/FATFS/Target
  -I Middlewares/ST/STM32_USB_Device_Library/Class/CDC/Inc
  -I Middlewares/ST/STM32_USB_Device_Library/Core/Inc
  -I USB_DEVICE/App
  -I USB_DEVICE/Target
  -D OVERRIDE_MY_MACHINE
  -D _USE_IOCTL=1
  -D _USE_WRITE=1
  -D _VOLUMES=1
  -Wl,-u,_printf_float
  -Wl,-u,_scanf_float
  ; Networking/Wiznet flags (merged from [wiznet_networking] to ensure they are available)
  -I networking/wiznet
  -I Middlewares/Third_Party/LwIP/src/include
  -I Middlewares/Third_Party/LwIP/system
  -I Middlewares/Third_Party/LwIP/src/include/netif
  -I Middlewares/Third_Party/LwIP/src/include/lwip

; Common Lib Extra Dirs (Critical for finding libraries in root)
lib_extra_dirs =
  .
  boards
  FatFs
  Middlewares/ST/STM32_USB_Device_Library
  USB_DEVICE

; Common Lib Deps
lib_deps =
  boards
  bluetooth
  grbl
  keypad
  laser
  motors
  trinamic
  odometer
  openpnp
  fans
  plugins
  FatFs
  sdcard
  spindle
  embroidery
  Drivers/FATFS/App
  Drivers/FATFS/Target
  Middlewares/ST/STM32_USB_Device_Library/Core
  Middlewares/ST/STM32_USB_Device_Library/Class
  USB_DEVICE/App
  USB_DEVICE/Target
  eeprom
  networking
  webui
  Middlewares/Third_Party/LwIP
  ./3rdparty/grblhal-rgb-plugin
  ./3rdparty/sienci-atci-plugin
"""

def sanitize_env_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[()]", "", name)
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")

def download_profile(url):
    print(f"Downloading profile from {url}...")
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode())

def format_build_flags(defines):
    flags = []
    for k, v in defines.items():
        if isinstance(v, bool):
            if v:
                flags.append(f"-D{k}")
        else:
            flags.append(f"-D{k}={v}")
    # Add indentation for generated flags
    return "\n    ".join(flags)

def generate_env(variant):
    display_name = variant["name"]
    env_name = sanitize_env_name(display_name)
    defines = variant.get("defines", {})

    # We append the variant specific flags to the global build_flags
    variant_flags = format_build_flags(defines)

    return textwrap.dedent(f"""
    ; {display_name}
    [env:{env_name}]
    build_flags =
        ${{env.build_flags}}
        {variant_flags}
    """).strip()

def main(build=False):
    try:
        profile = download_profile(PROFILE_URL)
    except Exception as e:
        print(f"Error downloading profile: {e}")
        sys.exit(1)

    variants = profile.get("variants")
    if not variants:
        raise RuntimeError("No variants found in profile")

    env_names = [sanitize_env_name(v["name"]) for v in variants]

    # Fill in the default_envs in the base template
    sections = [
        BASE_ENV.format(default_envs=", ".join(env_names))
    ]

    for variant in variants:
        sections.append(generate_env(variant))

    OUTPUT_INI.write_text("\n\n".join(sections))
    print(f"✔ Generated {OUTPUT_INI}")

    if build:
        for env in env_names:
            print(f"\n=== Building {env} ===")
            subprocess.check_call(["pio", "run", "-e", env])

if __name__ == "__main__":
    # Check if --build argument is passed
    build_flag = "--build" in sys.argv
    main(build=build_flag)
