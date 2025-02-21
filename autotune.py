import requests
import time
import threading
from config import load_config, get_miners, get_miner_defaults, detect_miners

# Load global configuration
config = load_config()

VOLTAGE_STEP = config["voltage_step"]
FREQUENCY_STEP = config["frequency_step"]
MONITOR_INTERVAL = config["monitor_interval"]
TEMP_TOLERANCE = config["temp_tolerance"]

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

    voltage_step = VOLTAGE_STEP
    frequency_step = FREQUENCY_STEP
    temp_tolerance = TEMP_TOLERANCE

    frequency_range = max_freq - min_freq
    voltage_range = max_volt - min_volt

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
        
        small_core_count = info.get("smallCoreCount")
        asic_count = info.get("asicCount")
        expected_hashrate = int(current_frequency * ((small_core_count * asic_count) / 1000)) # Calculate expected hashrate

        temp = info.get("temp", 0)
        vr_temp = info.get("vrTemp",0)
        hash_rate = info.get("hashRate", 0)
        power_consumption = info.get("power", 0)

        log_callback(f"{bitaxe_ip} -> Temp: {temp}°C | Hashrate: {int(hash_rate)}/{expected_hashrate} GH/s | Power: {round(power_consumption,2)}W | Voltage: {current_voltage}V | Frequency: {current_frequency} MHz",
                     "success")

        new_voltage, new_frequency = current_voltage, current_frequency
        volt_range_percent = (current_voltage - min_volt)/voltage_range # percentage from min to max voltage of where current voltage is
        freq_range_percent = (current_frequency - min_freq)/frequency_range # percentage from min to max voltage of where current voltage is

        stepping_down = False

        # **STEP-DOWN LOGIC**
        if temp is None or power_consumption > max_watts or temp > max_temp or vr_temp > (max_temp * 1.5):
            log_callback(f"{bitaxe_ip} -> Overheating by ({temp}/{max_temp}°C) or Power Limit of {max_watts}W Exceeded! Using {round(power_consumption,2)}W...Lowering settings.", "error")

            stepping_down = True # flag to take more time between changes to avoid hashrate falling off cliff

            if current_voltage - voltage_step >= min_volt:
                new_voltage -= voltage_step
                log_callback(f"{bitaxe_ip} -> Lowering voltage to {new_voltage}mV.", "warning")
            elif current_frequency - frequency_step >= min_freq:
                new_frequency -= frequency_step
                log_callback(f"{bitaxe_ip} -> Lowering frequency to {new_frequency}MHz.", "warning")
            else:
                log_callback(f"{bitaxe_ip} -> Minimum settings reached! Holding state.", "error")


        # NEW STEP-UP LOGIC BASED ON EXPECTED VS ACTUAL HASHRATE AND RANGE OF VOLTAGE AND FREQUENCY
        elif temp < (max_temp - temp_tolerance) and power_consumption < max_watts and hash_rate < expected_hashrate:
            log_callback(f"{bitaxe_ip} -> Temp {temp}°C is low. Trying to optimize.", "info")
            # checking in interval steps of 25%
            if ((freq_range_percent >= 0.25 and volt_range_percent <= 0.25) or
                (freq_range_percent >= 0.5 and volt_range_percent <= 0.5) or
                (freq_range_percent >= 0.75 and volt_range_percent <= 0.75)):
                
                new_voltage += voltage_step
                volt_range_percent = (new_voltage - min_volt)/voltage_range

                log_callback(f"{bitaxe_ip} -> Increasing voltage to {new_voltage}mV / {int(volt_range_percent*100)}% for stability.", "info")

            elif ((freq_range_percent < 0.25 and volt_range_percent <= 0.25) or
                (freq_range_percent < 0.5 and volt_range_percent <= 0.5) or
                (freq_range_percent < 0.75 and volt_range_percent <= 0.75)):

                new_frequency += frequency_step
                freq_range_percent = (new_frequency - min_freq)/frequency_range

                log_callback(f"{bitaxe_ip} -> Increasing frequency to {new_frequency}MHz / {int(freq_range_percent*100)}%", "info")

            else:
                log_callback(f"{bitaxe_ip} -> Already at maximum safe settings.", "info")

        # NEW HASHRATE FINE-TUNING BASED ON EXPECTED VS ACTUAL HASHRATE
        elif hash_rate > expected_hashrate and hash_rate < target_hashrate:
            log_callback(f"{bitaxe_ip} -> Hashrate below target hashrate {target_hashrate} GH/s! Adjusting settings.", "warning")

            if current_frequency + frequency_step <= max_freq:
                new_frequency += frequency_step
                freq_range_percent = (new_frequency - min_freq)/frequency_range

                log_callback(f"{bitaxe_ip} -> Increasing frequency to {new_frequency}MHz / {int(freq_range_percent*100)}% to fine-tune hashrate.", "info")

            elif current_voltage + voltage_step <= max_volt:
                new_voltage += voltage_step
                volt_range_percent = (new_voltage - min_volt)/voltage_range

                log_callback(f"{bitaxe_ip} -> Increasing voltage to {new_voltage}mV / {int(volt_range_percent*100)}% for hashrate fine-tuning.", "info")

            else:
                log_callback(f"{bitaxe_ip} -> Hashrate is under target of {target_hashrate} GH/s, but already at max safe settings.", "warning")

        # HEALTHY HASHING
        elif hash_rate > expected_hashrate and hash_rate > target_hashrate:
            log_callback(f"{bitaxe_ip} -> Hashrate above target {target_hashrate} GH/s and healthy! No adjustments needed.<Increase hashrate target for better results.>", "success")

        # # DECREASE VOLTAGE IF NO PROGRESS IS BEING MADE
        # else:
        #     if new_voltage - (voltage_step * 2) >= min_volt:
        #         new_voltage -= (voltage_step * 2) # try to reduce voltage if progress isn't being made
        #     else:
        #         new_voltage = min_volt
            
        #     volt_range_percent = (new_voltage - min_volt)/voltage_range
            
        #     stepping_down = True

        #     log_callback(f"{bitaxe_ip} -> Inefficinet hashing, decreasing voltage to {new_voltage}v / {int(volt_range_percent*100)}%.", "warning")
        
        # Apply changes dynamically without restarting
        if new_voltage != current_voltage or new_frequency != current_frequency:
            applied_settings = set_system_settings(bitaxe_ip, new_voltage, new_frequency)
            log_callback(applied_settings, "info")
            current_voltage, current_frequency = new_voltage, new_frequency

        if stepping_down:
            time.sleep(interval*3) #gives more time for step down so the hashrate doesn't crash
        else:
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
