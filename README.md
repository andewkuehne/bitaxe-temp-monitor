# Bitaxe Temperature Monitor and Auto-Tuner

This project contains a Python-based monitoring and auto-tuning application for the Bitaxe Gamma 601 Bitcoin solo miner. This tool dynamically adjusts operating frequency and voltage to achieve optimal hash rate while preventing overheating.

## Overview

The **Bitaxe Temp Monitor & Auto-Tuner** continuously polls the Bitaxe's `/api/system/info` endpoint to monitor current temperature, hash rate, and voltage. Based on configurable parameters (target temperature, interval, voltage step, etc.), the script automatically adjusts:

- **Frequency**: Decreases frequency if the temperature exceeds the target or increases if the temperature is well below the target.
- **Voltage**: If frequency adjustments alone are insufficient or if the settings are at their limits, voltage is also adjusted within safe operating ranges.

The app aims to maximize the miner's hash rate while maintaining stable and safe operation.

## Features

- **Automatic Auto-Tuning**: Continuously monitors the Bitaxe's performance and temperature.
- **Dynamic Adjustment**: Automatically adjusts frequency and voltage in real-time based on the current temperature and hash rate.
- **Graceful Shutdown**: Listens for interrupt signals (Ctrl+C) and exits safely.
- **Customizable Parameters**: Easily modify settings such as target temperature, sample interval, and safe operating limits.
- **Cross-Platform Support**: Works seamlessly on both **Windows** and **Linux**.

## Requirements

- **Python 3.x** (tested with Python 3.9+)
- Required Python modules:
  - `requests`
  - `tkinter` (pre-installed on Windows, may require manual installation on Linux)
  
## Installation

### For Windows

1. Open Command Prompt as Administrator.
2. Clone the repository:

   ```bash
   git clone https://github.com/hurllz/bitaxe-temp-monitor.git
   cd bitaxe-temp-monitor
   ```
   
3. Install dependencies:

   ```bash
	pip install requests
   ```
   
4. Run the application:

   ```bash
	pyhon main.py
   ```

### For Linux

1. Open terminal window
2. Clone the repository:

   ```bash
	git clone https://github.com/hurllz/bitaxe-temp-monitor.git
	cd bitaxe-temp-monitor
   ```

2. Install dependencies:

   ```bash
	sudo apt-get install python3-tk
	pip install requests
   ```
   
4. Run the application:

   ```bash
	python3 main.py
   ```

## Usage

To start the app, provide the IP address of your Bitaxe miner. You can specify initial voltage, frequency, target temperature, and the interval for autotuning.

## How It Works

1. **Initialization**: The script applies the initial voltage and frequency settings to the Bitaxe.
2. **autotuning Loop**:  
   - Continuously retrieves system data from the Bitaxe API.
   - Decreases frequency or voltage if the temperature exceeds the target.
   - ncreases frequency or voltage if the temperature is significantly below the target.
3. Dynamic Adjustment: Applies settings in real-time for optimized performance.
4. Graceful Exit: Listens for interrupt signals and logs the final state when the app is stopped.

## Disclaimer

**WARNING:** This tool modifies hardware settings and may stress test your Bitaxe. Although safeguards are in place, running the miner outside its standard operating parameters can pose risks. Use this script at your own risk. The authors are not responsible for any damage to your hardware.

## Contributors

1. Birdman332 (reddit)
   - created GUI managment features. 

## Contributing

Contributions, bug reports, and feature requests are welcome! Feel free to open an issue or submit a pull request.

## Inspirational  Shoutouts

The benchmark tool is awesome and a highly recommend tool to baseline and set and forget your miner. 

1. **WhiteyCookie**: Bitaxe-Hashrate-Benchmark
      - https://github.com/WhiteyCookie/Bitaxe-Hashrate-Benchmark
2. **mrv777**: forked bitaxe-hashrate-benchmark
   -    https://github.com/mrv777/bitaxe-hashrate-benchmark

## License

This project is licensed under the [MIT License](LICENSE).
