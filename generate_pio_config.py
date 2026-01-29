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

BASE_ENV = """
[platformio]
default_envs = {default_envs}

[env]
platform = ststm32
framework = stm32cube
lib_archive = no
lib_ldf_mode = off

; grblHAL STM32 layout
src_dir = Src
include_dir = Inc
"""


def sanitize_env_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[()]", "", name)
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")

def download_profile(url):
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
    return "\n    ".join(flags)


def generate_env(variant):
    display_name = variant["name"]
    env_name = sanitize_env_name(display_name)
    defines = variant.get("defines", {})

    build_flags = format_build_flags(defines)

    return textwrap.dedent(f"""
    ; {display_name}
    [env:{env_name}]
    board = genericSTM32F412VG
    upload_protocol = dfu
    board_build.ldscript = STM32F412VGTX_FLASH.ld

    build_flags =
        ${{env.build_flags}}
        {build_flags}
    """).strip()


def main(build=False):
    profile = download_profile(PROFILE_URL)

    variants = profile.get("variants")
    if not variants:
        raise RuntimeError("No variants found in profile")

    env_names = [sanitize_env_name(v["name"]) for v in variants]

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
    build_flag = "--build" in sys.argv
    main(build=build_flag)
