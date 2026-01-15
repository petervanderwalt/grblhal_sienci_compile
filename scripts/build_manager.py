import json
import os
import shutil
import subprocess
import datetime
import sys

# --- Configuration ---
PROFILES_FILE = 'profiles.json'
OUTPUT_DIR = 'build_output'
FIRMWARE_DIR = 'firmware'
TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d")

# --- PlatformIO INI Templates ---
ENV_CONFIGS = {
    "BOARD_LONGBOARD32_EXT": {
        "env_name": "slb_ext",
        "board": "genericSTM32F412VG",
        "ldscript": "STM32F412VGTX_FLASH.ld",
        "usb_flags": "-D USB_SERIAL_CDC=1",
        "extra_flags": "-D STM32F412Vx -D BOARD_LONGBOARD32_EXT"
    },
    "BOARD_LONGBOARD32": {
        "env_name": "slb",
        "board": "genericSTM32F412VG",
        "ldscript": "STM32F412VGTX_FLASH.ld",
        "usb_flags": "-D USB_SERIAL_CDC=1",
        "extra_flags": "-D STM32F412Vx -D BOARD_LONGBOARD32"
    }
}

# Added boards_dir = boards so PIO looks in local folder for genericSTM32F412VG.json
INI_HEADER_TEMPLATE = """[platformio]
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

[env]
platform = ststm32
platform_packages = framework-stm32cubef4
framework = stm32cube
lib_archive = no
lib_ldf_mode = off
extra_scripts =
    pre:extra_script.py
    post:extra_script.py
grblhal_driver_version = {date_str}
custom_prog_version = {board_id}
custom_board_name = 'default'

[env:{env_name}]
board = {board}
upload_protocol = dfu
board_build.ldscript = {ldscript}
lib_extra_dirs = ${{common.lib_extra_dirs}}
lib_deps = ${{common.lib_deps}}
  eeprom
  ${{wiznet_networking.lib_deps}}
  ./3rdparty/grblhal-rgb-plugin
  ./3rdparty/sienci-atci-plugin
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sienci Labs Firmware Downloads</title>
    <style>
        body {{ font-family: -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; background-color: #f4f6f8; color: #333; }}
        h1 {{ border-bottom: 2px solid #0056b3; padding-bottom: 10px; color: #0056b3; }}
        .card {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .machine-title {{ font-size: 1.5em; font-weight: bold; margin-bottom: 10px; }}
        .variant {{ margin-top: 15px; border-top: 1px solid #eee; padding-top: 10px; }}
        .btn {{ display: inline-block; background-color: #28a745; color: white; padding: 8px 15px; text-decoration: none; border-radius: 4px; font-weight: bold; }}
        .btn:hover {{ background-color: #218838; }}
        .meta {{ font-size: 0.85em; color: #666; margin-top: 5px; }}
    </style>
</head>
<body>
    <h1>Firmware Builds ({date})</h1>
    <p>Automated builds for Sienci Labs controllers.</p>
    {content}
</body>
</html>
"""

def generate_build_flags(machine_data, variant_data, base_config):
    flags = []

    # 1. Base Machine Defaults
    base_defs = {**machine_data.get("default_symbols", {}),
                 **machine_data.get("setting_defaults", {}),
                 **machine_data.get("setting_defaults_trinamic", {})}

    # 2. Variant Overrides
    variant_defs = {**variant_data.get("default_symbols", {}),
                    **variant_data.get("setting_defaults", {})}

    combined_defs = {**base_defs, **variant_defs}

    # 3. System Defaults
    system_flags = {
        "WEB_BUILD": None,
        "USE_HAL_DRIVER": None,
        "ETHERNET_ENABLE": 1,
        "_WIZCHIP_": 5500,
        "STEP_PULSE_LATENCY": 1.3,
        "EEPROM_ENABLE": 128,
        "MODBUS_ENABLE": 3,
        "MODBUS_BAUDRATE": 3,
        "N_EVENTS": 4,
        "ETH_TX_DESC_CNT": 12,
        "TCP_MSS": 1460,
        "TCP_SND_BUF": 5840,
        "LWIP_NUM_NETIF_CLIENT_DATA": 2,
        "LWIP_HTTPD_CUSTOM_FILES": 0,
        "MEM_SIZE": 16384,
        "LWIP_IGMP": 1,
        "LWIP_MDNS_RESPONDER": 1,
        "LWIP_NETIF_STATUS_CALLBACK": 1,
        "LWIP_HTTPD_DYNAMIC_HEADERS": 1,
        "LWIP_HTTPD_DYNAMIC_FILE_READ": 1,
        "LWIP_HTTPD_SUPPORT_11_KEEPALIVE": 1,
        "LWIP_HTTPD_CGI_ADV": 1,
        "LWIP_HTTPD_SUPPORT_POST": 1,
        "LWIP_HTTPD_SUPPORT_WEBDAV": 1
    }

    final_defs = {**system_flags, **combined_defs}

    for key, value in final_defs.items():
        if value is None:
            flags.append(f"-D {key}")
        else:
            flags.append(f"-D {key}={value}")

    flags.append(base_config['extra_flags'])
    flags.append(base_config['usb_flags'])

    return flags

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    with open(PROFILES_FILE, 'r') as f:
        profiles = json.load(f)

    html_content = ""
    build_failures = False

    cwd = os.getcwd()
    os.chdir(FIRMWARE_DIR)

    for machine in profiles['machines']:
        machine_name = machine['name']
        print(f"\n--- Processing Machine: {machine_name} ---")

        if "Altmill" in machine_name:
            json_file = "../altmill.json"
        elif "Longmill" in machine_name:
            json_file = "../longmill.json"
        else:
            print(f"Skipping unknown machine: {machine_name}")
            continue

        with open(json_file, 'r') as f:
            m_data = json.load(f)["machine"]
            f.seek(0)
            v_list = json.load(f)["variants"]

        default_board = m_data.get("default_board", "BOARD_LONGBOARD32")
        env_config = ENV_CONFIGS.get(default_board)

        if not env_config:
            print(f"Error: Unknown board type {default_board}")
            continue

        html_content += f"<div class='card'><div class='machine-title'>{machine_name}</div>"
        html_content += f"<div class='meta'>Board: {default_board} | Driver: {env_config['env_name']}</div>"

        for variant in v_list:
            variant_name = variant['name']
            print(f"  > Building Variant: {variant_name}")

            build_flags = generate_build_flags(m_data, variant, env_config)

            ini_content = INI_HEADER_TEMPLATE.format(
                date_str=TIMESTAMP,
                board_id=env_config['env_name'].upper(),
                env_name=env_config['env_name'],
                board=env_config['board'],
                ldscript=env_config['ldscript']
            )

            ini_content += "\nbuild_flags = \n"

            includes = [
                "${common.build_flags}",
                "${wiznet_networking.build_flags}",
                "-I ./3rdparty/grblhal-rgb-plugin",
                "-I ./3rdparty/sienci-atci-plugin"
            ]
            for inc in includes:
                ini_content += f"  {inc}\n"
            for flag in build_flags:
                ini_content += f"  {flag}\n"

            with open("platformio.ini", "w") as f:
                f.write(ini_content)

            subprocess.run(["pio", "run", "-t", "clean", "-e", env_config['env_name']], capture_output=True)
            result = subprocess.run(["pio", "run", "-e", env_config['env_name']], capture_output=True, text=True)

            if result.returncode != 0:
                print(f"    [FAILED] Build failed for {variant_name}")
                print(result.stderr)
                html_content += f"<div class='variant'><strong>{variant_name}</strong>: <span style='color:red'>Build Failed</span></div>"
                build_failures = True
            else:
                print(f"    [SUCCESS] Built successfully")

                safe_v_name = "".join(x for x in variant_name if x.isalnum() or x in " -_").replace(" ", "_")
                filename = f"grblhal_{env_config['env_name']}_{safe_v_name}_{TIMESTAMP}.hex"

                build_dir = f".pio/build/{env_config['env_name']}"
                found_hex = False
                for f_name in os.listdir(build_dir):
                    if f_name.endswith(".hex"):
                        shutil.copy(os.path.join(build_dir, f_name), os.path.join("../", OUTPUT_DIR, filename))
                        found_hex = True
                        break

                if found_hex:
                    html_content += f"<div class='variant'><strong>{variant_name}</strong><br><a href='{filename}' class='btn' download>Download .HEX</a></div>"
                else:
                    html_content += f"<div class='variant'><strong>{variant_name}</strong>: <span style='color:orange'>Hex not found</span></div>"

        html_content += "</div>"

    os.chdir(cwd)
    final_html = HTML_TEMPLATE.format(date=TIMESTAMP, content=html_content)
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w") as f:
        f.write(final_html)

    print("\n--- All Builds Complete ---")

    # Exit with error code if any build failed so GitHub Action turns Red
    if build_failures:
        print("Error: One or more builds failed. Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    main()
