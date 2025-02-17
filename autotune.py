import requests
import time
from config import load_config

# Load configuration
config = load_config()

VOLTAGE_STEP = config["voltage_step"]
FREQUENCY_STEP = config["frequency_step"]
MIN_ALLOWED_VOLTAGE = config["min_allowed_voltage"]
MAX_ALLOWED_VOLTAGE = config["max_allowed_voltage"]
MIN_ALLOWED_FREQUENCY = config["min_allowed_frequency"]
MAX_ALLOWED_FREQUENCY = config["max_allowed_frequency"]
DEFAULT_TARGET_TEMP = config["default_target_temp"]
TEMP_TOLERANCE = config["temp_tolerance"]
POWER_LIMIT = config["power_limit"]
MONITOR_INTERVAL = config["monitor_interval"]


# Global Running Flag
running = True

# Get information from the Bitaxe
def get_system_info(bitaxe_ip):
    """Fetch system info from Bitaxe API."""
    try:
        response = requests.get(f"http://{bitaxe_ip}/api/system/info", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return f"Error fetching system info from {bitaxe_ip}: {e}"

# Set Bitaxe settings to settings from autotuning (monitor_and_adjust)
def set_system_settings(bitaxe_ip, core_voltage, frequency, retries=3, delay=3):
    """Set system parameters via Bitaxe API with retry mechanism. Retries 3x's before giving up."""
    settings = {"coreVoltage": core_voltage, "frequency": frequency}
    
    for attempt in range(retries):
        try:
            response = requests.patch(f"http://{bitaxe_ip}/api/system", json=settings, timeout=10)
            response.raise_for_status()
            return f"{bitaxe_ip} -> Applied settings: Voltage = {core_voltage}mV, Frequency = {frequency}MHz"
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(delay)  # Wait before retrying
            else:
                return f"{bitaxe_ip} -> Error setting system settings after {retries} attempts: {e}"

def monitor_and_adjust(bitaxe_ip, voltage, frequency, target_temp, interval, power_limit, min_hashrate, log_callback):
    """Monitor and auto-adjust miner settings for a specific IP."""
    global running
    current_voltage, current_frequency = voltage, frequency

    log_callback(f"Starting autotuning for {bitaxe_ip}", "success")

    # Initial settings
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

        temp, hash_rate, power_consumption = info.get("temp", 0), info.get("hashRate", 0), info.get("power", 0)
        log_callback(f"{bitaxe_ip} -> Temp: {temp}°C | Hashrate: {int(hash_rate)} GH/s | Power: {power_consumption}W", "success")

        new_voltage, new_frequency = current_voltage, current_frequency  # Default to current settings

        # **STEP-DOWN LOGIC**
        if temp is None or power_consumption > power_limit or temp > target_temp:
            log_callback(f"{bitaxe_ip} -> Overheating or Power Limit Exceeded! Lowering settings.", "error")
            if current_voltage - VOLTAGE_STEP >= MIN_ALLOWED_VOLTAGE:
                new_voltage -= VOLTAGE_STEP
            elif current_frequency - FREQUENCY_STEP >= MIN_ALLOWED_FREQUENCY:
                new_frequency -= FREQUENCY_STEP

        # **STEP-UP LOGIC**
        elif temp < (target_temp - 3) and power_consumption < (power_limit * 0.9):
            log_callback(f"{bitaxe_ip} -> Temp {temp}°C is low. Trying to optimize.", "warning")
            if current_frequency + FREQUENCY_STEP <= MAX_ALLOWED_FREQUENCY:
                new_frequency += FREQUENCY_STEP
            elif current_voltage + VOLTAGE_STEP <= MAX_ALLOWED_VOLTAGE:
                new_voltage += VOLTAGE_STEP

        # **HASHRATE RECOVERY & MINIMUM HASH RATE TARGET**
        elif hash_rate < min_hashrate:
            log_callback(f"{bitaxe_ip} -> Hashrate below {min_hashrate} GH/s! Adjusting settings.", "warning")
            if current_voltage + VOLTAGE_STEP <= MAX_ALLOWED_VOLTAGE:
                new_voltage += VOLTAGE_STEP
            elif current_frequency + FREQUENCY_STEP <= MAX_ALLOWED_FREQUENCY:
                new_frequency += FREQUENCY_STEP
    
def stop_autotuning(self):
    """Stops autotuning miners and ensures threads are properly terminated."""
    global running
    running = False  # Stop the running autotuning loop

    for thread in self.threads:
        if thread.is_alive():
            thread.join(timeout=2)  # Give time for threads to terminate

    self.threads.clear()  # Clean up thread list
    self.log_message("Stopping autotuning...", "warning")
