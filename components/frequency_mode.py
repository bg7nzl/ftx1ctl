import threading
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont

from ftx1cat import P2_TO_MODE


class FrequencyModePanel(ttk.LabelFrame):
    """Frequency and mode controls."""

    def __init__(self, parent, cat_getter, schedule_full_read, translate, display_text):
        super().__init__(parent, text=translate("frame_frequency_mode"), padding=6)
        self._cat_getter = cat_getter
        self._schedule_full_read = schedule_full_read
        self._t = translate
        self.display_text = display_text

        self.digits = [0] * 9
        self._digit_cells = []
        self._freq_op_seq = 0
        self.current_freq_hz = 0

        self.mode_var = tk.StringVar()
        self.mode_buttons: dict[str, tk.Button] = {}

        self._build_ui()

    def _build_ui(self):
        row1 = ttk.Frame(self)
        row1.pack(fill="x", pady=4)

        self.lbl_freq_static = ttk.Label(row1, text=self._t("label_freq_static"))
        self.lbl_freq_static.pack(side="left", padx=(0, 6))

        digits_frame = ttk.Frame(row1)
        digits_frame.pack(side="left")

        self._build_digit_cells(digits_frame)

        ttk.Label(row1, text="MHz", foreground="#00a0a0").pack(side="left", padx=(6, 0))

        # Frequency is updated automatically; no explicit read button here.

        row2 = ttk.Frame(self)
        row2.pack(fill="x", pady=2)
        self.lbl_mode_static = ttk.Label(row2, text=self._t("label_mode_static"))
        self.lbl_mode_static.pack(side="left", padx=(0, 6))

        modes_frame = ttk.Frame(row2)
        modes_frame.pack(side="left", padx=2, pady=2)
        self._modes_frame = modes_frame

        # Desired explicit ordering (left->right):
        # Row 0: USB DATA-U CW-U RTTY-U AM FM FM-N C4FM-DN PSK
        # Row 1: LSB DATA-L CW-L RTTY-L AM-N DATA-FM DATA-FM-N C4FM-VW <blank>
        modes_row1 = [
            "USB", "DATA-U", "CW-U", "RTTY-U", "AM", "FM", "FM-N", "C4FM-DN", "PSK",
        ]
        modes_row2 = [
            "LSB", "DATA-L", "CW-L", "RTTY-L", "AM-N", "DATA-FM", "DATA-FM-N", "C4FM-VW", "",
        ]

        cols = max(len(modes_row1), len(modes_row2))
        for col in range(cols):
            m1 = modes_row1[col] if col < len(modes_row1) else ""
            m2 = modes_row2[col] if col < len(modes_row2) else ""

            # Top row
            if m1:
                btn = tk.Button(
                    modes_frame,
                    text=m1,
                    width=8,
                    relief="ridge",
                    bd=1,
                    command=lambda m=m1: self.on_set_mode(m),
                    bg="#ffffff",
                    fg="#000000",
                    activebackground="#d0ffd0",
                )
                btn.grid(row=0, column=col, padx=2, pady=2, sticky="nsew")
                self._fit_mode_font(btn, m1)
                self.mode_buttons[m1] = btn
            else:
                ttk.Label(modes_frame, text="", width=8).grid(row=0, column=col, padx=2, pady=2)

            # Bottom row
            if m2:
                btn2 = tk.Button(
                    modes_frame,
                    text=m2,
                    width=8,
                    relief="ridge",
                    bd=1,
                    command=lambda m=m2: self.on_set_mode(m),
                    bg="#ffffff",
                    fg="#000000",
                    activebackground="#d0ffd0",
                )
                btn2.grid(row=1, column=col, padx=2, pady=2, sticky="nsew")
                self._fit_mode_font(btn2, m2)
                self.mode_buttons[m2] = btn2
            else:
                ttk.Label(modes_frame, text="", width=8).grid(row=1, column=col, padx=2, pady=2)

        # Re-fit fonts when the modes frame is resized / configured
        self._modes_frame.bind("<Configure>", lambda e: self._fit_all_mode_fonts())
        self.after_idle(self._fit_all_mode_fonts)

    def apply_language(self):
        self.configure(text=self._t("frame_frequency_mode"))
        self.lbl_freq_static.configure(text=self._t("label_freq_static"))
        self.lbl_mode_static.configure(text=self._t("label_mode_static"))
        self.display_text = self._t.__globals__.get("DISPLAY_TEXT", self.display_text)
        # Mode buttons' labels may need updating for localization; re-set texts and re-fit fonts
        for mode, btn in self.mode_buttons.items():
            btn.configure(text=mode)
        self.after_idle(self._fit_all_mode_fonts)

    def sync_full_read(self, freq_hz=None, mode_name=None):
        if freq_hz is not None:
            self._set_digits_from_freq(freq_hz)
        if mode_name:
            try:
                self.mode_var.set(mode_name)
                self._highlight_mode(mode_name)
            except Exception:
                pass

    def on_read_freq(self):
        cat = self._cat_getter()
        if not cat:
            return
        freq_hz, _ = cat.get_freq()
        if freq_hz is None:
            messagebox.showerror(self._t("read_failed", "Read failed"), self._t("freq_parse_failed", "Cannot parse frequency"))
            return
        self._set_digits_from_freq(freq_hz)

    def on_read_mode(self):
        cat = self._cat_getter()
        if not cat:
            return
        mode_name, _ = cat.get_mode(main=True)
        if mode_name is None:
            messagebox.showerror(self._t("read_failed", "Read failed"), self._t("illegal_mode_code", "Illegal mode code"))
            return
        self.mode_var.set(mode_name)
        self._highlight_mode(mode_name)

    def on_set_mode(self, mode_name=None):
        cat = self._cat_getter()
        if not cat:
            return
        if mode_name is None:
            mode_name = self.mode_var.get().strip().upper()
        else:
            mode_name = (mode_name or "").strip().upper()
            self.mode_var.set(mode_name)
        if not mode_name:
            return
        try:
            cat.set_mode(mode_name, main=True)
            self._schedule_full_read(delay_ms=1000)
            self._highlight_mode(mode_name)
        except Exception as e:
            messagebox.showerror(self._t("set_failed", "Set failed"), str(e))

    def _highlight_mode(self, active_mode: str | None):
        active = (active_mode or "").strip().upper()
        for mode, btn in self.mode_buttons.items():
            if active and mode.upper() == active:
                btn.configure(bg="#006400", fg="#ffffff", activebackground="#008040", activeforeground="#ffffff")
            else:
                btn.configure(bg="#ffffff", fg="#000000", activebackground="#e0e0e0", activeforeground="#000000")

    def _fit_mode_font(self, btn: tk.Button, text: str, target_px: int = 72, min_size: int = 8):
        def do_fit():
            try:
                avail_w = btn.winfo_width()
                if avail_w <= 1:
                    # Not yet mapped; try again soon
                    btn.after(50, do_fit)
                    return
                # small padding allowance
                avail = max(8, avail_w - 8)
                f = tkfont.Font(font=btn.cget("font"))
                size = int(f.cget("size") or 10)
                # Reduce size until text fits within available pixel width
                while size > min_size and f.measure(text) > avail:
                    size -= 1
                    f.configure(size=size)
                btn.configure(font=f)
            except Exception:
                pass

        btn.after_idle(do_fit)

    def _fit_all_mode_fonts(self, event=None):
        for mode, btn in self.mode_buttons.items():
            self._fit_mode_font(btn, mode)

    # ---------- Digit UI ----------
    def _build_digit_cells(self, parent):
        font_digit = ("Consolas", 24, "bold")
        for idx in range(9):
            cell = self._DigitCell(parent, idx, font_digit, self._on_digit_step)
            cell.pack(side="left", padx=1)
            self._digit_cells.append(cell)
            if idx == 2:
                ttk.Label(parent, text=".", font=("Consolas", 22, "bold"), foreground="#00c0c0").pack(side="left", padx=(2, 2))
        self._set_digits_from_freq(30000)

    def _on_digit_step(self, idx: int, direction: int):
        new_digits = list(self.digits)
        if not self._step_digits(new_digits, idx, direction):
            return
        freq_hz = int("".join(str(d) for d in new_digits))
        freq_hz = self._normalize_range(freq_hz, direction)
        self._send_and_confirm_freq(freq_hz, idx, direction)

    def _set_digits_from_freq(self, freq_hz: int):
        try:
            freq_int = max(0, int(freq_hz))
        except Exception:
            return
        freq_int = self._normalize_range(freq_int, 0)
        s = f"{freq_int:09d}"[-9:]
        self.digits = [int(ch) for ch in s]
        for d, cell in zip(self.digits, self._digit_cells):
            cell.set_digit(d)
        self.current_freq_hz = freq_int

    def _step_digits(self, digits, idx, direction):
        if direction > 0:
            carry_idx = idx
            while carry_idx >= 0:
                if digits[carry_idx] < 9:
                    digits[carry_idx] += 1
                    break
                digits[carry_idx] = 0
                carry_idx -= 1
            else:
                return False
        else:
            if all(d == 0 for d in digits):
                return False
            borrow_idx = idx
            while borrow_idx >= 0:
                if digits[borrow_idx] > 0:
                    digits[borrow_idx] -= 1
                    break
                digits[borrow_idx] = 9
                borrow_idx -= 1
            else:
                return False
            if int("".join(str(d) for d in digits)) < 0:
                return False
        return True

    @staticmethod
    def _normalize_range(freq_hz: int, direction: int) -> int:
        MIN_F = 30_000
        MAX_F = 470_000_000
        BAND_SPLIT_LOW = 174_000_000
        BAND_SPLIT_HIGH = 400_000_000

        f = max(MIN_F, min(MAX_F, int(freq_hz)))
        if direction != 0 and BAND_SPLIT_LOW < f < BAND_SPLIT_HIGH:
            if direction >= 0:
                f = BAND_SPLIT_HIGH
            else:
                f = BAND_SPLIT_LOW
        return f

    def _send_and_confirm_freq(self, target_hz: int, op_idx: int | None = None, op_dir: int = 0):
        cat = self._cat_getter()
        if not cat:
            return
        self._freq_op_seq += 1
        token = self._freq_op_seq

        def worker():
            err = None
            read_back = None
            try:
                cat.set_freq(target_hz)
            except Exception as e:
                err = e
            try:
                read_back, _ = cat.get_freq()
            except Exception:
                pass

            def apply():
                if token != self._freq_op_seq:
                    return
                if err is not None:
                    messagebox.showerror(self._t("set_failed", "Set failed"), str(err))
                    return
                if read_back is not None:
                    # Flash the operated digit's half to indicate success
                    try:
                        if op_idx is not None and 0 <= op_idx < len(self._digit_cells):
                            self._digit_cells[op_idx].flash_half(op_dir)
                    except Exception:
                        pass
                    self._set_digits_from_freq(read_back)
                    return
            try:
                self.after(0, apply)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    class _DigitCell(ttk.Frame):
        def __init__(self, parent, idx, font_digit, on_step):
            super().__init__(parent, padding=0)
            self.idx = idx
            self.on_step = on_step
            self.up_btn = tk.Label(self, text="▲", font=("Consolas", 10, "bold"), fg="#50ff50", bg="#101010")
            self.up_btn.pack(fill="x")
            self.lbl = tk.Label(self, text="0", font=font_digit, width=2, anchor="center", bg="#101010", fg="#00ff80")
            self.lbl.pack(fill="both", expand=True)
            self.down_btn = tk.Label(self, text="▼", font=("Consolas", 10, "bold"), fg="#50ff50", bg="#101010")
            self.down_btn.pack(fill="x")

            self.up_btn.bind("<Button-1>", lambda _e: self.on_step(self.idx, 1))
            self.down_btn.bind("<Button-1>", lambda _e: self.on_step(self.idx, -1))
            for widget in (self.lbl, self):
                widget.bind("<Button-1>", self._on_click)
                widget.bind("<MouseWheel>", self._on_scroll)

            self._overlay = None

        def flash_half(self, direction: int, ms: int = 180):
            """Show a quick half-overlay on top (direction>0) or bottom (direction<0) to indicate success."""
            try:
                if self._overlay is not None:
                    try:
                        self._overlay.destroy()
                    except Exception:
                        pass
                    self._overlay = None

                # Use a plain Label as overlay; true alpha isn't available in tkinter, so pick a dim gray
                ov = tk.Label(self, bg="#666666", bd=0)
                # place on upper or lower half
                if direction >= 0:
                    ov.place(relx=0, rely=0, relwidth=1.0, relheight=0.5)
                else:
                    ov.place(relx=0, rely=0.5, relwidth=1.0, relheight=0.5)
                ov.lift(aboveThis=self.lbl)
                self._overlay = ov

                def _clear():
                    try:
                        if self._overlay is not None:
                            self._overlay.destroy()
                    except Exception:
                        pass
                    self._overlay = None

                # remove after ms milliseconds
                self.after(ms, _clear)
            except Exception:
                pass

        def set_digit(self, d):
            self.lbl.configure(text=str(int(d) % 10))

        def _on_click(self, event):
            try:
                h = self.lbl.winfo_height() or 1
                direction = 1 if event.y < h / 2 else -1
            except Exception:
                direction = 1
            self.on_step(self.idx, direction)

        def _on_scroll(self, event):
            direction = 1 if event.delta > 0 else -1
            self.on_step(self.idx, direction)
