#!/usr/bin/env python3

import json
import subprocess
import sys
import textwrap
from pathlib import Path
import urllib.request
import re

# --- CONFIGURATION ---
PROFILE_URL = (
    "https://raw.githubusercontent.com/Sienci-Labs/"
    "grblhal-profiles/main/profiles/altmill.json"
)

OUTPUT_INI = Path("platformio.ini")

# --- TEMPLATE ---
# Matches your working [platformio] and [env] setup
# Added -DSTM32F412Vx and -DBOARD_LONGBOARD32_EXT to ensure hardware is correctly mapped
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

; --- Common Build Flags (from [common] + [env:slb_ext]) ---
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
  ; Networking Includes
  -I networking/wiznet
  -I Middlewares/Third_Party/LwIP/src/include
  -I Middlewares/Third_Party/LwIP/system
  -I Middlewares/Third_Party/LwIP/src/include/netif
  -I Middlewares/Third_Party/LwIP/src/include/lwip
  ; Critical Hardware Defines (Fixed: These were missing in previous script)
  -D STM32F412Vx
  -D BOARD_LONGBOARD32_EXT
  -D USE_HAL_DRIVER
  -D HSE_VALUE=8000000

; --- Library Search Paths ---
lib_extra_dirs =
  .
  boards
  FatFs
  Middlewares/ST/STM32_USB_Device_Library
  USB_DEVICE

; --- Library Dependencies ---
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
    # Clean up the name for PlatformIO environment usage
    name = name.lower()
    name = re.sub(r"[()]", "", name)
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")

def download_profile(url):
    print(f"Downloading profile from {url}...")
    try:
        with urllib.request.urlopen(url) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"Error downloading profile: {e}")
        sys.exit(1)

def format_build_flags(defines):
    flags = []
    for k, v in defines.items():
        # Avoid duplicating flags if they are already in BASE_ENV
        if k in ["BOARD_LONGBOARD32_EXT", "STM32F412Vx"]:
            continue

        if isinstance(v, bool):
            if v:
                flags.append(f"-D{k}")
        else:
            flags.append(f"-D{k}={v}")
    return "\n    ".join(flags)

def generate_env(variant):
    display_name = variant["name"]
    env_name = sanitize_env_name(display_name)
    defines = variant.get("defines", {})

    variant_flags = format_build_flags(defines)

    return textwrap.dedent(f"""
    ; {display_name}
    [env:{env_name}]
    build_flags =
        ${{env.build_flags}}
        {variant_flags}
    """).strip()

def main(build=False):
    profile = download_profile(PROFILE_URL)

    variants = profile.get("variants")
    if not variants:
        raise RuntimeError("No variants found in profile")

    env_names = [sanitize_env_name(v["name"]) for v in variants]

    # Initialize the INI file content with the base environment
    sections = [
        BASE_ENV.format(default_envs=", ".join(env_names))
    ]

    # Append each variant environment
    for variant in variants:
        sections.append(generate_env(variant))

    # Write to file
    OUTPUT_INI.write_text("\n\n".join(sections))
    print(f"✔ Generated {OUTPUT_INI}")

    # Optional: Run build immediately
    if build:
        for env in env_names:
            print(f"\n=== Building {env} ===")
            try:
                subprocess.check_call(["pio", "run", "-e", env])
            except subprocess.CalledProcessError:
                print(f"❌ Failed to build {env}")

if __name__ == "__main__":
    build_flag = "--build" in sys.argv
    main(build=build_flag)
