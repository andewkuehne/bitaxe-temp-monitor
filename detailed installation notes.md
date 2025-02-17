# Bitaxe Temperature Monitor and Auto-Tuner

This project contains a Python script that continuously monitors a Bitaxe Gamma 601 Bitcoin solo miner's operating temperature and automatically adjusts its operating frequency (and voltage if necessary) to achieve optimal hash rate without overheating the device.

## Overview

The Bitaxe Temperature Monitor and Auto-Tuner script helps optimize your mining performance by:

- Monitoring temperature, hash rate, and power consumption.
- Adjusting voltage and frequency dynamically.
- Preventing overheating by maintaining a maximum temperature of 65°C.
- Managing power supply constraints to ensure efficient operation.

## Installation Guide

- **Step 1**: Install Python

- If Python is not already installed on your system:
- Visit Python’s official website
- Download and install Python 3.x
- Important: Check "Add Python to PATH" during installation.

- **Step 2**: Download the Program

- Open your browser and go to the GitHub repository: https://github.com/Hurllz/bitaxe-temp-monitor/tree/main
- Click on the Code button and select Download ZIP.
- Extract the downloaded ZIP file to a folder on your computer.

- **Step 3**: Install Required Dependencies

- This program requires the requests module to communicate with the Bitaxe miner. 
		- Install it by running:
	
   ```bash
	pip install requests
   ```
   
-**Step 4**: Running the Program

- Open Command Prompt (Windows) or Terminal (Mac/Linux).
- Navigate to the extracted program folder:
- (Replace path/to/the/folder with the actual location of the extracted folder.)
	
   ```bash
	cd path/to/the/folder
   ```

## Run the program using:

```bash
python bitaxe_temp_monitor.py <bitaxe_ip> -p 30
```
   
-(Replace <bitaxe_ip> with the actual IP address of your Bitaxe miner.)

## Example:

- If your miner’s IP is 192.168.2.26, you would run:

```bash
- python bitaxe_temp_monitor.py 192.168.2.26 -p 30
```

## Understanding the Program

- Monitors your miner’s temperature, hash rate, and power usage.
- Adjusts voltage & frequency dynamically to optimize performance.
- Maintains safe temperature levels by preventing overheating.
- Ensures power usage stays within limits (default: 30W).

## Stopping the Program

To stop the program, press Ctrl + C on your keyboard.
