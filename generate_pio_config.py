import requests
import json
import os
import sys

PROFILE_URL = "https://raw.githubusercontent.com/Sienci-Labs/grblhal-profiles/main/profiles/altmill.json"

def generate_config():
    print(f"Fetching profile from {PROFILE_URL}...")
    try:
        response = requests.get(PROFILE_URL)
        response.raise_for_status()
        profile_data = response.json()
    except Exception as e:
        print(f"Failed to fetch profile: {e}")
        sys.exit(1)

    # Convert JSON keys to -D flags
    ignore_keys = ['info', 'version', 'name', 'description']
    profile_flags = []
    for key, value in profile_data.items():
        if key not in ignore_keys:
            if value is True:
                profile_flags.append(f"-D{key}")
            elif value is False:
                pass
            elif isinstance(value, str):
                profile_flags.append(f'-D{key}=\\"{value}\\"')
            else:
                profile_flags.append(f"-D{key}={value}")

    # Indent flags for the .ini file
    profile_flags_str = "\n    ".join(profile_flags)

    # Construct the file content
    # Note: We use double {{ }} for PlatformIO variables so Python doesn't try to fill them
    ini_content = f"""
[platformio]
default_envs = altmill_mk2_4x4_stock_firmware_incl_4_axes_rotary, altmill_mk2_4x4_atc_firmware_keepout_plugin_ngc_expressions_tool_table
include_dir = Inc
src_dir = Src
boards_dir = boards

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

; --- Stock Firmware Environment ---
[env:altmill_mk2_4x4_stock_firmware_incl_4_axes_rotary]
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
    {profile_flags_str}

lib_deps = ${{common.lib_deps}}
  eeprom
  ${{wiznet_networking.lib_deps}}
  ./3rdparty/grblhal-rgb-plugin
  ./3rdparty/sienci-atci-plugin
lib_extra_dirs = ${{common.lib_extra_dirs}}

; --- ATC Firmware Environment ---
[env:altmill_mk2_4x4_atc_firmware_keepout_plugin_ngc_expressions_tool_table]
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
    {profile_flags_str}

lib_deps = ${{common.lib_deps}}
  eeprom
  ${{wiznet_networking.lib_deps}}
  ./3rdparty/grblhal-rgb-plugin
  ./3rdparty/sienci-atci-plugin
lib_extra_dirs = ${{common.lib_extra_dirs}}
"""

    # Write the file into the driver directory
    target_path = os.path.join("STM32F4xx", "platformio.ini")
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w") as f:
        f.write(ini_content)

    print(f"Done! Generated {target_path} using {len(profile_flags)} flags from {PROFILE_URL}")

if __name__ == "__main__":
    generate_config()
