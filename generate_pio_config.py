#!/usr/bin/env python3

import json
from pathlib import Path
import urllib.request
import re

# List of profiles to include
PROFILE_URLS = [
    "https://raw.githubusercontent.com/Sienci-Labs/grblhal-profiles/main/profiles/altmill.json",
    "https://raw.githubusercontent.com/Sienci-Labs/grblhal-profiles/main/profiles/longmill.json"
]

OUTPUT_INI = Path("platformio.ini")

# STATIC_HEADER remains the same
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

SYSTEM_BASELINE_FLAGS = [
    "-D BOARD_LONGBOARD32_EXT",
    "-D USE_HAL_DRIVER",
    "-D STM32F412Vx",
    "-D WEB_BUILD",
    "-D USB_SERIAL_CDC=1",
    "-D RTC_ENABLE=1",
    "-D STEP_PULSE_LATENCY=1.3",
    "-D ETH_TX_DESC_CNT=12",
    "-D TCP_MSS=1460",
    "-D TCP_SND_BUF=5840",
    "-D LWIP_NUM_NETIF_CLIENT_DATA=2",
    "-D LWIP_HTTPD_CUSTOM_FILES=0",
    "-D MEM_SIZE=16384",
    "-D LWIP_IGMP=1",
    "-D LWIP_MDNS_RESPONDER=1",
    "-D LWIP_NETIF_STATUS_CALLBACK=1",
    "-D LWIP_HTTPD_DYNAMIC_HEADERS=1",
    "-D LWIP_HTTPD_DYNAMIC_FILE_READ=1",
    "-D LWIP_HTTPD_SUPPORT_V09=0",
    "-D LWIP_HTTPD_SUPPORT_11_KEEPALIVE=1",
    "-D LWIP_HTTPD_CGI_ADV=1",
    "-D LWIP_HTTPD_SUPPORT_POST=1",
    "-D LWIP_HTTPD_SUPPORT_WEBDAV=1",
    "-D PROBE_ENABLE=1",
    "-D MODBUS_ENABLE=3",
    "-D MODBUS_BAUDRATE=3",
    "-D EEPROM_ENABLE=128",
    "-D N_EVENTS=4",
    "-D _WIZCHIP_=5500",
    "-D ETHERNET_ENABLE=1",
    "-D SAFETY_DOOR_ENABLE=0",
    "-D CONTROL_ENABLE=64",
    "-D DEFAULT_STEP_PULSE_MICROSECONDS=5",
    "-D DEFAULT_PARKING_ENABLE=0",
    "-D NETWORK_IPMODE=0"
]

def sanitize_env_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[()]", "", name)
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")

def download_profile(url):
    print(f"Downloading profile: {url}")
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode())

def format_build_flags(defines):
    lines = []
    for k in sorted(defines.keys()):
        v = defines[k]
        key = "ATCI_ENABLE" if k == "SIENCI_ATCI" else k
        if key.endswith("_LETTER") and isinstance(v, str):
            char = v.replace("'", "").strip()
            if len(char) == 1:
                v = ord(char)
        if isinstance(v, bool):
            if v: lines.append(f"  -D {key}")
        else:
            lines.append(f"  -D {key}={v}")
    return "\n".join(lines)

def generate_env(variant, global_defines):
    display_name = variant["name"]
    env_name = sanitize_env_name(display_name)

    merged_defines = global_defines.copy()
    merged_defines.update(variant.get("default_symbols", {}))
    merged_defines.update(variant.get("setting_defaults", {}))

    v_flags = format_build_flags(merged_defines)
    sys_flags = "\n".join([f"  {f}" for f in SYSTEM_BASELINE_FLAGS])

    return f"""
; {display_name}
[env:{env_name}]
board = genericSTM32F412VG
upload_protocol = dfu
board_build.ldscript = STM32F412VGTX_FLASH.ld
build_flags =
  ${{common.build_flags}}
  ${{wiznet_networking.build_flags}}
  -I ./3rdparty/grblhal-rgb-plugin
  -I ./3rdparty/grblhal-keepout-plugin
{sys_flags}
{v_flags}

lib_deps =
  ${{common.lib_deps}}
  eeprom
  ${{wiznet_networking.lib_deps}}
  ./3rdparty/grblhal-rgb-plugin
  ./3rdparty/sienci-atci-plugin
lib_extra_dirs = ${{common.lib_extra_dirs}}
"""

def main():
    all_env_names = []
    all_envs_content = ""

    for url in PROFILE_URLS:
        try:
            profile = download_profile(url)
            machine = profile.get("machine", {})
            global_defines = {
                **machine.get("default_symbols", {}),
                **machine.get("setting_defaults", {})
            }

            variants = profile.get("variants", [])
            for variant in variants:
                env_name = sanitize_env_name(variant["name"])
                all_env_names.append(env_name)
                all_envs_content += generate_env(variant, global_defines)
        except Exception as e:
            print(f"Error processing {url}: {e}")

    # Combine the static header with all found environments
    content = STATIC_HEADER.format(default_envs=", ".join(all_env_names)).strip() + "\n"
    content += all_envs_content

    OUTPUT_INI.write_text(content)
    print(f"Successfully generated platformio.ini with {len(all_env_names)} environments.")

if __name__ == "__main__":
    main()
