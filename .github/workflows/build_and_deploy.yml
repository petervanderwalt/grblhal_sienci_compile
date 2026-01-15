import json
import os
import shutil
import subprocess
import datetime
import sys
import urllib.request

# --- Configuration ---
PROFILES_URL = "https://raw.githubusercontent.com/Sienci-Labs/grblhal-profiles/main/profiles.json"
OUTPUT_DIR = 'build_output'
FIRMWARE_DIR = 'firmware'
TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d")

# Files to copy from repo root to firmware dir
LOCAL_FILES = {
    "genericSTM32F412VG.json": "boards/genericSTM32F412VG.json",
    "longboard32.c": "boards/longboard32.c",
    "longboard32_map.h": "boards/longboard32_map.h",
    "STM32F412VGTX_FLASH.ld": "STM32F412VGTX_FLASH.ld",
    "platformio.ini": "platformio.ini" # We read this into memory, but checking it exists is good
}

# --- Environment Mapping ---
ENV_CONFIGS = {
    "BOARD_LONGBOARD32_EXT": "slb_ext",
    "BOARD_LONGBOARD32": "slb"
}

def fetch_json(url):
    try:
        print(f"Fetching: {url}")
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def convert_to_raw_url(blob_url):
    if "github.com" in blob_url and "blob" in blob_url:
        return blob_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    return blob_url

def generate_build_flags(machine_data, variant_data):
    flags = []
    base_defs = {**machine_data.get("default_symbols", {}),
                 **machine_data.get("setting_defaults", {}),
                 **machine_data.get("setting_defaults_trinamic", {})}
    variant_defs = {**variant_data.get("default_symbols", {}),
                    **variant_data.get("setting_defaults", {})}
    combined_defs = {**base_defs, **variant_defs}

    # We DO NOT add system flags here anymore.
    # We trust your platformio.ini has the base system config.
    # We only add the overrides from the JSON profile.

    for key, value in combined_defs.items():
        if value is None:
            flags.append(f"-D {key}")
        else:
            flags.append(f"-D {key}={value}")

    return flags

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # --- 1. Copy Critical Local Files ---
    print("\n--- Setup: Copying Local Files ---")
    for filename, dest_rel_path in LOCAL_FILES.items():
        if filename == "platformio.ini": continue # We handle this specifically later

        src = filename
        dest = os.path.join(FIRMWARE_DIR, dest_rel_path)

        # Ensure dest dir exists
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        if os.path.exists(src):
            shutil.copy(src, dest)
            print(f"  OK: {src} -> {dest}")
        else:
            print(f"  ERROR: {src} missing in repo root.")
            sys.exit(1)

    # --- 2. Load Template platformio.ini ---
    if not os.path.exists("platformio.ini"):
        print("Error: platformio.ini not found in root.")
        sys.exit(1)

    with open("platformio.ini", "r") as f:
        ini_template = f.read()
    print("  OK: Loaded platformio.ini template")

    # --- 3. Fetch Profiles ---
    profiles = fetch_json(PROFILES_URL)
    if not profiles:
        print("Failed to load profiles.json. Exiting.")
        sys.exit(1)

    html_content = ""
    build_failures = False

    cwd = os.getcwd()
    os.chdir(FIRMWARE_DIR)

    # Iterate Machines
    for machine in profiles.get('machines', []):
        machine_name = machine['name']
        profile_url = machine.get('profileURL')

        print(f"\n--- Processing Machine: {machine_name} ---")

        if not profile_url:
            print(f"Skipping: No profileURL.")
            continue

        raw_url = convert_to_raw_url(profile_url)
        machine_config = fetch_json(raw_url)

        if not machine_config:
            print(f"Failed to fetch config")
            continue

        m_data = machine_config.get("machine", {})
        v_list = machine_config.get("variants", [])

        default_board = m_data.get("default_board", "BOARD_LONGBOARD32")
        env_name = ENV_CONFIGS.get(default_board)

        if not env_name:
            print(f"Error: Unknown board type {default_board}")
            continue

        html_content += f"<div class='card'><div class='machine-title'>{machine_name}</div>"
        html_content += f"<div class='meta'>Board: {default_board} | Driver: {env_name}</div>"

        # Iterate Variants
        for variant in v_list:
            variant_name = variant['name']
            print(f"  > Building Variant: {variant_name}")

            # Generate just the profile-specific flags
            variant_flags = generate_build_flags(m_data, variant)

            # --- Write INI ---
            # 1. Write the user's full template
            # 2. Append a new section that extends the existing environment
            #    This effectively adds the new flags to the existing ones.
            with open("platformio.ini", "w") as f:
                f.write(ini_template)
                f.write("\n\n# --- AUTOMATED PROFILE INJECTION ---\n")
                f.write(f"[env:{env_name}]\n")
                f.write(f"build_flags = \n")
                f.write(f"  ${{env:{env_name}.build_flags}}\n") # Inherit existing flags
                for flag in variant_flags:
                    f.write(f"  {flag}\n")

            # Clean
            subprocess.call(["pio", "run", "-t", "clean", "-e", env_name])

            # Build
            print(f"    Starting compilation...")
            return_code = subprocess.call(["pio", "run", "-e", env_name])

            if return_code != 0:
                print(f"    [FAILED] Build failed")
                html_content += f"<div class='variant'><strong>{variant_name}</strong>: <span style='color:red'>Build Failed</span></div>"
                build_failures = True
            else:
                print(f"    [SUCCESS] Built successfully")

                safe_v_name = "".join(x for x in variant_name if x.isalnum() or x in " -_").replace(" ", "_")
                filename_hex = f"grblhal_{env_name}_{safe_v_name}_{TIMESTAMP}.hex"
                filename_ini = f"grblhal_{env_name}_{safe_v_name}_{TIMESTAMP}.ini"

                build_dir = f".pio/build/{env_name}"
                found_hex = False

                for f_name in os.listdir(build_dir):
                    if f_name.endswith(".hex"):
                        shutil.copy(os.path.join(build_dir, f_name), os.path.join("../", OUTPUT_DIR, filename_hex))
                        found_hex = True
                        break

                shutil.copy("platformio.ini", os.path.join("../", OUTPUT_DIR, filename_ini))

                if found_hex:
                    html_content += f"""
                    <div class='variant'>
                        <strong>{variant_name}</strong><br>
                        <a href='{filename_hex}' class='btn' download>Download .HEX</a>
                        <a href='{filename_ini}' class='btn btn-secondary' download>View Config</a>
                    </div>
                    """
                else:
                    html_content += f"<div class='variant'><strong>{variant_name}</strong>: <span style='color:orange'>Hex not found</span></div>"

        html_content += "</div>"

    os.chdir(cwd)
    final_html = HTML_TEMPLATE.format(date=TIMESTAMP, content=html_content)
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w") as f:
        f.write(final_html)

    print("\n--- All Builds Complete ---")

    if build_failures:
        print("Error: One or more builds failed. Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    main()
