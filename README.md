# Bitaxe Temperature Monitor and Auto-Tuner

This project contains a Python script that continuously monitors a Bitaxe Gamma 601 Bitcoin solo miner's operating temperature and automatically adjusts its operating frequency (and voltage if necessary) to achieve optimal hash rate without overheating the device.

## Overview

The Bitaxe Gamma Autotuner and Auto-Tuner script continuously polls the Bitaxe's `/api/system/info` endpoint to read current temperature, hash rate, and voltage. Based on a configurable target temperature (default is 60°C) and a defined temperature margin, the script automatically adjusts:

- **Frequency**: Decreases frequency if the temperature exceeds the target or increases if the temperature is well below the target.
- **Voltage**: If frequency adjustments alone are insufficient or if the settings are at their limits, voltage is also adjusted within safe operating ranges.

The script aims to maximize the device's hash rate while preventing overheating, using safe settings based on your previously benchmarked results.

## Features

- **Automatic autotuning**: Continuously checks the Bitaxe's temperature and performance.
- **Dynamic Adjustment**: Adjusts frequency and voltage in real time based on the current temperature.
- **Graceful Shutdown**: Listens for interrupt signals (Ctrl+C) and exits gracefully.
- **Customizable Parameters**: Easily modify target temperature, sample interval, step sizes, and safe operating limits.

## Requirements

- Python 3.x
- `requests` module (install using `pip install requests`)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/bitaxe-temp-monitor.git
   cd bitaxe-temp-monitor
   ```

2. **Install dependencies:**
   ```bash
   pip install requests
   pip install tkinter
   ```

## Usage

Run the script by providing the IP address of your Bitaxe. You can also specify initial voltage, frequency, target temperature, and autotuning interval.

```bash
python main.py
```

#### Example

```bash
python main.py
```

## How It Works

1. **Initialization**: The script applies the initial voltage and frequency settings to the Bitaxe.
2. **autotuning Loop**:  
   - It retrieves system data from the Bitaxe.
   - If the temperature exceeds the target, the script reduces the frequency (or voltage if necessary) to cool the system.
   - If the temperature is well below the target minus a margin, it increases the frequency (or voltage) to maximize performance.
3. **Adjustment**: Settings are applied via the Bitaxe API, allowing time for system stabilization after each change.
4. **Graceful Exit**: The script listens for interrupt signals (Ctrl+C) and safely exits while logging the final state.

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
