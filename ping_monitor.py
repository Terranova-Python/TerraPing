"""
TerraPing - Network Outage Diagnostic Tool
Author: Anthony Terrano 2024

Monitors internet connectivity and, on failure, pings a user-defined list of
LAN IP addresses to diagnose the root cause. Reports findings in a structured
log with actionable root-cause analysis.
"""

import subprocess
import sys
import platform
import threading
import os
import re
import csv
import json
import shutil
import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog

# ---------------------------------------------------------------------------
# Platform helpers
# ---------------------------------------------------------------------------
IS_WINDOWS = platform.system() == "Windows"
PING_COUNT_FLAG = "-n" if IS_WINDOWS else "-c"
PING_TIMEOUT_FLAG = "-w" if IS_WINDOWS else "-W"
PING_TIMEOUT_VALUE = "1000" if IS_WINDOWS else "1"
TRACEROUTE_CMD = "tracert" if IS_WINDOWS else "traceroute"
SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0

LOG_FOLDER = "logs"
IP_FOLDER = "ip"
IP_FILE = os.path.join(IP_FOLDER, "ip_list.csv")
CONFIG_FILE = os.path.join(IP_FOLDER, "config.json")

INTERNET_TARGETS = ["8.8.8.8", "1.1.1.1"]
MAX_PING_WORKERS = 10
MAX_HISTORY = 30

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


def ping(host: str) -> tuple[bool, Optional[float]]:
    """Ping *host* once. Returns (success, latency_ms)."""
    try:
        result = subprocess.run(
            ["ping", PING_COUNT_FLAG, "1", PING_TIMEOUT_FLAG, PING_TIMEOUT_VALUE, host],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=SUBPROCESS_FLAGS,
        )
        if IS_WINDOWS:
            if "TTL=" in result.stdout.upper():
                match = re.search(r"time[=<]\s*(\d+)", result.stdout, re.IGNORECASE)
                return True, float(match.group(1)) if match else None
            return False, None
        if result.returncode == 0:
            match = re.search(r"time=(\d+\.?\d*)", result.stdout)
            return True, float(match.group(1)) if match else None
        return False, None
    except Exception:
        return False, None


def traceroute(host: str) -> str:
    """Run a traceroute/tracert and return the output."""
    try:
        result = subprocess.run(
            [TRACEROUTE_CMD, host],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            creationflags=SUBPROCESS_FLAGS,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return f"Traceroute to {host} timed out."
    except Exception as exc:
        return f"Traceroute error: {exc}"


def scan_ports(ip: str, ports: tuple[int, ...] = (21, 22, 23, 53, 80, 443, 3389)) -> list[tuple[int, bool]]:
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


def detect_default_gateway() -> Optional[str]:
    """Attempt to auto-detect the default gateway IP."""
    try:
        if IS_WINDOWS:
            result = subprocess.run(
                ["ipconfig"], stdout=subprocess.PIPE, text=True,
                creationflags=SUBPROCESS_FLAGS,
            )
            for match in re.finditer(r"Default Gateway[\s.]*:\s*([\d.]+)", result.stdout):
                ip = match.group(1)
                if validate_ip(ip) and ip != "0.0.0.0":
                    return ip
        else:
            result = subprocess.run(
                ["ip", "route", "show", "default"],
                stdout=subprocess.PIPE, text=True,
            )
            match = re.search(r"default via ([\d.]+)", result.stdout)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Root-cause analysis
# ---------------------------------------------------------------------------


def analyse_results(ping_results: dict[str, tuple[bool, Optional[float]]]) -> str:
    """Given {ip: (reachable, latency)} from a LAN sweep, produce a diagnosis."""
    if not ping_results:
        return (
            "DIAGNOSIS: No LAN IPs configured. Unable to determine root cause.\n"
            "Add your gateway and key infrastructure IPs to improve diagnostics."
        )

    reachable = [ip for ip, (ok, _) in ping_results.items() if ok]
    unreachable = [ip for ip, (ok, _) in ping_results.items() if not ok]

    if not reachable:
        return (
            "DIAGNOSIS: ALL LAN devices unreachable.\n"
            "Likely cause -- local network adapter is down, cable unplugged,\n"
            "or the default gateway / first-hop switch is offline."
        )

    if not unreachable:
        latencies = [
            f"{ip} ({lat:.0f}ms)" if lat is not None else ip
            for ip, (_, lat) in ping_results.items()
        ]
        return (
            "DIAGNOSIS: All LAN devices are reachable but internet is down.\n"
            f"  LAN latencies: {', '.join(latencies)}\n"
            "Likely cause -- ISP outage or upstream router/modem has lost its WAN link.\n"
            "Check modem sync lights and contact your ISP."
        )

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

    APP_VERSION = "4.0"

    def __init__(self):
        super().__init__()

        self.title(f"TerraPing v{self.APP_VERSION}")
        self.geometry("600x740")
        self.minsize(540, 620)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.ip_addresses: list[str] = []
        self._monitoring = False
        self._stop_event = threading.Event()
        self._monitor_thread: threading.Thread | None = None
        self._lock = threading.Lock()

        self._total_checks = 0
        self._outage_count = 0
        self._history: list[bool] = []

        self.traceroute_enabled = tk.BooleanVar(value=False)
        self.port_scan_enabled = tk.BooleanVar(value=False)
        self.selected_interval = ctk.StringVar(value="1 Minute")
        self.appearance_mode = ctk.StringVar(value="Dark")
        self.sound_alert = tk.BooleanVar(value=True)

        self._build_ui()
        self._load_ip_list()
        self._load_config()

    # ---- UI construction ---------------------------------------------------

    def _build_ui(self):
        pad = {"padx": 10, "pady": 4}

        # --- Header ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 0))

        title_block = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_block.pack(side="left")
        ctk.CTkLabel(
            title_block, text=f"TerraPing v{self.APP_VERSION}",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_block, text="Network Outage Diagnostic Tool",
            font=ctk.CTkFont(size=11), text_color="gray",
        ).pack(anchor="w")

        ctk.CTkSegmentedButton(
            header_frame, values=["Dark", "Light", "System"],
            variable=self.appearance_mode, command=self._change_appearance,
            width=180,
        ).pack(side="right", pady=4)

        # --- Status bar ---
        status_frame = ctk.CTkFrame(self)
        status_frame.pack(fill="x", **pad)

        self.status_label = ctk.CTkLabel(
            status_frame, text="  IDLE",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="gray",
        )
        self.status_label.pack(side="left", padx=10, pady=6)

        self.stats_label = ctk.CTkLabel(
            status_frame, text="Checks: 0  |  Outages: 0  |  Uptime: --",
            font=ctk.CTkFont(size=11), text_color="gray",
        )
        self.stats_label.pack(side="right", padx=10, pady=6)

        # --- History dots ---
        self.history_canvas = tk.Canvas(
            self, height=16, bg="#2b2b2b", highlightthickness=0,
        )
        self.history_canvas.pack(fill="x", padx=14, pady=(0, 4))

        # --- Tabview ---
        self.tabview = ctk.CTkTabview(self, height=260)
        self.tabview.pack(fill="both", expand=False, **pad)
        self.tabview.add("Monitor")
        self.tabview.add("Settings")
        self._build_monitor_tab(self.tabview.tab("Monitor"))
        self._build_settings_tab(self.tabview.tab("Settings"))

        # --- Log view ---
        log_frame = ctk.CTkFrame(self)
        log_frame.pack(fill="both", expand=True, **pad)

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=4, pady=(4, 0))
        ctk.CTkLabel(
            log_header, text="Event Log",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left")
        ctk.CTkButton(
            log_header, text="Clear", width=60,
            fg_color="gray30", hover_color="gray40",
            command=self._clear_log,
        ).pack(side="right", padx=2)
        ctk.CTkButton(
            log_header, text="Export", width=60,
            fg_color="gray30", hover_color="gray40",
            command=self._export_log,
        ).pack(side="right", padx=2)
        ctk.CTkButton(
            log_header, text="Open Folder", width=90,
            fg_color="gray30", hover_color="gray40",
            command=self._open_logs_folder,
        ).pack(side="right", padx=2)

        self.log_text = ctk.CTkTextbox(
            log_frame, font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

    def _build_monitor_tab(self, parent):
        pad = {"padx": 8, "pady": 4}

        ip_frame = ctk.CTkFrame(parent, fg_color="transparent")
        ip_frame.pack(**pad, fill="x")
        ctk.CTkLabel(ip_frame, text="LAN IP:").pack(side="left", padx=(4, 4))
        self.ip_entry = ctk.CTkEntry(ip_frame, width=170, placeholder_text="e.g. 192.168.1.1")
        self.ip_entry.pack(side="left", padx=4)
        self.ip_entry.bind("<Return>", lambda _: self._add_ip())
        ctk.CTkButton(ip_frame, text="Add", width=60, command=self._add_ip).pack(side="left", padx=4)
        ctk.CTkButton(
            ip_frame, text="Detect Gateway", width=120,
            fg_color="#555555", hover_color="#666666",
            command=self._detect_gateway,
        ).pack(side="left", padx=4)

        self.ip_list_frame = ctk.CTkScrollableFrame(
            parent, height=90, label_text="Monitored LAN IPs",
        )
        self.ip_list_frame.pack(**pad, fill="both", expand=True)

        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(**pad, fill="x")
        self.start_btn = ctk.CTkButton(
            btn_frame, text="\u25b6  Start Monitoring", fg_color="#2d8f2d",
            hover_color="#1e6b1e", command=self._start_monitoring,
        )
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = ctk.CTkButton(
            btn_frame, text="\u25a0  Stop Monitoring", fg_color="#b03030",
            hover_color="#882020", state="disabled", command=self._stop_monitoring,
        )
        self.stop_btn.pack(side="left", padx=6)

    def _build_settings_tab(self, parent):
        pad = {"padx": 8, "pady": 6}

        int_frame = ctk.CTkFrame(parent, fg_color="transparent")
        int_frame.pack(**pad, fill="x")
        ctk.CTkLabel(int_frame, text="Check Interval:").pack(side="left", padx=(4, 8))
        ctk.CTkSegmentedButton(
            int_frame,
            values=["30 Seconds", "1 Minute", "5 Minutes", "10 Minutes"],
            variable=self.selected_interval,
        ).pack(side="left", padx=4)

        diag_frame = ctk.CTkFrame(parent, fg_color="transparent")
        diag_frame.pack(**pad, fill="x")
        ctk.CTkLabel(
            diag_frame, text="Diagnostics:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=4)
        ctk.CTkCheckBox(
            diag_frame, text="Traceroute on unreachable hosts",
            variable=self.traceroute_enabled,
        ).pack(anchor="w", padx=20, pady=2)
        ctk.CTkCheckBox(
            diag_frame, text="Port scan on reachable hosts",
            variable=self.port_scan_enabled,
        ).pack(anchor="w", padx=20, pady=2)

        alert_frame = ctk.CTkFrame(parent, fg_color="transparent")
        alert_frame.pack(**pad, fill="x")
        ctk.CTkLabel(
            alert_frame, text="Alerts:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=4)
        ctk.CTkCheckBox(
            alert_frame, text="Sound alert on outage",
            variable=self.sound_alert,
        ).pack(anchor="w", padx=20, pady=2)

    # ---- Appearance --------------------------------------------------------

    def _change_appearance(self, mode: str):
        ctk.set_appearance_mode(mode)
        bg = "#2b2b2b" if mode == "Dark" else ("#e0e0e0" if mode == "Light" else "#2b2b2b")
        self.history_canvas.configure(bg=bg)
        self._save_config()

    # ---- History dots ------------------------------------------------------

    def _update_history_display(self):
        c = self.history_canvas
        c.delete("all")
        dot_r, spacing, x_start, y = 5, 14, 8, 8
        for i, ok in enumerate(self._history[-MAX_HISTORY:]):
            color = "#2dce2d" if ok else "#e03030"
            x = x_start + i * spacing
            c.create_oval(x - dot_r, y - dot_r, x + dot_r, y + dot_r, fill=color, outline="")

    # ---- Logging -----------------------------------------------------------

    def _log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}\n"

        self.after(0, self._append_log_text, entry)

        log_path = os.path.join(LOG_FOLDER, "ping_log.txt")
        with self._lock:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(entry)

    def _append_log_text(self, entry: str):
        self.log_text.insert("end", entry)
        self.log_text.see("end")

    def _set_status(self, text: str, color: str = "gray"):
        self.after(0, lambda: self.status_label.configure(text=f"  {text}", text_color=color))

    def _update_stats(self):
        uptime = (
            f"{(self._total_checks - self._outage_count) / self._total_checks * 100:.1f}%"
            if self._total_checks > 0 else "--"
        )
        text = f"Checks: {self._total_checks}  |  Outages: {self._outage_count}  |  Uptime: {uptime}"
        self.after(0, lambda: self.stats_label.configure(text=text))

    def _clear_log(self):
        self.log_text.delete("1.0", "end")

    def _export_log(self):
        log_path = os.path.join(LOG_FOLDER, "ping_log.txt")
        if not os.path.isfile(log_path):
            self._log("No log file to export.")
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"terraping_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if dest:
            shutil.copy2(log_path, dest)
            self._log(f"Log exported to: {dest}")

    # ---- IP list management ------------------------------------------------

    def _add_ip(self):
        ip = self.ip_entry.get().strip()
        if not validate_ip(ip):
            self._log("Invalid IP format. Use x.x.x.x with octets 0-255.")
            return
        if not is_private_ip(ip):
            self._log(f"{ip} is not a private/LAN address. Only RFC 1918 addresses are supported.")
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
        ctk.CTkButton(
            row, text="\u2715", width=30, height=24, fg_color="#b03030",
            hover_color="#882020",
            command=lambda: self._remove_ip(ip, row),
        ).pack(side="right", padx=4)

    def _detect_gateway(self):
        self._log("Detecting default gateway...")
        gw = detect_default_gateway()
        if gw:
            if gw in self.ip_addresses:
                self._log(f"Gateway {gw} is already in the list.")
            else:
                self.ip_addresses.append(gw)
                self._add_ip_row(gw)
                self._log(f"Detected and added gateway: {gw}")
                self._save_ip_list()
        else:
            self._log("Could not detect default gateway automatically.")

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

    # ---- Config persistence ------------------------------------------------

    def _save_config(self):
        config = {
            "appearance": self.appearance_mode.get(),
            "interval": self.selected_interval.get(),
            "traceroute": self.traceroute_enabled.get(),
            "port_scan": self.port_scan_enabled.get(),
            "sound_alert": self.sound_alert.get(),
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def _load_config(self):
        if not os.path.isfile(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            if "appearance" in config:
                self.appearance_mode.set(config["appearance"])
                ctk.set_appearance_mode(config["appearance"])
            if "interval" in config:
                self.selected_interval.set(config["interval"])
            if "traceroute" in config:
                self.traceroute_enabled.set(config["traceroute"])
            if "port_scan" in config:
                self.port_scan_enabled.set(config["port_scan"])
            if "sound_alert" in config:
                self.sound_alert.set(config["sound_alert"])
        except Exception:
            pass

    # ---- Monitoring --------------------------------------------------------

    def _start_monitoring(self):
        if self._monitoring:
            return
        if not self.ip_addresses:
            self._log("Add at least one LAN IP before starting.")
            return

        self._monitoring = True
        self._stop_event.clear()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        interval_map = {
            "30 Seconds": 30, "1 Minute": 60,
            "5 Minutes": 300, "10 Minutes": 600,
        }
        interval = interval_map.get(self.selected_interval.get(), 60)
        self._log(f"Monitoring started (interval: {self.selected_interval.get()}).")
        self._set_status("MONITORING", "#2d8f2d")
        self._save_config()

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, args=(interval,), daemon=True,
        )
        self._monitor_thread.start()

    def _stop_monitoring(self):
        if not self._monitoring:
            return
        self._monitoring = False
        self._stop_event.set()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self._log("Monitoring stopped.")
        self._set_status("IDLE")

    def _check_internet(self) -> bool:
        """Ping multiple internet targets concurrently; True if any respond."""
        with ThreadPoolExecutor(max_workers=len(INTERNET_TARGETS)) as pool:
            futures = {pool.submit(ping, t): t for t in INTERNET_TARGETS}
            for future in as_completed(futures):
                success, _ = future.result()
                if success:
                    return True
        return False

    def _monitor_loop(self, interval: int):
        while self._monitoring:
            self._total_checks += 1
            targets = ", ".join(INTERNET_TARGETS)
            self._log(f"Checking internet connectivity ({targets})...")

            if self._check_internet():
                self._log("Internet is reachable.")
                self._set_status("ONLINE", "#2d8f2d")
                self._history.append(True)
            else:
                self._outage_count += 1
                self._history.append(False)
                self._set_status("OUTAGE DETECTED", "#e03030")
                self._log("Internet is DOWN. Running LAN diagnostics...")
                self._play_alert()
                self._run_diagnostics()

            if len(self._history) > MAX_HISTORY:
                self._history = self._history[-MAX_HISTORY:]

            self.after(0, self._update_history_display)
            self._update_stats()

            if self._stop_event.wait(timeout=interval):
                break

        self._set_status("IDLE")

    def _play_alert(self):
        if not self.sound_alert.get():
            return
        try:
            if IS_WINDOWS:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            else:
                print("\a", end="", flush=True)
        except Exception:
            pass

    def _run_diagnostics(self):
        """Ping every configured LAN IP concurrently, run optional tools, then analyse."""
        self._log("=" * 50)
        self._log("BEGIN OUTAGE DIAGNOSTIC SWEEP")
        self._log("=" * 50)

        ips = list(self.ip_addresses)
        results: dict[str, tuple[bool, Optional[float]]] = {}

        with ThreadPoolExecutor(max_workers=min(len(ips), MAX_PING_WORKERS)) as pool:
            future_map = {pool.submit(ping, ip): ip for ip in ips}
            for future in as_completed(future_map):
                if not self._monitoring:
                    return
                ip = future_map[future]
                results[ip] = future.result()

        for ip in ips:
            if ip not in results:
                continue
            success, latency = results[ip]
            if success:
                lat_str = f" ({latency:.0f}ms)" if latency is not None else ""
                self._log(f"  {ip}  ....  REACHABLE{lat_str}")
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

        self._log("-" * 50)
        diagnosis = analyse_results(results)
        for line in diagnosis.splitlines():
            self._log(line)
        self._log("=" * 50)
        self._log("END OUTAGE DIAGNOSTIC SWEEP")
        self._log("=" * 50)

    # ---- Misc --------------------------------------------------------------

    def _open_logs_folder(self):
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
