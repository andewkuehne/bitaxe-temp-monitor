import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import threading
import time
from config import get_miner_defaults, add_miner, remove_miner, get_miners, update_miner, load_config, save_config
from autotune import monitor_and_adjust, stop_autotuning, get_system_info


class BitaxeAutotuningApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Bitaxe Multi Autotuner")
        self.root.geometry("1150x700")
        self.root.config(bg="black")
        self.root.resizable(True, True)

        self.running = False
        self.threads = []

        # Enable Full-Screen Toggle
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)

        # UI Layout
        tk.Label(self.root, text="- Bitaxe Multi-AutoTuner -", font=("Arial", 18, "bold"), bg="black", fg="gold").pack(pady=10)

        # Apply Themed Style for Treeview
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"), background="lightgray")  # Bold Headers
        style.configure("Treeview", rowheight=25)  # Adjust row height for better readability
        style.map("Treeview", background=[("selected", "lightblue")])  # Highlight selected row

        # Miner Configuration Table with Improved Visibility
        self.tree = ttk.Treeview(self.root, columns=(
            "Type", "IP", "Applied Freq", "Current Voltage mVA", "Current Temp", "Current Hash Rate", "Current Watts"
        ), show="headings", height=5, style="Treeview")

        # Add Column Headings with Styling
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col, anchor="center")  # Center align headers
            self.tree.column(col, width=120, anchor="center")  # Set column width

        # Pack Treeview
        self.tree.pack(pady=5, fill=tk.BOTH, expand=True)

        # Apply Row Striping (Alternating Background Colors)
        self.tree.tag_configure("evenrow", background="#f0f0f0")  # Light gray
        self.tree.tag_configure("oddrow", background="white")  # White

        # Function to Insert Data with Alternating Row Colors
        def insert_miner_data(values):
            """Inserts miner data with alternating row colors."""
            row_id = len(self.tree.get_children())  # Get row index
            tag = "evenrow" if row_id % 2 == 0 else "oddrow"  # Apply alternating row color
            self.tree.insert("", "end", values=values, tags=(tag,))

        # Load existing miners from config
        self.load_miners_from_config()

        # Bind click event to open settings
        self.tree.bind("<<TreeviewSelect>>", self.on_miner_select)

        # Preferences Section
        self.preferences_frame = tk.Frame(self.root, bg="black")
        self.preferences_frame.pack(pady=5, fill=tk.X)

        # Centering container for the label & buttons
        self.preferences_inner_frame = tk.Frame(self.preferences_frame, bg="black")
        self.preferences_inner_frame.pack(pady=5, expand=True)

        # Centered Label
        tk.Label(
            self.preferences_inner_frame,
            text="Preferences for Models:",
            font=("Arial", 10),
            bg="black",
            fg="white"
        ).pack(anchor="center", pady=5)

        # Centered Model Buttons
        self.model_buttons = {}
        for model in ["Gamma", "Ultra", "Supra", "Hex"]:
            self.model_buttons[model] = tk.Button(
                self.preferences_inner_frame,
                text=model,
                command=lambda m=model: self.open_preferences(m),
                width=10,  # Set uniform button width
                font=("Arial", 10),  # Set uniform font
                height=1,  # Optional: Adjust button height
                bg="gold"
            )
            self.model_buttons[model].pack(side=tk.LEFT, padx=10, pady=5)  # Proper spacing & alignment

        # Control Buttons Section
        control_frame = tk.Frame(self.root, bg="black")
        control_frame.pack(fill=tk.X, pady=5)

        # Create a sub-frame to center buttons
        button_container = tk.Frame(control_frame, bg="black")
        button_container.pack(pady=5)  # Pack inside control frame

        # Common button style
        button_style = {
            "font": ("Arial", 10),
            "width": 15,
            "bg": "gold",
            "highlightbackground": "black",  # Match frame background
            "relief": tk.FLAT  # Flat style to blend into frame
        }

        # Create buttons
        self.global_settings_button = tk.Button(button_container, text="Global Settings", command=self.open_global_settings,
                                                **button_style)
        self.add_button = tk.Button(button_container, text="Add Miner", command=self.add_miner, **button_style)
        self.delete_button = tk.Button(button_container, text="Remove Miner", command=self.delete_miner, **button_style)
        self.start_button = tk.Button(button_container, text="Start Autotuner", command=self.start_autotuning,
                                      font=("Arial", 10, "bold"), bg="gold")
        self.stop_button = tk.Button(button_container, text="Stop Autotuner", command=self.stop_autotuning,
                                     font=("Arial", 10, "bold"), bg="gold")

        # Arrange buttons in a centered row
        self.global_settings_button.grid(row=0, column=0, padx=5, pady=5)
        self.add_button.grid(row=0, column=1, padx=5, pady=5)
        self.delete_button.grid(row=0, column=2, padx=5, pady=5)
        self.start_button.grid(row=0, column=3, padx=5, pady=5)
        self.stop_button.grid(row=0, column=4, padx=5, pady=5)

        # Center the button container within control_frame
        button_container.pack(anchor="center")

        # Log Output
        self.log_output = scrolledtext.ScrolledText(self.root, width=100, height=15, bg="white")
        self.log_output.pack(pady=5, fill=tk.BOTH, expand=True)

        # Create a right-click menu for refreshing a single miner
        self.tree_menu = tk.Menu(self.root, tearoff=0)
        self.tree_menu.add_command(label="Refresh", command=self.refresh_selected_miner)

        # Bind right-click event to the miner table
        self.tree.bind("<Button-3>", self.show_tree_menu)

    def open_global_settings(self):
        """Opens a settings window for modifying global autotuner parameters."""
        global_settings_window = tk.Toplevel(self.root)
        global_settings_window.title("Settings")
        global_settings_window.geometry("450x300")
        global_settings_window.config(bg="white")

        # Ensure the settings window stays on top of the main GUI
        global_settings_window.transient(self.root)
        global_settings_window.grab_set()
        global_settings_window.focus_set()

        # Header with Help Button
        header_frame = tk.Frame(global_settings_window, bg="white")
        header_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(header_frame, text="Modify Settings", font=("Arial", 11), bg="white").pack(side=tk.LEFT)

        # Help Button (?)
        help_button = tk.Button(
            header_frame, text="?", font=("Arial", 10), width=2,
            command=lambda: self.show_global_settings_help(global_settings_window), bg="white"
        )
        help_button.pack(side=tk.RIGHT, padx=5)

        # Load current config values
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

        # Container Frame for Inputs
        input_frame = tk.Frame(global_settings_window, bg="white")
        input_frame.pack(padx=20, pady=10, fill=tk.X)

        # Create input fields for each setting
        for key, label_text in settings_fields.items():
            row_frame = tk.Frame(input_frame, bg="white")
            row_frame.pack(fill=tk.X, pady=2)

            tk.Label(row_frame, text=label_text, font=("Arial", 11), bg="white").pack(side=tk.LEFT)

            entry = tk.Entry(row_frame, font=("Arial", 11), width=10)
            entry.insert(0, str(config.get(key, "")))
            entry.pack(side=tk.RIGHT, padx=10)
            settings_entries[key] = entry

        def save_global_settings():
            """Saves global settings to config.json with validation."""
            try:
                new_settings = {key: int(entry.get()) for key, entry in settings_entries.items()}
                config.update(new_settings)
                save_config(config)
                messagebox.showinfo("Success", "Settings updated successfully.")
                global_settings_window.destroy()
                self.log_message("Settings updated.", "success")
            except ValueError:
                messagebox.showerror("Error", "Please enter valid integer values for all fields.")

        tk.Button(global_settings_window, text="Save", font=("Arial", 10), command=save_global_settings, bg="white").pack(
            pady=10)

    def show_global_settings_help(self, parent_window):
        """Displays a help message explaining each setting in detail and keeps it on top."""
        help_window = tk.Toplevel(parent_window)
        help_window.title("Settings Help")
        help_window.geometry("700x400")
        help_window.config(bg="white")
        help_window.transient(parent_window)  # Link window to settings window
        help_window.grab_set()  # Make it modal (prevents interaction with other windows)
        help_window.focus_set()  # Keep focus on this window

        tk.Label(help_window, text="Settings Help", font=("Arial", 12), bg="white").pack(pady=10)

        help_text = (
            "**Voltage Step (mV):** The amount by which voltage is increased or decreased during autotuning.\n\n"
            "**Frequency Step (MHz):** The amount by which frequency is increased or decreased during autotuning.\n\n"
            "**Monitor Interval (sec):** How often the autotuner checks and adjusts miner performance.\n\n"
            "**Default Target Temp (°C):** The default temperature at which miners should operate.\n\n"
            "**Temp Tolerance (°C):** The allowable temperature fluctuation before adjustments are made.\n\n"
            "**Autotuner Update Interval (sec):** How often the GUI refreshes miner status and performance."
        )

        tk.Message(help_window, text=help_text, font=("Arial", 10), width=650, bg="white").pack(padx=20, pady=10)

        tk.Button(help_window, text="Close", font=("Arial", 10), command=help_window.destroy, bg="white").pack(pady=10)

    def open_preferences(self, model):
        """Opens the settings window for a specific Bitaxe model."""
        pref_window = tk.Toplevel(self.root)
        pref_window.title(f"{model} Preferences")
        pref_window.geometry("400x300")
        pref_window.config(bg="white")

        tk.Label(pref_window, text=f"Preferences for {model}", font=("Arial", 12, "bold"), bg="white").pack(pady=5)

        # Load default or saved values
        settings = get_miner_defaults(model)

        input_frame = tk.Frame(pref_window, bg="white")
        input_frame.pack(pady=5, padx=10, fill=tk.X)

        # Input fields
        entries = {}

        fields = ["min_freq", "max_freq", "min_volt", "max_volt", "max_temp", "max_watts", "target_hashrate"]

        for idx, field in enumerate(fields):
            row_frame = tk.Frame(input_frame, bg="white")
            row_frame.pack(fill=tk.X, pady=2)

            tk.Label(row_frame, text=f"{field.replace('_', ' ').title()}:", bg="white").pack(side=tk.LEFT)

            entry = tk.Entry(row_frame, bg="white")
            entry.insert(0, settings.get(field, ""))
            entry.pack(side=tk.RIGHT, padx=5)
            entries[field] = entry

        def save_preferences():
            """Save preferences for the model."""
            new_settings = {field: int(entries[field].get()) for field in fields}
            update_miner(model, new_settings)
            self.log_message(f"Saved {model} preferences.", "success")
            pref_window.destroy()

        tk.Button(pref_window, text="Save", font = ("Arial", 10), width = 10, height = 1, bg="white", command=save_preferences).pack(pady=10)

    def refresh_selected_miner(self):
        """Fetches and updates live data for the selected miner only."""
        selected_item = self.tree.selection()

        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a miner to refresh.")
            return

        values = self.tree.item(selected_item, "values")
        ip = values[1]  # Extract miner's IP address

        self.log_message(f"Manually refreshing data for miner at {ip}...", "info")

        # Fetch live miner data
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
        updated_values[2] = new_frequency  # Applied Freq
        updated_values[3] = new_voltage  # Applied Voltage
        updated_values[4] = new_temp  # Current Temp
        updated_values[5] = new_hashrate  # Current Hashrate
        updated_values[6] = new_power  # Current Power Usage

        self.tree.item(selected_item, values=updated_values)

        self.log_message(f"Refreshed data for miner at {ip}.", "success")

    def load_miners_from_config(self):
        """Loads saved miners from config.json into the UI table with initial blank values."""
        self.tree.delete(*self.tree.get_children())  # Clear existing entries
        miners = get_miners()  # Load miners from config.json

        for miner in miners:
            self.tree.insert("", "end", values=(
                miner["type"], miner["ip"],
                "-", "-", "-", "-", "-"  # Initially blank values
            ))

    def on_miner_select(self, event):
        """Handles miner selection without triggering data refresh."""
        selected_item = self.tree.selection()
        if not selected_item:
            return

        values = self.tree.item(selected_item, "values")
        bitaxe_type, ip = values[:2]  # Extract miner type and IP

    def add_miner(self):
        """Opens a window to add a new miner and saves it to config."""
        add_window = tk.Toplevel(self.root)
        add_window.title("Add Miner")
        add_window.geometry("350x200")
        add_window.config(bg="white")
        add_window.transient(self.root)
        add_window.grab_set()

        # Header with Help Button
        header_frame = tk.Frame(add_window, bg="white")
        header_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(header_frame, text="Add New Miner", font=("Arial", 11), bg="white").pack(side=tk.LEFT)

        # Frame for Input Fields
        input_frame = tk.Frame(add_window, bg="white")
        input_frame.pack(pady=10)

        tk.Label(input_frame, text="Type:", bg="white", font=("Arial", 10)).grid(row=0, column=0, sticky="w", padx=10)
        type_var = tk.StringVar(value="Gamma")
        type_dropdown = ttk.Combobox(input_frame, textvariable=type_var, values=["Gamma", "Supra", "Ultra", "Hex"], width=15)
        type_dropdown.grid(row=0, column=1, padx=10, pady=2)

        # IP Address Entry
        tk.Label(input_frame,
                 text="IP Address:",
                 bg="white",
                 font=("Arial", 10)).grid(row=1, column=0, sticky="w", padx=10)

        ip_entry = tk.Entry(input_frame, width=20)
        ip_entry.grid(row=1, column=1, padx=10, pady=2)

        def add_entry():
            """Validates and adds the new miner to the list."""
            bitaxe_type = type_var.get()
            ip = ip_entry.get().strip()

            if not ip:
                messagebox.showerror("Error", "IP Address is required.")
                return

            defaults = get_miner_defaults(bitaxe_type)

            self.tree.insert("", "end", values=(
                bitaxe_type, ip,
                defaults["min_freq"], defaults["max_freq"],
                defaults["min_volt"], defaults["max_volt"],
                defaults["max_temp"], defaults["max_watts"], "1600"
            ))

            add_miner(bitaxe_type, ip)  # Save to config.json
            add_window.destroy()

        # Miner Button (Styled)
        tk.Button(add_window, text="Add", font=("Arial", 10), width=10, command=add_entry, bg="white").pack(pady=10)

    def delete_miner(self):
        """Deletes selected miner(s) from the table and removes them from config.json."""
        selected_items = self.tree.selection()

        if not selected_items:
            messagebox.showwarning("No Selection", "Please select a miner to delete.")
            return

        confirmation = messagebox.askyesno("Delete Miner", "Are you sure you want to remove the selected miner(s)?")
        if not confirmation:
            return

        config = load_config()  # Load current config
        miners = config.get("miners", [])  # Get the list of miners

        for item in selected_items:
            values = self.tree.item(item, "values")
            ip = values[1]  # Extract miner's IP address

            # Remove miner from GUI
            self.tree.delete(item)

            # Remove miner from config.json
            miners = [miner for miner in miners if miner["ip"] != ip]

        # Update config.json to remove deleted miners
        config["miners"] = miners
        save_config(config)  # Save changes to config.json

        self.log_message("Miner(s) removed successfully.", "success")

    def start_autotuning(self):
        """Starts autotuning miners."""
        self.running = True
        self.threads.clear()

        # Load interval from global settings in config.json
        config = load_config()
        interval = config.get("monitor_interval", 5)  # Default to 5 sec if missing

        self.log_message("Starting autotuning for selected miners...", "success")

        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            ip, bitaxe_type = values[1], values[0]  # Adjust based on your columns

            thread = threading.Thread(target=monitor_and_adjust, args=(ip, bitaxe_type, interval, self.log_message))
            thread.start()
            self.threads.append(thread)

    def stop_autotuning(self):
        """Stops all autotuning processes."""
        self.running = False
        stop_autotuning()
        self.log_message("Stopping autotuning...", "warning")

    def exit_fullscreen(self, event=None):
        """Exit full-screen mode."""
        self.root.attributes("-fullscreen", False)

    def toggle_fullscreen(self, event=None):
        """Toggle full-screen mode."""
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))

    def show_tree_menu(self, event):
        """Displays the right-click context menu when a miner is right-clicked."""
        selected_item = self.tree.identify_row(event.y)  # Get row under cursor

        if selected_item:
            self.tree.selection_set(selected_item)  # Highlight the selected item
            self.tree_menu.post(event.x_root, event.y_root)  # Show the menu at the cursor position

    def log_message(self, message, level="info"):
        """Logs messages to the UI."""
        colors = {"success": "green", "warning": "orange", "error": "red", "info": "black"}
        self.log_output.insert(tk.END, message + "\n", level)
        self.log_output.tag_config(level, foreground=colors[level])
        self.log_output.yview(tk.END)

    def run(self):
        """Runs the Tkinter event loop."""
        self.root.mainloop()

if __name__ == "__main__":
    app = BitaxeAutotuningApp()
    app.run()
