# TerraPing
Pinging tool for Sysadmins and Network Engineers for monitoring outages on internal network infrastructure.

Author: Terranovatech
Version: 1.0

# Description
The Ping Monitor Tool is a Python-based application with a GUI built using Tkinter. It monitors internet connectivity by periodically pinging a target address (8.8.8.8). If internet access is lost, it pings a user-specified list of IP addresses to help identify potential issues in the local network or external infrastructure. Additionally, users can enable a traceroute for more advanced troubleshooting. 

# Features
Dynamic IP Management: Add and remove IP addresses directly through the GUI.
Interval Selection: Choose from 1-minute, 5-minute, or 10-minute monitoring intervals.
Real-Time Logging: Logs results in a scrollable GUI and saves them to ping_log.txt.
Responsive GUI: Background monitoring ensures the application remains responsive.
Advanced Network Diagnostics: Ability to enable a traceroute on failure.

# How to Use
Launch the application by running the script:
python3 ping_monitor.py

Add IP addresses to the list using the input box and "Add" button.
Select the desired monitoring interval from the dropdown menu.
Click "Start Monitoring" to begin checking connectivity.
View real-time logs in the GUI or check the ping_log.txt file for a complete history.

# Requirements
Python 3.7 or later
Modules: tkinter, subprocess, datetime, threading
**A .exe version of this can be made available for you in a Zip folder upon request**

# Known Issues
The tool assumes ping -n syntax for Windows-based systems. Update the code for Windows (ping -c) if necessary.

# Future Enhancements
Add support for exporting the list of IPs.
Enable real-time notification (e.g., sound or popup) on connectivity loss.
