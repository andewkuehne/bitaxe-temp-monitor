import requests
import time
import signal
import sys
import argparse
import threading

# ANSI Color Codes for console output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

# Flag to control all monitoring loops
running = True

# Signal handler for graceful exit
def handle_sigint(signum, frame):
    global running
    print(RED + "\nExiting Bitaxe Monitor." + RESET)
    running = False

signal.signal(signal.SIGINT, handle_sigint)

# Parse command-line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description="Bitaxe Temperature Monitor and Auto-Tuner")
    parser.add_argument('bitaxe_ips', nargs='+', help="List of IP addresses of Bitaxe miners (e.g., 192.168.2.26 192.168.2.27)")
    parser.add_argument('-v', '--voltage', type=int, default=1150, help="Initial core voltage in mV (default: 1150)")
    parser.add_argument('-f', '--frequency', type=int, default=525, help="Initial frequency in MHz (default: 525)")
    parser.add_argument('-t', '--target_temp', type=int, default=50, help="Target CPU temperature in °C (default: 50)")
    parser.add_argument('-i', '--interval', type=int, default=5, help="Monitoring sample interval in seconds (default: 5)")
    parser.add_argument('-p', '--power_limit', type=int, default=25, help="Power supply wattage limit (default: 25W)")
    return parser.parse_args()

args = parse_arguments()

# Configuration parameters
voltage_step = 10  # mV adjustment step
frequency_step = 5  # MHz adjustment step
min_allowed_voltage = 1000  # mV
max_allowed_voltage = 1300  # mV
min_allowed_frequency = 500  # MHz
max_allowed_frequency = 1000  # MHz

def get_system_info(bitaxe_ip):
    """Fetch system info from Bitaxe API."""
    try:
        response = requests.get(f"http://{bitaxe_ip}/api/system/info", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(YELLOW + f"Error fetching system info from {bitaxe_ip}: {e}" + RESET)
        return None

def set_system_settings(bitaxe_ip, core_voltage, frequency):
    """Set system parameters via Bitaxe API."""
    settings = {
        "coreVoltage": core_voltage,
        "frequency": frequency
    }
    try:
        response = requests.patch(f"http://{bitaxe_ip}/api/system", json=settings, timeout=10)
        response.raise_for_status()
        print(YELLOW + f"{bitaxe_ip} -> Applying settings: Voltage = {core_voltage}mV, Frequency = {frequency}MHz" + RESET)
        time.sleep(2)
    except requests.exceptions.RequestException as e:
        print(RED + f"{bitaxe_ip} -> Error setting system settings: {e}" + RESET)

def monitor_and_adjust(bitaxe_ip):
    """Monitor and auto-adjust miner settings for a specific IP."""
    global running
    current_voltage = args.voltage
    current_frequency = args.frequency
    target_temp = args.target_temp
    sample_interval = args.interval
    power_limit = args.power_limit

    print(GREEN + f"Starting Bitaxe Monitor for {bitaxe_ip}. Target temp: {target_temp}°C" + RESET)
    set_system_settings(bitaxe_ip, current_voltage, current_frequency)

    while running:
        info = get_system_info(bitaxe_ip)
        if info is None:
            time.sleep(sample_interval)
            continue

        temp = info.get("temp")
        hash_rate = info.get("hashRate", 0)
        voltage_reported = info.get("voltage", 0)
        power_consumption = info.get("power", 0)

        status = (f"{bitaxe_ip} -> Temp: {temp}°C | Hashrate: {int(hash_rate)} GH/s | "
                  f"Power: {power_consumption}W | Voltage: {voltage_reported}mV | "
                  f"Current Settings -> Voltage: {current_voltage}mV, Frequency: {current_frequency}MHz")
        print(GREEN + status + RESET)

        if temp is None or power_consumption > power_limit:
            print(RED + f"{bitaxe_ip} -> Power limit exceeded! Lowering settings." + RESET)
            if current_frequency - frequency_step >= min_allowed_frequency:
                current_frequency -= frequency_step
            elif current_voltage - voltage_step >= min_allowed_voltage:
                current_voltage -= voltage_step
            set_system_settings(bitaxe_ip, current_voltage, current_frequency)

        elif temp > target_temp:
            print(RED + f"{bitaxe_ip} -> Temp {temp}°C exceeds limit. Lowering settings." + RESET)
            if current_frequency - frequency_step >= min_allowed_frequency:
                current_frequency -= frequency_step
            elif current_voltage - voltage_step >= min_allowed_voltage:
                current_voltage -= voltage_step
            set_system_settings(bitaxe_ip, current_voltage, current_frequency)

        elif temp < (target_temp - 2):
            print(YELLOW + f"{bitaxe_ip} -> Temp {temp}°C is low. Trying to optimize." + RESET)
            if current_frequency + frequency_step <= max_allowed_frequency:
                current_frequency += frequency_step
            elif current_voltage + voltage_step <= max_allowed_voltage:
                current_voltage += voltage_step
            set_system_settings(bitaxe_ip, current_voltage, current_frequency)

        elif hash_rate < 1600:
            print(YELLOW + f"{bitaxe_ip} -> Hashrate underperforming! Adjusting voltage." + RESET)
            if current_voltage + voltage_step <= max_allowed_voltage:
                current_voltage += voltage_step
                set_system_settings(bitaxe_ip, current_voltage, current_frequency)

        else:
            print(GREEN + f"{bitaxe_ip} -> Stable. No adjustment needed." + RESET)

        time.sleep(sample_interval)

if __name__ == "__main__":
    try:
        threads = []
        for ip in args.bitaxe_ips:
            thread = threading.Thread(target=monitor_and_adjust, args=(ip,))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()
    except Exception as e:
        print(RED + f"An unexpected error occurred: {e}" + RESET)
    finally:
        print(GREEN + "Exiting monitor. Goodbye." + RESET)
