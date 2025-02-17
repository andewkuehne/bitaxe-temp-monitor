#!/usr/bin/env python3
import requests
import time
import signal
import sys
import argparse

# ANSI Color Codes for console output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

# Parse command-line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Bitaxe Temperature Monitor and Auto-Tuner'
    )
    parser.add_argument('bitaxe_ip', help='IP address of the Bitaxe (e.g., 192.168.2.26)')
    parser.add_argument('-v', '--voltage', type=int, default=1150,
                        help='Initial core voltage in mV (default: 1150)')
    parser.add_argument('-f', '--frequency', type=int, default=600,
                        help='Initial frequency in MHz (default: 600)')
    parser.add_argument('-t', '--target_temp', type=int, default=60,
                        help='Target CPU temperature in °C (default: 60)')
    parser.add_argument('-i', '--interval', type=int, default=5,
                        help='Monitoring sample interval in seconds (default: 5)')
    return parser.parse_args()

args = parse_arguments()
bitaxe_ip = f"http://{args.bitaxe_ip}"
current_voltage = args.voltage
current_frequency = args.frequency
target_temp = args.target_temp
sample_interval = args.interval

# Configuration parameters (adjust these as needed)
voltage_step = 20         # mV adjustment step
frequency_step = 25       # MHz adjustment step
min_allowed_voltage = 1000  # mV
max_allowed_voltage = 1400  # mV
min_allowed_frequency = 400  # MHz
max_allowed_frequency = 1200  # MHz

# Temperature margins:
# If temp exceeds target_temp, we step down.
# If temp is below (target_temp - margin), we try to step up.
temp_margin = 2

# Flag to control the main loop when exiting
running = True

# Signal handler to exit gracefully on Ctrl+C
def handle_sigint(signum, frame):
    global running
    print(RED + "\nExiting Bitaxe Monitor. No further adjustments will be made." + RESET)
    running = False

signal.signal(signal.SIGINT, handle_sigint)

def get_system_info():
    """Fetch system info from Bitaxe API."""
    try:
        response = requests.get(f"{bitaxe_ip}/api/system/info", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(YELLOW + f"Error fetching system info: {e}" + RESET)
        return None

def set_system_settings(core_voltage, frequency):
    """Set system parameters via Bitaxe API."""
    settings = {
        "coreVoltage": core_voltage,
        "frequency": frequency
    }
    try:
        response = requests.patch(f"{bitaxe_ip}/api/system", json=settings, timeout=10)
        response.raise_for_status()
        print(YELLOW + f"Applied settings: Voltage = {core_voltage}mV, Frequency = {frequency}MHz" + RESET)
        # Allow some time for the system to stabilize after applying new settings.
        time.sleep(2)
    except requests.exceptions.RequestException as e:
        print(RED + f"Error setting system settings: {e}" + RESET)

def monitor_and_adjust():
    global current_voltage, current_frequency
    print(GREEN + f"Starting Bitaxe Temperature Monitor. Target temp: {target_temp}°C" + RESET)
    # Apply the initial settings once at the start
    set_system_settings(current_voltage, current_frequency)
    
    while running:
        info = get_system_info()
        if info is None:
            time.sleep(sample_interval)
            continue

        # Retrieve temperature and hashrate (if available)
        temp = info.get("temp")
        hash_rate = info.get("hashRate", 0)
        voltage_reported = info.get("voltage", 0)

        # Print current status
        status = (f"Temp: {temp}°C | "
                  f"Hashrate: {int(hash_rate)} GH/s | "
                  f"Voltage: {voltage_reported}mV | "
                  f"Current Settings -> Voltage: {current_voltage}mV, Frequency: {current_frequency}MHz")
        print(GREEN + status + RESET)

        # Decision logic based on temperature
        if temp is None:
            print(YELLOW + "Temperature reading not available. Retrying..." + RESET)
        elif temp > target_temp:
            # Temperature is too high: decrease performance parameters.
            print(RED + f"Temperature {temp}°C exceeds target of {target_temp}°C. Reducing settings." + RESET)
            # Try reducing frequency first if possible.
            if current_frequency - frequency_step >= min_allowed_frequency:
                current_frequency -= frequency_step
            # If frequency is already low, reduce voltage (if possible).
            elif current_voltage - voltage_step >= min_allowed_voltage:
                current_voltage -= voltage_step
            else:
                print(YELLOW + "Already at minimum allowed settings. Cannot reduce further." + RESET)
            set_system_settings(current_voltage, current_frequency)
        elif temp < (target_temp - temp_margin):
            # Temperature is comfortably low: try to increase performance if not at limits.
            print(YELLOW + f"Temperature {temp}°C is well below target. Attempting to increase performance." + RESET)
            # First, try increasing frequency if within limits.
            if current_frequency + frequency_step <= max_allowed_frequency:
                current_frequency += frequency_step
            # If frequency is at max, try increasing voltage if within limits.
            elif current_voltage + voltage_step <= max_allowed_voltage:
                current_voltage += voltage_step
            else:
                print(YELLOW + "Already at maximum allowed settings. No increase possible." + RESET)
            set_system_settings(current_voltage, current_frequency)
        else:
            # Temperature is within an acceptable range; no adjustment needed.
            print(GREEN + "Temperature within acceptable range. No adjustment needed." + RESET)
        time.sleep(sample_interval)

if __name__ == "__main__":
    try:
        monitor_and_adjust()
    except Exception as e:
        print(RED + f"An unexpected error occurred: {e}" + RESET)
    finally:
        print(GREEN + "Exiting monitor. Goodbye." + RESET)
