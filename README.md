# TerraPing
Network Outage Diagnostic Tool for Sysadmins and Network Engineers.

Author: Anthony Terrano

# Description
TerraPing is a Python-based GUI application built with CustomTkinter that monitors internet connectivity by periodically pinging multiple public DNS servers (8.8.8.8 and 1.1.1.1) to reduce false positives. When internet access is lost, it automatically pings a user-defined list of LAN IP addresses (gateways, switches, APs, servers) **concurrently** and performs a **root-cause analysis** to determine where the failure likely occurred. Results are reported in a clear diagnosis inside the GUI log — complete with latency data — and saved to a text file for later review.

Optionally, users can enable **traceroute** (on unreachable hosts) and **port scanning** (on reachable hosts) for deeper troubleshooting.

![image](https://github.com/user-attachments/assets/5261923a-dc34-45b1-9bb1-d532427f3459)
![image](https://github.com/user-attachments/assets/d12796f6-a04f-473c-a81b-5a7ba4fd9599)

# Features
1. Add and remove LAN IP addresses directly through the GUI.
2. **Auto-detect default gateway** with one click.
3. Choose from 30-second, 1-minute, 5-minute, or 10-minute monitoring intervals.
4. **Multi-target internet check** — pings both 8.8.8.8 and 1.1.1.1 concurrently to eliminate false positives.
5. **Concurrent LAN sweeps** — all configured IPs are pinged in parallel using a thread pool for faster diagnostics.
6. **Ping latency reporting** — shows round-trip time in milliseconds for each reachable host.
7. Automatic **root-cause analysis** on every outage — diagnoses whether the issue is local (adapter/cable), infrastructure (switch/AP), or upstream (ISP/modem).
8. **Live statistics** — tracks total checks, outage count, and uptime percentage.
9. **Connection history** — visual dot indicator showing the last 30 check results at a glance.
10. Logs results in a scrollable GUI and saves them to `logs/ping_log.txt`.
11. **Export logs** to any location via Save As dialog.
12. **Clear log** display with one click.
13. **Settings persistence** — appearance mode, interval, and diagnostic options are saved between sessions.
14. **Appearance mode toggle** — switch between Dark, Light, and System themes.
15. **Sound alerts** — audible notification on outage detection (toggleable).
16. Background monitoring with responsive stop via `threading.Event`.
17. Optional traceroute on unreachable hosts for path analysis.
18. Optional port scan on reachable hosts for service verification.
19. **Tabbed UI** — Monitor and Settings tabs keep the interface clean and organized.
20. Cross-platform: works on Windows, macOS, and Linux.

# How to Use
**Download the ZIP file and extract to a location of choice. DO NOT REMOVE THE .EXE FROM ITS PARENT FOLDER. Run the .exe — logs will be exported automatically to the `logs/` folder.**

**IDE or Python Users:**
Launch the application by running the script:
```
python ping_monitor.py
```

1. Add LAN IP addresses using the input box and "Add" button, or click **Detect Gateway** to auto-add your default gateway.
2. Switch to the **Settings** tab to configure the monitoring interval, enable traceroute/port scan, and toggle sound alerts.
3. Click **Start Monitoring** on the Monitor tab to begin checking connectivity.
4. When an outage is detected, TerraPing sweeps all configured IPs concurrently and prints a diagnosis explaining the likely cause, including latency data.
5. Monitor the **status bar** for live statistics (checks, outages, uptime %) and the **history dots** for a visual timeline.
6. Use **Export** to save the full log to a file, or **Open Folder** to browse the logs directory.

# Requirements
If running from source:
- Python 3.10 or later
- Modules: `customtkinter`

All other dependencies (`subprocess`, `threading`, `socket`, `ipaddress`, `csv`, `json`, `concurrent.futures`, `platform`, etc.) are part of the Python standard library.

Install the required modules:
```
pip install -r requirements.txt
```

Otherwise, just a Windows OS is required to run the .exe.

# Recommended LAN IPs to Monitor
For best diagnostic results, add these in order:
1. **Default gateway** (e.g. 192.168.1.1) — use the **Detect Gateway** button
2. **Core switch / distribution switch**
3. **Key servers** (DNS, DHCP, file server)
4. **Wireless access points**

This ordering helps TerraPing pinpoint exactly where connectivity breaks down.

# Changelog

## v4.0
- Concurrent LAN ping sweeps using thread pool for significantly faster diagnostics.
- Multi-target internet check (8.8.8.8 + 1.1.1.1) to reduce false positives.
- Ping latency extraction and display (ms) for all reachable hosts.
- Auto-detect default gateway button.
- Live statistics bar: total checks, outage count, uptime percentage.
- Visual connection history dots (last 30 results).
- Tabbed UI with separate Monitor and Settings tabs.
- Dark / Light / System appearance mode toggle.
- Settings persistence (saved to `ip/config.json`).
- Export log to file via Save As dialog.
- Clear log button.
- Sound alert on outage detection (toggleable).
- 30-second monitoring interval option.
- Responsive stop using `threading.Event` instead of polling loop.
- Removed redundant `os.makedirs` call and unused `time` import.

## v3.0
- Initial public release with root-cause analysis, traceroute, and port scanning.
