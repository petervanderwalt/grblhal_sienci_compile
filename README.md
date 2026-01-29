# grblHAL Sienci Automated Firmware Builder

This repository provides an automated pipeline for building and deploying firmware for grblHAL-based Sienci Labs controllers. It combines a CI/CD build system with a browser-based flashing tool.

## How it Works

1.  **Automated Profiles:** A GitHub Action triggers to download the latest machine profiles from [Sienci-Labs/grblhal-profiles](https://github.com/Sienci-Labs/grblhal-profiles/). These are the same profiles as used by [grblHAL Web Builder 2](https://svn.io-engineering.com:8443/index2.html?dev=1) - it generates a platformio.ini dynamically from these profiles and base environment.
2.  **PlatformIO Build:** The system uses PlatformIO to compile the firmware variants based on those profiles.
3.  **Automatic Deployment:** Successful builds are pushed to GitHub Pages along with a hosted Web-DFU flasher interface.

## Web-Based Tool

You can access the hosted firmware portal at:
**[https://petervanderwalt.github.io/grblhal_sienci_compile/](https://petervanderwalt.github.io/grblhal_sienci_compile/)**

### Features:
*   **Direct Flashing:** Flash firmware directly from your browser to your controller.
*   **DFU Trigger:** Built-in WebSerial support to reboot boards into DFU mode remotely.
*   **Build Archive:** Download `.hex` files from the automated build list.

### Requirements:
To use the browser-flashing features, you must use a **WebUSB/WebSerial/WebDFU compatible browser** (such as Google Chrome, Microsoft Edge, or Opera).
