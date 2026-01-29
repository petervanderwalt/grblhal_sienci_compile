#!/usr/bin/env python3

import json
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

# MATCHING YOUR WORKING [common], [wiznet], and [env] EXACTLY
STATIC_HEADER = """
[platformio]
default_envs = {default_envs}
include_dir = Inc
src_dir = Src

[common]
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
lib_extra_dirs =
  .
  boards
  FatFs
  Middlewares/ST/STM32_USB_Device_Library
  USB_DEVICE

[wiznet_networking]
build_flags =
  -I networking/wiznet
  -I Middlewares/Third_Party/LwIP/src/include
  -I Middlewares/Third_Party/LwIP/system
  -I Middlewares/Third_Party/LwIP/src/include/netif
  -I Middlewares/Third_Party/LwIP/src/include/lwip
lib_deps =
   networking
   webui
   Middlewares/Third_Party/LwIP
lib_extra_dirs =

[env]
platform = ststm32
platform_packages = framework-stm32cubef4
framework = stm32cube
lib_archive = no
lib_ldf_mode = off
extra_scripts =
    pre:extra_script.py
    post:extra_script.py
custom_prog_version = SLB_EXT
custom_board_name = 'default'
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
        # Clean up values: if it's a string, keep it; if it's a bool, handle -D flag
        if isinstance(v, bool):
            if v:
                flags.append(f"-D {k}")
        else:
            flags.append(f"-D {k}={v}")
    # Indent by 4 spaces to match the slb_ext environment style
    return "\n    ".join(flags)

def generate_env(variant):
    display_name = variant["name"]
    env_name = sanitize_env_name(display_name)
    defines = variant.get("defines", {})

    # Generate the 100+ machine defines from the JSON
    v_flags = format_build_flags(defines)

    return textwrap.dedent(f"""
    ; {display_name}
    [env:{env_name}]
    board = genericSTM32F412VG
    upload_protocol = dfu
    board_build.ldscript = STM32F412VGTX_FLASH.ld
    build_flags = ${{common.build_flags}}
      ${{wiznet_networking.build_flags}}
      -I ./3rdparty/grblhal-rgb-plugin
      -I ./3rdparty/grblhal-keepout-plugin
      -D WEB_BUILD
      -D BOARD_LONGBOARD32_EXT
      -D USE_HAL_DRIVER
      -D STM32F412Vx
      {v_flags}

    lib_deps = ${{common.lib_deps}}
      eeprom
      ${{wiznet_networking.lib_deps}}
      ./3rdparty/grblhal-rgb-plugin
      ./3rdparty/sienci-atci-plugin
    lib_extra_dirs = ${{common.lib_extra_dirs}}
    """).strip()

def main():
    profile = download_profile(PROFILE_URL)
    variants = profile.get("variants")
    if not variants:
        raise RuntimeError("No variants found in profile")

    env_names = [sanitize_env_name(v["name"]) for v in variants]

    sections = [
        STATIC_HEADER.format(default_envs=", ".join(env_names))
    ]

    for variant in variants:
        sections.append(generate_env(variant))

    content = "\n\n".join(sections)
    OUTPUT_INI.write_text(content)

    # Log the output so you can verify it in the GitHub Action console
    print("--- GENERATED PLATFORMIO.INI ---")
    print(content)
    print("--- END GENERATED FILE ---")

if __name__ == "__main__":
    main()
