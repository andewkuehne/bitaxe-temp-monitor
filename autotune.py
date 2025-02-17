import requests
import time

# ============================
# CONFIGURATION PARAMETERS
# ============================
VOLTAGE_STEP = 10  # mV adjustment step
FREQUENCY_STEP = 5  # MHz adjustment step

# Voltage Limits
MIN_ALLOWED_VOLTAGE = 1000  # mV
MAX_ALLOWED_VOLTAGE = 1300  # mV

# Frequency Limits
MIN_ALLOWED_FREQUENCY = 650  # MHz
MAX_ALLOWED_FREQUENCY = 1000  # MHz

# Temperature Limits
DEFAULT_TARGET_TEMP = 50  # °C
TEMP_TOLERANCE = 2  # Allowable fluctuation range before adjusting

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
    """Set system parameters via Bitaxe API."""
    settings = {"coreVoltage": core_voltage, "frequency": frequency}
    try:
        response = requests.patch(f"http://{bitaxe_ip}/api/system", json=settings, timeout=10)
        response.raise_for_status()
        return f"{bitaxe_ip} -> Applied settings: Voltage = {core_voltage}mV, Frequency = {frequency}MHz"
    except requests.exceptions.RequestException as e:
        return f"{bitaxe_ip} -> Error setting system settings: {e}"

def monitor_and_adjust(bitaxe_ip, voltage, frequency, target_temp, interval, power_limit, log_callback):
    """Monitor and auto-adjust miner settings for a specific IP."""
    global running
    current_voltage, current_frequency = voltage, frequency

    log_callback(f"Starting autotuning for {bitaxe_ip}", "success")
    log_callback(set_system_settings(bitaxe_ip, current_voltage, current_frequency), "info")

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

        # Adjust settings based on conditions
        if temp > target_temp or power_consumption > power_limit:
            log_callback(f"{bitaxe_ip} -> Adjusting settings due to high temp/power!", "warning")
            if current_frequency - FREQUENCY_STEP >= MIN_ALLOWED_FREQUENCY:
                current_frequency -= FREQUENCY_STEP
            elif current_voltage - VOLTAGE_STEP >= MIN_ALLOWED_VOLTAGE:
                current_voltage -= VOLTAGE_STEP

        elif temp < (target_temp - TEMP_TOLERANCE):
            log_callback(f"{bitaxe_ip} -> Trying to optimize performance.", "info")
            if current_frequency + FREQUENCY_STEP <= MAX_ALLOWED_FREQUENCY:
                current_frequency += FREQUENCY_STEP
            elif current_voltage + VOLTAGE_STEP <= MAX_ALLOWED_VOLTAGE:
                current_voltage += VOLTAGE_STEP

        log_callback(set_system_settings(bitaxe_ip, current_voltage, current_frequency), "info")
        time.sleep(interval)

    log_callback(f"{bitaxe_ip} -> Autotuning stopped.", "warning")

def stop_autotuning():
    """Stops all autotuning threads."""
    global running
    running = False
