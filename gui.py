import tkinter as tk
from tkinter import scrolledtext
import threading
from autotune import monitor_and_adjust, stop_autotuning

class BitaxeGammaAutotuningApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Bitaxe Autotuner")
        self.root.geometry("1200x700")  # Default window size
        self.root.state('zoomed')  # Start in maximized mode
        self.root.resizable(True, True)  # Allow resizing both ways

        self.running = False
        self.threads = []
        self.autotuning_status = {}

        # Enable Full-Screen Toggle (Press F11)
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)

        # Configure grid resizing
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=1)
        self.root.columnconfigure(3, weight=1)
        self.root.rowconfigure(5, weight=1)  # Log section grows dynamically

        # === UI Layout === #
        top_frame = tk.Frame(self.root)
        top_frame.grid(row=0, column=0, columnspan=4, sticky="ew", padx=5, pady=5)

        # === Title Section === #
        tk.Label(top_frame, text="Bitaxe Autotuner", font=("Arial", 12, "bold")).pack(side=tk.LEFT)

        # === Input Section === #
        input_frame = tk.Frame(self.root)
        input_frame.grid(row=1, column=0, columnspan=4, sticky="ew", padx=5, pady=5)

        tk.Label(input_frame, text="Enter IPs (space-separated):").grid(row=0, column=0, sticky="w")
        self.ip_entry = tk.Entry(input_frame, width=50)
        self.ip_entry.insert(0, "192.168.0.101")
        self.ip_entry.grid(row=0, column=1, columnspan=3, sticky="ew")

        # Voltage Entry
        tk.Label(input_frame, text="Voltage (mV):").grid(row=1, column=0, sticky="w")
        self.voltage_entry = tk.Entry(input_frame, width=10)
        self.voltage_entry.insert(0, "1150")
        self.voltage_entry.grid(row=1, column=1, sticky="ew")

        # Frequency Entry
        tk.Label(input_frame, text="Frequency (MHz):").grid(row=1, column=2, sticky="w")
        self.frequency_entry = tk.Entry(input_frame, width=10)
        self.frequency_entry.insert(0, "525")
        self.frequency_entry.grid(row=1, column=3, sticky="ew")

        # Target Temperature Entry
        tk.Label(input_frame, text="Target Temp (°C):").grid(row=2, column=0, sticky="w")
        self.target_temp_entry = tk.Entry(input_frame, width=10)
        self.target_temp_entry.insert(0, "60")
        self.target_temp_entry.grid(row=2, column=1, sticky="ew")

        # Interval Entry
        tk.Label(input_frame, text="Interval (sec):").grid(row=2, column=2, sticky="w")
        self.interval_entry = tk.Entry(input_frame, width=10)
        self.interval_entry.insert(0, "5")
        self.interval_entry.grid(row=2, column=3, sticky="ew")

        # Power Limit Entry
        tk.Label(input_frame, text="Power Limit (W):").grid(row=3, column=0, sticky="w")
        self.power_limit_entry = tk.Entry(input_frame, width=10)
        self.power_limit_entry.insert(0, "25")
        self.power_limit_entry.grid(row=3, column=1, sticky="ew")

        # Min Hash Rate Entry
        tk.Label(input_frame, text="Min Hashrate (GH/s):").grid(row=3, column=2, sticky="w")
        self.min_hashrate_entry = tk.Entry(input_frame, width=10)
        self.min_hashrate_entry.insert(0, "1600")
        self.min_hashrate_entry.grid(row=3, column=3, sticky="ew")

        # === Buttons === #
        button_frame = tk.Frame(self.root)
        button_frame.grid(row=4, column=0, columnspan=4, sticky="ew", padx=5, pady=5)

        self.start_button = tk.Button(button_frame, text="Start Autotuning", command=self.start_autotuning)
        self.start_button.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.stop_button = tk.Button(button_frame, text="Stop Autotuning", command=self.stop_autotuning)
        self.stop_button.pack(side=tk.RIGHT, expand=True, fill=tk.X)

        # === Log Output (Expands Dynamically) === #
        self.log_output = scrolledtext.ScrolledText(self.root, width=100, height=20)
        self.log_output.grid(row=5, column=0, columnspan=4, sticky="nsew")

    def toggle_fullscreen(self, event=None):
        """Toggle full-screen mode."""
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))

    def exit_fullscreen(self, event=None):
        """Exit full-screen mode."""
        self.root.attributes("-fullscreen", False)

    def log_message(self, message, level="info"):
        """Logs messages to the UI."""
        colors = {"success": "green", "warning": "orange", "error": "red", "info": "black"}
        self.log_output.insert(tk.END, message + "\n", level)
        self.log_output.tag_config(level, foreground=colors[level])
        self.log_output.yview(tk.END)

    def start_autotuning(self):
        """Starts autotuning miners."""
        self.running = True
        self.autotuning_status.clear()
        self.threads.clear()

        ip_addresses = self.ip_entry.get().split()
        voltage = int(self.voltage_entry.get())
        frequency = int(self.frequency_entry.get())
        target_temp = int(self.target_temp_entry.get())
        interval = int(self.interval_entry.get())
        power_limit = int(self.power_limit_entry.get())
        min_hashrate = int(self.min_hashrate_entry.get())

        self.log_message(f"Starting autotuning for: {', '.join(ip_addresses)}", "success")

        for ip in ip_addresses:
            self.autotuning_status[ip] = True
            thread = threading.Thread(target=monitor_and_adjust, args=(
                ip, voltage, frequency, target_temp, interval, power_limit, min_hashrate, self.log_message))
            thread.start()
            self.threads.append(thread)

    def stop_autotuning(self):
        """Stops autotuning miners."""
        self.running = False
        stop_autotuning()
        self.log_message("Stopping autotuning...", "warning")

    def run(self):
        """Runs the Tkinter event loop."""
        self.root.mainloop()
