import requests
import json
import os
import sys

# Define the source URLs
PROFILE_URL = "https://raw.githubusercontent.com/Sienci-Labs/grblhal-profiles/refs/heads/main/profiles/altmill.json"

def generate_config():
    print(f"Fetching profile from {PROFILE_URL}...")
    try:
        response = requests.get(PROFILE_URL)
        response.raise_for_status()
        profile_data = response.json()
    except Exception as e:
        print(f"Failed to fetch profile: {e}")
        sys.exit(1)

    # 1. Process JSON Keys into Build Flags
    # We exclude metadata keys that aren't compile flags
    ignore_keys = ['info', 'version', 'name', 'description']
    json_flags = []

    for key, value in profile_data.items():
        if key not in ignore_keys:
            if value is True:
                json_flags.append(f"-D{key}")
            elif value is False:
                pass
            elif isinstance(value, str):
                # Handle string values with escaped quotes
                json_flags.append(f'-D{key}=\\"{value}\\"')
            else:
                # Handle numbers
                json_flags.append(f"-D{key}={value}")

    # Join them with indentation for the INI file
    json_flags_str = "\n    ".join(json_flags)

    # 2. Define the PlatformIO Configuration Template
    # NOTE: We use double curly braces {{ }} for things that must stay in the INI file
    # and single curly braces { } for Python variable injection.
    ini_template = f"""
[platformio]
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

[eth_networking]
build_flags =
  -I LWIP/App
  -I LWIP/dp83848/Target
  -I Middlewares/Third_Party/LwIP/src/include
  -I Middlewares/Third_Party/LwIP/system
  -I Middlewares/Third_Party/LwIP/src/include/netif
  -I Middlewares/Third_Party/LwIP/src/include/lwip
  -I Drivers/BSP/Components/dp83848
lib_deps =
   networking
   webui
   LWIP/App
   LWIP/dp83848/Target
   Middlewares/Third_Party/LwIP
   Drivers/BSP/Components/dp83848
lib_extra_dirs =

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

[env:slb_ext]
platform = ststm32
platform_packages = framework-stm32cubef4
framework = stm32cube
board = genericSTM32F412VG
upload_protocol = dfu
board_build.ldscript = STM32F412VGTx_FLASH.ld

# Scripts to handle variants and build environment
extra_scripts =
    pre:extra_script.py
    post:extra_script.py

# Dependencies
lib_deps = ${{common.lib_deps}}
  eeprom
  ${{wiznet_networking.lib_deps}}
  ./3rdparty/grblhal-rgb-plugin
  ./3rdparty/sienci-atci-plugin

lib_extra_dirs = ${{common.lib_extra_dirs}}

# Build Flags
build_flags = ${{common.build_flags}}
  ${{wiznet_networking.build_flags}}
  -I ./3rdparty/grblhal-rgb-plugin
  -I ./3rdparty/sienci-atci-plugin

  # --- Hardcoded Hardware Flags ---
  -D WEB_BUILD
  -D BOARD_LONGBOARD32_EXT
  -D USE_HAL_DRIVER
  -D STM32F412Vx
  -D _WIZCHIP_=5500
  -D ETHERNET_ENABLE=1
  -D TELNET_ENABLE=1
  -D WEBSOCKET_ENABLE=1
  -D FTP_ENABLE=1
  -D USB_SERIAL_CDC=1

  # --- Dynamic Flags from JSON Profile ---
  {json_flags_str}
"""

    # 3. Write to File
    target_path = os.path.join("STM32F4xx", "platformio.ini")

    # Ensure directory exists (though git clone usually creates it)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    with open(target_path, "w") as f:
        f.write(ini_template)

    print(f"Successfully generated {target_path}")

if __name__ == "__main__":
    generate_config()
