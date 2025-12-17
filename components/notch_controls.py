import threading
import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
import sounddevice as sd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class MicWaterfallPanel(ttk.Frame):
    """Audio waterfall for notch selection."""

    def __init__(self, parent, on_click_freq, get_notch_state=None, translate=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_click_freq = on_click_freq
        self.get_notch_state = get_notch_state
        self._t = translate or (lambda k, d=None: d or k)

        self.SAMPLE_RATE = 16000
        self.BLOCK_SIZE = 1024
        self.MAX_FREQ = 4000

        self.freqs_full = np.fft.rfftfreq(self.BLOCK_SIZE, 1.0 / self.SAMPLE_RATE)
        self.freq_mask = self.freqs_full <= self.MAX_FREQ
        self.freqs = self.freqs_full[self.freq_mask]
        self.n_freq = len(self.freqs)

        self.MAX_FRAMES = 1000
        self.data_lock = threading.Lock()
        self.waterfall = np.full((self.n_freq, self.MAX_FRAMES), np.nan, dtype=np.float32)
        self.frame_count = 0
        self.stream = None

        self.mesh = None
        self.im = None
        self._notch_line_lo = None
        self._notch_line_hi = None

        self._build_gui()
        self._init_devices()
        self._schedule_update_plot()

    def _build_gui(self):
        top_frame = ttk.Frame(self)
        top_frame.pack(side=tk.TOP, fill=tk.X)

        self.lbl_input_device = ttk.Label(top_frame, text=self._t("label_input_device", "Input device"))
        self.lbl_input_device.pack(side=tk.LEFT, padx=5, pady=5)

        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(top_frame, textvariable=self.device_var, state="readonly")
        self.device_combo.pack(side=tk.LEFT, padx=5, pady=5)
        self.device_combo.bind("<<ComboboxSelected>>", self.on_device_selected)

        fig = Figure(figsize=(8, 3.5), dpi=100)
        self.ax = fig.add_subplot(111)
        self.ax.set_title("")
        self.ax.set_xlabel("t (s)")
        self.ax.set_ylabel("Frequency (Hz)")
        self.ax.set_ylim(0, self.MAX_FREQ)

        self.dt = self.BLOCK_SIZE / self.SAMPLE_RATE
        self.window_seconds = self.MAX_FRAMES * self.dt
        self.ax.set_xlim(-self.window_seconds, 0.0)
        self.ax.tick_params(axis="x", top=True, labeltop=True, bottom=True, labelbottom=True)

        self.canvas = FigureCanvasTkAgg(fig, master=self)
        self.canvas.draw()
        widget = self.canvas.get_tk_widget()
        widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.mpl_connect("button_press_event", self.on_plot_click)

    def _init_devices(self):
        try:
            all_devices = sd.query_devices()
        except Exception as e:
            print(self._t("audio_devices_query_failed_fmt", "Audio devices query failed: {e}").format(e=e))
            self.devices = []
            return

        self.devices = [(idx, dev["name"]) for idx, dev in enumerate(all_devices) if dev.get("max_input_channels", 0) > 0]

        if not self.devices:
            self.device_combo["values"] = [self._t("no_input_device", "No input device")]
            self.device_combo.current(0)
            return

        values = [f"{idx}: {name}" for idx, name in self.devices]
        self.device_combo["values"] = values
        preferred_idx = 0
        for list_idx, (_dev_idx, name) in enumerate(self.devices):
            if "usb audio device" in name.lower():
                preferred_idx = list_idx
                break
        self.device_combo.current(preferred_idx)
        default_index = self.devices[preferred_idx][0]
        self.after(300, lambda: self.start_stream(default_index))

    def on_device_selected(self, event):
        sel = self.device_var.get()
        try:
            dev_index = int(sel.split(":")[0])
        except ValueError:
            return
        self.start_stream(dev_index)

    def start_stream(self, device_index: int):
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
            window = np.hanning(self.BLOCK_SIZE)
            windowed = mono * window
            fft_vals = np.fft.rfft(windowed)
            mag = np.abs(fft_vals)
            spec = mag[self.freq_mask]
            spec_db = 20 * np.log10(spec + 1e-8)
            with self.data_lock:
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
            print(self._t("audio_stream_start_failed_fmt", "Error starting stream on device {device}: {e}").format(device=device_index, e=e))
            self.stream = None

    def _schedule_update_plot(self):
        self.update_plot()
        self.after(120, self._schedule_update_plot)

    def update_plot(self):
        with self.data_lock:
            fc = int(self.frame_count)
            wf = self.waterfall.copy()

        data_display = np.full((self.n_freq, self.MAX_FRAMES), np.nan, dtype=np.float32)
        if fc < self.MAX_FRAMES:
            n_frames = fc
            if n_frames > 0:
                data_display[:, -n_frames:] = wf[:, :n_frames]
        else:
            oldest_col = fc % self.MAX_FRAMES
            ordered = wf if oldest_col == 0 else np.concatenate([wf[:, oldest_col:], wf[:, :oldest_col]], axis=1)
            data_display[:, :] = ordered

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
            self._notch_line_lo = self.ax.axhline(0.0, color="red", linewidth=1, visible=False)
            self._notch_line_hi = self.ax.axhline(0.0, color="red", linewidth=1, visible=False)

        self.im.set_data(data_display)

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
        if event.inaxes != self.ax or event.ydata is None:
            return
        freq_clicked = float(event.ydata)
        if 0 <= freq_clicked <= self.MAX_FREQ and self.on_click_freq is not None:
            self.on_click_freq(freq_clicked)

    def refresh_plot(self):
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


class NotchControlsPanel(ttk.LabelFrame):
    """Manual notch controls plus FFT waterfall."""

    def __init__(self, parent, cat_getter, schedule_full_read, translate, display_text):
        super().__init__(parent, text=translate("frame_manual_notch_control", "Manual Notch Control"), padding=6)
        self._cat_getter = cat_getter
        self._schedule_full_read = schedule_full_read
        self._t = translate
        self.display_text = display_text

        self.notch_enabled_var = tk.BooleanVar(value=False)
        self.notch_freq_var = tk.StringVar(value="—")
        self.notch_freq_input_var = tk.StringVar(value="")

        self.waterfall_panel = None
        self._build_ui()

    def _build_ui(self):
        top_row = ttk.Frame(self)
        top_row.pack(fill="x")

        self.lbl_notch_hint = ttk.Label(top_row, text=self._t("hint_fft_click_notch", "Click spectrum to set notch"), foreground="#666666")
        self.lbl_notch_hint.pack(side="left", padx=(0, 12))

        self.chk_enable_notch = ttk.Checkbutton(top_row, text=self._t("chk_enable_notch", "Enable"), variable=self.notch_enabled_var, command=self.on_notch_toggle)
        self.chk_enable_notch.pack(side="left")

        self.lbl_notch_freq = ttk.Label(top_row, text=self._t("label_freq_hz", "Freq (Hz)"))
        self.lbl_notch_freq.pack(side="left", padx=(12, 2))
        notch_entry = ttk.Entry(top_row, textvariable=self.notch_freq_input_var, width=8)
        notch_entry.pack(side="left")
        notch_entry.bind("<Return>", lambda _e: self.on_set_notch_freq())

        self.lbl_notch_current = ttk.Label(top_row, text=self._t("label_current", "Current"))
        self.lbl_notch_current.pack(side="left", padx=(8, 2))
        ttk.Label(top_row, textvariable=self.notch_freq_var, width=10).pack(side="left")

        self.btn_set_notch = ttk.Button(top_row, text=self._t("btn_set", "Set"), command=self.on_set_notch_freq)
        self.btn_set_notch.pack(side="left", padx=4)
        self.btn_read_notch = ttk.Button(top_row, text=self._t("menu_read", "Read"), command=self.on_read_notch)
        self.btn_read_notch.pack(side="left", padx=2)

        self.waterfall_panel = MicWaterfallPanel(
            self,
            on_click_freq=self._apply_notch_freq,
            get_notch_state=self._get_notch_state_for_plot,
            translate=self._t,
        )
        self.waterfall_panel.pack(fill="both", expand=True, pady=(4, 0))

    def apply_language(self):
        self.configure(text=self._t("frame_manual_notch_control", "Manual Notch Control"))
        self.lbl_notch_hint.configure(text=self._t("hint_fft_click_notch", "Click spectrum to set notch"))
        self.chk_enable_notch.configure(text=self._t("chk_enable_notch", "Enable"))
        self.lbl_notch_freq.configure(text=self._t("label_freq_hz", "Freq (Hz)"))
        self.lbl_notch_current.configure(text=self._t("label_current", "Current"))
        self.btn_set_notch.configure(text=self._t("btn_set", "Set"))
        self.btn_read_notch.configure(text=self._t("menu_read", "Read"))
        if self.waterfall_panel is not None and hasattr(self.waterfall_panel, "lbl_input_device"):
            self.waterfall_panel.lbl_input_device.configure(text=self._t("label_input_device", "Input device"))

    def sync_full_read(self, notch_enabled=False, notch_freq_hz=None):
        try:
            self.notch_enabled_var.set(bool(notch_enabled))
        except Exception:
            pass
        if notch_freq_hz is None:
            self.notch_freq_var.set("—")
            self.notch_freq_input_var.set("")
        else:
            self.notch_freq_var.set(f"{int(notch_freq_hz)} Hz")
            self.notch_freq_input_var.set(str(int(notch_freq_hz)))
        self.refresh_overlay()

    def refresh_overlay(self):
        if self.waterfall_panel is not None:
            self.waterfall_panel.refresh_plot()

    def _get_notch_state_for_plot(self):
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

    def on_read_notch(self):
        cat = self._cat_getter()
        if not cat:
            return
        enabled, freq_hz, _ = cat.get_manual_notch(main=True)
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
            self.refresh_overlay()

    def on_set_notch_freq(self):
        text = (self.notch_freq_input_var.get() or "").strip()
        if not text:
            return
        try:
            f = float(text)
        except Exception:
            messagebox.showwarning(self._t("error_title", "Error"), self._t("notch_freq_must_number", "Notch frequency must be a number"))
            return
        self._apply_notch_freq(f)

    def on_notch_toggle(self):
        cat = self._cat_getter()
        if not cat:
            return
        enabled = self.notch_enabled_var.get()
        try:
            cat.set_manual_notch(main=True, enabled=enabled, freq_hz=None)
            self._schedule_full_read(delay_ms=1000)
            self.refresh_overlay()
        except Exception as e:
            messagebox.showerror(self._t("notch_set_failed", "Notch set failed"), str(e))
            self.on_read_notch()

    def _apply_notch_freq(self, freq_hz_float: float):
        cat = self._cat_getter()
        if not cat:
            return
        steps = int(round(freq_hz_float / 10.0))
        if steps < 1 or steps > 320:
            try:
                cat.set_manual_notch(main=True, enabled=False, freq_hz=None)
                self.notch_enabled_var.set(False)
                self.notch_freq_var.set("—")
                self.notch_freq_input_var.set("")
                self._schedule_full_read(delay_ms=1000)
                self.refresh_overlay()
            except Exception as e:
                messagebox.showerror(self._t("notch_set_failed", "Notch set failed"), str(e))
            return

        freq_hz = steps * 10
        try:
            cat.set_manual_notch(main=True, enabled=True, freq_hz=freq_hz)
            self.notch_enabled_var.set(True)
            self.notch_freq_var.set(f"{freq_hz} Hz")
            self.notch_freq_input_var.set(str(freq_hz))
        except Exception as e:
            messagebox.showerror(self._t("notch_set_failed", "Notch set failed"), str(e))
