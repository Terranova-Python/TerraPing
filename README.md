# TerraPing
Pinging tool for Sysadmins and Network Engineers for monitoring outages on internal network infrastructure.

Author: Anthony Terrano

# Description
The Ping Monitor Tool is a Python-based application with a GUI built using CustomTkinter. It monitors internet connectivity by periodically pinging a target address (8.8.8.8). If internet access is lost, it pings a user-specified list of IP addresses to help identify potential issues in the local network or external infrastructure. Additionally, users can enable a traceroute and a simple common port scan for more advanced troubleshooting.

![image](https://github.com/user-attachments/assets/5261923a-dc34-45b1-9bb1-d532427f3459)
![image](https://github.com/user-attachments/assets/d12796f6-a04f-473c-a81b-5a7ba4fd9599)

# Features
1. Add and remove IP addresses directly through the GUI.
2. Choose from 1-minute, 5-minute, or 10-minute monitoring intervals.
3. Logs results in a scrollable GUI and saves them to ping_log.txt.
4. Background monitoring ensures the application remains responsive.
5. Ability to enable a traceroute on failure.
6. Portscans for advanced troubleshooting.

# How to Use
**Download the ZIP file and export to a location of choice. DO NOT REMOVE THE .EXE FROM ITS PARENT FOLDER. Run the .exe, logs will be exported automatically via .txt to the root of this folder.**

**IDE or Python Users:**
Launch the application by running the script:
python3 ping_monitor.py

1. Add IP addresses to the list using the input box and "Add" button.
2. Select the desired monitoring interval from the dropdown menu.
3. Click "Start Monitoring" to begin checking connectivity.
4. (Optional) Enable Traceroute to pings when internet connectivity is lost for more advanced logging.
5. View real-time logs in the GUI or check the ping_log.txt file for a complete history.

# Requirements
If running on IDE or Pythin natively:
Python 3.7 or later
Modules: customtkinter, tk, subprocess, datetime, threading, os, socket, ipaddress, csv, re, time

Otherwise, just a windows OS is required to run the .exe

# Known Issues
The tool assumes ping -n syntax for Windows-based systems. Update the code for Linux (ping -c) if you plan to run this on Linux.
