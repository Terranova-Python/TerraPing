import subprocess
import time
from datetime import datetime
import threading
import os
import csv
import re
import ipaddress
import subprocess
import socket
import customtkinter as ctk
import tkinter as tk

# INIT Crap
log_folder = "logs"
if not os.path.exists(log_folder):
    os.makedirs(log_folder)

# CUstomer TKinter INIT Crap
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

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
            ["ping", "-n", "1", "-w", "1000", host],  # Add a timeout with `-w` for Windows
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return "TTL=" in result.stdout  # Ensures a valid response by checking for TTL
    except Exception as e:
        log_message(f"Error pinging {host}: {e}")
        return False

def scan_open_ports(ip, ports=(21, 22, 23, 25, 53, 80, 443, 3389)):
    log_message(f"#### Scanning for commonly open ports on {ip} ####")
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
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
        if not (0 <= int(octet) <= 255):
            return False
    return True

def load_ip_list():
    try:
        ip_addresses.clear()
        for child in ip_list_frame.winfo_children():  # Clear existing items in the frame
            child.destroy()
        with open("ip/ip_list.csv", mode="r") as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    ip_addresses.append(row[0])
                    add_ip_to_frame(row[0])  # Add each IP to the scrollable frame
    except FileNotFoundError:
        log_message("No saved IP list found, starting fresh.")


def remove_ip(ip, ip_frame):
    if ip in ip_addresses:
        ip_addresses.remove(ip)
        ip_frame.destroy()  # Remove the IP's frame from the UI
        log_message(f"Removed IP: {ip}")
        save_ip_list()

def save_ip_list():
    os.makedirs("ip", exist_ok=True)
    with open("ip/ip_list.csv", mode="w", newline="") as file:
        writer = csv.writer(file)
        for ip in ip_addresses:
            writer.writerow([ip])

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    log_text.insert("end", log_entry)
    log_text.see("end")
    log_file_path = os.path.join(log_folder, "ping_log.txt")
    with open(log_file_path, "a") as log_file:
        log_file.write(log_entry)

def open_logs_folder():
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    if os.name == 'nt':
        os.startfile(log_folder)
    else:
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
                    
                    # Perform a port scan if enabled
                    if port_scan_enabled.get():
                        scan_open_ports(ip)
                    
                else:
                    log_message(f"Ping to {ip} failed.")
                    
                    # Perform a traceroute if enabled
                    if traceroute_enabled.get():
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

def start_monitoring():
    global monitoring
    monitoring = True
    try:
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

def add_ip_to_frame(ip):
    # Frame to Hold the IP label and Remove button
    ip_frame = ctk.CTkFrame(ip_list_frame)
    ip_frame.pack(fill="x", pady=2)
    
    # IP address as a label
    ip_label = ctk.CTkLabel(ip_frame, text=ip, anchor="w")
    ip_label.pack(side="left", fill="x", expand=True, padx=5)
    
    # Remove button next to the IP Address
    remove_button = ctk.CTkButton(ip_frame, text="Remove", width=60, 
                                   command=lambda: remove_ip(ip, ip_frame))
    remove_button.pack(side="right", padx=5)

def add_ip():
    ip = ip_entry.get().strip()
    if not is_valid_ip(ip):
        log_message("Error: Invalid IP format. Please enter a valid IP address in the format x.x.x.x.")
        return
    if not validate_ip_range(ip):
        log_message(f"Error: {ip} contains an invalid octet. Each octet must be between 0 and 255.")
        return
    if not is_private_ip(ip):
        log_message(f"Error: {ip} is in the public IP space. Cannot ping this IP address.")
        return
    if ip not in ip_addresses:
        ip_addresses.append(ip)
        add_ip_to_frame(ip)  # Add the IP to the scrollable frame
        log_message(f"Added IP: {ip}")
        save_ip_list()
    ip_entry.delete(0, "end")

# TK and CTK Magic below
root = ctk.CTk()
root.title("TerraPing v2.1")
root.resizable(False, False)

ip_addresses = []
monitoring = False
traceroute_enabled = tk.BooleanVar(value=False)
port_scan_enabled = tk.BooleanVar(value=False)

input_frame = ctk.CTkFrame(root, fg_color="#242424")
input_frame.pack(pady=10)

ctk.CTkLabel(input_frame, text="LAN IP Address:").grid(row=0, column=0, padx=5)
ip_entry = ctk.CTkEntry(input_frame, width=200)
ip_entry.bind("<Return>", lambda event: add_ip())
ip_entry.grid(row=0, column=1, padx=5)

add_button = ctk.CTkButton(input_frame, text="Add", command=add_ip)
add_button.grid(row=0, column=2, padx=5)

button_frame = ctk.CTkFrame(root)
button_frame.pack(pady=10)

traceroute_checkbox = ctk.CTkCheckBox(
    root,
    text="Traceroute",
    variable=traceroute_enabled
)
traceroute_checkbox.pack(pady=5)

port_scan_checkbox = ctk.CTkCheckBox(
    root,
    text="Port Scan",
    variable=port_scan_enabled
)
port_scan_checkbox.pack(pady=5)

start_button = ctk.CTkButton(button_frame, text="Start Monitoring", command=start_monitoring)
start_button.grid(row=0, column=0, padx=5)

stop_button = ctk.CTkButton(button_frame, text="Stop Monitoring", command=stop_monitoring)
stop_button.grid(row=0, column=1, padx=5)

ip_list_frame = ctk.CTkScrollableFrame(root, width=300, height=1)
ip_list_frame.pack(pady=10)

log_text = ctk.CTkTextbox(root, width=450, height=250)  ###########       LOGBOX
log_text.pack(pady=10)

open_logs_button = ctk.CTkButton(root, text="Open Log Folder", command=open_logs_folder)
open_logs_button.pack(pady=10)

selected_interval = ctk.StringVar(value="1 Minute")

interval_menu = ctk.CTkLabel(input_frame, text="Connection Interval")
interval_menu.grid(row=1, column=0, padx=5, pady=5)

interval_button = ctk.CTkSegmentedButton(
    input_frame,
    values=["1 Minute", "5 Minutes", "10 Minutes"],
    variable=selected_interval
)
interval_button.grid(row=1, column=1, padx=5, pady=5)

load_ip_list() # Dont move this :)
root.mainloop()
