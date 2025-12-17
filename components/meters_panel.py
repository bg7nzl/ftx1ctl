import math
import tkinter as tk
from tkinter import ttk

from ftx1cat import convert_meter_value, METER_CONVERT, s_meter_text_from_raw


class MeterHeader(ttk.Frame):
    def __init__(self, parent, meter_name: str, meter_id: int, use_convert: bool):
        super().__init__(parent, padding=4)
        self.meter_name = meter_name
        self.meter_id = meter_id
        self.use_convert = use_convert

        self.label_title = ttk.Label(self, text=meter_name, font=("Segoe UI", 11, "bold"))
        self.label_title.pack()

        self.bar_canvas = tk.Canvas(self, width=80, height=12, bg="#202020", highlightthickness=0)
        self.bar_canvas.pack(pady=(2, 0))
        self.bar_canvas.create_rectangle(0, 0, 80, 12, fill="#404040", outline="")
        self.bar_id = self.bar_canvas.create_rectangle(0, 0, 0, 12, fill="#00ff00", outline="")

        threshold_raw = 128
        self.threshold_x = int(80 * threshold_raw / 255.0)
        self.threshold_id = self.bar_canvas.create_line(self.threshold_x, 0, self.threshold_x, 12, fill="red", width=1)

        self.tick_frame = ttk.Frame(self)
        self.tick_frame.pack(pady=(2, 2))
        ticks = self._calc_ticks()
        self.tick_labels = []
        for t in ticks:
            lbl = ttk.Label(self.tick_frame, text=t, font=("Consolas", 9))
            lbl.pack(side="left", padx=4)
            self.tick_labels.append(lbl)

        self.value_var = tk.StringVar(value="—")
        self.label_value = ttk.Label(self, textvariable=self.value_var, font=("Consolas", 11, "bold"), foreground="#00d000")
        self.label_value.pack(pady=(2, 0))

    def _calc_ticks(self):
        if self.meter_id in (1, 2):
            ticks = []
            for raw in (0, 128, 255):
                t = s_meter_text_from_raw(raw)
                if t.startswith("+"):
                    t = t.replace("dB", "").replace(".0", "")
                ticks.append(t)
            return ticks

        if self.meter_id == 3:
            return ["0dB", "+15dB", "+30dB"]
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
                if abs(val) >= 10:
                    s = f"{val:.1f}"
                else:
                    s = f"{val:.2f}"
                ticks.append(s)
        return ticks

    def set_threshold(self, value=None, raw=None):
        if raw is not None:
            try:
                r = float(raw)
            except Exception:
                r = 0.0
            r = max(0.0, min(255.0, r))
            self.threshold_x = int(80 * r / 255.0)
            self.bar_canvas.coords(self.threshold_id, self.threshold_x, 0, self.threshold_x, 12)
            return

        if value is None:
            return

        fn = METER_CONVERT.get(self.meter_id)
        if fn is None:
            v = max(0.0, min(1.0, float(value)))
            self.threshold_x = int(80 * v)
            self.bar_canvas.coords(self.threshold_id, self.threshold_x, 0, self.threshold_x, 12)
            return

        target = float(value)
        best_raw = 0
        best_err = float("inf")
        for r in range(256):
            v = fn(r)
            if math.isinf(v):
                continue
            err = abs(v - target)
            if err < best_err:
                best_err = err
                best_raw = r

        best_raw = max(0.0, min(255.0, float(best_raw)))
        self.threshold_x = int(80 * best_raw / 255.0)
        self.bar_canvas.coords(self.threshold_id, self.threshold_x, 0, self.threshold_x, 12)

    def update_value(self, raw, value):
        if raw is None or value is None:
            self.value_var.set("—")
            self.bar_canvas.coords(self.bar_id, 0, 0, 0, 12)
            return

        if math.isinf(value):
            self.value_var.set("∞")
            self.bar_canvas.coords(self.bar_id, 0, 0, 80, 12)
            return

        if self.meter_id in (1, 2):
            self.value_var.set(s_meter_text_from_raw(int(raw)))
        elif self.meter_id == 3:
            self.value_var.set(f"+{value:.0f}dB")
        elif self.meter_id == 4:
            self.value_var.set(f"{value:.0f}%")
        elif self.meter_id == 5:
            self.value_var.set(f"{value:.1f}W")
        elif self.meter_id == 7:
            self.value_var.set(f"{value:.2f}A")
        elif self.meter_id == 8:
            self.value_var.set(f"{value:.1f}V")
        else:
            if abs(value) >= 10:
                self.value_var.set(f"{value:.1f}")
            else:
                self.value_var.set(f"{value:.2f}")

        try:
            r = float(raw)
        except (TypeError, ValueError):
            r = 0.0
        r = max(0.0, min(255.0, r))
        frac = r / 255.0
        bar_len = int(80 * frac)
        self.bar_canvas.coords(self.bar_id, 0, 0, bar_len, 12)


class MetersPanel(ttk.LabelFrame):
    def __init__(self, parent, translate):
        super().__init__(parent, text=translate("frame_meters"), padding=6)
        self._t = translate
        self.meter_widgets: dict[str, MeterHeader] = {}
        self._build_ui()

    def _build_ui(self):
        layout_meters = [
            ("S_MAIN", 1, True, True, 128),
            ("COMP", 3, True, False, 15),
            ("ALC", 4, True, False, 100),
            ("PO", 5, True, False, 10),
            ("SWR", 6, True, False, 3),
            ("IDD", 7, True, False, 2),
            ("VDD", 8, True, False, 13.8),
        ]

        row = ttk.Frame(self)
        row.pack()
        for name, mid, use_conv, raw_tr, tr in layout_meters:
            w = MeterHeader(row, name, mid, use_conv)
            w.pack(side="left", padx=6)
            self.meter_widgets[name] = w
            if raw_tr:
                w.set_threshold(raw=tr)
            else:
                w.set_threshold(value=tr)

    def apply_language(self):
        self.configure(text=self._t("frame_meters"))

    def update_meters(self, data):
        if data is None:
            self.clear()
            return
        for name, widget in self.meter_widgets.items():
            info = data.get(name) if isinstance(data, dict) else None
            if not info:
                widget.update_value(None, None)
                continue
            raw = info.get("raw")
            value = info.get("value")
            widget.update_value(raw, value)

    def clear(self):
        for _, widget in self.meter_widgets.items():
            widget.update_value(None, None)
