import subprocess
import time
import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime
import threading
import os
import csv
import re
import ipaddress
import subprocess
import socket


# INIT Crap
log_folder = "logs"
if not os.path.exists(log_folder):
    os.makedirs(log_folder)

def is_valid_ip(ip):
    pattern = r"^([0-9]{1,3}\.){3}[0-9]{1,3}$"
    return bool(re.match(pattern, ip))


def is_private_ip(ip):
    try:
        ip_obj = ipaddress.ip_address(ip)
        return ip_obj.is_private
    except ValueError:
        return False  # If the IP is invalid, it's treated as non-private
    

def ping(host):
    try:
        result = subprocess.run(
            ["ping", "-n", "1", host],  # Comment this line out and enable NEXT Line if running on Linux.
            # ["ping", "-c", "1", host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except Exception as e:
        log_message(f"Error pinging {host}: {e}")
        return False


def scan_open_ports(ip, ports=(21, 22, 23, 25, 53, 80, 443, 3389)):
    log_message(f"#### Scanning for commonly open ports on {ip} ####")
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)  # Set a timeout for the connection attempt
                result = s.connect_ex((ip, port))
                if result == 0:
                    log_message(f"Port {port} on {ip} is OPEN.")
                else:
                    log_message(f"Port {port} on {ip} is CLOSED.")
        except Exception as e:
            log_message(f"Error scanning port {port} on {ip}: {e}")
    log_message(f"#### END PORT SCAN #####")


def validate_ip_range(ip):
    octets = ip.split('.')
    for octet in octets:
        if not (0 <= int(octet) <= 255): # Check if the IP's octets are within the valid range of 0-255.
            return False
    return True


def load_ip_list():
    try:
        # Clear existing data from ip_addresses and Listbox
        ip_addresses.clear()
        ip_list.delete(0, tk.END)
        
        # Open and read the CSV file
        with open("ip/ip_list.csv", mode="r") as file:
            reader = csv.reader(file)
            for row in reader:
                if row:  # Ensure the row isn't empty
                    ip_addresses.append(row[0])  # Add each IP to the list
                    ip_list.insert(tk.END, row[0])  # Insert the IP into the Listbox
    except FileNotFoundError:
        log_message("No saved IP list found, starting fresh.")


def remove_selected_ip():
    selected = ip_list.curselection()
    if selected:
        ip = ip_list.get(selected)
        ip_addresses.remove(ip)
        ip_list.delete(selected)
        log_message(f"Removed IP: {ip}")
        save_ip_list()  # Save the list to CSV after removing IP
       

def save_ip_list():
    os.makedirs("ip", exist_ok=True)  # Create the 'ip' folder if it doesn't exist
    with open("ip/ip_list.csv", mode="w", newline="") as file:
        writer = csv.writer(file)
        for ip in ip_addresses:
            writer.writerow([ip])  # Write each IP as a new row


def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    # Update the GUI log display
    log_text.insert(tk.END, log_entry)
    log_text.see(tk.END)  # Auto-scroll to the bottom

    # Use os.path.join to create a valid path in a platform-independent way
    log_file_path = os.path.join(log_folder, "ping_log.txt")
    
    # Save the log to a file in the 'logs' folder
    with open(log_file_path, "a") as log_file:
        log_file.write(log_entry)


def open_logs_folder():
    log_folder = "logs"
    
    # Ensure the folder exists before trying to open it
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    
    # For Windows
    if os.name == 'nt':  # Check if we're on Windows
        os.startfile(log_folder)  # Opens the folder in the default file explorer
    else:
        # For macOS/Linux, use subprocess to open the folder
        subprocess.run(['open', log_folder] if os.name == 'posix' else ['xdg-open', log_folder])


def monitor_internet(interval=60):
    global monitoring
    while monitoring:
        log_message("Checking internet connectivity...")
        if ping("8.8.8.8"):
            log_message("Internet is reachable.")
        else:
            log_message("Internet is down. Pinging specified IP addresses...")
            for ip in ip_addresses:
                if not monitoring:  # Exit early if monitoring is stopped
                    break
                if ping(ip):
                    log_message(f"Ping to {ip} successful.")
                    
                    if port_scan_enabled.get(): # Perform a port scan if enabled
                        scan_open_ports(ip)
                    
                else:
                    log_message(f"Ping to {ip} failed.")
                    if traceroute_enabled.get():  # Check if traceroute is enabled
                        perform_traceroute(ip)
        time.sleep(interval)
    log_message("Monitoring stopped.")


def perform_traceroute(ip):
    log_message(f"Performing a traceroute to {ip}...")
    try:
        result = subprocess.run(["tracert", ip], capture_output=True, text=True, timeout=30)
        log_message(f"Traceroute to {ip}:\n{result.stdout}")
    except Exception as e:
        log_message(f"Error during traceroute to {ip}: {e}")


def save_ip_list():
    os.makedirs("ip", exist_ok=True)  # Create the 'ip' folder if it doesn't exist
    with open("ip/ip_list.csv", mode="w", newline="") as file:
        writer = csv.writer(file)
        for ip in ip_addresses:
            writer.writerow([ip])  # Write each IP as a new row


def start_monitoring():
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


def stop_monitoring():
    global monitoring
    monitoring = False
    log_message("Stopped monitoring...")


def add_ip():
    ip = ip_entry.get().strip()
    
    # Check if the IP format is valid
    if not is_valid_ip(ip):
        log_message("Error: Invalid IP format. Please enter a valid IP address in the format x.x.x.x.")
        return
    
    # Check if each octet is within the correct range (0-255)
    if not validate_ip_range(ip):
        log_message(f"Error: {ip} contains an invalid octet. Each octet must be between 0 and 255.")
        return
    
    # Check if the IP is in the private space
    if not is_private_ip(ip):
        log_message(f"Error: {ip} is in the public IP space. Cannot ping this IP address.")
        return
    
    # If All checks pass, add the IP to the list
    if ip not in ip_addresses:
        ip_addresses.append(ip)
        ip_list.insert(tk.END, ip)
        log_message(f"Added IP: {ip}")
        
        # Save the updated list to the CSV file
        save_ip_list()
        
    # Clears the entry field
    ip_entry.delete(0, tk.END)


root = tk.Tk()
root.title("TerraPing v1.3")

port_scan_enabled = tk.BooleanVar(value=False)

input_frame = tk.Frame(root)
input_frame.pack(pady=10)

# Globals
ip_addresses = []
monitoring = False
traceroute_enabled = tk.BooleanVar(value=False)

tk.Label(input_frame, text="LAN IP Address:").grid(row=0, column=0, padx=5)
ip_entry = tk.Entry(input_frame, width=20)
ip_entry.bind("<Return>", lambda event: add_ip())
ip_entry.grid(row=0, column=1, padx=5)

add_button = tk.Button(input_frame, text="Add", command=add_ip)
add_button.grid(row=0, column=2, padx=5)

remove_button = tk.Button(input_frame, text="Remove Selected", command=remove_selected_ip)
remove_button.grid(row=0, column=3, padx=5)

button_frame = tk.Frame(root)
button_frame.pack(pady=10)

traceroute_toggle = tk.Checkbutton(root, text="Enable Traceroute?", variable=traceroute_enabled)
traceroute_toggle.pack(pady=5)

port_scan_checkbox = tk.Checkbutton(root, text="Common Port Scan?", variable=port_scan_enabled)
port_scan_checkbox.pack(pady=5)

start_button = tk.Button(button_frame, text="Start Monitoring", command=start_monitoring)
start_button.grid(row=0, column=0, padx=5)
stop_button = tk.Button(button_frame, text="Stop Monitoring", command=stop_monitoring)
stop_button.grid(row=0, column=1, padx=5)

ip_list = tk.Listbox(root, width=40, height=10)
ip_list.pack(pady=10)

log_text = scrolledtext.ScrolledText(root, width=80, height=20, state="normal")
log_text.pack(pady=10)

open_logs_button = tk.Button(root, text="Open Log Folder", command=open_logs_folder)
open_logs_button.pack(pady=10)  # Add it at the bottom with some padding

selected_interval = tk.StringVar(value="1 Minute")

tk.Label(input_frame, text="Check Connection Interval").grid(row=1, column=0, padx=5)
interval_menu = tk.OptionMenu(input_frame, selected_interval, "1 Minute", "5 Minutes", "10 Minutes")
interval_menu.grid(row=1, column=1, padx=5)

load_ip_list()
root.mainloop()
