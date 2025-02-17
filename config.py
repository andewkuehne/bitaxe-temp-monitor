import json
import os

CONFIG_FILE = "config.json"

def load_config():
    """Load configuration settings from config.json."""
    if not os.path.exists(CONFIG_FILE):
        print(f"Config file {CONFIG_FILE} not found! Creating default config...")
        save_config(get_default_config())

    with open(CONFIG_FILE, "r") as file:
        return json.load(file)

def save_config(config):
    """Save configuration settings to config.json."""
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file, indent=4)

def get_default_config():
    """Returns default configuration settings."""
    return {
        "voltage_step": 10,
        "frequency_step": 5,
        "min_allowed_voltage": 1000,
        "max_allowed_voltage": 1300,
        "min_allowed_frequency": 650,
        "max_allowed_frequency": 1000,
        "default_target_temp": 50,
        "temp_tolerance": 2,
        "power_limit": 25,
        "monitor_interval": 5
    }
