import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import threading
from datetime import datetime
from config import get_miner_defaults, add_miner, remove_miner, get_miners, update_miner, load_config, save_config, detect_miners
from autotune import monitor_and_adjust, stop_autotuning, get_system_info


class BitaxeAutotuningApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Bitaxe Multi Autotuner")
        self.root.geometry("1200x700")
        self.root.config(bg="black")
        self.root.resizable(True, True)

        self.running = False
        self.threads = []

        # Enable Full-Screen Toggle
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)

        # UI Layout
        tk.Label(self.root, text="- Bitaxe Multi-AutoTuner -", font=("Arial", 18, "bold"), bg="black", fg="gold").pack(
            pady=10)

        # Apply Themed Style for Treeview
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"), background="black")
        style.configure("Treeview", rowheight=25)
        style.map("Treeview", background=[("selected", "gold")])

        # Miner Configuration Table
        self.tree = ttk.Treeview(self.root, columns=(
            "Nickname", "Type", "IP", "Applied Freq", "Current Voltage mVA", "Current Temp", "Current Hash Rate",
            "Current Watts"
        ), show="headings", height=5, style="Treeview")

        # Add Column Headings
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col, anchor="center")
            self.tree.column(col, width=120, anchor="center")

        self.tree.pack(pady=5, fill=tk.BOTH, expand=True)

        # Row Striping
        self.tree.tag_configure("evenrow", background="#f0f0f0")
        self.tree.tag_configure("oddrow", background="white")

        # Control Buttons Section (Frame for Scan, Settings, Add, Remove, Save, AutoTuner)
        control_frame = tk.Frame(self.root, bg="black")
        control_frame.pack(fill=tk.X, pady=5)

        # Centering container for buttons
        control_inner_frame = tk.Frame(control_frame, bg="black")
        control_inner_frame.pack(expand=True)

        button_style = {
            "font": ("Arial", 10),
            "width": 15,
            "bg": "gold",
            "highlightbackground": "black",
            "relief": tk.FLAT
        }

        # Create buttons
        self.scan_button = tk.Button(control_inner_frame, text="Scan Network", command=self.scan_network,
                                     **button_style)
        self.global_settings_button = tk.Button(control_inner_frame, text="Global Settings",
                                                command=self.open_global_settings, **button_style)
        self.add_button = tk.Button(control_inner_frame, text="Add Miner", command=self.add_miner, **button_style)
        self.delete_button = tk.Button(control_inner_frame, text="Remove Miner", command=self.delete_miner,
                                       **button_style)
        self.save_settings_button = tk.Button(control_inner_frame, text="Save Settings", command=self.save_settings,
                                              **button_style)
        self.autotuner_settings_button = tk.Button(control_inner_frame, text="AutoTuner Settings",
                                                   command=self.open_autotuner_settings, **button_style)

        # Use grid layout to center buttons
        self.scan_button.grid(row=0, column=0, padx=5, pady=5)
        self.global_settings_button.grid(row=0, column=1, padx=5, pady=5)
        self.add_button.grid(row=0, column=2, padx=5, pady=5)
        self.delete_button.grid(row=0, column=3, padx=5, pady=5)
        self.save_settings_button.grid(row=0, column=4, padx=5, pady=5)
        self.autotuner_settings_button.grid(row=0, column=5, padx=5, pady=5)

        # Center the button container inside control_frame
        control_inner_frame.pack(anchor="center")

        # Start/Stop Buttons Section
        start_stop_frame = tk.Frame(self.root, bg="black")
        start_stop_frame.pack(fill=tk.X, pady=5)

        start_stop_inner_frame = tk.Frame(start_stop_frame, bg="black")
        start_stop_inner_frame.pack(expand=True)

        self.start_button = tk.Button(start_stop_inner_frame, text="Start Autotuner", command=self.start_autotuning,
                                      font=("Arial", 10, "bold"), bg="gold")
        self.stop_button = tk.Button(start_stop_inner_frame, text="Stop Autotuner", command=self.stop_autotuning,
                                     font=("Arial", 10, "bold"), bg="gold")

        # Use grid layout to center buttons
        self.start_button.grid(row=0, column=0, padx=5, pady=5)
        self.stop_button.grid(row=0, column=1, padx=5, pady=5)

        # Center the button container
        start_stop_inner_frame.pack(anchor="center")

        # Create a right-click menu for interacting with a miner
        self.tree_menu = tk.Menu(self.root, tearoff=0)
        self.tree_menu.add_command(label="Edit Miner Settings", command=self.edit_miner_settings)  # Added Edit Miner
        self.tree_menu.add_command(label="Refresh", command=self.refresh_selected_miner)

        # Bind right-click event to the miner table
        self.tree.bind("<Button-3>", self.show_tree_menu)

        # Log Output
        self.log_output = scrolledtext.ScrolledText(self.root, width=100, height=15, bg="white")
        self.log_output.pack(pady=5, fill=tk.BOTH, expand=True)

        # Load miners from config.json on startup
        self.load_miners_from_config()

    def scan_network(self):
        """Opens a window to allow the user to enter a custom IP range for scanning."""
        scan_window = tk.Toplevel(self.root)
        scan_window.title("Scan Network")
        scan_window.geometry("400x200")
        scan_window.config(bg="white")

        tk.Label(scan_window, text="Enter IP Range to Scan", font=("Arial", 12, "bold"), bg="white").pack(pady=10)

        # Input Fields
        tk.Label(scan_window, text="Starting IP:", bg="white", font=("Arial", 10)).pack()
        start_ip_entry = tk.Entry(scan_window, width=20)
        start_ip_entry.pack(pady=2)

        tk.Label(scan_window, text="Ending IP:", bg="white", font=("Arial", 10)).pack()
        end_ip_entry = tk.Entry(scan_window, width=20)
        end_ip_entry.pack(pady=2)

        def start_scan():
            """Starts the scan with user-defined IP range."""
            start_ip = start_ip_entry.get().strip()
            end_ip = end_ip_entry.get().strip()

            if not start_ip or not end_ip:
                messagebox.showerror("Error", "Both Starting IP and Ending IP are required.")
                return

            self.log_message(f"Scanning network from {start_ip} to {end_ip}...", "info")
            scan_window.destroy()  # Close the scan window

            # Disable scan button while scanning
            self.scan_button.config(state=tk.DISABLED)

            # Background scanning process
            def scan_task():
                detect_miners(start_ip, end_ip)  # Call detect_miners() with the range
                self.root.after(100, self.load_miners_from_config)  # Update UI safely
                self.scan_button.config(state=tk.NORMAL)  # Re-enable button

            threading.Thread(target=scan_task, daemon=True).start()

        tk.Button(scan_window, text="Start Scan", font=("Arial", 10), command=start_scan, bg="gold").pack(pady=10)

    def load_miners_from_config(self):
        """Loads miners from config.json into the UI."""
        self.tree.delete(*self.tree.get_children())  # Clear existing entries
        miners = get_miners()

        for miner in miners:
            values = (
            miner.get("nickname", f"Miner-{miner['ip']}"), miner["type"], miner["ip"], "-", "-", "-", "-", "-")
            self.tree.insert("", "end", values=values)

        self.log_message(f"Loaded {len(miners)} miners.", "success")

    def add_miner(self):
        """Opens a window to manually add a miner."""
        add_window = tk.Toplevel(self.root)
        add_window.title("Add Miner")
        add_window.geometry("400x200")
        add_window.config(bg="white")

        tk.Label(add_window, text="Nickname:", bg="white", font=("Arial", 10)).grid(row=0, column=0, sticky="w", padx=10)
        nickname_entry = tk.Entry(add_window, width=20)
        nickname_entry.grid(row=0, column=1, padx=10, pady=2)

        tk.Label(add_window, text="IP Address:", bg="white", font=("Arial", 10)).grid(row=1, column=0, sticky="w", padx=10)
        ip_entry = tk.Entry(add_window, width=20)
        ip_entry.grid(row=1, column=1, padx=10, pady=2)

        def add_entry():
            nickname = nickname_entry.get().strip()
            ip = ip_entry.get().strip()
            if not ip:
                messagebox.showerror("Error", "IP Address is required.")
                return

            self.tree.insert("", "end", values=(nickname, "Unknown", ip, "-", "-", "-", "-", "-"))
            add_miner("Unknown", ip, nickname)
            messagebox.showinfo("Success", f"Miner {nickname} added successfully.")
            add_window.destroy()

        add_button = tk.Button(add_window, text="Add", font=("Arial", 10), command=add_entry, bg="white")
        add_button.grid(row=2, column=0, columnspan=2, pady=10)

    def refresh_selected_miner(self):
        """Fetches and updates real-time data for the selected miner."""
        selected_item = self.tree.selection()

        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a miner to refresh.")
            return

        values = self.tree.item(selected_item, "values")
        ip = values[2]  # Extract miner's IP address

        self.log_message(f"Refreshing data for miner at {ip}...", "info")

        # Fetch miner data
        miner_data = get_system_info(ip)
        if isinstance(miner_data, str):
            self.log_message(f"Error fetching miner data from {ip}: {miner_data}", "error")
            return

        # Extract real-time values
        new_frequency = miner_data.get("frequency", "-")
        new_voltage = miner_data.get("coreVoltage", "-")
        new_temp = f"{miner_data.get('temp', '-')}°C"
        new_hashrate = f"{float(miner_data.get('hashRate', 0)):.2f} GH/s"
        new_power = f"{float(miner_data.get('power', 0)):.2f} W"

        # Update only the selected miner's row
        updated_values = list(values)
        updated_values[3] = new_frequency  # Applied Frequency
        updated_values[4] = new_voltage  # Current Voltage
        updated_values[5] = new_temp  # Current Temp
        updated_values[6] = new_hashrate  # Current Hash Rate
        updated_values[7] = new_power  # Current Power Usage

        self.tree.item(selected_item, values=updated_values)

        self.log_message(f"Refreshed data for miner at {ip}.", "success")

    def edit_miner_settings(self):
        """Opens a window to edit a miner's nickname, type, and IP address."""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a miner first.")
            return

        values = self.tree.item(selected_item, "values")
        miner_nickname = values[0]  # Nickname
        miner_type = values[1]  # Type
        miner_ip = values[2]  # IP Address

        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Miner Settings")
        edit_window.geometry("400x250")
        edit_window.config(bg="white")

        tk.Label(edit_window, text="Edit Miner Settings", font=("Arial", 12, "bold"), bg="white").pack(pady=10)

        # Input Fields
        tk.Label(edit_window, text="Nickname:", bg="white", font=("Arial", 10)).pack()
        nickname_entry = tk.Entry(edit_window, width=30)
        nickname_entry.insert(0, miner_nickname)
        nickname_entry.pack(pady=2)

        tk.Label(edit_window, text="Miner Type:", bg="white", font=("Arial", 10)).pack()
        type_entry = tk.Entry(edit_window, width=30)
        type_entry.insert(0, miner_type)
        type_entry.pack(pady=2)

        tk.Label(edit_window, text="IP Address:", bg="white", font=("Arial", 10)).pack()
        ip_entry = tk.Entry(edit_window, width=30)
        ip_entry.insert(0, miner_ip)
        ip_entry.pack(pady=2)

        def save_miner_settings():
            """Save the updated miner settings."""
            new_nickname = nickname_entry.get().strip()
            new_type = type_entry.get().strip()
            new_ip = ip_entry.get().strip()

            if not new_ip:
                messagebox.showerror("Error", "IP Address is required.")
                return

            # Update the miner in config.json
            config = load_config()
            for miner in config["miners"]:
                if miner["ip"] == miner_ip:  # Find the correct miner by IP
                    miner["nickname"] = new_nickname
                    miner["type"] = new_type
                    miner["ip"] = new_ip
                    break

            save_config(config)
            self.log_message(f"Updated miner settings: {new_nickname} ({new_type}) at {new_ip}", "success")
            edit_window.destroy()
            self.load_miners_from_config()  # Refresh UI

        tk.Button(edit_window, text="Save", font=("Arial", 10), command=save_miner_settings, bg="gold").pack(pady=10)

    def open_autotuner_settings(self):
        """Opens a window to modify AutoTuner settings for all miners, with a scrollbar for large lists."""
        config = load_config()
        miners = config.get("miners", [])

        if not miners:
            messagebox.showwarning("No Miners Found", "Please add a miner first before modifying AutoTuner settings.")
            return

        autotuner_window = tk.Toplevel(self.root)
        autotuner_window.title("AutoTuner Settings")
        autotuner_window.geometry("1150x500")
        autotuner_window.config(bg="white")

        tk.Label(autotuner_window, text="Modify AutoTuner Settings", font=("Arial", 12, "bold"), bg="white").pack(
            pady=10)

        container = tk.Frame(autotuner_window, bg="white")
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        canvas = tk.Canvas(container, bg="white")
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="white")

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        headers = ["Enable", "Miner", "Min Freq", "Max Freq", "Min Volt", "Max Volt", "Max Temp", "Max Watts",
                   "Target Hashrate", "Actions"]

        # Create table headers
        for col_idx, header in enumerate(headers):
            tk.Label(scrollable_frame, text=header, font=("Arial", 10, "bold"), bg="white").grid(
                row=0, column=col_idx, padx=5, pady=5
            )

        settings_entries = {}
        selected_miners = {}  # Track enabled/disabled miners
        clipboard = {}  # Stores copied row data

        def copy_row(row_idx):
            """Copies values from the selected row into clipboard."""
            nonlocal clipboard
            clipboard = {field: settings_entries[row_idx][field].get() for field in settings_entries[row_idx]}

        def paste_row(row_idx):
            """Pastes values from the clipboard into the selected row."""
            if not clipboard:
                messagebox.showwarning("No Data", "No row has been copied yet.")
                return

            for field, entry in settings_entries[row_idx].items():
                if field in clipboard:
                    entry.delete(0, tk.END)
                    entry.insert(0, clipboard[field])

            validate_miner_settings(row_idx)  # Recheck if miner can be enabled after pasting

        def validate_miner_settings(row_idx):
            """Checks if all required values are filled and enables/disables the checkbox accordingly."""
            has_empty_values = any(entry.get() == "" for entry in settings_entries[row_idx].values())

            if has_empty_values:
                selected_miners[row_idx].set(False)
                enable_checkboxes[row_idx].config(state=tk.DISABLED)
            else:
                enable_checkboxes[row_idx].config(state=tk.NORMAL)

        enable_checkboxes = {}  # Store references to checkboxes

        # Populate rows with miner data
        for row_idx, miner in enumerate(miners, start=1):
            # Checkbox to enable/disable miner
            var = tk.BooleanVar(value=miner.get("enabled", False))
            chk = tk.Checkbutton(scrollable_frame, variable=var, bg="white")
            chk.grid(row=row_idx, column=0, padx=5, pady=5)
            selected_miners[row_idx] = var
            enable_checkboxes[row_idx] = chk

            # Miner Nickname & IP
            tk.Label(scrollable_frame, text=f"{miner['nickname']} ({miner['ip']})", bg="white",
                     font=("Arial", 10)).grid(row=row_idx, column=1, padx=5, pady=5, sticky="w")

            fields = ["min_freq", "max_freq", "min_volt", "max_volt", "max_temp", "max_watts", "target_hashrate"]
            miner_settings = {}

            for col_idx, field in enumerate(fields, start=2):
                entry = tk.Entry(scrollable_frame, bg="white", width=10)
                entry.insert(0, miner.get(field, ""))
                entry.grid(row=row_idx, column=col_idx, padx=5, pady=5)
                miner_settings[field] = entry

                # Bind validation function to detect changes
                entry.bind("<KeyRelease>", lambda event, idx=row_idx: validate_miner_settings(idx))

            settings_entries[row_idx] = miner_settings

            # **Add Copy and Paste Buttons**
            copy_button = tk.Button(scrollable_frame, text="Copy", font=("Arial", 8), width=10,
                                    command=lambda idx=row_idx: copy_row(idx))
            paste_button = tk.Button(scrollable_frame, text="Paste", font=("Arial", 8), width=10,
                                     command=lambda idx=row_idx: paste_row(idx))

            copy_button.grid(row=row_idx, column=len(fields) + 2, padx=2, pady=5)
            paste_button.grid(row=row_idx, column=len(fields) + 3, padx=2, pady=5)

            # Validate miner settings initially
            validate_miner_settings(row_idx)

        def save_autotuner_settings():
            """Save the modified AutoTuner settings to config.json."""
            for idx, miner in enumerate(config["miners"], start=1):
                if idx in settings_entries:
                    for field, entry in settings_entries[idx].items():
                        miner[field] = int(entry.get()) if entry.get().isdigit() else ""

                # Store the selection status
                miner["enabled"] = selected_miners[idx].get()

            save_config(config)
            self.log_message("Updated AutoTuner settings for all miners.", "success")
            messagebox.showinfo("Settings Saved", "AutoTuner settings have been successfully saved!")
            autotuner_window.destroy()

        tk.Button(autotuner_window, text="Save", font=("Arial", 10), width=10, bg="gold",
                  command=save_autotuner_settings).pack(
            pady=10
        )

    def delete_miner(self):
        """Deletes the selected miner from the UI and config.json."""
        selected_items = self.tree.selection()

        if not selected_items:
            messagebox.showwarning("No Selection", "Please select a miner to delete.")
            return

        confirmation = messagebox.askyesno("Delete Miner", "Are you sure you want to remove the selected miner(s)?")
        if not confirmation:
            return

        config = load_config()  # Load the current configuration
        miners = config.get("miners", [])  # Get the list of miners

        for item in selected_items:
            values = self.tree.item(item, "values")
            ip = values[2]  # Extract miner's IP address

            # Remove miner from UI
            self.tree.delete(item)

            # Remove miner from config.json
            miners = [miner for miner in miners if miner["ip"] != ip]

        # Update config.json to remove deleted miners
        config["miners"] = miners
        save_config(config)  # Save changes to config.json

        self.log_message("Miner(s) removed successfully.", "success")

    def open_global_settings(self):
        """Opens a settings window for modifying global autotuner parameters."""
        global_settings_window = tk.Toplevel(self.root)
        global_settings_window.title("Global Settings")
        global_settings_window.geometry("450x300")
        global_settings_window.config(bg="white")

        tk.Label(global_settings_window, text="Modify Settings", font=("Arial", 12, "bold"), bg="white").pack(pady=10)

        # Load current settings
        config = load_config()

        settings_entries = {}
        settings_fields = {
            "voltage_step": "Voltage Step (mV):",
            "frequency_step": "Frequency Step (MHz):",
            "monitor_interval": "Monitor Interval (sec):",
            "default_target_temp": "Default Target Temp (°C):",
            "temp_tolerance": "Temp Tolerance (°C):",
            "refresh_interval": "Autotuner Update Interval (sec):"
        }

        # Create input fields
        input_frame = tk.Frame(global_settings_window, bg="white")
        input_frame.pack(padx=20, pady=10, fill=tk.X)

        for key, label_text in settings_fields.items():
            row_frame = tk.Frame(input_frame, bg="white")
            row_frame.pack(fill=tk.X, pady=2)

            tk.Label(row_frame, text=label_text, font=("Arial", 11), bg="white").pack(side=tk.LEFT)

            entry = tk.Entry(row_frame, font=("Arial", 11), width=10)
            entry.insert(0, str(config.get(key, "")))
            entry.pack(side=tk.RIGHT, padx=10)
            settings_entries[key] = entry

        def save_global_settings():
            """Saves global settings to config.json."""
            try:
                new_settings = {key: int(entry.get()) for key, entry in settings_entries.items()}
                config.update(new_settings)
                save_config(config)
                messagebox.showinfo("Success", "Settings updated successfully.")
                global_settings_window.destroy()
                self.log_message("Global settings updated.", "success")
            except ValueError:
                messagebox.showerror("Error", "Please enter valid integer values.")

        tk.Button(global_settings_window, text="Save", font=("Arial", 10), command=save_global_settings,
                  bg="white").pack(pady=10)

    def save_settings(self):
        """Saves all miner tuning settings and miner details to config.json."""
        config = load_config()  # Load existing config

        updated_miners = []

        # Get current values from the UI and update config.json
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            nickname = values[0]
            miner_type = values[1]
            ip = values[2]

            # Retrieve tuning settings from stored config
            miner_defaults = get_miner_defaults(miner_type)

            updated_miner = {
                "nickname": nickname,
                "type": miner_type,
                "ip": ip,
                "min_freq": miner_defaults.get("min_freq", ""),
                "max_freq": miner_defaults.get("max_freq", ""),
                "min_volt": miner_defaults.get("min_volt", ""),
                "max_volt": miner_defaults.get("max_volt", ""),
                "max_temp": miner_defaults.get("max_temp", ""),
                "max_watts": miner_defaults.get("max_watts", ""),
                "target_hashrate": miner_defaults.get("target_hashrate", "")
            }

            updated_miners.append(updated_miner)

        config["miners"] = updated_miners  # Replace old miner data with updated values
        save_config(config)  # Save back to config.json

        self.log_message("Tuning & miner settings have been saved to config.json.", "success")
        messagebox.showinfo("Settings Saved", "All miner settings have been successfully saved!")

    def toggle_fullscreen(self, event=None):
        """Toggle full-screen mode."""
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))

    def exit_fullscreen(self, event=None):
        """Exit full-screen mode."""
        self.root.attributes("-fullscreen", False)

    def start_autotuning(self):
        """Starts autotuning miners using the latest saved AutoTuner settings."""
        self.running = True
        self.threads.clear()

        config = load_config()  # Load the latest config

        self.log_message("Checking AutoTuner settings before starting...", "info")

        missing_settings = []
        required_fields = ["min_freq", "max_freq", "min_volt", "max_volt", "max_temp", "max_watts", "target_hashrate"]

        # Validate that each miner has all required AutoTuner settings
        for miner in config.get("miners", []):
            if not miner.get("enabled", False):  # Skip miners that are disabled
                continue

            for field in required_fields:
                if field not in miner or miner[field] == "" or miner[field] is None:
                    missing_settings.append((miner["ip"], field))

        # If missing settings are found, alert the user and prevent startup
        if missing_settings:
            error_message = "AutoTuner settings are incomplete. Please populate the following missing fields:\n\n"
            for ip, field in missing_settings:
                error_message += f"- Miner {ip}: Missing {field}\n"

            self.log_message(error_message, "error")
            messagebox.showerror("Incomplete Settings", error_message)
            self.running = False
            return

        self.log_message("Starting autotuning for selected miners...", "success")

        active_miners = [m for m in config.get("miners", []) if m.get("enabled", False)]

        if not active_miners:
            self.log_message("No miners are enabled for AutoTuning. Please enable at least one miner.", "error")
            messagebox.showwarning("No Miners Enabled",
                                   "No miners are enabled for AutoTuning. Please enable at least one miner in settings.")
            self.running = False
            return

        for miner in active_miners:
            ip, bitaxe_type = miner["ip"], miner["type"]

            min_freq = miner.get("min_freq", 0)
            max_freq = miner.get("max_freq", 0)
            min_volt = miner.get("min_volt", 0)
            max_volt = miner.get("max_volt", 0)
            max_temp = miner.get("max_temp", 0)
            max_watts = miner.get("max_watts", 0)
            target_hashrate = miner.get("target_hashrate", 0)
            interval = config.get("monitor_interval", 5)  # Global setting

            # Pass settings dynamically to `monitor_and_adjust`
            thread = threading.Thread(
                target=monitor_and_adjust,
                args=(ip, bitaxe_type, interval, self.log_message,
                      min_freq, max_freq, min_volt, max_volt,
                      max_temp, max_watts, target_hashrate)
            )
            thread.start()
            self.threads.append(thread)

        # Ensure UI updates based on monitor interval
        self.update_miner_display(interval)

    def stop_autotuning(self):
        """Stops all autotuning processes."""
        self.running = False
        stop_autotuning()
        self.log_message("Stopping autotuning...", "warning")

    def show_tree_menu(self, event):
        """Displays the right-click menu when a miner is selected."""
        selected_item = self.tree.identify_row(event.y)
        if selected_item:
            self.tree.selection_set(selected_item)  # Select miner
            self.tree_menu.post(event.x_root, event.y_root)  # Show right-click menu

    def update_miner_display(self, interval):
        """Refresh miner status in the UI at the global monitor interval."""
        if not self.running:
            return

        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            ip = values[2]  # Extract miner's IP address

            miner_data = get_system_info(ip)
            if isinstance(miner_data, str):
                self.log_message(f"Error fetching miner data from {ip}: {miner_data}", "error")
                continue

            # Extract real-time values
            new_frequency = miner_data.get("frequency", "-")
            new_voltage = miner_data.get("coreVoltage", "-")
            new_temp = f"{miner_data.get('temp', '-')}°C"
            new_hashrate = f"{float(miner_data.get('hashRate', 0)):.2f} GH/s"
            new_power = f"{float(miner_data.get('power', 0)):.2f} W"

            # Update UI
            updated_values = list(values)
            updated_values[3] = new_frequency  # Applied Frequency
            updated_values[4] = new_voltage  # Current Voltage
            updated_values[5] = new_temp  # Current Temp
            updated_values[6] = new_hashrate  # Current Hashrate
            updated_values[7] = new_power  # Current Power Usage

            self.tree.item(item, values=updated_values)

        # schedule the next update based on monitor interval
        self.root.after(interval * 1000, self.update_miner_display, interval)

    def log_message(self, message, level="info"):
        """Logs messages to the UI, ensuring updates run on the main thread."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"[{timestamp}] {message}"
    
        def _update_log():
            if not self.root.winfo_exists():  # Check if window is still open
                return

            colors = {"success": "green", "warning": "orange", "error": "red", "info": "black"}
            self.log_output.insert(tk.END, message + "\n", level)
            self.log_output.tag_config(level, foreground=colors[level])
            self.log_output.yview(tk.END)
    
        # Ensure Tkinter UI updates run on the main thread
        if self.root.winfo_exists():  # Prevent calls after window is closed
            self.root.after(0, _update_log)


    def run(self):
        """Runs the Tkinter event loop."""
        self.root.mainloop()


if __name__ == "__main__":
    app = BitaxeAutotuningApp()
    app.run()
