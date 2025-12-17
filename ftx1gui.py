import os
import queue
import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import matplotlib

matplotlib.use("TkAgg")

from ftx1cat import FTX1Cat
from i18n import I18N_TEXT as I18N_TEXT
from serial.tools import list_ports

from components import (
    FrequencyModePanel,
    MetersPanel,
    NotchControlsPanel,
    PreampAgcPanel,
    PttPowerPanel,
    MicWaterfallPanel,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DISPLAY_TEXT = I18N_TEXT["en"]


def _T(key: str, default: str | None = None) -> str:
    if default is None:
        default = key
    return DISPLAY_TEXT.get(key, default)


COMMON_BAUD_RATES = [
    "2400",
    "4800",
    "9600",
    "19200",
    "38400",
    "57600",
    "76800",
    "115200",
    "230400",
    "460800",
    "576000",
]
DEFAULT_BAUD_RATE = "38400"


# ==========================
# Hamlib net rigctl 服务器
# ==========================


class RigctlTCPServer(threading.Thread):
    def __init__(self, cat: FTX1Cat, host: str = "127.0.0.1", port: int = 4532, on_activity=None):
        super().__init__(daemon=True)
        self.cat = cat
        self.host = host
        self.port = port
        self.on_activity = on_activity
        self._stop_event = threading.Event()
        self._server_sock = None

    def stop(self):
        self._stop_event.set()
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock = sock
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((self.host, self.port))
            sock.listen(5)
        except OSError as e:
            print(DISPLAY_TEXT["log_rigctl_listen_failed_fmt"].format(e=e))
            return

        print(DISPLAY_TEXT["log_rigctl_listen_fmt"].format(host=self.host, port=self.port))

        while not self._stop_event.is_set():
            try:
                sock.settimeout(1.0)
                try:
                    conn, addr = sock.accept()
                except socket.timeout:
                    continue
            except OSError:
                break

            print(DISPLAY_TEXT["log_rigctl_client_fmt"].format(addr=addr))
            th = threading.Thread(target=self.handle_client, args=(conn,), daemon=True)
            th.start()

        print(DISPLAY_TEXT["log_rigctl_exit"])

    def handle_client(self, conn: socket.socket):
        with conn:
            conn.settimeout(20)
            f = conn.makefile("rwb", buffering=0)
            while not self._stop_event.is_set():
                try:
                    line = f.readline()
                except Exception:
                    break
                if not line:
                    break
                try:
                    text = line.decode("utf-8", errors="ignore").strip()
                except Exception:
                    continue
                if not text:
                    continue

                parts = text.split()
                cmd = parts[0]

                if cmd.lower() == "q":
                    break

                resp = self._handle_command(parts)
                try:
                    f.write(resp.encode("utf-8"))
                except Exception:
                    break

    def _handle_command(self, parts):
        def ok():
            return "RPRT 0\n"

        def err():
            return "RPRT -1\n"

        cmd = parts[0]

        if cmd.startswith("\\"):
            long_cmd = cmd.lower()
            if long_cmd == "\\get_powerstat":
                return "1\n"
            if long_cmd == "\\chk_vfo":
                return "0\n"
            if long_cmd == "\\dump_state":
                lines = [
                    "1",
                    "6",
                    "0",
                    "0 0 0 0 0 0 0",
                    "0 0 0 0 0 0 0",
                    "0 0",
                    "0 0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0 0 0 0 0 0 0 0",
                    "0 0 0 0 0 0 0 0",
                    "0x00000000",
                    "0x00000000",
                    "0x00000000",
                    "0x00000000",
                    "0x00000000",
                    "0x00000000",
                    "vfo_opts=0x00000000",
                    "ptt_type=0x00000001",
                    "targetable_vfo=0x00000000",
                    "has_set_vfo=0",
                    "has_get_vfo=0",
                    "has_set_freq=1",
                    "has_get_freq=1",
                    "has_set_conf=0",
                    "has_get_conf=0",
                    "has_power2mW=0",
                    "has_mw2power=0",
                    "timeout=0",
                    "rig_model=6",
                    "rigctl_version=4.5.5",
                    "agc_levels=",
                    "done",
                    "0",
                ]
                return "\n".join(lines) + "\n"
            return err()

        if cmd == "f":
            freq_hz, _ = self.cat.get_freq()
            if freq_hz is None:
                return err()
            return f"{freq_hz}\n"

        if cmd == "F":
            if len(parts) < 2:
                return err()
            try:
                freq_hz = int(float(parts[1]))
            except ValueError:
                return err()
            try:
                self.cat.set_freq(freq_hz)
                if self.on_activity:
                    try:
                        self.on_activity()
                    except Exception:
                        pass
                return ok()
            except Exception:
                return err()

        if cmd == "m":
            mode_name, _ = self.cat.get_mode(main=True)
            if mode_name is None:
                return err()
            return f"{mode_name}\n2400\n"

        if cmd == "M":
            if len(parts) < 2:
                return err()
            mode_name = parts[1].upper()
            try:
                self.cat.set_mode(mode_name, main=True)
                if self.on_activity:
                    try:
                        self.on_activity()
                    except Exception:
                        pass
                return ok()
            except Exception:
                return err()

        if cmd == "t":
            try:
                on = self.cat.get_rts()
            except Exception:
                return err()
            return f"{1 if on else 0}\n"

        if cmd == "T":
            if len(parts) < 2:
                return err()
            v = parts[1].strip()
            if v not in ("0", "1"):
                return err()
            try:
                self.cat.set_rts(v == "1")
                if self.on_activity:
                    try:
                        self.on_activity()
                    except Exception:
                        pass
                return ok()
            except Exception:
                return err()

        return err()


# ==========================
# 主 Tk App
# ==========================


class FTX1TkApp:
    def __init__(self, master):
        self.master = master
        self.master.title(_T("app_title"))
        self.cat: FTX1Cat | None = None
        self.rigctl_server = None

        self.current_lang = "en"
        self.tcp_port_var = tk.IntVar(value=4532)
        self.cat_port_var = tk.StringVar()
        self.ptt_port_var = tk.StringVar()
        self.cat_baud_var = tk.StringVar(value=DEFAULT_BAUD_RATE)
        self.ptt_baud_var = tk.StringVar(value=DEFAULT_BAUD_RATE)
        self.refresh_rate_var = tk.DoubleVar(value=1.0)
        self._meter_hz = 1.0
        try:
            self.refresh_rate_var.trace_add("write", lambda *_: self._on_refresh_rate_changed())
        except Exception:
            pass

        self.status_var = tk.StringVar(value=DISPLAY_TEXT.get("status_disconnected", "Disconnected"))
        self.rigctl_status_var = tk.StringVar(value=DISPLAY_TEXT.get("rigctl_stop", "Rigctl stopped"))

        self._full_read_after_id = None
        self._full_read_thread = None

        self.freq_mode_panel: FrequencyModePanel | None = None
        self.ptt_power_panel: PttPowerPanel | None = None
        self.preamp_agc_panel: PreampAgcPanel | None = None
        self.notch_panel: NotchControlsPanel | None = None
        self.meters_panel: MetersPanel | None = None

        self._meter_stop = None
        self._meter_queue = None
        self._meter_thread = None

        self._build_gui()
        self.apply_language()

        self._start_meter_thread()
        self._schedule_meter_update()
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)

    def _get_cat(self) -> FTX1Cat | None:
        return self.cat

    def _on_refresh_rate_changed(self):
        try:
            self._meter_hz = float(self.refresh_rate_var.get())
        except Exception:
            self._meter_hz = 1.0

    def on_language_changed(self, event=None):
        lang = (self.lang_var.get() or "").strip()
        if lang in I18N_TEXT:
            self.current_lang = lang
            self.apply_language()

    def apply_language(self):
        global DISPLAY_TEXT
        DISPLAY_TEXT = I18N_TEXT.get(self.current_lang, DISPLAY_TEXT)

        try:
            self.master.title(_T("app_title"))
        except Exception:
            pass

        for attr, key in [
            ("lbl_cat_port", "label_cat_port"),
            ("lbl_ptt_port", "label_ptt_port"),
            ("lbl_baud1", "label_baud"),
            ("lbl_baud2", "label_baud"),
            ("lbl_rigctl_port", "label_rigctl_port"),
        ]:
            widget = getattr(self, attr, None)
            if widget is not None:
                try:
                    widget.configure(text=_T(key))
                except Exception:
                    pass

        for attr, key in [
            ("btn_connect", "btn_connect"),
            ("btn_disconnect", "btn_disconnect"),
            ("btn_full_read", "btn_full_read"),
        ]:
            widget = getattr(self, attr, None)
            if widget is not None:
                try:
                    widget.configure(text=_T(key))
                except Exception:
                    pass

        try:
            if self.cat is None:
                self.status_var.set(_T("status_disconnected"))
            else:
                self.status_var.set(
                    _T("status_connected_fmt").format(
                        port=self.cat_port_var.get(),
                        baud=self.cat_baud_var.get(),
                        port2=self.ptt_port_var.get(),
                        baud2=self.ptt_baud_var.get(),
                    )
                )
        except Exception:
            pass

        try:
            if self.rigctl_server is None:
                self.rigctl_status_var.set(_T("rigctl_stop"))
            else:
                self.rigctl_status_var.set(_T("rigctl_started_fmt").format(tcp_port=int(self.tcp_port_var.get())))
        except Exception:
            pass

        if self.freq_mode_panel:
            self.freq_mode_panel.apply_language()
        if self.ptt_power_panel:
            self.ptt_power_panel.apply_language()
        if self.preamp_agc_panel:
            self.preamp_agc_panel.apply_language()
        if self.notch_panel:
            self.notch_panel.apply_language()
        if self.meters_panel:
            self.meters_panel.apply_language()

    def _build_gui(self):
        top = ttk.Frame(self.master, padding=6)
        top.pack(side="top", fill="x")

        self.lbl_cat_port = ttk.Label(top, text=_T("label_cat_port"))
        self.lbl_cat_port.pack(side="left")
        self.port_combo = ttk.Combobox(
            top,
            textvariable=self.cat_port_var,
            values=[],
            width=8,
            state="readonly",
            postcommand=self._scan_com_ports,
        )
        self.port_combo.pack(side="left", padx=2)

        self.lbl_baud1 = ttk.Label(top, text=_T("label_baud"))
        self.lbl_baud1.pack(side="left")
        self.cat_baud_combo = ttk.Combobox(
            top,
            values=COMMON_BAUD_RATES,
            width=8,
            state="readonly",
            textvariable=self.cat_baud_var,
        )
        self.cat_baud_combo.pack(side="left", padx=4)
        self.cat_baud_combo.set(DEFAULT_BAUD_RATE)

        self.lbl_ptt_port = ttk.Label(top, text=_T("label_ptt_port"))
        self.lbl_ptt_port.pack(side="left", padx=(10, 2))
        self.port2_combo = ttk.Combobox(
            top,
            textvariable=self.ptt_port_var,
            values=[],
            width=8,
            state="readonly",
            postcommand=self._scan_com_ports,
        )
        self.port2_combo.pack(side="left", padx=2)

        self.lbl_baud2 = ttk.Label(top, text=_T("label_baud"))
        self.lbl_baud2.pack(side="left")
        self.ptt_baud_combo = ttk.Combobox(
            top,
            values=COMMON_BAUD_RATES,
            width=8,
            state="readonly",
            textvariable=self.ptt_baud_var,
        )
        self.ptt_baud_combo.pack(side="left", padx=4)
        self.ptt_baud_combo.set(DEFAULT_BAUD_RATE)

        self.btn_connect = ttk.Button(top, text=_T("btn_connect"), command=self.on_connect)
        self.btn_connect.pack(side="left", padx=4)
        self.btn_disconnect = ttk.Button(top, text=_T("btn_disconnect"), command=self.on_disconnect, state="disabled")
        self.btn_disconnect.pack(side="left", padx=4)
        self.btn_full_read = ttk.Button(top, text=_T("btn_full_read"), command=self.on_full_read, state="disabled")
        self.btn_full_read.pack(side="left", padx=(12, 4))

        lang_frame = ttk.Frame(top)
        lang_frame.pack(side="right", padx=(8, 0))
        self.lang_var = tk.StringVar(value=self.current_lang)
        self.lang_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.lang_var,
            values=sorted(I18N_TEXT.keys()),
            width=4,
            state="readonly",
        )
        self.lang_combo.pack(side="right")
        ttk.Label(lang_frame, text="Lang:").pack(side="right", padx=(0, 6))
        self.lang_combo.bind("<<ComboboxSelected>>", self.on_language_changed)

        self.lbl_rigctl_port = ttk.Label(top, text=_T("label_rigctl_port"))
        self.lbl_rigctl_port.pack(side="left", padx=(20, 2))
        self.port_tcp_entry = ttk.Entry(top, width=6, textvariable=self.tcp_port_var)
        self.port_tcp_entry.pack(side="left", padx=2)

        self.lbl_rigctl_status = ttk.Label(top, textvariable=self.rigctl_status_var)
        self.lbl_rigctl_status.pack(side="right")

        self._scan_com_ports()

        mid = ttk.Frame(self.master, padding=6)
        mid.pack(side="top", fill="x")

        self.freq_mode_panel = FrequencyModePanel(mid, self._get_cat, self._schedule_full_read, _T, DISPLAY_TEXT)
        self.freq_mode_panel.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.ptt_power_panel = PttPowerPanel(mid, self._get_cat, self._schedule_full_read, _T, DISPLAY_TEXT)
        self.ptt_power_panel.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.preamp_agc_panel = PreampAgcPanel(mid, self._get_cat, self._schedule_full_read, _T, DISPLAY_TEXT)
        self.preamp_agc_panel.pack(side="left", fill="both", expand=True)

        self.notch_panel = NotchControlsPanel(self.master, self._get_cat, self._schedule_full_read, _T, DISPLAY_TEXT)
        self.notch_panel.pack(side="top", fill="both", expand=True, padx=6, pady=4)

        bottom = ttk.Frame(self.master, padding=6)
        bottom.pack(side="top", fill="both", expand=True)

        # Meters (meter refresh rate control removed — default 1 Hz)
        self.meters_panel = MetersPanel(bottom, _T)
        self.meters_panel.pack(side="left", fill="both", expand=True, padx=(12, 0))

        # Status bar: full-width at the bottom of the window
        status_bar = ttk.Frame(self.master, relief="sunken")
        status_bar.pack(side="bottom", fill="x")
        ttk.Label(status_bar, textvariable=self.status_var, foreground="#0080ff").pack(side="left", padx=6, pady=2)

    def _scan_com_ports(self):
        try:
            ports = sorted(list_ports.comports(), key=lambda info: self._com_port_sort_key(info.device))
        except Exception:
            ports = []
        devices = [info.device for info in ports]
        try:
            self.port_combo.configure(values=devices)
            self.port2_combo.configure(values=devices)
        except Exception:
            pass

        cat_preferred = self._find_port_by_keyword(ports, "enhanced com port")
        ptt_preferred = self._find_port_by_keyword(ports, "standard com port")
        if not cat_preferred and devices:
            cat_preferred = devices[0]
        if not ptt_preferred:
            if len(devices) > 1:
                ptt_preferred = devices[1]
            elif devices:
                ptt_preferred = devices[0]

        current_cat = (self.cat_port_var.get() or "").strip()
        current_ptt = (self.ptt_port_var.get() or "").strip()
        if cat_preferred and (not current_cat or current_cat not in devices):
            self.cat_port_var.set(cat_preferred)
        elif not cat_preferred and not current_cat:
            self.cat_port_var.set("")
        if ptt_preferred and (not current_ptt or current_ptt not in devices):
            self.ptt_port_var.set(ptt_preferred)
        elif not ptt_preferred and not current_ptt:
            self.ptt_port_var.set("")

    @staticmethod
    def _find_port_by_keyword(ports, keyword):
        key = (keyword or "").strip().lower()
        if not key:
            return None
        for info in ports:
            desc = (info.description or "").lower()
            if key in desc:
                return info.device
        return None

    @staticmethod
    def _com_port_sort_key(device):
        if not device:
            return (float("inf"), "")
        name = device.upper()
        if name.startswith("COM"):
            try:
                num = int(name[3:])
            except Exception:
                num = float("inf")
        else:
            num = float("inf")
        return (num, device)

    def on_connect(self):
        self._start_meter_thread()
        if self.cat is not None:
            return
        self._scan_com_ports()
        port = (self.cat_port_var.get() or "").strip()
        port2 = (self.ptt_port_var.get() or "").strip()
        if not port or not port2:
            messagebox.showwarning(DISPLAY_TEXT.get("error_title", "Error"), DISPLAY_TEXT.get("need_cat_and_ptt_ports", "Need CAT and PTT ports"))
            return
        try:
            baud = int((self.cat_baud_var.get() or DEFAULT_BAUD_RATE).strip())
        except ValueError:
            messagebox.showwarning(DISPLAY_TEXT.get("error_title", "Error"), DISPLAY_TEXT.get("cat_baud_must_int", "CAT baud must be int"))
            return
        try:
            baud2 = int((self.ptt_baud_var.get() or DEFAULT_BAUD_RATE).strip())
        except ValueError:
            messagebox.showwarning(DISPLAY_TEXT.get("error_title", "Error"), DISPLAY_TEXT.get("ptt_baud_must_int", "PTT baud must be int"))
            return

        try:
            self.cat = FTX1Cat(port=port, baudrate=baud, port2=port2, baudrate2=baud2, timeout=0.3)
        except Exception as e:
            self.cat = None
            messagebox.showerror(DISPLAY_TEXT.get("connect_failed", "Connect failed"), str(e))
            return

        self.status_var.set(DISPLAY_TEXT.get("status_connected_fmt", "Connected {port}/{baud} {port2}/{baud2}").format(port=port, baud=baud, port2=port2, baud2=baud2))
        self.btn_connect.configure(state="disabled")
        self.btn_disconnect.configure(state="normal")

        try:
            tcp_port = int(self.tcp_port_var.get())
        except ValueError:
            tcp_port = 4532
            self.tcp_port_var.set(tcp_port)

        self.rigctl_server = RigctlTCPServer(self.cat, host="127.0.0.1", port=tcp_port, on_activity=self.on_network_activity)
        self.rigctl_server.start()
        self.rigctl_status_var.set(DISPLAY_TEXT.get("rigctl_started_fmt", "Rigctl started {tcp_port}").format(tcp_port=tcp_port))

        try:
            self.btn_full_read.configure(state="normal")
        except Exception:
            pass
        self._schedule_full_read(delay_ms=0)

    def on_disconnect(self):
        self._stop_meter_thread()
        if self.cat:
            try:
                self.cat.close()
            except Exception:
                pass
        self.cat = None
        self.status_var.set(DISPLAY_TEXT.get("status_disconnected", "Disconnected"))
        self.btn_connect.configure(state="normal")
        self.btn_disconnect.configure(state="disabled")

        if self.rigctl_server:
            self.rigctl_server.stop()
            self.rigctl_server = None
        self.rigctl_status_var.set(DISPLAY_TEXT.get("rigctl_stop", "Rigctl stopped"))

        if self._full_read_after_id is not None:
            try:
                self.master.after_cancel(self._full_read_after_id)
            except Exception:
                pass
            self._full_read_after_id = None
        try:
            self.btn_full_read.configure(state="disabled")
        except Exception:
            pass
        if self.meters_panel:
            self.meters_panel.clear()

    def on_full_read(self):
        self._schedule_full_read(delay_ms=0)

    def on_network_activity(self):
        try:
            self.master.after(0, lambda: self._schedule_full_read(delay_ms=1000))
        except Exception:
            pass

    def _schedule_full_read(self, delay_ms: int = 1000):
        if not self.cat:
            return
        if self._full_read_after_id is not None:
            try:
                self.master.after_cancel(self._full_read_after_id)
            except Exception:
                pass
            self._full_read_after_id = None
        self._full_read_after_id = self.master.after(delay_ms, self._start_full_read_thread)

    def _start_full_read_thread(self):
        self._full_read_after_id = None
        if not self.cat:
            return
        if self._full_read_thread is not None and self._full_read_thread.is_alive():
            return

        def worker():
            cat = self.cat
            result = {}
            try:
                result["freq_hz"], _ = cat.get_freq()
            except Exception:
                result["freq_hz"] = None
            try:
                result["mode_name"], _ = cat.get_mode(main=True)
            except Exception:
                result["mode_name"] = None
            try:
                result["rts"] = bool(cat.get_rts())
            except Exception:
                result["rts"] = None

            result["preamp"] = {}
            bands = self.preamp_agc_panel.get_preamp_bands() if self.preamp_agc_panel else []
            for band in bands:
                try:
                    level, _ = cat.get_preamp(band)
                except Exception:
                    level = None
                result["preamp"][band] = level

            try:
                result["agc_name"], _ = cat.get_agc(main=True)
            except Exception:
                result["agc_name"] = None

            try:
                result["power_dev"], result["power_watts"], _ = cat.get_power_control()
            except Exception:
                result["power_dev"], result["power_watts"] = None, None

            try:
                enabled, freq_hz, _ = cat.get_manual_notch(main=True)
            except Exception:
                enabled, freq_hz = None, None
            result["notch_enabled"] = bool(enabled) if enabled is not None else False
            result["notch_freq_hz"] = freq_hz

            try:
                self.master.after(0, lambda: self._apply_full_read_result(result))
            except Exception:
                pass

        self._full_read_thread = threading.Thread(target=worker, daemon=True)
        self._full_read_thread.start()

    def _apply_full_read_result(self, result: dict):
        if self.freq_mode_panel:
            self.freq_mode_panel.sync_full_read(result.get("freq_hz"), result.get("mode_name"))
        if self.ptt_power_panel:
            self.ptt_power_panel.sync_full_read(result.get("rts"), result.get("power_dev"), result.get("power_watts"))
        if self.preamp_agc_panel:
            self.preamp_agc_panel.sync_full_read(result.get("preamp"), result.get("agc_name"))
        if self.notch_panel:
            self.notch_panel.sync_full_read(result.get("notch_enabled", False), result.get("notch_freq_hz"))

    def _refresh_notch_overlay(self):
        if self.notch_panel:
            self.notch_panel.refresh_overlay()

    def _schedule_meter_update(self):
        self._update_meters()
        self.master.after(100, self._schedule_meter_update)

    def _start_meter_thread(self):
        if self._meter_stop is None or self._meter_stop.is_set():
            self._meter_stop = threading.Event()
        if self._meter_queue is None:
            self._meter_queue = queue.Queue(maxsize=1)
        if self._meter_thread is not None and self._meter_thread.is_alive():
            return

        def worker():
            while not self._meter_stop.is_set():
                try:
                    hz = float(self._meter_hz)
                except Exception:
                    hz = 1.0
                hz = max(min(hz, 5.0), 0.1)
                sleep_s = 1.0 / hz

                cat = self.cat
                if cat is None:
                    self._meter_stop.wait(0.2)
                    continue
                try:
                    data = cat.read_all_meters()
                except Exception:
                    data = None
                try:
                    if self._meter_queue.full():
                        _ = self._meter_queue.get_nowait()
                    self._meter_queue.put_nowait(data)
                except Exception:
                    pass
                self._meter_stop.wait(sleep_s)

        self._meter_thread = threading.Thread(target=worker, daemon=True)
        self._meter_thread.start()

    def _stop_meter_thread(self):
        try:
            if self._meter_stop is not None:
                self._meter_stop.set()
        except Exception:
            pass

    def _update_meters(self):
        if self._meter_queue is None or self.meters_panel is None:
            return
        data = None
        try:
            while True:
                data = self._meter_queue.get_nowait()
        except Exception:
            pass

        if data is None:
            if not self.cat:
                self.meters_panel.clear()
            return
        self.meters_panel.update_meters(data)

    def on_close(self):
        self._stop_meter_thread()
        if self.notch_panel and self.notch_panel.waterfall_panel:
            self.notch_panel.waterfall_panel.close()
        self.on_disconnect()
        self.master.destroy()


def main():
    root = tk.Tk()
    _ = FTX1TkApp(root)
    root.mainloop()


try:
    MicWaterfallPanel.refresh_plot.__doc__ = DISPLAY_TEXT.get("hint_force_waterfall_refresh", "")
    FTX1TkApp.on_full_read.__doc__ = DISPLAY_TEXT.get("hint_btn_full_read", "")
    FTX1TkApp.on_network_activity.__doc__ = DISPLAY_TEXT.get("hint_rigctl_autoread", "")
    FTX1TkApp._apply_full_read_result.__doc__ = DISPLAY_TEXT.get("hint_overwrite_ui", "")
    FTX1TkApp.on_close.__doc__ = DISPLAY_TEXT.get("hint_notch_input", "")
except Exception:
    pass


if __name__ == "__main__":
    main()
