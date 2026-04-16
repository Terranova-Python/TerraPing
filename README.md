# TerraPing
Network Outage Diagnostic Tool for Sysadmins and Network Engineers.

Author: Anthony Terrano

# Description
TerraPing is a Python-based GUI application built with CustomTkinter that monitors internet connectivity by periodically pinging 8.8.8.8. When internet access is lost, it automatically pings a user-defined list of LAN IP addresses (gateways, switches, APs, servers) and performs a **root-cause analysis** to determine where the failure likely occurred. Results are reported in a clear diagnosis inside the GUI log and saved to a text file for later review.

Optionally, users can enable **traceroute** (on unreachable hosts) and **port scanning** (on reachable hosts) for deeper troubleshooting.

![image](https://github.com/user-attachments/assets/5261923a-dc34-45b1-9bb1-d532427f3459)
![image](https://github.com/user-attachments/assets/d12796f6-a04f-473c-a81b-5a7ba4fd9599)

# Features
1. Add and remove LAN IP addresses directly through the GUI.
2. Choose from 1-minute, 5-minute, or 10-minute monitoring intervals.
3. Automatic **root-cause analysis** on every outage — diagnoses whether the issue is local (adapter/cable), infrastructure (switch/AP), or upstream (ISP/modem).
4. Logs results in a scrollable GUI and saves them to `logs/ping_log.txt`.
5. Background monitoring keeps the application responsive.
6. Optional traceroute on unreachable hosts for path analysis.
7. Optional port scan on reachable hosts for service verification.
8. Cross-platform: works on Windows, macOS, and Linux.

# How to Use
**Download the ZIP file and extract to a location of choice. DO NOT REMOVE THE .EXE FROM ITS PARENT FOLDER. Run the .exe — logs will be exported automatically to the `logs/` folder.**

**IDE or Python Users:**
Launch the application by running the script:
```
python ping_monitor.py
```

1. Add LAN IP addresses (e.g. your default gateway, switches, APs) using the input box and "Add" button.
2. Select the desired monitoring interval.
3. Click "Start Monitoring" to begin checking connectivity.
4. When an outage is detected, TerraPing sweeps all configured IPs and prints a diagnosis explaining the likely cause.
5. (Optional) Enable Traceroute and/or Port Scan checkboxes for deeper diagnostic data.
6. View real-time logs in the GUI or check `logs/ping_log.txt` for full history.

# Requirements
If running from source:
- Python 3.10 or later
- Modules: `customtkinter`

All other dependencies (`subprocess`, `threading`, `socket`, `ipaddress`, `csv`, `platform`, etc.) are part of the Python standard library.

Install the required modules:
```
pip install -r requirements.txt
```

Otherwise, just a Windows OS is required to run the .exe.

# Recommended LAN IPs to Monitor
For best diagnostic results, add these in order:
1. **Default gateway** (e.g. 192.168.1.1)
2. **Core switch / distribution switch**
3. **Key servers** (DNS, DHCP, file server)
4. **Wireless access points**

This ordering helps TerraPing pinpoint exactly where connectivity breaks down.
