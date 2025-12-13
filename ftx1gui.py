import socket
import threading
import queue
import math
import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
import sounddevice as sd
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ftx1cat import (
    FTX1Cat,
    convert_meter_value,
    METER_MAP,
    METER_CONVERT,
    P2_TO_MODE,
    s_meter_text_from_raw,
)

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from i18n import I18N_TEXT as I18N_TEXT

DISPLAY_TEXT = I18N_TEXT["en"]

def _T(key: str, default: str | None = None) -> str:
    """Safe text lookup: avoid KeyError if a key is missing in DISPLAY_TEXT."""
    if default is None:
        default = key
    return DISPLAY_TEXT.get(key, default)

# ==========================
# Hamlib net rigctl 服务器
# ==========================

class RigctlTCPServer(threading.Thread):
    """
    简单的 net rigctl 兼容 TCP 服务器（文本协议），
    供 WSJT-X 使用。

    支持命令：
      f           -> 返回当前频率 (Hz)
      F <freq>    -> 设置频率
      m           -> 返回当前模式（字符串）以及带宽（简单返回 2400）
      M <mode> <passband> -> 设置模式（只看 mode 字符串）
      t           -> 返回 PTT 状态 (0/1) —— 使用第二串口 RTS
      T <0|1>     -> 设置 PTT (RTS)

      q           -> 关闭当前连接

    返回格式尽量贴近 rigctl：
      - 成功设置后返回: "RPRT 0\n"
      - 失败时返回: "RPRT -1\n"
    """
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
            th = threading.Thread(
                target=self.handle_client, args=(conn,), daemon=True
            )
            th.start()

        print(DISPLAY_TEXT["log_rigctl_exit"])

    def handle_client(self, conn: socket.socket):
        with conn:
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
                    # 客户端要求退出
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

        # ---------- Hamlib 长命令（反斜杠开头） ----------
        # WSJT-X / rigctl -m 2 会在连接时发：
        #   \get_powerstat
        #   \chk_vfo
        #   \dump_state
        # 我们这里做一个“假实现”，只要返回格式对，它就会满意。
        if cmd.startswith("\\"):
            long_cmd = cmd.lower()

            # 功率状态：永远报告“开机”
            if long_cmd == "\\get_powerstat":
                return "1\n"

            # 检查 VFO：0 表示 OK/单 VFO
            if long_cmd == "\\chk_vfo":
                return "0\n"

            # dump_state：返回一堆状态信息，最后一个 0 代表 OK
            if long_cmd == "\\dump_state":
                lines = [
                    "1",              # 协议版本 v1
                    "6",              # rig model（随便用 6: dummy）
                    "0",              # ITU region - 不用
                    "0 0 0 0 0 0 0",  # RX 频段结束标记
                    "0 0 0 0 0 0 0",  # TX 频段结束标记
                    "0 0",            # 调谐步进结束
                    "0 0",            # 滤波器结束
                    "0",              # max_rit
                    "0",              # max_xit
                    "0",              # max_ifshift
                    "0",              # announces
                    "0 0 0 0 0 0 0 0",  # preamp 列表（全 0）
                    "0 0 0 0 0 0 0 0",  # attenuator 列表（全 0）
                    "0x00000000",     # has_get_func
                    "0x00000000",     # has_set_func
                    "0x00000000",     # has_get_level
                    "0x00000000",     # has_set_level
                    "0x00000000",     # has_get_parm
                    "0x00000000",     # has_set_parm
                    "vfo_opts=0x00000000",
                    "ptt_type=0x00000001",   # PTT=RIG
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
                    "0",                    # 最后一行 0 -> OK
                ]
                return "\n".join(lines) + "\n"

            # 其它未知的长命令，一律报错
            return err()

        # ---------- 读频率 ----------
        if cmd == "f":
            freq_hz, _ = self.cat.get_freq()
            if freq_hz is None:
                return err()
            return f"{freq_hz}\n"

        # ---------- 写频率 ----------
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

        # ---------- 读模式 ----------
        if cmd == "m":
            mode_name, _ = self.cat.get_mode(main=True)
            if mode_name is None:
                return err()
            # 第二行返回带宽
            return f"{mode_name}\n2400\n"

        # ---------- 写模式 ----------
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

        # ---------- 读 PTT (RTS) ----------
        if cmd == "t":
            try:
                on = self.cat.get_rts()
            except Exception:
                return err()
            return f"{1 if on else 0}\n"

        # ---------- 写 PTT (RTS) ----------
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

        # 未实现命令
        return err()



# ==========================
# 顶部 Meter 表头
# ==========================

class MeterHeader(ttk.Frame):
    """
    顶部表头组件：
      - meter_name: "S_MAIN" 等
      - ticks: 3 个刻度（字符串）
      - 值：显示当前转换后的数值
    """
    def __init__(self, parent, meter_name: str, meter_id: int, use_convert: bool):
        super().__init__(parent, padding=4)
        self.meter_name = meter_name
        self.meter_id = meter_id
        self.use_convert = use_convert

        self.label_title = ttk.Label(self, text=meter_name, font=("Segoe UI", 11, "bold"))
        self.label_title.pack()
        
        # --- Bar 图形区域 ---
        self.bar_canvas = tk.Canvas(self, width=80, height=12, bg="#202020", highlightthickness=0)
        self.bar_canvas.pack(pady=(2, 0))

        # 灰色底条
        self.bar_canvas.create_rectangle(0, 0, 80, 12, fill="#404040", outline="")

        # 动态条 (存 ID 方便更新)
        self.bar_id = self.bar_canvas.create_rectangle(0, 0, 0, 12, fill="#00ff00", outline="")
        
        # 固定红线（阈值线），默认 raw = 128 的位置
        threshold_raw = 128          # 想改位置就改这个，0~255
        self.threshold_x = int(80 * threshold_raw / 255.0)

        self.threshold_id = self.bar_canvas.create_line(
            self.threshold_x, 0,
            self.threshold_x, 12,
            fill="red",
            width=1
        )

        # 刻度行
        self.tick_frame = ttk.Frame(self)
        self.tick_frame.pack(pady=(2, 2))

        ticks = self._calc_ticks()
        self.tick_labels = []
        for t in ticks:
            lbl = ttk.Label(self.tick_frame, text=t, font=("Consolas", 9))
            lbl.pack(side="left", padx=4)
            self.tick_labels.append(lbl)

        # 当前值
        self.value_var = tk.StringVar(value="—")
        self.label_value = ttk.Label(self, textvariable=self.value_var,
                                     font=("Consolas", 11, "bold"), foreground="#00d000")
        self.label_value.pack(pady=(2, 0))

    def _calc_ticks(self):
        """
        对刻度的显示做“物理量 + 单位”的直观化：

        - S 表：按 S 表盘（S0..S9 / +dB）
        - COMP：0..+30 dB（线性）
        - ALC：0..200 %
        - PO：W
        - SWR：无单位
        - IDD：A
        - VDD：V
        """
        # S 表（S_MAIN/S_SUB）：显示更直观的刻度
        if self.meter_id in (1, 2):
            ticks = []
            for raw in (0, 128, 255):
                t = s_meter_text_from_raw(raw)
                if t.startswith("+"):
                    t = t.replace("dB", "").replace(".0", "")
                ticks.append(t)
            return ticks

        # COMP：线性 0..+30 dB
        if self.meter_id == 3:
            return ["0dB", "+15dB", "+30dB"]

        # ALC：0..200 %
        if self.meter_id == 4:
            return ["0%", "100%", "200%"]

        if not self.use_convert:
            return ["0", "0.5", "1"]

        ticks = []
        for raw in (0, 128, 255):
            val = convert_meter_value(self.meter_id, raw)
            if math.isinf(val):
                ticks.append("∞")
            else:
                if self.meter_id == 5:      # PO
                    ticks.append(f"{val:.1f}W")
                elif self.meter_id == 7:    # IDD
                    ticks.append(f"{val:.2f}A")
                elif self.meter_id == 8:    # VDD
                    ticks.append(f"{val:.1f}V")
                else:                       # SWR 等
                    ticks.append(f"{val:.2f}")
        return ticks

        if not self.use_convert:
            return ["0", "0.5", "1"]

        ticks = []
        for raw in (0, 128, 255):
            val = convert_meter_value(self.meter_id, raw)
            if math.isinf(val):
                ticks.append("∞")
            else:
                if abs(val) >= 10:
                    s = f"{val:.1f}"
                else:
                    s = f"{val:.2f}"
                ticks.append(s)
        return ticks

    def set_threshold(self, value=None, raw=None):
        """
        设置红线位置：
          - raw:  0 ~ 255 原始值
          - value: 转换后的物理量（会自动转回 raw）

        两者二选一，如果同时给，raw 优先。
        """
        # ------------------------
        # 1. 如果直接给 raw
        # ------------------------
        if raw is not None:
            try:
                r = float(raw)
            except Exception:
                r = 0.0
            r = max(0.0, min(255.0, r))
            self.threshold_x = int(80 * r / 255.0)
            self.bar_canvas.coords(
                self.threshold_id,
                self.threshold_x, 0,
                self.threshold_x, 12
            )
            return

        # ------------------------
        # 2. 如果给的是转换后的值
        # ------------------------
        if value is None:
            return

        # 没有转换公式的（S_MAIN, COMP），直接按 0~1 缩放
        fn = METER_CONVERT.get(self.meter_id)
        if fn is None:
            v = max(0.0, min(1.0, float(value)))
            self.threshold_x = int(80 * v)
            self.bar_canvas.coords(
                self.threshold_id,
                self.threshold_x, 0,
                self.threshold_x, 12
            )
            return

        # 有转换公式的 -> 需要反向求 raw
        target = float(value)
        best_raw = 0
        best_err = float("inf")

        # 暴力扫 raw=0..255，用 ftx1cat 里的转换函数找最接近的点
        for r in range(256):
            v = fn(r)
            if math.isinf(v):
                continue  # 比如 SWR 的无穷大，直接跳过
            err = abs(v - target)
            if err < best_err:
                best_err = err
                best_raw = r

        best_raw = max(0.0, min(255.0, float(best_raw)))
        self.threshold_x = int(80 * best_raw / 255.0)
        self.bar_canvas.coords(
            self.threshold_id,
            self.threshold_x, 0,
            self.threshold_x, 12
        )



    def update_value(self, raw, value):
        """
        raw:   原始 0~255 数值
        value: 转换后的物理量（ALC/PO/SWR/IDD/VDD），或者非转换时就等于 raw
        """
        # 没数据：清空
        if raw is None or value is None:
            self.value_var.set("—")
            self.bar_canvas.coords(self.bar_id, 0, 0, 0, 12)
            return

        # 无限大（主要是 SWR）
        if math.isinf(value):
            self.value_var.set("∞")
            # 直接打满
            self.bar_canvas.coords(self.bar_id, 0, 0, 80, 12)
            return

        # 文本显示：按单位格式化
        if self.meter_id in (1, 2):
            self.value_var.set(s_meter_text_from_raw(int(raw)))
        elif self.meter_id == 3:
            # COMP：+xdB
            self.value_var.set(f"+{value:.0f}dB")
        elif self.meter_id == 4:
            # ALC：0..200%
            self.value_var.set(f"{value:.0f}%")
        elif self.meter_id == 5:
            # PO：W
            self.value_var.set(f"{value:.1f}W")
        elif self.meter_id == 7:
            # IDD：A
            self.value_var.set(f"{value:.2f}A")
        elif self.meter_id == 8:
            # VDD：V
            self.value_var.set(f"{value:.1f}V")
        else:
            # SWR：无单位
            if abs(value) >= 10:
                self.value_var.set(f"{value:.1f}")
            else:
                self.value_var.set(f"{value:.2f}")

        # --- Bar 映射：严格按 raw 0~255 缩放 ---
        try:
            r = float(raw)
        except (TypeError, ValueError):
            r = 0.0

        # 限制范围
        if r < 0:
            r = 0.0
        if r > 255:
            r = 255.0

        frac = r / 255.0          # 0 → 0, 255 → 1
        bar_len = int(80 * frac)  # 80 像素宽

        self.bar_canvas.coords(self.bar_id, 0, 0, bar_len, 12)




# ==========================
# 麦克风瀑布面板
# ==========================

class MicWaterfallPanel(ttk.Frame):
    """音频输入瀑布图 (0–4000 Hz, 线性时间轴)

    - 点击瀑布图可设置 Notch 频率（由 on_click_freq 处理）
    - get_notch_state: 可选回调，返回 (enabled, freq_hz)，用于在图上画 Notch 边界线
    """

    def __init__(self, parent, on_click_freq, get_notch_state=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_click_freq = on_click_freq
        self.get_notch_state = get_notch_state

        # 音频参数
        self.SAMPLE_RATE = 16000
        self.BLOCK_SIZE = 1024
        self.MAX_FREQ = 4000

        # 频率轴
        self.freqs_full = np.fft.rfftfreq(self.BLOCK_SIZE, 1.0 / self.SAMPLE_RATE)
        self.freq_mask = self.freqs_full <= self.MAX_FREQ
        self.freqs = self.freqs_full[self.freq_mask]
        self.n_freq = len(self.freqs)

        # 历史最大帧数（环形缓冲长度）
        self.MAX_FRAMES = 1000

        # 预分配：shape = (n_freq, MAX_FRAMES)
        # 用 NaN 代表“还没有数据”（左侧会先空白，然后逐渐推进）
        self.data_lock = threading.Lock()
        self.waterfall = np.full(
            (self.n_freq, self.MAX_FRAMES), np.nan, dtype=np.float32
        )

        # 已经写入的帧计数（可能 > MAX_FRAMES，用来算时间）
        self.frame_count = 0

        self.stream = None

        self._build_gui()
        self._init_devices()
        self._schedule_update_plot()

    def _build_gui(self):
        # 设备选择
        top_frame = ttk.Frame(self)
        top_frame.pack(side=tk.TOP, fill=tk.X)

        self.lbl_input_device = ttk.Label(top_frame, text=_T("label_input_device"))
        self.lbl_input_device.pack(side=tk.LEFT, padx=5, pady=5)

        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(
            top_frame, textvariable=self.device_var, state="readonly"
        )
        self.device_combo.pack(side=tk.LEFT, padx=5, pady=5)
        self.device_combo.bind("<<ComboboxSelected>>", self.on_device_selected)

        # 图像
        fig = Figure(figsize=(8, 3.5), dpi=100)
        self.ax = fig.add_subplot(111)

        # 不需要标题，整体更“融合”
        self.ax.set_title("")
        self.ax.set_xlabel("t (s)")
        self.ax.set_ylabel("Frequency (Hz)")
        self.ax.set_ylim(0, self.MAX_FREQ)

        # 固定时间窗：右侧为 0（现在），左侧为“过去多少秒”
        self.dt = self.BLOCK_SIZE / self.SAMPLE_RATE
        self.window_seconds = self.MAX_FRAMES * self.dt
        self.ax.set_xlim(-self.window_seconds, 0.0)

        # x轴上方刻度
        self.ax.tick_params(
            axis="x", top=True, labeltop=True, bottom=True, labelbottom=True
        )

        self.mesh = None
        self.im = None
        self._notch_line_lo = None
        self._notch_line_hi = None

        self.canvas = FigureCanvasTkAgg(fig, master=self)
        self.canvas.draw()
        widget = self.canvas.get_tk_widget()
        widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 点击事件
        self.canvas.mpl_connect("button_press_event", self.on_plot_click)

    # --------------------- 设备 ---------------------

    def _init_devices(self):
        try:
            all_devices = sd.query_devices()
        except Exception as e:
            print(_T("audio_devices_query_failed_fmt").format(e=e))
            self.devices = []
            return

        self.devices = [
            (idx, dev["name"])
            for idx, dev in enumerate(all_devices)
            if dev["max_input_channels"] > 0
        ]

        if not self.devices:
            self.device_combo["values"] = [_T("no_input_device")]
            self.device_combo.current(0)
            return

        values = [f"{idx}: {name}" for idx, name in self.devices]
        self.device_combo["values"] = values
        self.device_combo.current(0)

        # 默认启动第一个设备
        default_index = self.devices[0][0]
        self.after(300, lambda: self.start_stream(default_index))

    def on_device_selected(self, event):
        sel = self.device_var.get()
        try:
            dev_index = int(sel.split(":")[0])
        except ValueError:
            return
        self.start_stream(dev_index)

    # --------------------- 音频流 & FFT ---------------------

    def start_stream(self, device_index: int):
        # 停止旧流
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

        def audio_callback(indata, frames, time, status):
            if status:
                print(status)
            mono = indata[:, 0]
            if len(mono) != self.BLOCK_SIZE:
                return

            # 加窗
            window = np.hanning(self.BLOCK_SIZE)
            windowed = mono * window

            fft_vals = np.fft.rfft(windowed)
            mag = np.abs(fft_vals)

            spec = mag[self.freq_mask]
            spec_db = 20 * np.log10(spec + 1e-8)

            with self.data_lock:
                # 环形缓冲区写入
                col = self.frame_count % self.MAX_FRAMES
                self.waterfall[:, col] = spec_db.astype(np.float32)
                self.frame_count += 1

        try:
            self.stream = sd.InputStream(
                device=device_index,
                channels=1,
                samplerate=self.SAMPLE_RATE,
                blocksize=self.BLOCK_SIZE,
                callback=audio_callback,
            )
            self.stream.start()
        except Exception as e:
            print(_T("audio_stream_start_failed_fmt", "Error starting stream on device {device}: {e}").format(device=device_index, e=e))
            self.stream = None

    # --------------------- 绘图 & 点击 ---------------------

    def _schedule_update_plot(self):
        self.update_plot()
        # 100~150ms 刷新一次就够了
        self.after(120, self._schedule_update_plot)

    def update_plot(self):
        """Redraw / update waterfall using a fast imshow backend.

        IMPORTANT: This runs in the Tk thread. Audio capture happens in a background thread,
        but all matplotlib/tk calls stay here.
        """
        with self.data_lock:
            fc = int(self.frame_count)
            wf = self.waterfall.copy()

        # Assemble a fixed-width display buffer: shape=(n_freq, MAX_FRAMES)
        data_display = np.full((self.n_freq, self.MAX_FRAMES), np.nan, dtype=np.float32)
        if fc < self.MAX_FRAMES:
            n_frames = fc
            if n_frames > 0:
                data_display[:, -n_frames:] = wf[:, :n_frames]
        else:
            oldest_col = fc % self.MAX_FRAMES
            if oldest_col == 0:
                ordered = wf
            else:
                ordered = np.concatenate([wf[:, oldest_col:], wf[:, :oldest_col]], axis=1)
            data_display[:, :] = ordered

        # Lazily create imshow artist once
        if getattr(self, "im", None) is None:
            self.im = self.ax.imshow(
                data_display,
                origin="lower",
                aspect="auto",
                extent=[-self.window_seconds, 0.0, 0.0, self.MAX_FREQ],
                interpolation="nearest",
                vmin=-120.0,
                vmax=-20.0,
            )
            # Notch lines (hidden by default)
            self._notch_line_lo = self.ax.axhline(0.0, color="red", linewidth=1, visible=False)
            self._notch_line_hi = self.ax.axhline(0.0, color="red", linewidth=1, visible=False)

        # Update image data
        self.im.set_data(data_display)

        # Robust color scaling (ignore NaN), avoid extreme spikes
        valid = data_display[np.isfinite(data_display)]
        if valid.size == 0:
            vmin, vmax = -120.0, -20.0
        else:
            vmin = float(np.percentile(valid, 5))
            vmax = float(np.percentile(valid, 95))
            if not np.isfinite(vmin):
                vmin = -120.0
            if not np.isfinite(vmax):
                vmax = -20.0
            if vmax <= vmin:
                vmax = vmin + 1.0
        self.im.set_clim(vmin, vmax)

        # Update notch overlay lines (bandwidth 100 Hz)
        try:
            if self.get_notch_state is not None:
                enabled, notch_hz = self.get_notch_state()
            else:
                enabled, notch_hz = False, None
        except Exception:
            enabled, notch_hz = False, None

        if enabled and notch_hz is not None:
            f0 = float(notch_hz)
            bw = 100.0
            f_lo = f0 - bw / 2.0
            f_hi = f0 + bw / 2.0
            try:
                self._notch_line_lo.set_ydata([f_lo, f_lo])
                self._notch_line_hi.set_ydata([f_hi, f_hi])
                self._notch_line_lo.set_visible(True)
                self._notch_line_hi.set_visible(True)
            except Exception:
                pass
        else:
            try:
                self._notch_line_lo.set_visible(False)
                self._notch_line_hi.set_visible(False)
            except Exception:
                pass

        self.canvas.draw_idle()

    def on_plot_click(self, event):
        if event.inaxes != self.ax:
            return
        if event.ydata is None:
            return

        freq_clicked = float(event.ydata)
        if 0 <= freq_clicked <= self.MAX_FREQ:
            if self.on_click_freq is not None:
                self.on_click_freq(freq_clicked)


    def refresh_plot(self):
        """ """
        try:
            self.update_plot()
        except Exception:
            pass

    def close(self):
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
        self.stream = None


# ==========================
# 主 Tk App
# ==========================

class FTX1TkApp:
    def __init__(self, master):
        self.master = master
        self.master.title(DISPLAY_TEXT["app_title"])
        self.cat = None  # type: FTX1Cat | None
        self.rigctl_server = None

        # i18n language (default en)
        self.current_lang = "en"

        # 默认 TCP 端口
        self.tcp_port_var = tk.IntVar(value=4532)

        # 刷新率 (Hz)
        self.refresh_rate_var = tk.DoubleVar(value=1.0)
        self._meter_hz = 1.0
        try:
            self.refresh_rate_var.trace_add('write', lambda *_: self._on_refresh_rate_changed())
        except Exception:
            pass

        # Manual Notch 当前状态
        self.notch_enabled_var = tk.BooleanVar(value=False)
        self.notch_freq_var = tk.StringVar(value="—")
        # 允许手动输入 notch 频率（Hz）
        self.notch_freq_input_var = tk.StringVar(value="")

        self.waterfall_panel = None  # type: MicWaterfallPanel | None

        # 全量读取（网络/手动写入后延迟 1s 执行，可被重置）
        self._full_read_after_id = None
        self._full_read_thread = None
        self.preamp_vars = {}  # band -> tk.StringVar

        self._build_gui()
        # Apply initial language to all widgets
        self.apply_language()

        # 启动 Meter 后台线程 + UI 轮询
        self._start_meter_thread()
        self._schedule_meter_update()

        self.master.protocol("WM_DELETE_WINDOW", self.on_close)



    def _on_refresh_rate_changed(self):
        # Tk thread: cache refresh rate for worker thread (tk vars are not thread-safe)
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
        """Apply current language text to existing widgets (Tk does not auto-refresh)."""
        global DISPLAY_TEXT
        DISPLAY_TEXT = I18N_TEXT.get(self.current_lang, I18N_TEXT.get("zh", DISPLAY_TEXT))

        # Window title
        try:
            self.master.title(_T("app_title"))
        except Exception:
            pass

        # Top labels/buttons
        for attr, key in [
            ("lbl_cat_port", "label_cat_port"),
            ("lbl_ptt_port", "label_ptt_port"),
            ("lbl_baud1", "label_baud"),
            ("lbl_baud2", "label_baud"),
            ("lbl_rigctl_port", "label_rigctl_port"),
        ]:
            w = getattr(self, attr, None)
            if w is not None:
                try:
                    w.configure(text=_T(key))
                except Exception:
                    pass

        for attr, key in [
            ("btn_connect", "btn_connect"),
            ("btn_disconnect", "btn_disconnect"),
            ("btn_full_read", "btn_full_read"),
            ("btn_refresh_rts", "btn_refresh_rts"),
            ("btn_set_notch", "btn_set"),
            ("btn_read_notch", "menu_read"),
        ]:
            w = getattr(self, attr, None)
            if w is not None:
                try:
                    w.configure(text=_T(key))
                except Exception:
                    pass

        # Frames
        for attr, key in [
            ("freq_frame", "frame_freq_mode_ptt"),
            ("preamp_frame", "frame_preamp"),
            ("meter_frame", "frame_meters"),
            ("notch_frame", "frame_notch_main"),
        ]:
            w = getattr(self, attr, None)
            if w is not None:
                try:
                    w.configure(text=_T(key))
                except Exception:
                    pass

        # Static labels
        for attr, key in [
            ("lbl_freq_static", "label_freq_static"),
            ("lbl_mode_static", "label_mode_static"),
            ("lbl_meter_rate", "label_meter_rate"),
            ("lbl_notch_hint", "hint_fft_click_notch"),
            ("lbl_notch_freq", "label_freq_hz"),
            ("lbl_notch_current", "label_current"),
            ("lbl_agc", "label_agc"),
            ("lbl_power", "label_power_w"),
        ]:
            w = getattr(self, attr, None)
            if w is not None:
                try:
                    w.configure(text=_T(key))
                except Exception:
                    pass

        # Checkbuttons
        if getattr(self, "rts_check", None) is not None:
            try:
                self.rts_check.configure(text=_T("label_rts_ptt"))
            except Exception:
                pass
        if getattr(self, "chk_enable_notch", None) is not None:
            try:
                self.chk_enable_notch.configure(text=_T("chk_enable_notch"))
            except Exception:
                pass

        # Status vars (best-effort refresh)
        try:
            if self.cat is None:
                self.status_var.set(_T("status_disconnected"))
            else:
                self.status_var.set(
                    _T("status_connected_fmt").format(
                        port=self.port_entry.get(),
                        baud=self.baud_entry.get(),
                        port2=self.port2_entry.get(),
                        baud2=self.baud2_entry.get(),
                    )
                )
        except Exception:
            pass

        try:
            if self.rigctl_server is None:
                self.rigctl_status_var.set(_T("rigctl_stop"))
            else:
                self.rigctl_status_var.set(
                    _T("rigctl_started_fmt").format(tcp_port=int(self.tcp_port_var.get()))
                )
        except Exception:
            pass

        # Waterfall panel label
        if getattr(self, "waterfall_panel", None) is not None and hasattr(self.waterfall_panel, "lbl_input_device"):
            try:
                self.waterfall_panel.lbl_input_device.configure(text=_T("label_input_device"))
            except Exception:
                pass

    # ---------- GUI 搭建 ----------

    def _build_gui(self):
        # 顶部: 串口 & rigctl
        top = ttk.Frame(self.master, padding=6)
        top.pack(side="top", fill="x")

        # 串口1: CAT
        self.lbl_cat_port = ttk.Label(top, text=_T("label_cat_port"))
        self.lbl_cat_port.pack(side="left")
        self.port_entry = ttk.Entry(top, width=8)
        self.port_entry.insert(0, "COM11")
        self.port_entry.pack(side="left", padx=2)

        self.lbl_baud1 = ttk.Label(top, text=_T("label_baud"))
        self.lbl_baud1.pack(side="left")
        self.baud_entry = ttk.Entry(top, width=8)
        self.baud_entry.insert(0, "38400")
        self.baud_entry.pack(side="left", padx=4)

        # 串口2: PTT (RTS)
        self.lbl_ptt_port = ttk.Label(top, text=_T("label_ptt_port"))
        self.lbl_ptt_port.pack(side="left", padx=(10, 2))
        self.port2_entry = ttk.Entry(top, width=8)
        self.port2_entry.insert(0, "COM12")
        self.port2_entry.pack(side="left", padx=2)

        self.lbl_baud2 = ttk.Label(top, text=_T("label_baud"))
        self.lbl_baud2.pack(side="left")
        self.baud2_entry = ttk.Entry(top, width=8)
        self.baud2_entry.insert(0, "38400")
        self.baud2_entry.pack(side="left", padx=4)

        self.btn_connect = ttk.Button(top, text=DISPLAY_TEXT["btn_connect"], command=self.on_connect)
        self.btn_connect.pack(side="left", padx=4)

        self.btn_disconnect = ttk.Button(top, text=DISPLAY_TEXT["btn_disconnect"], command=self.on_disconnect, state="disabled")
        self.btn_disconnect.pack(side="left", padx=4)

        self.btn_full_read = ttk.Button(top, text=DISPLAY_TEXT["btn_full_read"], command=self.on_full_read, state="disabled")
        self.btn_full_read.pack(side="left", padx=(12, 4))

        # Language selector
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

        self.rigctl_status_var = tk.StringVar(value=DISPLAY_TEXT["rigctl_stop"])
        self.lbl_rigctl_status = ttk.Label(top, textvariable=self.rigctl_status_var)
        self.lbl_rigctl_status.pack(side="right")
        
        # 中间: 频率/模式/PTT/Preamp
        mid = ttk.Frame(self.master, padding=6)
        mid.pack(side="top", fill="x")

        # 频率 / 模式 / RTS PTT
        self.freq_frame = ttk.LabelFrame(mid, text=_T("frame_freq_mode_ptt"), padding=6)
        self.freq_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))

        freq_frame = self.freq_frame
        row1 = ttk.Frame(freq_frame)
        row1.pack(fill="x", pady=2)
        self.lbl_freq_static = ttk.Label(row1, text=_T("label_freq_static"))
        self.lbl_freq_static.pack(side="left")
        self.freq_entry = ttk.Entry(row1, width=12)
        self.freq_entry.pack(side="left", padx=4)
        ttk.Button(row1, text=DISPLAY_TEXT["btn_read"], command=self.on_read_freq).pack(side="left", padx=2)
        ttk.Button(row1, text=DISPLAY_TEXT["btn_write"], command=self.on_set_freq).pack(side="left", padx=2)

        row2 = ttk.Frame(freq_frame)
        row2.pack(fill="x", pady=2)
        self.lbl_mode_static = ttk.Label(row2, text=_T("label_mode_static"))
        self.lbl_mode_static.pack(side="left")
        self.mode_var = tk.StringVar()
        mode_values = sorted(set(P2_TO_MODE.values()))  # 字符串模式列表
        self.mode_combo = ttk.Combobox(row2, textvariable=self.mode_var, values=mode_values, width=12, state="readonly")
        self.mode_combo.pack(side="left", padx=4)
        ttk.Button(row2, text=DISPLAY_TEXT["btn_read"], command=self.on_read_mode).pack(side="left", padx=2)
        ttk.Button(row2, text=DISPLAY_TEXT["btn_write"], command=self.on_set_mode).pack(side="left", padx=2)

        row3 = ttk.Frame(freq_frame)
        row3.pack(fill="x", pady=2)
        self.rts_var = tk.BooleanVar(value=False)
        self.rts_check = ttk.Checkbutton(
            row3, text=DISPLAY_TEXT["label_rts_ptt"], variable=self.rts_var, command=self.on_toggle_rts
        )
        self.rts_check.pack(side="left")
        self.btn_refresh_rts = ttk.Button(row3, text=_T("btn_refresh_rts", "Refresh"), command=self.on_read_rts)
        self.btn_refresh_rts.pack(side="left", padx=4)


        # AGC
        row4 = ttk.Frame(freq_frame)
        row4.pack(fill="x", pady=2)
        self.lbl_agc = ttk.Label(row4, text=_T("label_agc", "AGC:"))
        self.lbl_agc.pack(side="left")
        self.agc_var = tk.StringVar(value="AUTO")
        # Set 可选：OFF / FAST / MID / SLOW / AUTO
        agc_values = ["OFF", "FAST", "MID", "SLOW", "AUTO"]
        self.agc_combo = ttk.Combobox(row4, textvariable=self.agc_var, values=agc_values, width=12, state="readonly")
        self.agc_combo.pack(side="left", padx=4)
        ttk.Button(row4, text=DISPLAY_TEXT["btn_read"], command=self.on_read_agc).pack(side="left", padx=2)
        ttk.Button(row4, text=DISPLAY_TEXT["btn_write"], command=self.on_set_agc).pack(side="left", padx=2)
        self.agc_readback_var = tk.StringVar(value="—")
        ttk.Label(row4, textvariable=self.agc_readback_var, font=("Consolas", 10)).pack(side="left", padx=(8, 0))

        # Power (PC)
        row5 = ttk.Frame(freq_frame)
        row5.pack(fill="x", pady=2)
        self.lbl_power = ttk.Label(row5, text=_T("label_power_w", "Power (W):"))
        self.lbl_power.pack(side="left")
        self.power_entry = ttk.Entry(row5, width=6)
        self.power_entry.pack(side="left", padx=4)
        ttk.Button(row5, text=DISPLAY_TEXT["btn_read"], command=self.on_read_power).pack(side="left", padx=2)
        ttk.Button(row5, text=DISPLAY_TEXT["btn_write"], command=self.on_set_power).pack(side="left", padx=2)
        self.power_dev_var = tk.StringVar(value="—")
        ttk.Label(row5, textvariable=self.power_dev_var, font=("Consolas", 10)).pack(side="left", padx=(8, 0))

        # Preamp
        self.preamp_frame = ttk.LabelFrame(mid, text=_T("frame_preamp"), padding=6)
        self.preamp_frame.pack(side="left", fill="both", expand=True)

        preamp_frame = self.preamp_frame
        self._build_preamp_row(preamp_frame, "HF50", ["IPO", "AMP1", "AMP2"])
        self._build_preamp_row(preamp_frame, "VHF", ["OFF", "ON"])
        self._build_preamp_row(preamp_frame, "UHF", ["OFF", "ON"])

        # Manual Notch + 瀑布
        self.notch_frame = ttk.LabelFrame(self.master, text=_T("frame_notch_main", "Manual Notch (MAIN)"), padding=6)
        notch_frame = self.notch_frame
        notch_frame.pack(side="top", fill="both", expand=True, padx=6, pady=4)

        top_row = ttk.Frame(notch_frame)
        top_row.pack(fill="x")

        # 提示：点击瀑布图（FFT 图像）来设置 Notch
        self.lbl_notch_hint = ttk.Label(top_row, text=_T("hint_fft_click_notch"), foreground="#666666")
        self.lbl_notch_hint.pack(side="left", padx=(0, 12))

        self.chk_enable_notch = ttk.Checkbutton(top_row, text=_T("chk_enable_notch", "Enable"), variable=self.notch_enabled_var, command=self.on_notch_toggle)
        self.chk_enable_notch.pack(side="left")

        self.lbl_notch_freq = ttk.Label(top_row, text=_T("label_freq_hz"))
        self.lbl_notch_freq.pack(side="left", padx=(12, 2))
        notch_entry = ttk.Entry(top_row, textvariable=self.notch_freq_input_var, width=8)
        notch_entry.pack(side="left")
        notch_entry.bind("<Return>", lambda _e: self.on_set_notch_freq())

        self.lbl_notch_current = ttk.Label(top_row, text=_T("label_current"))
        self.lbl_notch_current.pack(side="left", padx=(8, 2))
        ttk.Label(top_row, textvariable=self.notch_freq_var, width=10).pack(side="left")

        self.btn_set_notch = ttk.Button(top_row, text=_T("btn_set"), command=self.on_set_notch_freq)
        self.btn_set_notch.pack(side="left", padx=4)
        self.btn_read_notch = ttk.Button(top_row, text=_T("menu_read"), command=self.on_read_notch)
        self.btn_read_notch.pack(side="left", padx=2)

        # 瀑布面板
        self.waterfall_panel = MicWaterfallPanel(
            notch_frame,
            on_click_freq=self._apply_notch_freq,
            get_notch_state=self._get_notch_state_for_plot,
        )
        self.waterfall_panel.pack(fill="both", expand=True, pady=(4, 0))

        # 刷新率 & Meters
        bottom = ttk.Frame(self.master, padding=6)
        bottom.pack(side="top", fill="both", expand=True)

        left_bottom = ttk.Frame(bottom)
        left_bottom.pack(side="left", fill="y")

        self.lbl_meter_rate = ttk.Label(left_bottom, text=_T("label_meter_rate"))
        self.lbl_meter_rate.pack(anchor="w")
        rate_values = [5, 2, 1, 0.5, 0.2, 0.1]
        self.rate_combo = ttk.Combobox(
            left_bottom,
            values=[str(v) for v in rate_values],
            width=6,
            state="readonly",
            textvariable=self.refresh_rate_var
        )
        self.rate_combo.pack(anchor="w")
        self.rate_combo.set("1.0")

        self.status_var = tk.StringVar(value=DISPLAY_TEXT["status_disconnected"])
        ttk.Label(left_bottom, textvariable=self.status_var, foreground="#0080ff").pack(anchor="w", pady=(8, 0))

        # 表头 Meters（右侧）
        self.meter_frame = ttk.LabelFrame(bottom, text=_T("frame_meters"), padding=6)
        meter_frame = self.meter_frame
        meter_frame.pack(side="left", fill="both", expand=True, padx=(12, 0))

        self.meter_widgets = {}
        # 只做这几个：S_MAIN, COMP, ALC, PO, SWR, IDD, VDD
        layout_meters = [
            # S 表使用非线性转换（raw -> S0/1/3/5/7/9 或 +dB）
            ("S_MAIN", 1, True, True, 128),
            ("COMP", 3, True, False, 15),
            ("ALC", 4, True, False, 100),
            ("PO", 5, True, False, 10),
            ("SWR", 6, True, False, 3),
            ("IDD", 7, True, False, 2),
            ("VDD", 8, True, False, 13.8),
        ]

        row = ttk.Frame(meter_frame)
        row.pack()
        for name, mid, use_conv, raw_tr, tr in layout_meters:
            w = MeterHeader(row, name, mid, use_conv)
            w.pack(side="left", padx=6)
            self.meter_widgets[name] = w
            if raw_tr:
                w.set_threshold(raw=tr)
            else:
                w.set_threshold(value=tr)


    # ---------- 全量读取（所有参数）----------

    def on_full_read(self):
        """ """
        self._schedule_full_read(delay_ms=0)

    def on_network_activity(self):
        """ """
        # 在子线程里回调，切回 Tk 主线程
        try:
            self.master.after(0, lambda: self._schedule_full_read(delay_ms=1000))
        except Exception:
            pass

    def _schedule_full_read(self, delay_ms: int = 1000):
        if not self.cat:
            return
        # 重置等待：如果 1s 内又有新指令，则重新计时
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
        # 避免并发跑多个全量读取
        if self._full_read_thread is not None and self._full_read_thread.is_alive():
            return

        def worker():
            cat = self.cat
            result = {}
            try:
                # 频率/模式/RTS
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

            # Preamp
            result["preamp"] = {}
            for band in list(self.preamp_vars.keys()):
                try:
                    level, _ = cat.get_preamp(band)
                except Exception:
                    level = None
                result["preamp"][band] = level

            
            # AGC
            try:
                result["agc_name"], _ = cat.get_agc(main=True)
            except Exception:
                result["agc_name"] = None

            # Power (PC)
            try:
                result["power_dev"], result["power_watts"], _ = cat.get_power_control()
            except Exception:
                result["power_dev"], result["power_watts"] = None, None

# Manual Notch
            try:
                enabled, freq_hz, _ = cat.get_manual_notch(main=True)
            except Exception:
                enabled, freq_hz = None, None
            result["notch_enabled"] = bool(enabled) if enabled is not None else False
            result["notch_freq_hz"] = freq_hz

            # 切回主线程更新 UI
            try:
                self.master.after(0, lambda: self._apply_full_read_result(result))
            except Exception:
                pass

        self._full_read_thread = threading.Thread(target=worker, daemon=True)
        self._full_read_thread.start()

    def _apply_full_read_result(self, result: dict):
        """ """
        # freq
        freq_hz = result.get("freq_hz")
        if freq_hz is not None:
            try:
                self.freq_entry.delete(0, tk.END)
                self.freq_entry.insert(0, str(int(freq_hz)))
            except Exception:
                pass

        # mode
        mode_name = result.get("mode_name")
        if mode_name:
            try:
                self.mode_var.set(mode_name)
            except Exception:
                pass


        # agc
        agc_name = result.get("agc_name")
        if agc_name:
            try:
                self.agc_readback_var.set(agc_name)
                if str(agc_name).startswith("AUTO"):
                    self.agc_var.set("AUTO")
                else:
                    self.agc_var.set(agc_name)
            except Exception:
                pass
        else:
            try:
                self.agc_readback_var.set("—")
            except Exception:
                pass

        # power
        pdev = result.get("power_dev")
        pw = result.get("power_watts")
        try:
            self.power_dev_var.set(pdev or "—")
        except Exception:
            pass
        if pw is not None:
            try:
                self.power_entry.delete(0, tk.END)
                self.power_entry.insert(0, str(int(pw)))
            except Exception:
                pass

        # rts
        rts = result.get("rts")
        if rts is not None:
            try:
                self.rts_var.set(bool(rts))
            except Exception:
                pass

        # preamp
        pre = result.get("preamp") or {}
        for band, val in pre.items():
            if val:
                try:
                    self.preamp_vars[band].set(val)
                except Exception:
                    pass

        # notch
        try:
            self.notch_enabled_var.set(bool(result.get("notch_enabled", False)))
        except Exception:
            pass

        nf = result.get("notch_freq_hz")
        if nf is None:
            self.notch_freq_var.set("—")
            self.notch_freq_input_var.set("")
        else:
            self.notch_freq_var.set(f"{int(nf)} Hz")
            self.notch_freq_input_var.set(str(int(nf)))

        self._refresh_notch_overlay()

    def _refresh_notch_overlay(self):
        if self.waterfall_panel is not None:
            try:
                self.waterfall_panel.refresh_plot()
            except Exception:
                pass

    def _build_preamp_row(self, parent, band_name, choices):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=2)
        ttk.Label(frame, text=band_name + ":").pack(side="left", padx=2)
        var = tk.StringVar()
        # 记录，供全量读取更新 UI
        self.preamp_vars[band_name] = var
        combo = ttk.Combobox(frame, textvariable=var, values=choices, width=8, state="readonly")
        combo.pack(side="left", padx=2)
        combo.set(choices[0])

        def do_read(band=band_name, var=var):
            if not self.cat:
                return
            level, _ = self.cat.get_preamp(band)
            if level:
                var.set(level)

        def do_set(band=band_name, var=var):
            if not self.cat:
                return
            try:
                self.cat.set_preamp(band, var.get())
                self._schedule_full_read(delay_ms=1000)
            except Exception as e:
                messagebox.showerror(DISPLAY_TEXT["preamp_set_failed"], str(e))

        ttk.Button(frame, text=DISPLAY_TEXT["btn_read"], command=do_read).pack(side="left", padx=2)
        ttk.Button(frame, text=DISPLAY_TEXT["btn_write"], command=do_set).pack(side="left", padx=2)

    # ---------- 连接 / 断开 ----------

    def on_connect(self):
        self._start_meter_thread()
        if self.cat is not None:
            return
        port = self.port_entry.get().strip()
        port2 = self.port2_entry.get().strip()
        if not port or not port2:
            messagebox.showwarning(DISPLAY_TEXT["error_title"], DISPLAY_TEXT["need_cat_and_ptt_ports"])
            return
        try:
            baud = int(self.baud_entry.get().strip())
        except ValueError:
            messagebox.showwarning(DISPLAY_TEXT["error_title"], DISPLAY_TEXT["cat_baud_must_int"])
            return
        try:
            baud2 = int(self.baud2_entry.get().strip())
        except ValueError:
            messagebox.showwarning(DISPLAY_TEXT["error_title"], DISPLAY_TEXT["ptt_baud_must_int"])
            return

        try:
            self.cat = FTX1Cat(port=port, baudrate=baud,
                               port2=port2, baudrate2=baud2,
                               timeout=1.0)
        except Exception as e:
            self.cat = None
            messagebox.showerror(DISPLAY_TEXT["connect_failed"], str(e))
            return

        self.status_var.set(DISPLAY_TEXT["status_connected_fmt"].format(port=port, baud=baud, port2=port2, baud2=baud2))
        self.btn_connect.configure(state="disabled")
        self.btn_disconnect.configure(state="normal")

        # 启动 rigctl 服务器
        try:
            tcp_port = int(self.tcp_port_var.get())
        except ValueError:
            tcp_port = 4532
            self.tcp_port_var.set(tcp_port)

        self.rigctl_server = RigctlTCPServer(self.cat, host="127.0.0.1", port=tcp_port, on_activity=self.on_network_activity)
        self.rigctl_server.start()
        self.rigctl_status_var.set(DISPLAY_TEXT["rigctl_started_fmt"].format(tcp_port=tcp_port))


        # 连接后：先全量读取一次，确保 UI 与机器状态一致
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
        self.status_var.set(DISPLAY_TEXT["status_disconnected"])
        self.btn_connect.configure(state="normal")
        self.btn_disconnect.configure(state="disabled")

        if self.rigctl_server:
            self.rigctl_server.stop()
            self.rigctl_server = None

        # i18n language (default zh)
        self.current_lang = "en"
        self.rigctl_status_var.set(DISPLAY_TEXT["rigctl_stop"])


        # 断开时：取消全量读取计划
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

    # ---------- 频率 / 模式 / RTS PTT ----------

    def on_read_freq(self):
        if not self.cat:
            return
        freq_hz, _ = self.cat.get_freq()
        if freq_hz is None:
            messagebox.showerror(DISPLAY_TEXT["read_failed"], DISPLAY_TEXT["freq_parse_failed"])
            return
        self.freq_entry.delete(0, tk.END)
        self.freq_entry.insert(0, str(freq_hz))

    def on_set_freq(self):
        if not self.cat:
            return
        text = self.freq_entry.get().strip()
        try:
            freq_hz = int(float(text))
        except ValueError:
            messagebox.showwarning(DISPLAY_TEXT["error_title"], DISPLAY_TEXT["freq_must_number"])
            return
        try:
            self.cat.set_freq(freq_hz)
            self._schedule_full_read(delay_ms=1000)
        except Exception as e:
            messagebox.showerror(DISPLAY_TEXT["set_failed"], str(e))

    def on_read_mode(self):
        if not self.cat:
            return
        mode_name, _ = self.cat.get_mode(main=True)
        if mode_name is None:
            messagebox.showerror(DISPLAY_TEXT["read_failed"], DISPLAY_TEXT["illegal_mode_code"])
            return
        self.mode_var.set(mode_name)

    def on_set_mode(self):
        if not self.cat:
            return
        mode_name = self.mode_var.get().strip().upper()
        if not mode_name:
            return
        try:
            self.cat.set_mode(mode_name, main=True)
            self._schedule_full_read(delay_ms=1000)
        except Exception as e:
            messagebox.showerror(DISPLAY_TEXT["set_failed"], str(e))

    def on_toggle_rts(self):
        if not self.cat:
            return
        try:
            self.cat.set_rts(self.rts_var.get())
            self._schedule_full_read(delay_ms=1000)
        except Exception as e:
            messagebox.showerror(DISPLAY_TEXT["rts_ptt_set_failed"], str(e))
            # 回退 UI
            self.on_read_rts()


    def on_read_agc(self):
        if not self.cat:
            return
        try:
            agc_name, _ = self.cat.get_agc(main=True)
        except Exception as e:
            messagebox.showerror(DISPLAY_TEXT["read_failed"], DISPLAY_TEXT["agc_read_failed_fmt"].format(e=e))
            return
        # 读回值可能是 AUTO-FAST / AUTO-MID / AUTO-SLOW
        if not agc_name:
            self.agc_readback_var.set("—")
            return
        self.agc_readback_var.set(agc_name)
        # 若是 AUTO-FAST 等，combo 仍保持 AUTO（因为 Set 只支持 AUTO）
        if str(agc_name).startswith("AUTO"):
            self.agc_var.set("AUTO")
        else:
            self.agc_var.set(agc_name)

    def on_set_agc(self):
        if not self.cat:
            return
        agc = (self.agc_var.get() or "").strip().upper()
        if not agc:
            return
        try:
            self.cat.set_agc(agc, main=True)
            self._schedule_full_read(delay_ms=1000)
        except Exception as e:
            messagebox.showerror(DISPLAY_TEXT["agc_set_failed"], str(e))
            # 回退读取状态
            self.on_read_agc()

    def on_read_power(self):
        if not self.cat:
            return
        try:
            dev, watts, _ = self.cat.get_power_control()
        except Exception as e:
            messagebox.showerror(DISPLAY_TEXT["read_failed"], DISPLAY_TEXT["power_read_failed_fmt"].format(e=e))
            return
        if watts is None:
            try:
                self.power_entry.delete(0, tk.END)
            except Exception:
                pass
            self.power_dev_var.set(dev or "—")
            return
        try:
            self.power_entry.delete(0, tk.END)
            self.power_entry.insert(0, str(int(watts)))
        except Exception:
            pass
        self.power_dev_var.set(dev or "—")

    def on_set_power(self):
        if not self.cat:
            return
        s = self.power_entry.get().strip()
        if not s:
            return
        try:
            w = int(float(s))
        except ValueError:
            messagebox.showwarning(DISPLAY_TEXT["error_title"], DISPLAY_TEXT["power_must_int_w"])
            return
        try:
            self.cat.set_power_watts(w)
            self._schedule_full_read(delay_ms=1000)
        except Exception as e:
            messagebox.showerror(DISPLAY_TEXT["power_set_failed"], str(e))
            self.on_read_power()

    def on_read_rts(self):
        if not self.cat:
            return
        try:
            val = self.cat.get_rts()
        except Exception as e:
            messagebox.showerror(DISPLAY_TEXT["read_failed"], DISPLAY_TEXT["rts_read_failed_fmt"].format(e=e))
            return
        self.rts_var.set(bool(val))

    # ---------- Manual Notch ----------

    def on_read_notch(self):
        if not self.cat:
            return
        enabled, freq_hz, _ = self.cat.get_manual_notch(main=True)
        if enabled is None:
            self.notch_enabled_var.set(False)
        else:
            self.notch_enabled_var.set(enabled)
        if freq_hz is None:
            self.notch_freq_var.set("—")
            self.notch_freq_input_var.set("")
        else:
            self.notch_freq_var.set(f"{freq_hz} Hz")
            self.notch_freq_input_var.set(str(freq_hz))
            self._schedule_full_read(delay_ms=1000)
            self._refresh_notch_overlay()
            self.notch_freq_input_var.set(str(freq_hz))

    def on_set_notch_freq(self):
        """ """
        text = (self.notch_freq_input_var.get() or "").strip()
        if not text:
            return
        try:
            f = float(text)
        except Exception:
            messagebox.showwarning(_T("error_title"), _T("notch_freq_must_number", "Notch frequency must be a number"))
            return
        self._apply_notch_freq(f)

    def _get_notch_state_for_plot(self):
        """ """
        # notch_freq_var 里带 " Hz"，这里优先读输入框/显示值
        enabled = bool(self.notch_enabled_var.get())
        freq = None
        s = (self.notch_freq_input_var.get() or "").strip()
        if not s:
            s = (self.notch_freq_var.get() or "").replace("Hz", "").strip()
        try:
            if s and s != "—":
                freq = float(s)
        except Exception:
            freq = None
        return enabled, freq

    def on_notch_toggle(self):
        if not self.cat:
            return
        enabled = self.notch_enabled_var.get()
        try:
            # 只改 ON/OFF，不动频率
            self.cat.set_manual_notch(main=True, enabled=enabled, freq_hz=None)
            self._schedule_full_read(delay_ms=1000)
            self._refresh_notch_overlay()
        except Exception as e:
            messagebox.showerror(_T("notch_set_failed", "Notch set failed"), str(e))
            # 回退读取状态
            self.on_read_notch()

    def _apply_notch_freq(self, freq_hz_float: float):
        """
        手动设置 notch 频率：
          - 四舍五入到 10Hz 步进
          - 若 <10 或 >3200，则关闭 Notch
        """
        if not self.cat:
            return
        steps = int(round(freq_hz_float / 10.0))
        if steps < 1 or steps > 320:
            # 超出范围 -> 关闭
            try:
                self.cat.set_manual_notch(main=True, enabled=False, freq_hz=None)
                self.notch_enabled_var.set(False)
                self.notch_freq_var.set("—")
                self.notch_freq_input_var.set("")
                self._schedule_full_read(delay_ms=1000)
                self._refresh_notch_overlay()
            except Exception as e:
                messagebox.showerror(_T("notch_set_failed", "Notch set failed"), str(e))
            return

        freq_hz = steps * 10
        try:
            self.cat.set_manual_notch(main=True, enabled=True, freq_hz=freq_hz)
            self.notch_enabled_var.set(True)
            self.notch_freq_var.set(f"{freq_hz} Hz")
            self.notch_freq_input_var.set(str(freq_hz))
        except Exception as e:
            messagebox.showerror(_T("notch_set_failed", "Notch set failed"), str(e))

    # ---------- Meters 周期刷新 ----------

    def _schedule_meter_update(self):
        """UI-thread meter updater: only consumes results produced by the background worker."""
        self._update_meters()

        # Keep UI polling fairly light; actual CAT reads happen in worker thread
        self.master.after(100, self._schedule_meter_update)

    def _start_meter_thread(self):
        if getattr(self, "_meter_stop", None) is None or getattr(self, "_meter_stop").is_set():
            self._meter_stop = threading.Event()
        if getattr(self, "_meter_queue", None) is None:
            self._meter_queue = queue.Queue(maxsize=1)

        if getattr(self, "_meter_thread", None) is not None and self._meter_thread.is_alive():
            return

        def worker():
            # NOTE: never touch any tk variables/widgets from this thread.
            while not self._meter_stop.is_set():
                try:
                    hz = float(getattr(self, "_meter_hz", 1.0))
                except Exception:
                    hz = 1.0
                hz = max(min(hz, 5.0), 0.1)
                sleep_s = 1.0 / hz

                cat = getattr(self, "cat", None)
                if cat is None:
                    self._meter_stop.wait(0.2)
                    continue

                try:
                    data = cat.read_all_meters()
                except Exception:
                    # Don't spam; UI thread will show a brief status if needed
                    data = None

                # Overwrite previous (keep most recent only)
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
            if getattr(self, "_meter_stop", None) is not None:
                self._meter_stop.set()
        except Exception:
            pass

    def _update_meters(self):
        """Consume latest meter results and update widgets (Tk thread only)."""
        if getattr(self, "_meter_queue", None) is None:
            return

        data = None
        try:
            # Drain to latest
            while True:
                data = self._meter_queue.get_nowait()
        except Exception:
            pass

        if data is None:
            # If disconnected, clear display; if connected but read failed, keep last values
            if not self.cat:
                for _, widget in self.meter_widgets.items():
                    widget.update_value(None, None)
            return

        for name, widget in self.meter_widgets.items():
            info = data.get(name) if isinstance(data, dict) else None
            if not info:
                widget.update_value(None, None)
                continue
            raw = info.get("raw")
            value = info.get("value")
            widget.update_value(raw, value)

    # ---------- 关闭 ----------

    def on_close(self):
        self._stop_meter_thread()
        if self.waterfall_panel is not None:
            self.waterfall_panel.close()
        self.on_disconnect()
        self.master.destroy()


def main():
    root = tk.Tk()
    app = FTX1TkApp(root)
    root.mainloop()

# --------------------------
# Docstrings (i18n extracted)
# --------------------------
try:
    MicWaterfallPanel.refresh_plot.__doc__ = DISPLAY_TEXT["hint_force_waterfall_refresh"]
    FTX1TkApp.on_full_read.__doc__ = DISPLAY_TEXT["hint_btn_full_read"]
    FTX1TkApp.on_network_activity.__doc__ = DISPLAY_TEXT["hint_rigctl_autoread"]
    FTX1TkApp._apply_full_read_result.__doc__ = DISPLAY_TEXT["hint_overwrite_ui"]
    FTX1TkApp.on_set_notch_freq.__doc__ = DISPLAY_TEXT["hint_notch_input"]
    FTX1TkApp._get_notch_state_for_plot.__doc__ = DISPLAY_TEXT["doc_for_waterfall"]
except Exception:
    pass


if __name__ == "__main__":
    main()
