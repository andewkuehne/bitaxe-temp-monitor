import requests
import time
import threading
from config import load_config, get_miners, get_miner_defaults, detect_miners

# Load global configuration
config = load_config()

VOLTAGE_STEP = config["voltage_step"]
FREQUENCY_STEP = config["frequency_step"]
MONITOR_INTERVAL = config["monitor_interval"]

# Global Running Flag
running = True

def get_system_info(bitaxe_ip):
    """Fetch system info from Bitaxe API."""
    try:
        response = requests.get(f"http://{bitaxe_ip}/api/system/info", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return f"Error fetching system info from {bitaxe_ip}: {e}"

def set_system_settings(bitaxe_ip, core_voltage, frequency):
    """Set system parameters via Bitaxe API dynamically."""
    settings = {"coreVoltage": core_voltage, "frequency": frequency}
    try:
        response = requests.patch(f"http://{bitaxe_ip}/api/system", json=settings, timeout=10)
        response.raise_for_status()
        return f"{bitaxe_ip} -> Applied settings: Voltage = {core_voltage}mV, Frequency = {frequency}MHz"
    except requests.exceptions.RequestException as e:
        return f"{bitaxe_ip} -> Error setting system settings: {e}"

def restart_bitaxe(bitaxe_ip):
    """Restart the Bitaxe using the API."""
    try:
        response = requests.post(f"http://{bitaxe_ip}/api/system/restart", timeout=10)
        response.raise_for_status()
        return f"{bitaxe_ip} -> Restart initiated."
    except requests.exceptions.RequestException as e:
        return f"{bitaxe_ip} -> Error restarting system: {e}"

def monitor_and_adjust(bitaxe_ip, bitaxe_type, interval, log_callback,
                        min_freq, max_freq, min_volt, max_volt,
                        max_temp, max_watts, target_hashrate):
    """Monitor and auto-adjust miner settings dynamically based on user-defined AutoTuner settings."""
    global running
    running = True

    # Ensure all required settings are present
    required_fields = [min_freq, max_freq, min_volt, max_volt, max_temp, max_watts, target_hashrate]
    if any(value is None or value == "" for value in required_fields):
        log_callback(f"{bitaxe_ip} -> Missing AutoTuner settings. Skipping tuning.", "error")
        running = False
        return

    current_voltage = min_volt
    current_frequency = min_freq

    # Apply initial settings
    applied_settings = set_system_settings(bitaxe_ip, current_voltage, current_frequency)
    log_callback(applied_settings, "info")

    while running:
        info = get_system_info(bitaxe_ip)
        if not running:
            break

        if isinstance(info, str):
            log_callback(info, "error")
            time.sleep(interval)
            continue

        temp = info.get("temp", 0)
        hash_rate = info.get("hashRate", 0)
        power_consumption = info.get("power", 0)

        log_callback(f"{bitaxe_ip} -> Temp: {temp}°C | Hashrate: {int(hash_rate)} GH/s | Power: {power_consumption}W",
                     "success")

        new_voltage, new_frequency = current_voltage, current_frequency

        # **STEP-DOWN LOGIC**
        if temp is None or power_consumption > max_watts or temp > max_temp:
            log_callback(f"{bitaxe_ip} -> Overheating or Power Limit Exceeded! Lowering settings.", "error")

            if current_voltage - 10 >= min_volt:
                new_voltage -= 10
                log_callback(f"{bitaxe_ip} -> Lowering voltage to {new_voltage}mV.", "warning")
            elif current_frequency - 5 >= min_freq:
                new_frequency -= 5
                log_callback(f"{bitaxe_ip} -> Lowering frequency to {new_frequency}MHz.", "warning")
            else:
                log_callback(f"{bitaxe_ip} -> Minimum settings reached! Holding state.", "error")

        # **STEP-UP LOGIC**
        elif temp < (max_temp - 3) and power_consumption < (max_watts * 0.9):
            log_callback(f"{bitaxe_ip} -> Temp {temp}°C is low. Trying to optimize.", "info")

            if current_voltage + 10 <= max_volt:
                new_voltage += 10
                log_callback(f"{bitaxe_ip} -> Increasing voltage to {new_voltage}mV for stability.", "info")
            elif current_frequency + 5 <= max_freq:
                new_frequency += 5
                log_callback(f"{bitaxe_ip} -> Increasing frequency to {new_frequency}MHz.", "info")
            else:
                log_callback(f"{bitaxe_ip} -> Already at maximum safe settings.", "info")

        # **HASHRATE RECOVERY**
        elif hash_rate < target_hashrate:
            log_callback(f"{bitaxe_ip} -> Hashrate below {target_hashrate} GH/s! Adjusting settings.", "warning")

            if current_voltage + 10 <= max_volt:
                new_voltage += 10
                log_callback(f"{bitaxe_ip} -> Increasing voltage to {new_voltage}mV for hashrate recovery.", "info")
            elif current_frequency + 5 <= max_freq:
                new_frequency += 5
                log_callback(f"{bitaxe_ip} -> Increasing frequency to {new_frequency}MHz to recover hashrate.", "info")
            else:
                log_callback(f"{bitaxe_ip} -> Hashrate is low, but already at max safe settings.", "warning")

        # Apply changes dynamically without restarting
        if new_voltage != current_voltage or new_frequency != current_frequency:
            applied_settings = set_system_settings(bitaxe_ip, new_voltage, new_frequency)
            log_callback(applied_settings, "info")
            current_voltage, current_frequency = new_voltage, new_frequency

        time.sleep(interval)

    log_callback(f"{bitaxe_ip} -> Autotuning stopped.", "warning")

def stop_autotuning():
    """Stops autotuning miners globally."""
    global running
    running = False

def start_autotuning_all(log_callback):
    """Starts autotuning for all configured miners."""

    # Detect new miners before starting
    log_callback("Scanning network for new miners...", "info")
    detect_miners()

    miners = get_miners()
    if not miners:
        log_callback("No miners configured. Please add miners in the GUI.", "error")
        return

    threads = []
    for miner in miners:
        thread = threading.Thread(target=monitor_and_adjust, args=(
            miner["ip"], miner["type"], MONITOR_INTERVAL, log_callback
        ))
        thread.start()
        threads.append(thread)

    return threads  # Return thread references to manage later
