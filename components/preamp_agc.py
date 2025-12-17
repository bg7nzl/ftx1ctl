import tkinter as tk
from tkinter import ttk, messagebox


class PreampAgcPanel(ttk.LabelFrame):
    """Preamp controls plus AGC using a button-driven interface."""

    def __init__(self, parent, cat_getter, schedule_full_read, translate, display_text):
        super().__init__(parent, text=translate("frame_receive_preprocessing"), padding=6)
        self._cat_getter = cat_getter
        self._schedule_full_read = schedule_full_read
        self._t = translate
        self.display_text = display_text

        self.agc_var = tk.StringVar(value="")
        self._auto_variant: str | None = None

        self.preamp_vars: dict[str, tk.StringVar] = {}
        self.preamp_buttons: dict[str, dict[str, tk.Button]] = {}
        self.agc_buttons: dict[str, tk.Button] = {}
        self._column_labels: dict[str, tuple[ttk.Label, str]] = {}

        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        columns = ttk.Frame(self)
        columns.pack(fill="x", pady=2)
        agc_values = ["OFF", "FAST", "MID", "SLOW", "AUTO"]
        agc_label, agc_buttons = self._build_option_column(columns, "label_agc", "AGC", agc_values, self.on_select_agc)
        self._column_labels["label_agc"] = (agc_label, "AGC")
        self.agc_buttons = agc_buttons
        self._build_preamp_column(columns, "HF50", ["IPO", "AMP1", "AMP2"])
        self._build_preamp_column(columns, "VHF", ["OFF", "ON"])
        self._build_preamp_column(columns, "UHF", ["OFF", "ON"])

    def _build_preamp_column(self, parent, band_name, choices):
        label, buttons = self._build_option_column(parent, band_name, band_name, choices, lambda choice, b=band_name: self.on_select_preamp(b, choice))
        self._column_labels[band_name] = (label, band_name)
        var = tk.StringVar()
        self.preamp_vars[band_name] = var
        self.preamp_buttons[band_name] = buttons

    # ---------- Language ----------
    def apply_language(self):
        self.configure(text=self._t("frame_receive_preprocessing"))
        self.display_text = self._t.__globals__.get("DISPLAY_TEXT", self.display_text)
        for key, (label, fallback) in self._column_labels.items():
            label.configure(text=self._t(key, fallback))

    # ---------- Sync ----------
    def sync_full_read(self, preamp=None, agc_name=None):
        preamp = preamp or {}
        for band, var in self.preamp_vars.items():
            val = preamp.get(band)
            if val:
                try:
                    var.set(val)
                except Exception:
                    pass
            self._highlight_preamp(band, val)
        self._apply_agc_state(agc_name)

    def get_preamp_bands(self):
        return list(self.preamp_vars.keys())

    # ---------- Actions ----------
    def on_read_agc(self):
        cat = self._cat_getter()
        if not cat:
            return
        try:
            agc_name, _ = cat.get_agc(main=True)
        except Exception as e:
            messagebox.showerror(self._t("read_failed", "Read failed"), self._t("agc_read_failed_fmt", "AGC read failed: {e}").format(e=e))
            return
        self._apply_agc_state(agc_name)

    def on_select_agc(self, agc_choice):
        cat = self._cat_getter()
        if not cat:
            return
        name = (agc_choice or "").strip().upper()
        if not name:
            return
        try:
            cat.set_agc(name, main=True)
            self.agc_var.set(name)
            self._auto_variant = None
            self._highlight_agc(name, self._auto_variant)
            self._schedule_full_read(delay_ms=1000)
        except Exception as e:
            messagebox.showerror(self._t("agc_set_failed", "AGC set failed"), str(e))
            self.on_read_agc()

    def on_select_preamp(self, band, level):
        cat = self._cat_getter()
        if not cat:
            return
        try:
            cat.set_preamp(band, level)
            self.preamp_vars[band].set(level)
            self._highlight_preamp(band, level)
            self._schedule_full_read(delay_ms=1000)
        except Exception as e:
            messagebox.showerror(self.display_text.get("preamp_set_failed", "Preamp set failed"), str(e))

    def _apply_agc_state(self, agc_name):
        if not agc_name:
            self.agc_var.set("")
            self._auto_variant = None
            self._highlight_agc(None, None)
            return
        text = str(agc_name).strip()
        normalized = text.upper()
        if normalized.startswith("AUTO-"):
            variant = normalized.split("-", 1)[1]
            self.agc_var.set("AUTO")
            self._auto_variant = variant
            self._highlight_agc("AUTO", variant)
        else:
            self.agc_var.set(normalized)
            self._auto_variant = None
            self._highlight_agc(normalized, None)

    def _highlight_agc(self, active, auto_variant):
        active = (active or "").strip().upper()
        auto_variant = (auto_variant or "").strip().upper()
        for option, btn in self.agc_buttons.items():
            key = option.upper()
            should_highlight = False
            if active and key == active:
                should_highlight = True
            if auto_variant and key == auto_variant:
                should_highlight = True
            self._style_button(btn, should_highlight)

    def _highlight_preamp(self, band, current):
        buttons = self.preamp_buttons.get(band, {})
        target = (current or "").strip().upper()
        for option, btn in buttons.items():
            is_active = bool(target and option.upper() == target)
            self._style_button(btn, is_active)

    def _build_option_column(self, parent, text_key, fallback, choices, command):
        frame = ttk.Frame(parent)
        frame.pack(side="left", padx=6, anchor="n")
        label = ttk.Label(frame, text=self._t(text_key, fallback))
        label.pack()
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=4)
        buttons: dict[str, tk.Button] = {}
        for choice in choices:
            btn = tk.Button(
                btn_frame,
                text=choice,
                width=8,
                relief="ridge",
                bd=1,
                command=lambda c=choice: command(c),
                bg="#ffffff",
                fg="#000000",
                activebackground="#f0f0f0",
            )
            btn.pack(side="top", pady=2, fill="x")
            buttons[choice] = btn
        return label, buttons

    def _style_button(self, button, active):
        try:
            if active:
                button.configure(bg="#ffeb4a", fg="#000000", activebackground="#ffd900", activeforeground="#000000")
            else:
                button.configure(bg="#ffffff", fg="#000000", activebackground="#f0f0f0", activeforeground="#000000")
        except Exception:
            pass
