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
    """Return expected target hashrate (in GH/s) for a given frequency from tier list (CSV stores TH/s)."""
    if not tier_list:
        return 0  # Prevents IndexError when enforcement is disabled

    sorted_tiers = sorted(tier_list, key=lambda x: x["frequency_(mhz)"])
    for tier in reversed(sorted_tiers):
        if freq >= tier["frequency_(mhz)"]:
            # Convert TH/s to GH/s by multiplying by 1000
            return tier.get("target_hashrate", 0)
    return sorted_tiers[0].get("target_hashrate", 0) * 1000


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
                       max_temp, max_watts, start_freq=None, start_volt=None, max_vr_temp=None):
    """Monitor and auto-adjust miner settings dynamically based on user-defined AutoTuner settings."""
    global running, tier_list

    running = True
    last_tune_time = 0   # Timestamp of last tuning action

    # Load the scaling table once at the start
    scaling_table = load_scaling_table()
    config = load_config()
    enforce_tiers = config.get("enforce_safe_pairing", False)
    # Always set tier_list based on enforcement
    tier_list = scaling_table if enforce_tiers else []

    # Flatline detection
    hashrate_history = []
    flatline_repeat_count = config.get("flatline_hashrate_repeat_count", 5)
    flatline_enabled = config.get("flatline_detection_enabled", True)

    required_fields = [min_freq, max_freq, min_volt, max_volt, max_temp, max_watts]
    if any(value is None or value == "" for value in required_fields):
        log_callback(f"{bitaxe_ip} -> Missing AutoTuner settings. Skipping tuning.", "error")
        running = False
        return

    current_frequency = start_freq if start_freq not in [None, ""] else min_freq
    current_voltage = start_volt if start_volt not in [None, ""] else min_volt

    frequency_range = max_freq - min_freq
    voltage_range = max_volt - min_volt

    applied_settings = set_system_settings(bitaxe_ip, current_voltage, current_frequency)
    log_callback(applied_settings, "info")

    last_config_refresh = 0
    config = load_config()

    while running:
        if time.time() - last_config_refresh > 5:
            config = load_config()
            last_config_refresh = time.time()

        voltage_step = config.get("voltage_step", 10)
        frequency_step = config.get("frequency_step", 5)
        temp_tolerance = config.get("temp_tolerance", 2)
        interval = config.get("monitor_interval", 5)
        refresh_interval = config.get("refresh_interval", 60)

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

        target_hashrate = get_target_hashrate_for_freq(current_frequency, tier_list)

        if target_hashrate is None:
            log_callback(f"{bitaxe_ip} -> WARNING: No target hashrate found for {current_frequency} MHz", "warning")
            target_hashrate = expected_hashrate

        temp = info.get("temp", 0)
        vr_temp = info.get("vrTemp", 0)
        hash_rate = info.get("hashRate", 0)
        power_consumption = info.get("power", 0)

        # Track flatline hashrate history
        hashrate_history.append(hash_rate)
        if len(hashrate_history) > flatline_repeat_count:
            hashrate_history.pop(0)

        if flatline_enabled and len(set(hashrate_history)) == 1 and len(hashrate_history) == flatline_repeat_count:
            log_callback(f"{bitaxe_ip} -> Flatline detected ({hash_rate} GH/s). Restarting...", "error")
            restart_bitaxe(bitaxe_ip)
            hashrate_history.clear()
            time.sleep(60)  # Allow reboot cooldown
            continue  # Skip tuning for this cycle

        log_callback(f"{bitaxe_ip} -> Temp: {temp}°C | Hashrate: {int(hash_rate)}/{expected_hashrate} GH/s | Power: {round(power_consumption,2)}W | Voltage: {current_voltage}V | Frequency: {current_frequency} MHz", "success")

        now = time.time()
        new_voltage, new_frequency = current_voltage, current_frequency
        volt_range_percent = (current_voltage - min_volt)/voltage_range
        freq_range_percent = (current_frequency - min_freq)/frequency_range
        stepping_down = False

        # Only run tuning logic if refresh_interval has passed
        if now - last_tune_time >= refresh_interval:
            if temp is None or power_consumption > max_watts or temp > max_temp or vr_temp > max_vr_temp:
                # ... (step-down logic unchanged)
                stepping_down = True
                # Drop to next lower tier if possible
                tier_freqs = [t["frequency_(mhz)"] for t in tier_list]
                current_idx = tier_freqs.index(current_frequency) if current_frequency in tier_freqs else -1
                if current_idx > 0:
                    new_frequency = tier_freqs[current_idx - 1]
                    new_voltage = get_tier_voltage_for_freq(new_frequency, tier_list)
                    log_callback(f"{bitaxe_ip} -> Dropping to tier: {new_frequency} MHz / {new_voltage} mV", "warning")
                else:
                    log_callback(f"{bitaxe_ip} -> Already at minimum tier. Holding.", "warning")

            elif temp < (max_temp - temp_tolerance) and power_consumption < max_watts and hash_rate < expected_hashrate:
                log_callback(f"{bitaxe_ip} -> Temp {temp}°C. Checking if program should optimize.", "info")
                if ((freq_range_percent >= 0.25 and volt_range_percent <= 0.25) or
                    (freq_range_percent >= 0.5 and volt_range_percent <= 0.5) or
                    (freq_range_percent >= 0.75 and volt_range_percent <= 0.75)):
                    new_voltage += voltage_step
                    log_callback(f"{bitaxe_ip} -> Increasing voltage to {new_voltage}mV.", "info")
                elif ((freq_range_percent < 0.25 and volt_range_percent <= 0.25) or
                      (freq_range_percent < 0.5 and volt_range_percent <= 0.5) or
                      (freq_range_percent < 0.75 and volt_range_percent <= 0.75)):
                    new_frequency += frequency_step
                    log_callback(f"{bitaxe_ip} -> Increasing frequency to {new_frequency}MHz.", "info")
                else:
                    log_callback(f"{bitaxe_ip} -> Already at maximum safe settings.", "info")

            elif hash_rate > expected_hashrate and hash_rate < target_hashrate:
                log_callback(f"{bitaxe_ip} -> Hashrate below target hashrate {target_hashrate} GH/s.", "warning")
                tier_freqs = [t["frequency_(mhz)"] for t in tier_list]
                current_idx = tier_freqs.index(current_frequency) if current_frequency in tier_freqs else -1
                if current_idx >= 0 and current_idx + 1 < len(tier_freqs):
                    new_frequency = tier_freqs[current_idx + 1]
                    new_voltage = get_tier_voltage_for_freq(new_frequency, tier_list)
                    log_callback(f"{bitaxe_ip} -> Stepping up to tier: {new_frequency} MHz / {new_voltage} mV", "info")

            elif hash_rate > expected_hashrate and hash_rate > target_hashrate:
                log_callback(f"{bitaxe_ip} -> Hashrate above target and healthy. No adjustment needed.", "success")

            else:
                if new_voltage - voltage_step >= min_volt:
                    new_voltage -= voltage_step
                else:
                    new_voltage = min_volt
                if new_frequency - frequency_step >= min_freq:
                    new_frequency -= frequency_step
                else:
                    new_frequency = min_freq
                stepping_down = True
                log_callback(f"{bitaxe_ip} -> Decreasing voltage and frequency due to inefficiency.", "warning")

            if new_voltage != current_voltage or new_frequency != current_frequency:
                applied_settings = set_system_settings(bitaxe_ip, new_voltage, new_frequency)
                log_callback(applied_settings, "info")
                current_voltage, current_frequency = new_voltage, new_frequency
                last_tune_time = now

        if stepping_down:
            time.sleep(interval * 3)
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
            miner.get("start_freq"), miner.get("start_volt"),
            miner.get("max_vr_temp")
        ))

        thread.start()
        threads.append(thread)

    return threads  # Return thread references to manage later

