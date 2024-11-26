import subprocess
import time
import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime
import threading

def ping(host):
    """Pings a host and returns True if successful, False otherwise."""
    try:
        result = subprocess.run(
            ["ping", "-n", "1", host],  # Use "ping -n 1" on Windows
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except Exception as e:
        log_message(f"Error pinging {host}: {e}")
        return False

def log_message(message):
    """Logs a message to the GUI and a log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    log_text.insert(tk.END, log_entry)
    log_text.see(tk.END)  # Auto-scroll to the bottom

    with open("ping_log.txt", "a") as log_file:
        log_file.write(log_entry)

def monitor_internet(interval=60):
    """Monitors internet connectivity and optionally performs traceroutes."""
    global monitoring
    while monitoring:
        log_message("Pinging 8.8.8.8 to check internet connectivity...")
        if ping("8.8.8.8"):
            log_message("Internet is reachable.")
        else:
            log_message("Internet is down. Pinging specified IP addresses...")
            for ip in ip_addresses:
                if not monitoring:  # Exit early if monitoring is stopped
                    break
                if ping(ip):
                    log_message(f"Ping to {ip} successful.")
                else:
                    log_message(f"Ping to {ip} failed.")
                    if traceroute_enabled.get():  # Check if traceroute is enabled
                        perform_traceroute(ip)
        time.sleep(interval)
    log_message("Monitoring stopped.")

def stop_monitoring():
    """Stops the monitoring process."""
    global monitoring
    monitoring = False
    log_message("Stopped monitoring...")

def add_ip():
    """Adds an IP address to the list."""
    ip = ip_entry.get().strip()
    if ip and ip not in ip_addresses:
        ip_addresses.append(ip)
        ip_list.insert(tk.END, ip)
        log_message(f"Added IP: {ip}")
    ip_entry.delete(0, tk.END)

def remove_selected_ip():
    """Removes the selected IP from the list."""
    selected = ip_list.curselection()
    if selected:
        ip = ip_list.get(selected)
        ip_addresses.remove(ip)
        ip_list.delete(selected)
        log_message(f"Removed IP: {ip}")

def start_monitoring():
    """Starts the monitoring in a separate thread with the selected interval."""
    global monitoring
    monitoring = True  # Enable monitoring
    try:
        # Convert the selected interval to seconds
        interval_map = {
            "1 Minute": 60,
            "5 Minutes": 300,
            "10 Minutes": 600
        }
        interval_seconds = interval_map[selected_interval.get()]
        log_message(f"Starting monitoring with interval: {selected_interval.get()}...")
        
        monitor_thread = threading.Thread(target=monitor_internet, args=(interval_seconds,), daemon=True)
        monitor_thread.start()
    except KeyError:
        log_message("Invalid interval selected. Please choose a valid option.")

def perform_traceroute(ip):
    """Performs a traceroute to the given IP address and logs the result."""
    log_message(f"Performing traceroute to {ip}...")
    try:
        result = subprocess.run(["tracert", ip], capture_output=True, text=True, timeout=30)
        log_message(f"Traceroute to {ip}:\n{result.stdout}")
    except Exception as e:
        log_message(f"Error during traceroute to {ip}: {e}")

# GUI setup
root = tk.Tk()
root.title("TerraPing v1.2")

# Input section
input_frame = tk.Frame(root)
input_frame.pack(pady=10)

tk.Label(input_frame, text="IP Address:").grid(row=0, column=0, padx=5)
ip_entry = tk.Entry(input_frame, width=20)
ip_entry.grid(row=0, column=1, padx=5)

add_button = tk.Button(input_frame, text="Add", command=add_ip)
add_button.grid(row=0, column=2, padx=5)

# frame to hold Start and Stop buttons
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

# Stop and Start Buttons
start_button = tk.Button(button_frame, text="Start Monitoring", command=start_monitoring)
start_button.grid(row=0, column=0, padx=5)
stop_button = tk.Button(button_frame, text="Stop Monitoring", command=stop_monitoring)
stop_button.grid(row=0, column=1, padx=5)

remove_button = tk.Button(input_frame, text="Remove Selected", command=remove_selected_ip)
remove_button.grid(row=0, column=3, padx=5)


# Listbox for IP addresses
ip_list = tk.Listbox(root, width=40, height=10)
ip_list.pack(pady=10)

# Log display
log_text = scrolledtext.ScrolledText(root, width=60, height=15, state="normal")
log_text.pack(pady=10)

selected_interval = tk.StringVar(value="1 Minute")

# Globals
ip_addresses = []
monitoring = False
traceroute_enabled = tk.BooleanVar(value=False)

# Button for traceroute
traceroute_toggle = tk.Checkbutton(root, text="Enable Traceroute?", variable=traceroute_enabled)
traceroute_toggle.pack(pady=5)

tk.Label(input_frame, text="Ping Interval:").grid(row=1, column=0, padx=5)
interval_menu = tk.OptionMenu(input_frame, selected_interval, "1 Minute", "5 Minutes", "10 Minutes")
interval_menu.grid(row=1, column=1, padx=5)

# Start the GUI loop
root.mainloop()
