import json
import os
import requests
import ipaddress

CONFIG_FILE = "config.json"

def detect_miners(start_ip, end_ip):
    """Scan a user-defined IP range and detect Bitaxe miners."""

    # Convert IPs to IPv4 objects
    try:
        start_ip = ipaddress.IPv4Address(start_ip)
        end_ip = ipaddress.IPv4Address(end_ip)
    except ipaddress.AddressValueError:
        print("Error: Invalid IP range provided.")
        return []

    detected_miners = []
    config = load_config()

    for ip in range(int(start_ip), int(end_ip) + 1):
        ip_str = str(ipaddress.IPv4Address(ip))
        try:
            response = requests.get(f"http://{ip_str}/api/system/info", timeout=1)
            if response.status_code == 200:
                miner_info = response.json()
                model = miner_info.get("model", "Unknown")

                # Prevent duplicate miner entries
                if not any(m["ip"] == ip_str for m in config["miners"]):
                    detected_miners.append({
                        "nickname": f"Miner-{ip_str}",
                        "ip": ip_str,
                        "type": model,
                        "min_freq": miner_info.get("min_freq", ""),
                        "max_freq": miner_info.get("max_freq", ""),
                        "min_volt": miner_info.get("min_volt", ""),
                        "max_volt": miner_info.get("max_volt", ""),
                        "max_temp": miner_info.get("max_temp", ""),
                        "max_watts": miner_info.get("max_watts", ""),
                        "target_hashrate": miner_info.get("target_hashrate", "")
                    })
                    print(f"Detected miner: {model} at {ip_str}, added as {detected_miners[-1]['nickname']}")

        except requests.exceptions.RequestException:
            continue

    if detected_miners:
        config["miners"].extend(detected_miners)
        save_config(config)

    return detected_miners

def load_config():
    """Load configuration settings from config.json."""
    if not os.path.exists(CONFIG_FILE):
        save_config(get_default_config())

    try:
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        save_config(get_default_config())
        return get_default_config()

def save_config(config):
    """Save configuration settings to config.json."""
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file, indent=4)

def get_default_config():
    """Returns default configuration settings."""
    return {
        "voltage_step": 10,
        "frequency_step": 5,
        "monitor_interval": 5,
        "default_target_temp": 50,
        "temp_tolerance": 2,
        "refresh_interval": 5,  # Default miner status refresh rate in seconds
        "enforce_safe_pairing": True,
        "miners": []  # No predefined models, settings are per miner
    }

def get_miner_defaults(miner_ip):
    """Returns the AutoTuner settings for a given miner's IP address."""
    config = load_config()
    for miner in config["miners"]:
        if miner["ip"] == miner_ip:
            return miner  # Return the miner's settings
    return {}  # Return empty dict if not found

def add_miner(miner_type, ip, nickname=""):
    """Adds a new miner with default settings based on type, including nickname."""
    config = load_config()

    # Prevent duplicate miner entries
    if any(miner["ip"] == ip for miner in config["miners"]):
        print(f"Error: Miner with IP {ip} already exists.")
        return

    new_miner = {
        "nickname": nickname,
        "type": miner_type,
        "ip": ip,
        "min_freq": "",
        "max_freq": "",
        "start_freq": "",
        "min_volt": "",
        "max_volt": "",
        "start_volt": "",
        "max_temp": "",
        "max_watts": "",
        "target_hashrate": ""
    }

    config["miners"].append(new_miner)
    save_config(config)
    print(f"Added new miner: ({miner_type}) at {ip} with nickname '{nickname}'")

def remove_miner(ip):
    """Removes a miner from the config by IP address."""
    config = load_config()
    new_miners = [miner for miner in config["miners"] if miner["ip"] != ip]

    if len(new_miners) == len(config["miners"]):
        print(f"Error: Miner with IP {ip} not found.")
        return

    config["miners"] = new_miners
    save_config(config)
    print(f"Removed miner with IP: {ip}")

def update_miner(ip, new_settings):
    """Updates an existing miner's settings in config.json."""
    config = load_config()
    updated = False

    for miner in config["miners"]:
        if miner["ip"] == ip:
            miner.update(new_settings)
            updated = True
            break

    if updated:
        save_config(config)
        print(f"Updated miner {ip} settings successfully.")
    else:
        print(f"Error: Miner {ip} not found.")

def get_miners():
    """Returns the list of configured miners."""
    return load_config().get("miners", [])

def reset_config():
    """Resets configuration to default settings."""
    save_config(get_default_config())
    print("Configuration reset to default.")

if __name__ == "__main__":
    print("Scanning for Bitaxe miners...")
    miners = detect_miners("192.168.0.1", "192.168.0.255")  # Example default scan range
    if miners:
        print(f"Found {len(miners)} miners: {miners}")
    else:
        print("No miners found.")
