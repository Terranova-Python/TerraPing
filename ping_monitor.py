"""
TerraPing - Network Outage Diagnostic Tool
Author: Anthony Terrano

Monitors internet connectivity and, on failure, pings a user-defined list of
LAN IP addresses to diagnose the root cause. Reports findings in a structured
log with actionable root-cause analysis.
"""

import subprocess
import sys
import time
import platform
import threading
import os
import csv
import ipaddress
import socket
from datetime import datetime

import customtkinter as ctk
import tkinter as tk

# ---------------------------------------------------------------------------
# Platform helpers
# ---------------------------------------------------------------------------
IS_WINDOWS = platform.system() == "Windows"
PING_COUNT_FLAG = "-n" if IS_WINDOWS else "-c"
PING_TIMEOUT_FLAG = "-w" if IS_WINDOWS else "-W"
PING_TIMEOUT_VALUE = "1000" if IS_WINDOWS else "1"
TRACEROUTE_CMD = "tracert" if IS_WINDOWS else "traceroute"

LOG_FOLDER = "logs"
IP_FOLDER = "ip"
IP_FILE = os.path.join(IP_FOLDER, "ip_list.csv")

os.makedirs(LOG_FOLDER, exist_ok=True)
os.makedirs(IP_FOLDER, exist_ok=True)

# ---------------------------------------------------------------------------
# Networking utilities
# ---------------------------------------------------------------------------

def validate_ip(ip_str: str) -> bool:
    """Return True if *ip_str* is a valid IPv4 address."""
    try:
        ipaddress.IPv4Address(ip_str)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def is_private_ip(ip_str: str) -> bool:
    try:
        return ipaddress.IPv4Address(ip_str).is_private
    except (ipaddress.AddressValueError, ValueError):
        return False


def ping(host: str) -> bool:
    """Ping *host* once. Returns True on success."""
    try:
        result = subprocess.run(
            ["ping", PING_COUNT_FLAG, "1", PING_TIMEOUT_FLAG, PING_TIMEOUT_VALUE, host],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0,
        )
        if IS_WINDOWS:
            return "TTL=" in result.stdout.upper()
        return result.returncode == 0
    except Exception:
        return False


def traceroute(host: str) -> str:
    """Run a traceroute/tracert and return the output."""
    try:
        result = subprocess.run(
            [TRACEROUTE_CMD, host],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return f"Traceroute to {host} timed out."
    except Exception as exc:
        return f"Traceroute error: {exc}"


def scan_ports(ip: str, ports=(21, 22, 23, 53, 80, 443, 3389)) -> list[tuple[int, bool]]:
    """Return a list of (port, is_open) tuples."""
    results = []
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                is_open = s.connect_ex((ip, port)) == 0
                results.append((port, is_open))
        except Exception:
            results.append((port, False))
    return results


# ---------------------------------------------------------------------------
# Root-cause analysis
# ---------------------------------------------------------------------------

def analyse_results(ping_results: dict[str, bool]) -> str:
    """Given {ip: reachable} from a LAN sweep, produce a diagnosis string."""
    if not ping_results:
        return (
            "DIAGNOSIS: No LAN IPs configured. Unable to determine root cause. "
            "Add your gateway and key infrastructure IPs to improve diagnostics."
        )

    reachable = [ip for ip, ok in ping_results.items() if ok]
    unreachable = [ip for ip, ok in ping_results.items() if not ok]

    if not reachable:
        return (
            "DIAGNOSIS: ALL LAN devices unreachable. "
            "Likely cause -- local network adapter is down, cable unplugged, "
            "or the default gateway / first-hop switch is offline."
        )

    if not unreachable:
        return (
            "DIAGNOSIS: All LAN devices are reachable but internet is down. "
            "Likely cause -- ISP outage or upstream router/modem has lost its WAN link. "
            "Check modem sync lights and contact your ISP."
        )

    # Partial reachability
    lines = [
        "DIAGNOSIS: Partial LAN connectivity detected.",
        f"  Reachable  : {', '.join(reachable)}",
        f"  Unreachable: {', '.join(unreachable)}",
        "  Likely cause -- one or more intermediate switches, APs, or VLANs are down.",
        "  The devices that ARE reachable share a working path to this host.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class TerraPing(ctk.CTk):
    """Main application window."""

    APP_VERSION = "3.0"

    def __init__(self):
        super().__init__()

        self.title(f"TerraPing v{self.APP_VERSION}")
        self.resizable(False, False)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.ip_addresses: list[str] = []
        self._monitoring = False
        self._monitor_thread: threading.Thread | None = None
        self._lock = threading.Lock()

        self.traceroute_enabled = tk.BooleanVar(value=False)
        self.port_scan_enabled = tk.BooleanVar(value=False)
        self.selected_interval = ctk.StringVar(value="1 Minute")

        self._build_ui()
        self._load_ip_list()

    # ---- UI construction ---------------------------------------------------

    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        # --- Header / title ---
        header = ctk.CTkLabel(
            self, text=f"TerraPing v{self.APP_VERSION}",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        header.pack(pady=(12, 2))
        subtitle = ctk.CTkLabel(
            self, text="Network Outage Diagnostic Tool",
            font=ctk.CTkFont(size=12), text_color="gray",
        )
        subtitle.pack(pady=(0, 8))

        # --- IP entry row ---
        ip_frame = ctk.CTkFrame(self, fg_color="transparent")
        ip_frame.pack(**pad, fill="x")

        ctk.CTkLabel(ip_frame, text="LAN IP:").pack(side="left", padx=(10, 4))
        self.ip_entry = ctk.CTkEntry(ip_frame, width=200, placeholder_text="e.g. 192.168.1.1")
        self.ip_entry.pack(side="left", padx=4)
        self.ip_entry.bind("<Return>", lambda _: self._add_ip())
        ctk.CTkButton(ip_frame, text="Add", width=60, command=self._add_ip).pack(side="left", padx=4)

        # --- IP list ---
        self.ip_list_frame = ctk.CTkScrollableFrame(self, width=420, height=90, label_text="Monitored LAN IPs")
        self.ip_list_frame.pack(**pad, fill="x")

        # --- Interval selector ---
        interval_frame = ctk.CTkFrame(self, fg_color="transparent")
        interval_frame.pack(**pad, fill="x")
        ctk.CTkLabel(interval_frame, text="Check Interval:").pack(side="left", padx=(10, 6))
        ctk.CTkSegmentedButton(
            interval_frame,
            values=["1 Minute", "5 Minutes", "10 Minutes"],
            variable=self.selected_interval,
        ).pack(side="left", padx=4)

        # --- Options row ---
        opts_frame = ctk.CTkFrame(self, fg_color="transparent")
        opts_frame.pack(**pad, fill="x")
        ctk.CTkCheckBox(opts_frame, text="Traceroute on failure", variable=self.traceroute_enabled).pack(side="left", padx=10)
        ctk.CTkCheckBox(opts_frame, text="Port scan on success", variable=self.port_scan_enabled).pack(side="left", padx=10)

        # --- Action buttons ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(**pad)
        self.start_btn = ctk.CTkButton(btn_frame, text="Start Monitoring", fg_color="#2d8f2d",
                                        hover_color="#1e6b1e", command=self._start_monitoring)
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = ctk.CTkButton(btn_frame, text="Stop Monitoring", fg_color="#b03030",
                                       hover_color="#882020", state="disabled", command=self._stop_monitoring)
        self.stop_btn.pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Open Logs", width=90, command=self._open_logs_folder).pack(side="left", padx=6)

        # --- Status indicator ---
        self.status_label = ctk.CTkLabel(self, text="STATUS: Idle", font=ctk.CTkFont(size=13, weight="bold"),
                                          text_color="gray")
        self.status_label.pack(pady=(4, 0))

        # --- Log view ---
        self.log_text = ctk.CTkTextbox(self, width=500, height=280, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_text.pack(**pad, fill="both", expand=True)

    # ---- Logging -----------------------------------------------------------

    def _log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}\n"

        # Thread-safe GUI update
        self.after(0, self._append_log_text, entry)

        log_path = os.path.join(LOG_FOLDER, "ping_log.txt")
        with self._lock:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(entry)

    def _append_log_text(self, entry: str):
        self.log_text.insert("end", entry)
        self.log_text.see("end")

    def _set_status(self, text: str, color: str = "gray"):
        self.after(0, lambda: self.status_label.configure(text=f"STATUS: {text}", text_color=color))

    # ---- IP list management ------------------------------------------------

    def _add_ip(self):
        ip = self.ip_entry.get().strip()
        if not validate_ip(ip):
            self._log("Invalid IP format. Use x.x.x.x with octets 0-255.")
            return
        if not is_private_ip(ip):
            self._log(f"{ip} is not a private/LAN address. Only LAN IPs are supported.")
            return
        if ip in self.ip_addresses:
            self._log(f"{ip} is already in the list.")
            return

        self.ip_addresses.append(ip)
        self._add_ip_row(ip)
        self._log(f"Added IP: {ip}")
        self._save_ip_list()
        self.ip_entry.delete(0, "end")

    def _remove_ip(self, ip: str, row_widget):
        if ip in self.ip_addresses:
            self.ip_addresses.remove(ip)
            row_widget.destroy()
            self._log(f"Removed IP: {ip}")
            self._save_ip_list()

    def _add_ip_row(self, ip: str):
        row = ctk.CTkFrame(self.ip_list_frame)
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=ip, anchor="w").pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkButton(row, text="Remove", width=60, fg_color="#b03030",
                       hover_color="#882020",
                       command=lambda: self._remove_ip(ip, row)).pack(side="right", padx=4)

    def _save_ip_list(self):
        with open(IP_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for ip in self.ip_addresses:
                writer.writerow([ip])

    def _load_ip_list(self):
        if not os.path.isfile(IP_FILE):
            return
        try:
            with open(IP_FILE, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and validate_ip(row[0]) and row[0] not in self.ip_addresses:
                        self.ip_addresses.append(row[0])
                        self._add_ip_row(row[0])
        except Exception as exc:
            self._log(f"Error loading IP list: {exc}")

    # ---- Monitoring --------------------------------------------------------

    def _start_monitoring(self):
        if self._monitoring:
            return
        if not self.ip_addresses:
            self._log("Add at least one LAN IP before starting.")
            return

        self._monitoring = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        interval_map = {"1 Minute": 60, "5 Minutes": 300, "10 Minutes": 600}
        interval = interval_map.get(self.selected_interval.get(), 60)
        self._log(f"Monitoring started (interval: {self.selected_interval.get()}).")
        self._set_status("Monitoring", "#2d8f2d")

        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self._monitor_thread.start()

    def _stop_monitoring(self):
        if not self._monitoring:
            return
        self._monitoring = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self._log("Monitoring stopped.")
        self._set_status("Idle")

    def _monitor_loop(self, interval: int):
        while self._monitoring:
            self._log("Checking internet connectivity (8.8.8.8)...")
            if ping("8.8.8.8"):
                self._log("Internet is reachable.")
                self._set_status("Online", "#2d8f2d")
            else:
                self._set_status("OUTAGE DETECTED", "#e03030")
                self._log("Internet is DOWN. Running LAN diagnostics...")
                self._run_diagnostics()

            # Sleep in small increments so stop is responsive
            elapsed = 0
            while self._monitoring and elapsed < interval:
                time.sleep(1)
                elapsed += 1

        self._set_status("Idle")

    def _run_diagnostics(self):
        """Ping every configured LAN IP, run optional tools, then analyse."""
        self._log("=" * 50)
        self._log("BEGIN OUTAGE DIAGNOSTIC SWEEP")
        self._log("=" * 50)

        results: dict[str, bool] = {}
        for ip in list(self.ip_addresses):
            if not self._monitoring:
                return

            reachable = ping(ip)
            results[ip] = reachable

            if reachable:
                self._log(f"  {ip}  ....  REACHABLE")
                if self.port_scan_enabled.get():
                    self._log(f"  Port scan on {ip}:")
                    for port, is_open in scan_ports(ip):
                        status = "OPEN" if is_open else "closed"
                        self._log(f"    port {port:>5}  {status}")
            else:
                self._log(f"  {ip}  ....  UNREACHABLE")
                if self.traceroute_enabled.get():
                    self._log(f"  Traceroute to {ip}:")
                    for line in traceroute(ip).splitlines():
                        self._log(f"    {line}")

        # Root-cause analysis
        self._log("-" * 50)
        diagnosis = analyse_results(results)
        for line in diagnosis.splitlines():
            self._log(line)
        self._log("=" * 50)
        self._log("END OUTAGE DIAGNOSTIC SWEEP")
        self._log("=" * 50)

    # ---- Misc --------------------------------------------------------------

    def _open_logs_folder(self):
        os.makedirs(LOG_FOLDER, exist_ok=True)
        if IS_WINDOWS:
            os.startfile(LOG_FOLDER)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", LOG_FOLDER])
        else:
            subprocess.Popen(["xdg-open", LOG_FOLDER])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = TerraPing()
    app.mainloop()
