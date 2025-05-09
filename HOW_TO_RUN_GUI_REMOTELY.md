# How to Run the Bitaxe GUI Remotely from a Headless Raspberry Pi

This guide explains how to run the Bitaxe Temp Monitor & Auto-Tuner GUI remotely from a headless Raspberry Pi and display it on your local Linux or macOS machine using X11 forwarding.

---

## Prerequisites

- A headless Raspberry Pi running Raspberry Pi OS (or any Debian-based Linux).
- SSH access to the Pi from a local Linux/macOS machine.
- X11 server running on the local machine (macOS users should install [XQuartz](https://www.xquartz.org/)).

---

## Step 1: Configure the Raspberry Pi

### 1.1 Install X11 and Tkinter Support

Run the following commands on your Raspberry Pi:

  ```bash
  sudo apt update
  sudo apt install xauth x11-xserver-utils python3-tk
  ```

### 1.2 Enable X11 Forwarding in SSH

Edit the SSH server configuration:

  ```bash
  sudo nano /etc/ssh/sshd_config
  ```

Ensure the following lines are present (uncomment or add them if needed):
  
  ```bash
  X11Forwarding yes
  X11DisplayOffset 10
  ```
Then restart the SSH service:
  
  ```bash
  sudo systemctl restart ssh
  ```

## Step 2: Prepare Your Local Machine
macOS Users
Install and launch XQuartz, then log out and log back in for changes to take effect.

Linux Users
X11 is typically installed by default. You’re good to go.

## Step 3: Connect via SSH with X11 Forwarding

On your local machine, use the -X flag to enable X11 forwarding:

```bash
ssh -X pi@<your_pi_ip_address>
```

Replace <your_pi_ip_address> with the actual IP of your Pi.

If you want stronger OpenGL graphics support (experimental), use:

  ```bash
  ssh -Y pi@<your_pi_ip_address>
  ```

## Step 4: Launch the GUI Application

Once logged in, navigate to the Bitaxe project folder:

  ```bash
  cd ~/bitaxe-temp-monitor
  python3 main.py
  ```

The GUI will launch and appear on your local machine while running from the Pi.

## Troubleshooting
If you see an error like TclError: no display name and no $DISPLAY environment variable, X11 forwarding is not active. Ensure you connected using ssh -X and that X11 is installed on both systems.

On macOS, confirm XQuartz is running before using SSH.




