import json
import os

CONFIG_FILE = "config.json"

# Default miner models and configurations
BITAXE_MODELS = {
    "Gamma": {"min_freq": 525, "max_freq": 1275, "min_volt": 1000, "max_volt": 1300, "max_temp": 65, "max_watts": 25, "target_hashrate": 1400},
    "Supra": {"min_freq": 700, "max_freq": 1100, "min_volt": 1050, "max_volt": 1350, "max_temp": 65, "max_watts": 25, "target_hashrate": 700},
    "Ultra": {"min_freq": 750, "max_freq": 1200, "min_volt": 1100, "max_volt": 1400, "max_temp": 65, "max_watts": 25, "target_hashrate": 400},
    "Hex": {"min_freq": 800, "max_freq": 1250, "min_volt": 1150, "max_volt": 1450, "max_temp": 65, "max_watts": 25, "target_hashrate": 200}
}

def load_config():
    """Load configuration settings from config.json. If missing or corrupted, create a new one."""
    if not os.path.exists(CONFIG_FILE):
        print(f"Config file {CONFIG_FILE} not found! Creating a new one with default settings...")
        save_config(get_default_config())

    try:
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        print("Error: Config file is corrupted or missing. Resetting to default settings.")
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
        "models": BITAXE_MODELS,  # Store model defaults in config
        "miners": []
    }

def get_miner_defaults(miner_type):
    """Returns the default settings for a given Bitaxe type."""
    config = load_config()
    return config["models"].get(miner_type, {})

def add_miner(miner_type, ip):
    """Adds a new miner with default settings based on type."""
    config = load_config()

    if miner_type not in BITAXE_MODELS:
        print(f"Error: Unknown miner type {miner_type}.")
        return

    # Prevent duplicate miner entries
    if any(miner["ip"] == ip for miner in config["miners"]):
        print(f"Error: Miner with IP {ip} already exists.")
        return

    new_miner = {
        "type": miner_type,
        "ip": ip,
        **config["models"][miner_type]  # Use saved preferences from config.json
    }

    config["miners"].append(new_miner)
    save_config(config)
    print(f"Added new miner: ({miner_type}) at {ip}")

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

def update_miner(ip_or_model, new_settings):
    """Updates an existing miner (by IP) or a model's default preferences in config.json."""
    config = load_config()
    updated = False

    # If updating a miner by IP
    for miner in config["miners"]:
        if miner["ip"] == ip_or_model:
            miner.update(new_settings)
            updated = True
            break

    # If updating model defaults
    if not updated and ip_or_model in config["models"]:
        config["models"][ip_or_model].update(new_settings)
        updated = True

    if updated:
        save_config(config)
        print(f"Updated {ip_or_model} settings successfully.")
    else:
        print(f"Error: Miner or model {ip_or_model} not found.")

def get_miners():
    """Returns the list of configured miners."""
    return load_config().get("miners", [])

def reset_config():
    """Resets configuration to default settings."""
    save_config(get_default_config())
    print("Configuration reset to default.")
