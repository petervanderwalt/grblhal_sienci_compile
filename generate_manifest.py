import os
import json
import datetime

# Configuration
OUTPUT_DIR = "public/firmware"
MANIFEST_FILE = "public/firmware_manifest.json"

def generate_manifest():
    files = []

    # Walk through the output directory
    if not os.path.exists(OUTPUT_DIR):
        print(f"Directory {OUTPUT_DIR} does not exist.")
        return

    for filename in os.listdir(OUTPUT_DIR):
        if filename.endswith(".bin") or filename.endswith(".hex"):
            # Parse info from filename if using the naming convention
            # Ex: SLB_EXT_altmill_mk2_4x4_atc_20260129-1606.bin

            file_path = os.path.join("firmware", filename) # Web path relative to root

            file_entry = {
                "name": filename,
                "path": file_path,
                "size": os.path.getsize(os.path.join(OUTPUT_DIR, filename)),
                "date": datetime.datetime.now().isoformat(),
                "type": "binary" if filename.endswith(".bin") else "hex"
            }
            files.append(file_entry)

    manifest = {
        "generated_at": datetime.datetime.now().isoformat(),
        "files": files
    }

    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, indent=4)

    print(f"Manifest generated with {len(files)} entries.")

if __name__ == "__main__":
    generate_manifest()
