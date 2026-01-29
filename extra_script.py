import datetime
Import("env")

# 1. Generate the realtime date
# Format: 20260129-1606
build_date = datetime.datetime.now().strftime("%Y%m%d-%H%M")

# 2. Get the variables from platformio.ini and the Environment
custom_ver = env.GetProjectOption("custom_prog_version")  # e.g., SLB_EXT
variant_name = env["PIOENV"]                              # e.g., altmill_mk2_4x4_atc...

# 3. Construct the new program name
# Format: SLB_EXT_<VARIANT_NAME>_<DATE>
# Example: SLB_EXT_altmill_mk2_4x4_atc_firmware..._20260129-1606
new_prog_name = "%s_%s_%s" % (custom_ver, variant_name, build_date)

# 4. Apply the new name to the environment
print(f"Renaming output firmware to: {new_prog_name}")
env.Replace(PROGNAME=new_prog_name)
env.Replace(custom_board_name=new_prog_name)

# 5. Custom HEX from ELF
env.AddPostAction(
    "$BUILD_DIR/${PROGNAME}.elf",
    env.VerboseAction(" ".join([
        "$OBJCOPY", "-O", "ihex", "-R", ".eeprom",
        '"$BUILD_DIR/${PROGNAME}.elf"', '"$BUILD_DIR/${PROGNAME}.hex"'
    ]), "Building $BUILD_DIR/${PROGNAME}.hex")
)
