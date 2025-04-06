import requests
import time
import threading
from config import load_config, get_miners, get_miner_defaults, detect_miners
import pandas as pd

# Load global configuration
config = load_config()
VOLTAGE_STEP = config["voltage_step"]
FREQUENCY_STEP = config["frequency_step"]
MONITOR_INTERVAL = config["monitor_interval"]
TEMP_TOLERANCE = config["temp_tolerance"]

# Global Running Flag
running = True

def load_scaling_table():
    try:
        df = pd.read_csv("cpu_voltage_scaling_safeguards.csv")
        df = df.rename(columns=lambda x: x.strip().lower().replace(" ", "_"))
        df = df.sort_values(by="frequency_(mhz)").reset_index(drop=True)
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Failed to load CPU scaling table: {e}")
        return []

def get_target_hashrate_for_freq(freq, tier_list):
    """Return expected target hashrate for a given frequency from tier list."""
    sorted_tiers = sorted(tier_list, key=lambda x: x["frequency_(mhz)"])
    for tier in reversed(sorted_tiers):
        if freq >= tier["frequency_(mhz)"]:
            return tier.get("target_hashrate", 0)
    return sorted_tiers[0].get("target_hashrate", 0)

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

def get_tier_voltage_for_freq(freq, tier_list):
    """Return voltage for the closest frequency in tier list."""
    sorted_tiers = sorted(tier_list, key=lambda x: x["frequency_(mhz)"])
    for tier in reversed(sorted_tiers):
        if freq >= tier["frequency_(mhz)"]:
            return tier["voltage"]
    return sorted_tiers[0]["voltage"]

def monitor_and_adjust(bitaxe_ip, bitaxe_type, interval, log_callback,
                       min_freq, max_freq, min_volt, max_volt,
                       max_temp, max_watts, start_freq=None, start_volt=None):
    """Monitor and auto-adjust miner settings dynamically based on user-defined AutoTuner settings."""
    global running, tier_list
    running = True

    # Ensure all required settings are present
    required_fields = [min_freq, max_freq, min_volt, max_volt, max_temp, max_watts]
    if any(value is None or value == "" for value in required_fields):
        log_callback(f"{bitaxe_ip} -> Missing AutoTuner settings. Skipping tuning.", "error")
        running = False
        return

    current_frequency = start_freq if start_freq not in [None, ""] else min_freq
    current_voltage = start_volt if start_volt not in [None, ""] else min_volt

    target_hashrate = get_target_hashrate_for_freq(current_frequency, tier_list)

    frequency_range = max_freq - min_freq
    voltage_range = max_volt - min_volt

    # Apply initial settings
    applied_settings = set_system_settings(bitaxe_ip, current_voltage, current_frequency)
    log_callback(applied_settings, "info")

    last_config_refresh = 0
    config = load_config()  # Initial config

    while running:
        if time.time() - last_config_refresh > 5:
            config = load_config()
            last_config_refresh = time.time()

        voltage_step = config.get("voltage_step", 10)
        frequency_step = config.get("frequency_step", 5)
        temp_tolerance = config.get("temp_tolerance", 2)
        interval = config.get("monitor_interval", 5)

        info = get_system_info(bitaxe_ip)
        if not running:
            break

        if isinstance(info, str):
            log_callback(info, "error")
            time.sleep(interval)
            continue
        
        small_core_count = info.get("smallCoreCount")
        asic_count = info.get("asicCount")
        expected_hashrate = int(current_frequency * ((small_core_count * asic_count) / 1000))

        # Pull dynamic target hashrate from scaling table
        target_hashrate = get_target_hashrate_for_freq(current_frequency, tier_list)
        if target_hashrate is None:
            log_callback(f"{bitaxe_ip} -> WARNING: No target hashrate found for {current_frequency} MHz", "warning")
            target_hashrate = expected_hashrate  # Fallback to expected if missing

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

            if temp > max_temp or power_consumption > max_watts:
                log_callback(f"{bitaxe_ip} -> Overheating detected. Tier step-down engaged.", "error")

                # Drop to next lower tier (if available)
                tier_freqs = [t["frequency_(mhz)"] for t in tier_list]
                current_idx = tier_freqs.index(current_frequency) if current_frequency in tier_freqs else -1
                if current_idx > 0:
                    new_frequency = tier_freqs[current_idx - 1]
                    new_voltage = get_tier_voltage_for_freq(new_frequency, tier_list)
                    log_callback(f"{bitaxe_ip} -> Dropping to tier: {new_frequency} MHz / {new_voltage} mV", "warning")
                else:
                    log_callback(f"{bitaxe_ip} -> Already at minimum tier. Holding.", "warning")


        # NEW STEP-UP LOGIC BASED ON EXPECTED VS ACTUAL HASHRATE AND RANGE OF VOLTAGE AND FREQUENCY
        elif temp < (max_temp - temp_tolerance) and power_consumption < max_watts and hash_rate < expected_hashrate:
            log_callback(f"{bitaxe_ip} -> Temp {temp}°C. Checking if program should optimize.", "info")
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

            # Step-up logic
            if temp < (max_temp - temp_tolerance) and hash_rate < expected_hashrate:
                tier_freqs = [t["frequency_(mhz)"] for t in tier_list]
                current_idx = tier_freqs.index(current_frequency) if current_frequency in tier_freqs else -1
                if current_idx >= 0 and current_idx + 1 < len(tier_freqs):
                    new_frequency = tier_freqs[current_idx + 1]
                    new_voltage = get_tier_voltage_for_freq(new_frequency, tier_list)
                    log_callback(f"{bitaxe_ip} -> Stepping up to tier: {new_frequency} MHz / {new_voltage} mV", "info")
                else:
                    log_callback(f"{bitaxe_ip} -> Already at max tier or unknown freq. No step-up.", "info")

            else:
                log_callback(f"{bitaxe_ip} -> Hashrate is under target of {target_hashrate} GH/s, but already at max safe settings.", "warning")

        # HEALTHY HASHING
        elif hash_rate > expected_hashrate and hash_rate > target_hashrate:
            log_callback(f"{bitaxe_ip} -> Hashrate above target {target_hashrate} GH/s and healthy! No adjustments needed.<Increase hashrate target for better results.>", "success")
            #### ADD CODE HERE TO KEEP SETTINGS

        # DECREASE VOLTAGE AND FREQUENCY IF NO PROGRESS IS BEING MADE
        else:
            if new_voltage - voltage_step >= min_volt:
                new_voltage -= voltage_step # try to reduce voltage if progress isn't being made
            else:
                new_voltage = min_volt
            
            volt_range_percent = (new_voltage - min_volt)/voltage_range
            
            if new_frequency - frequency_step >= min_freq:
                new_frequency -= frequency_step # try to reduce frequency if progress isn't being made
            else:
                new_frequency = min_freq
            
            freq_range_percent = (new_frequency - min_freq)/frequency_range
            
            stepping_down = True

            log_callback(f"{bitaxe_ip} -> Inefficient hashing, decreasing voltage to {new_voltage}V / {int(volt_range_percent*100)}%. Decreasing frequency to {new_frequency}MHz / {int(freq_range_percent*100)}%", "warning")
        
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
            miner["ip"], miner["type"], MONITOR_INTERVAL, log_callback,
            miner.get("min_freq"), miner.get("max_freq"),
            miner.get("min_volt"), miner.get("max_volt"),
            miner.get("max_temp"), miner.get("max_watts"),
            miner.get("start_freq"), miner.get("start_volt")
        ))

        thread.start()
        threads.append(thread)

    return threads  # Return thread references to manage later

# Load the scaling table once at the start
scaling_table = load_scaling_table()
config = load_config()
enforce_tiers = config.get("enforce_safe_pairing", False)

# Always set tier_list based on enforcement
tier_list = scaling_table if enforce_tiers else []
