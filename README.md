# TerraPing
Pinging tool for Sysadmins and Network Engineers for monitoring outages on internal network infrastructure.

Author: Terranovatech
Version: 1.2

# Description
The Ping Monitor Tool is a Python-based application with a GUI built using Tkinter. It monitors internet connectivity by periodically pinging a target address (8.8.8.8). If internet access is lost, it pings a user-specified list of IP addresses to help identify potential issues in the local network or external infrastructure. Additionally, users can enable a traceroute for more advanced troubleshooting. 

# Features
Dynamic IP Management: Add and remove IP addresses directly through the GUI.
Interval Selection: Choose from 1-minute, 5-minute, or 10-minute monitoring intervals.
Real-Time Logging: Logs results in a scrollable GUI and saves them to ping_log.txt.
Responsive GUI: Background monitoring ensures the application remains responsive.
Advanced Network Diagnostics: Ability to enable a traceroute on failure.

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

Python 3.7 or later
Modules: tkinter, subprocess, datetime, threading

# Known Issues
The tool assumes ping -n syntax for Windows-based systems. Update the code for Linux (ping -c) if you plan to run this on Linux.

# Future Enhancements
Add support for saving the list of IPs added in a session
