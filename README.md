# BLE Over-The-Air (OTA) Firmware Update System

## Overview

This project implements a custom **Over-The-Air (OTA) firmware update system over Bluetooth Low Energy (BLE)**, designed for a dual-MCU setup using an ESP32-C6 and an STM32F411 (Black Pill). It enables seamless firmware updates via a wireless interface and ensures safe flash memory operations using a dual-bank bootloader on the STM32.

## System Components

### 1. Python BLE OTA GUI

A cross-platform graphical interface built with Python that:

- Scans for available BLE devices.
- Connects to the ESP32-C6 module over BLE.
- Sends firmware files using a custom OTA protocol.
- Uses chunked data transfer, acknowledgments, and CRC32 verification.

### 2. ESP32-C6 (BLE Relay)

Acts as a communication bridge between the GUI and the STM32:

- Receives firmware data over BLE.
- Handles basic protocol commands (e.g., `OPEN`, `DATA`, `CLOSE`, `ACK`).
- Forwards firmware data to the STM32F4 over UART.

### 3. STM32F411CEU6 (Black Pill)

The target microcontroller responsible for executing and updating firmware:

- Runs a **custom dual-bank bootloader** for safe OTA updates.
- Flash memory is partitioned into:
  - **Bootloader region**
  - **Active application slot**
  - **Inactive application slot**
- On boot:
  - Checks for an update flag.
  - If present, verifies the received firmware using CRC32.
  - If valid, erases the inactive region and writes the new firmware.
  - Jumps to the new firmware after successful update.
  - If no update is pending, it boots into the current active application.

## Flash Layout

| Bootloader | App Slot A (Active) | App Slot B (Inactive) |
| ---------- | ------------------- | --------------------- |
     64KB            192KB                   256KB


## Features

- Secure OTA firmware updates via BLE.
- CRC32 integrity check before flashing.
- Safe dual-bank update mechanism with fallback.
- UART communication between ESP32 and STM32.
- Python-based GUI for cross-platform firmware delivery.

---

Feel free to contribute or fork this project to adapt it to your own hardware configuration.
