import threading
import tkinter as tk
from tkinter import ttk, messagebox


class PttPowerPanel(ttk.LabelFrame):
    """RTS/PTT and power controls."""

    def __init__(self, parent, cat_getter, schedule_full_read, translate, display_text):
        super().__init__(parent, text=translate("frame_transmit_control"), padding=6)
        self._cat_getter = cat_getter
        self._schedule_full_read = schedule_full_read
        self._t = translate
        self.display_text = display_text

        self.rts_var = tk.BooleanVar(value=False)
        self.power_dev_var = tk.StringVar(value="—")
        self.power_value_var = tk.IntVar(value=1)
        self._power_range = (1, 10)
        self.transmit_btn = None
        self.power_scale = None
        self.power_value_label = None

        self._build_ui()

    def _build_ui(self):
        row_rts = ttk.Frame(self)
        row_rts.pack(fill="x", pady=2)
        self.transmit_btn = tk.Button(
            row_rts,
            text=self._t("btn_transmit", self.display_text.get("btn_transmit", "Transmit")),
            width=14,
            relief="ridge",
            command=self.on_toggle_rts,
        )
        self.transmit_btn.pack(anchor="center")
        self._update_transmit_button()

        row_power = ttk.Frame(self)
        row_power.pack(fill="x", pady=2)
        self.lbl_power = ttk.Label(row_power, text=self._t("label_power_w", "Power (W):"))
        self.lbl_power.pack(side="left")

        slider_frame = ttk.Frame(row_power)
        slider_frame.pack(side="left", padx=6)
        self.power_scale = ttk.Scale(
            slider_frame,
            orient="vertical",
            from_=self._power_range[1],
            to=self._power_range[0],
            length=160,
            command=self._on_power_slide,
        )
        self.power_scale.pack()
        self.power_scale.bind("<ButtonRelease-1>", self._on_slider_release)
        self.power_value_label = ttk.Label(slider_frame, textvariable=self.power_value_var, font=("Consolas", 10, "bold"))
        self.power_value_label.pack()
        ttk.Label(row_power, textvariable=self.power_dev_var, font=("Consolas", 10)).pack(side="left", padx=(8, 0))

    def apply_language(self):
        self.configure(text=self._t("frame_transmit_control"))
        self.display_text = self._t.__globals__.get("DISPLAY_TEXT", self.display_text)
        if self.transmit_btn is not None:
            self.transmit_btn.configure(text=self._t("btn_transmit", self.display_text.get("btn_transmit", "Transmit")))
        self.lbl_power.configure(text=self._t("label_power_w", "Power (W):"))

    def sync_full_read(self, rts=None, power_dev=None, power_watts=None):
        if rts is not None:
            self.rts_var.set(bool(rts))
            self._update_transmit_button()
        if power_dev is not None:
            self.power_dev_var.set(power_dev or "—")
            self._set_power_range(power_dev)
        if power_watts is not None:
            self._apply_power_value(int(power_watts))

    def on_toggle_rts(self):
        cat = self._cat_getter()
        if not cat:
            return
        new_state = not self.rts_var.get()
        try:
            cat.set_rts(new_state)
            self.rts_var.set(new_state)
            self._update_transmit_button()
            self._schedule_full_read(delay_ms=1000)
        except Exception as e:
            messagebox.showerror(self._t("rts_ptt_set_failed", "RTS PTT set failed"), str(e))
            try:
                read_back = cat.get_rts()
                self.rts_var.set(bool(read_back))
            except Exception:
                pass
            self._update_transmit_button()

    def _on_power_slide(self, value):
        try:
            v = int(round(float(value)))
        except Exception:
            return
        self.power_value_var.set(v)

    def _on_slider_release(self, _event=None):
        self._commit_power_from_slider()

    def _commit_power_from_slider(self):
        cat = self._cat_getter()
        if not cat:
            return
        watts = int(self.power_value_var.get())

        def worker():
            try:
                cat.set_power_watts(watts)
            except Exception as e:
                def show_err():
                    messagebox.showerror(self._t("power_set_failed", "Power set failed"), str(e))
                    self._schedule_full_read(delay_ms=200)
                try:
                    self.after(0, show_err)
                except Exception:
                    pass
                return

            # After setting, read back current power control to confirm and update UI
            try:
                dev, cur_w, raw = cat.get_power_control()
            except Exception:
                dev, cur_w, raw = None, None, None

            def apply_read():
                if dev is not None:
                    self.power_dev_var.set(dev or "—")
                if cur_w is not None:
                    try:
                        self._apply_power_value(int(cur_w))
                    except Exception:
                        pass
                # Still schedule a full read to refresh other panels
                self._schedule_full_read(delay_ms=1000)

            try:
                self.after(0, apply_read)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _apply_power_value(self, watts: int):
        min_w, max_w = self._power_range
        clamped = max(min_w, min(max_w, watts))
        self.power_value_var.set(clamped)
        if self.power_scale is not None:
            self.power_scale.set(clamped)

    def _set_power_range(self, device: str | None):
        if device == "FIELD":
            min_w, max_w = 1, 10
        elif device == "SPA1":
            min_w, max_w = 5, 100
        else:
            min_w, max_w = 1, 100
        self._power_range = (min_w, max_w)
        if self.power_scale is not None:
            self.power_scale.configure(from_=max_w, to=min_w)
            self._apply_power_value(self.power_value_var.get())

    def _update_transmit_button(self):
        if self.transmit_btn is None:
            return
        if self.rts_var.get():
            self.transmit_btn.configure(bg="#b22222", fg="#ffffff", activebackground="#ff4d4d", activeforeground="#ffffff")
        else:
            self.transmit_btn.configure(bg="#ffffff", fg="#000000", activebackground="#e0e0e0", activeforeground="#000000")
