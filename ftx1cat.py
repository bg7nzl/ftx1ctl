import time
import math
import threading
from typing import Optional, Dict, Tuple

import serial

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from i18n import I18N_TEXT as I18N_TEXT

DISPLAY_TEXT = I18N_TEXT["en"]


# ==========================
# 串口 & CAT 封装为类
# ==========================

METER_MAP = {
    1: "S_MAIN",
    2: "S_SUB",
    3: "COMP",
    4: "ALC",
    5: "PO",
    6: "SWR",
    7: "IDD",
    8: "VDD",
}

import math



def swr_from_meter(rm):
    C = 0.333
    B = 0.0151
    if rm >= 255:
        return float('inf')
    if rm <= 0:
        return 1.0
    return 1.0 + C * (math.exp(B * rm) - 1.0)
    
def vdd_from_meter(rm):
    scale = 13.8 / 203.0
    return rm * scale
    
def idd_from_meter(rm):
    scale = 3 / 255.0
    return rm * scale   
    


def comp_db_from_meter(rm):
    """Speech compressor meter: linear 0..+30 dB."""
    scale = 30.0 / 255.0
    return rm * scale
def alc_from_meter(rm):
    """ALC meter as percentage: 0..200%."""
    # Historically this was ~0..2.0; we now express it as 0..200%.
    scale = 200.0 / 252.0
    v = rm * scale
    return 200.0 if v > 200.0 else v

def po_from_meter(x: float) -> float:
    points = [
        (55.0, 0.5),
        (73.0, 1.0),
        (113.0, 3.0),
        (139.0, 5.0),
        (164.0, 7.5),
        (189.0, 10.0),
        (255.0, 15.0),
    ]

    if x <= 0:
        return 0.0

    if x <= points[0][0]:
        x1, y1 = 0.0, 0.0
        x2, y2 = points[0]
        return y1 + (y2 - y1) * (x - x1) / (x2 - x1)

    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        if x <= x2:
            return y1 + (y2 - y1) * (x - x1) / (x2 - x1)

    return points[-1][1]



# ==========================
# S-meter 非线性映射 (FTX-1)
# - raw=0   -> S0
# - raw=128 -> S9
# - raw=255 -> +60dB
#
# 说明：
# 1) s_meter_from_raw() 返回 float，便于 UI 直接判断：
#       <10  : 显示 S（取值仅为 0/1/3/5/7/9）
#       >=10 : 显示 dB（10~60，可为小数）
#    且 +10dB 以下一律按 9 处理（用于“仍显示 S9”）。
# 2) s_meter_text_from_raw() 保留字符串输出（暂不启用，隐藏备用）。
# ==========================

# 这些断点是依据表盘刻线做的近似标定，
# 并满足 raw=128 为 S9、raw=255 为 +60dB 的硬约束。
_S_RAW_S1  = 14
_S_RAW_S3  = 42
_S_RAW_S5  = 81
_S_RAW_S7  = 103
_S_RAW_S9  = 128
_S_RAW_P20 = 202
_S_RAW_P40 = 233
_S_RAW_P60 = 255

# +10dB 在 S9(0dB) 与 +20dB 中点处（按刻线弧长近似线性）
_S_RAW_P10 = int(round(_S_RAW_S9 + (_S_RAW_P20 - _S_RAW_S9) * (10.0 / 20.0)))  # ~=165


def _piecewise_lerp(x: float, points: list[tuple[float, float]]) -> float:
    """一维分段线性插值，points 按 x 递增。"""
    if not points:
        return 0.0
    if x <= points[0][0]:
        x1, y1 = points[0]
        x0, y0 = 0.0, 0.0
        if x1 == x0:
            return y1
        return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x <= x1:
            if x1 == x0:
                return y1
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

    return points[-1][1]


def s_meter_from_raw(raw: int) -> float:
    """
    返回 float:
      - S 区只返回 0/1/3/5/7/9（整数，但用 float 承载）
      - +10dB 以下按 9.0
      - +10dB 及以上返回 dB（10~60，可为小数）
    """
    r = 0 if raw < 0 else 255 if raw > 255 else int(raw)

    # S9 以下：按刻线区间“阶梯”输出（只输出 0/1/3/5/7/9）
    if r < _S_RAW_S1:
        return 0.0
    if r < _S_RAW_S3:
        return 1.0
    if r < _S_RAW_S5:
        return 3.0
    if r < _S_RAW_S7:
        return 5.0
    if r < _S_RAW_S9:
        return 7.0

    # S9 ~ +10dB：仍按 S9
    if r < _S_RAW_P10:
        return 9.0

    # +10dB 及以上：分段线性插值返回 dB（10~60）
    db = _piecewise_lerp(
        r,
        [
            (_S_RAW_S9, 0.0),
            (_S_RAW_P20, 20.0),
            (_S_RAW_P40, 40.0),
            (_S_RAW_P60, 60.0),
        ],
    )
    # 保险：避免 +10dB 附近插值返回 <10
    if db < 10.0:
        return 9.0
    return float(db)


def s_meter_text_from_raw(raw: int) -> str:
    """字符串输出（隐藏备用）：Sx 或 +XdB。"""
    v = s_meter_from_raw(raw)
    if v < 10.0:
        # S 区：只会是 0/1/3/5/7/9
        return f"S{int(v)}"
    # dB 区
    # 保留 1 位小数（如不需要可改为 round(v)）
    return f"+{v:.1f}dB"


METER_CONVERT = {
    1: s_meter_from_raw,   # S_MAIN (float: <10 => S, >=10 => dB)
    2: s_meter_from_raw,   # S_SUB  (float: <10 => S, >=10 => dB)
    3: comp_db_from_meter, # COMP (dB, linear 0..30)
    4: alc_from_meter,     # ALC (%) 0..200
    5: po_from_meter,      # PO (W)
    6: swr_from_meter,     # SWR
    7: idd_from_meter,     # IDD (A)
    8: vdd_from_meter,     # VDD (V)
}

def convert_meter_value(meter_id: int, raw: int) -> float:
    fn = METER_CONVERT.get(meter_id)
    if fn is None:
        return raw
    return fn(raw)


# 模式映射表：CAT字符 <-> 模式名
P2_TO_MODE = {
    "1": "LSB",
    "2": "USB",
    "3": "CW-U",
    "4": "FM",
    "5": "AM",
    "6": "RTTY-L",
    "7": "CW-L",
    "8": "DATA-L",
    "9": "RTTY-U",
    "A": "DATA-FM",
    "B": "FM-N",
    "C": "DATA-U",
    "D": "AM-N",
    "E": "PSK",
    "F": "DATA-FM-N",
    "H": "C4FM-DN",
    "I": "C4FM-VW",
}
MODE_TO_P2 = {v: k for k, v in P2_TO_MODE.items()}


# AGC 映射表：CAT 数字 <-> 选项名
# 参考 CAT 手册 GT 命令：Set 用 P2，Read/Answer 用 P3
# - Set(P2): 0 OFF, 1 FAST, 2 MID, 3 SLOW, 4 AUTO
# - Answer(P3): 0 OFF, 1 FAST, 2 MID, 3 SLOW, 4 AUTO-FAST, 5 AUTO-MID, 6 AUTO-SLOW
AGC_SET_TO_P2 = {
    "OFF": "0",
    "FAST": "1",
    "MID": "2",
    "SLOW": "3",
    "AUTO": "4",
}

AGC_P3_TO_NAME = {
    "0": "OFF",
    "1": "FAST",
    "2": "MID",
    "3": "SLOW",
    "4": "AUTO-FAST",
    "5": "AUTO-MID",
    "6": "AUTO-SLOW",
}
AGC_NAME_TO_P2 = AGC_SET_TO_P2  # 别名，便于调用方理解


BAND_TO_P1 = {
    "HF50": "0",      # HF/50MHz 共用
    "HF/50": "0",
    "HF": "0",
    "VHF": "1",
    "UHF": "2",
}

P1_TO_BAND_CANON = {
    "0": "HF50",
    "1": "VHF",
    "2": "UHF",
}

HF50_PREAMP_TO_P2 = {
    "IPO": "0",
    "AMP1": "1",
    "AMP2": "2",
}

HF50_P2_TO_PREAMP = {v: k for k, v in HF50_PREAMP_TO_P2.items()}

VU_PREAMP_TO_P2 = {
    "OFF": "0",
    "ON": "1",
}

VU_P2_TO_PREAMP = {v: k for k, v in VU_PREAMP_TO_P2.items()}

class FTX1Cat:
    """
    FTX-1 CAT 封装，内部带 RLock，保证整个一次操作是串行的。

    所有对串口的访问都必须通过 public 方法，这些方法都会:
    - with self._lock:   # 严格串行化
    - 使用同一个 serial.Serial 对象
    """

    def __init__(self, port: str = "COM11", baudrate: int = 38400, port2: str = "COM12", baudrate2: int = 38400, timeout: float = 1.0):
        self._port = port
        self._baudrate = baudrate
        self._port2 = port2
        self._baudrate2 = baudrate2
        self._timeout = timeout

        # 使用 RLock，方便方法内部再调用其他需要锁的方法
        self._lock = threading.RLock()

        self._ser = serial.Serial(
            port=self._port,
            baudrate=self._baudrate,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=self._timeout,
        )
        self._ser2 = serial.Serial(
            port=self._port2,
            baudrate=self._baudrate2,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=self._timeout,
            rtscts=False,
            dsrdtr=False,
        )
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()
        self._ser2.rts = False

    # ---------- 基础方法 ----------

    def close(self):
        with self._lock:
            if self._ser and self._ser.is_open:
                self._ser.close()
            if self._ser2 and self._ser2.is_open:
                self._ser2.close()

    def _send_cat(self, cmd: str) -> str:
        """
        低层 CAT 发送/接收，内部自己持锁；
        所有 CAT 调用都应该通过本函数间接完成，确保串口串行访问。
        """
        with self._lock:
            if not cmd.endswith(";"):
                cmd = cmd + ";"

            # 清一下缓冲，避免旧数据干扰
            self._ser.reset_input_buffer()

            self._ser.write(cmd.encode("ascii"))
            # 稍微等一下，避免读空
            time.sleep(0.002)
            resp = self._ser.read_until(b";")
            return resp.decode(errors="ignore")

    # ---------- TX ----------

    def set_rts(self, on: bool) -> None:
        self._ser2.rts = bool(on)

    def get_rts(self) -> bool:
        return bool(self._ser2.rts)

    # ---------- MOX ----------

    def set_mox(self, on: bool) -> str:
        """
        设置 MOX ON/OFF
        MX 命令：MOX SET
          P1=0: OFF
          P1=1: ON
        """
        
        p1 = "1" if on else "0"
        resp = self._send_cat(f"MX{p1}")
        return resp

    def get_mox(self) -> Tuple[Optional[bool], str]:
        """
        读取 MOX 状态
        MX; → MX0; 或 MX1;
        """

        resp = self._send_cat("MX")
        r = resp.strip()
        if r.startswith("MX") and r.endswith(";") and len(r) >= 3:
            try:
                val = int(r[2])
                return bool(val), resp
            except Exception:
                return None, resp
        return None, resp

    # ---------- 频率 ----------

    def get_freq(self) -> Tuple[Optional[int], str]:
        """
        读取 MAIN 频率 (FA;)
        返回 (freq_hz, 原始应答)
        """
        
        resp = self._send_cat("FA")
        r = resp.strip()
        # 典型返回: FA014250000;
        if r.startswith("FA") and r.endswith(";"):
            freq_str = r[2:-1]
            try:
                return int(freq_str), resp
            except Exception:
                return None, resp
        return None, resp

    def set_freq(self, freq_hz: int) -> str:
        """
        设置 MAIN 频率
        freq_hz 为整数，如 14250000
        FTX-1 要求 9 位十进制数字
        """

        freq_str = f"{freq_hz:09d}"
        resp = self._send_cat(f"FA{freq_str}")
        return resp

    # ---------- 模式 ----------

    def get_mode(self, main: bool = True) -> Tuple[Optional[str], str]:
        """
        读取模式，输出：("LSB" / "USB" / ...)，绝不输出数字编码
        遇到非法码（0,G,J 等）返回 None
        """
        
        p1 = "0" if main else "1"
        resp = self._send_cat(f"MD{p1}")
        r = resp.strip()

        if not (r.startswith("MD") and r.endswith(";") and len(r) == 5):
            return None, resp

        p2 = r[3].upper()
        mode_name = P2_TO_MODE.get(p2)
        return mode_name, resp

    def set_mode(self, mode_name: str, main: bool = True) -> str:
        """
        设置模式，输入为字符串，例如：
            set_mode("USB")
            set_mode("DATA-L")
            set_mode("C4FM-DN")
        若模式名非法，抛 ValueError
        """
        
        mode_name = mode_name.upper()
        if mode_name not in MODE_TO_P2:
            raise ValueError(DISPLAY_TEXT["err_invalid_mode_fmt"].format(mode_name=mode_name))
        p2 = MODE_TO_P2[mode_name]
        p1 = "0" if main else "1"
        resp = self._send_cat(f"MD{p1}{p2}")
        return resp


    # ---------- AGC ----------

    def get_agc(self, main: bool = True) -> Tuple[Optional[str], str]:
        """
        读取 AGC（GT 命令）

        参数:
            main: True=MAIN-side, False=SUB-side

        返回:
            (agc_name, 原始应答)

        agc_name 可能值:
            OFF / FAST / MID / SLOW / AUTO-FAST / AUTO-MID / AUTO-SLOW
        """

        p1 = "0" if main else "1"
        resp = self._send_cat(f"GT{p1}")
        r = resp.strip()

        # Answer: GT P1 P3 ;
        if not (r.startswith("GT") and r.endswith(";")):
            return None, resp
        body = r[2:-1]
        digits = "".join(ch for ch in body if ch.isdigit())
        # 期望至少两位：P1 + P3
        if len(digits) < 2:
            return None, resp

        recv_p1 = digits[0]
        p3 = digits[1]
        if recv_p1 != p1:
            return None, resp

        return AGC_P3_TO_NAME.get(p3), resp

    def set_agc(self, agc: str, main: bool = True) -> str:
        """
        设置 AGC（GT 命令）

        参数:
            agc:
                OFF / FAST / MID / SLOW / AUTO
            main:
                True=MAIN-side, False=SUB-side
        """

        agc_u = agc.strip().upper()
        if agc_u not in AGC_NAME_TO_P2:
            raise ValueError(DISPLAY_TEXT["err_invalid_agc_fmt"].format(agc=agc, opts=list(AGC_NAME_TO_P2.keys())))

        p1 = "0" if main else "1"
        p2 = AGC_NAME_TO_P2[agc_u]
        return self._send_cat(f"GT{p1}{p2}")

    # ---------- RF Power (PC POWER CONTROL) ----------

    def get_power_control(self) -> Tuple[Optional[str], Optional[int], str]:
        """
        读取功率控制（PC 命令）

        返回:
            (device, watts, 原始应答)

        device:
            "FIELD" (FTX-1 field head) 或 "SPA1"

        watts:
            整数 W（P2，三位数）

        注意：手册给出的范围是
            P1=1(field): 005-010W
            P1=2(SPA-1): 005-100W
        但实测 field head 可用 001-010W，这里 set_power_watts 会按实测放开到 1W 起。
        """

        resp = self._send_cat("PC")
        r = resp.strip()
        if not (r.startswith("PC") and r.endswith(";")):
            return None, None, resp

        body = r[2:-1]
        digits = "".join(ch for ch in body if ch.isdigit())
        # 期望：P1(1位) + P2(3位) = 4 位
        if len(digits) < 4:
            return None, None, resp

        p1 = digits[0]
        p2 = digits[1:4]
        try:
            watts = int(p2)
        except Exception:
            return None, None, resp

        if p1 == "1":
            return "FIELD", watts, resp
        if p1 == "2":
            return "SPA1", watts, resp
        return None, watts, resp

    def set_power_watts(self, watts: int) -> str:
        """
        设置输出功率（PC 命令）
        
        说明：
        - 先执行一次读取，判断当前连接的是 FIELD 还是 SPA-1
        - FIELD: 允许 1~10W（发送 P1=1，P2=001~010）
        - SPA-1: 允许 5~100W（发送 P1=2，P2=005~100）

        参数:
            watts: 整数 W
        """

        if not isinstance(watts, int):
            raise TypeError(DISPLAY_TEXT["err_watts_type"])

        dev, cur_w, raw = self.get_power_control()
        if dev is None:
            raise RuntimeError(DISPLAY_TEXT["err_parse_pc_fmt"].format(raw=raw))

        if dev == "FIELD":
            if watts < 1 or watts > 10:
                raise ValueError(DISPLAY_TEXT["err_field_power_range"])
            p1 = "1"
            p2 = f"{watts:03d}"  # 001~010
        else:
            # SPA1
            if watts < 5 or watts > 100:
                raise ValueError(DISPLAY_TEXT["err_spa1_power_range"])
            p1 = "2"
            p2 = f"{watts:03d}"  # 005~100

        return self._send_cat(f"PC{p1}{p2}")


    # ---------- METER 读取 ----------

    def read_meter(self, meter_id: int) -> Tuple[Optional[int], Optional[float], str]:
        """
        读取一个 meter
        RM 命令:
          P1: 1 ~ 8
          P2: 000 ~ 255
          P3: 000 固定
        返回 (raw_value, conv_value, 原始应答)
        """
        
        resp = self._send_cat(f"RM{meter_id}")
        r = resp.strip()
        # 解析，如: "RM5 123000;" 或 "RM5123000;"
        if not (r.startswith("RM") and r.endswith(";")):
            return None, None, resp
        try:
            p1 = int(r[2])          # 第三个字符是 P1 (1..8)
            if p1 != meter_id:
                # 不匹配的话直接视为错误
                return None, None, resp
            p2_str = r[3:6]         # 接下来 3 位是 P2 (000-255)
            p3_str = r[6:9]
            if p3_str != "000":
                return None, None, resp
            raw_val = int(p2_str)
            conv_val = convert_meter_value(meter_id, raw_val)
            return raw_val, conv_val, resp
        except Exception:
            return None, None, resp

    def read_all_meters(self) -> Dict[str, Dict[str, int | float | None]]:
        """
        依次读 1..8 meter
        """
        
        results: Dict[str, Dict[str, int | float | None]] = {}
        for mid in range(1, 9):
            with self._lock:
                name = METER_MAP.get(mid, f"METER_{mid}")
                raw, conv, resp = self.read_meter(mid)  # read_meter 内部也会锁，但 RLock 可重入
                if raw is not None:
                    results[name] = {
                        "raw": raw,
                        "value": conv,
                    }
        return results

    # ---------- Manual NOTCH ----------

    def set_manual_notch(
        self,
        main: bool = True,
        enabled: Optional[bool] = None,
        freq_hz: Optional[int] = None,
    ) -> str:
        """
        设置 Manual NOTCH（手动陷波）

        参数:
            main:  True=MAIN-side, False=SUB-side
            enabled:
                - True  -> ON
                - False -> OFF
                - None  -> 不改变 ON/OFF 状态
            freq_hz:
                - 整数 Hz，例如 1000 表示 1000 Hz
                - None -> 不改变频率

        返回:
            最后一条 CAT 命令的原始返回字符串（如果两个都设置，则是频率那条的返回）
        """
        if enabled is None and freq_hz is None:
            raise ValueError(DISPLAY_TEXT["err_notch_args"])

        
        p1 = "0" if main else "1"
        last_resp = ""

        # 先设置 ON/OFF
        if enabled is not None:
            # P2 = 0, P3 = 000/001
            p2 = "0"
            p3 = 1 if enabled else 0
            cmd = f"BP{p1}{p2}{p3:03d}"
            last_resp = self._send_cat(cmd)

        # 再设置频率
        if freq_hz is not None:
            # FTX-1: P3 = 001-320, 单位 10 Hz，即 10~3200 Hz
            steps = int(round(freq_hz / 10))
            if steps < 1 or steps > 320:
                raise ValueError(DISPLAY_TEXT["err_notch_range"])

            p2 = "1"
            p3 = steps
            cmd = f"BP{p1}{p2}{p3:03d}"
            last_resp = self._send_cat(cmd)

        return last_resp

    def get_manual_notch(
        self, main: bool = True
    ) -> Tuple[Optional[bool], Optional[int], Tuple[str, str]]:
        """
        读取 Manual NOTCH 状态和频率

        返回:
            enabled:
                - True  -> ON
                - False -> OFF
                - None  -> 无法解析/收到非法编码
            freq_hz:
                - 整数 Hz，例如 1000
                - None  -> 无法解析/收到非法编码
            (raw_on, raw_freq):
                - 两次 CAT 应答的原始字符串，便于调试
        """

        p1 = "0" if main else "1"

        # 先读 ON/OFF: BP P1 0 ;
        resp_on = self._send_cat(f"BP{p1}0")
        r_on = resp_on.strip()
        enabled: Optional[bool] = None

        # 典型返回: BP0001; 等
        if r_on.startswith("BP") and r_on.endswith(";") and len(r_on) == 8:
            try:
                # 索引: B(0) P(1) P1(2) P2(3) P3(4:7) ;(7)
                p2 = r_on[3]
                p3 = int(r_on[4:7])

                if p2 == "0":
                    if p3 == 0:
                        enabled = False
                    elif p3 == 1:
                        enabled = True
            except Exception:
                enabled = None

        # 再读频率: BP P1 1 ;
        resp_freq = self._send_cat(f"BP{p1}1")
        r_freq = resp_freq.strip()
        freq_hz: Optional[int] = None

        if r_freq.startswith("BP") and r_freq.endswith(";") and len(r_freq) == 8:
            try:
                p2 = r_freq[3]
                p3 = int(r_freq[4:7])
                if p2 == "1" and 1 <= p3 <= 320:
                    freq_hz = p3 * 10  # 单位 10 Hz
            except Exception:
                freq_hz = None

        return enabled, freq_hz, (resp_on, resp_freq)
            
    # ---------- PRE-AMP / IPO ----------

    def get_preamp(self, band: str) -> Tuple[Optional[str], str]:
        """
        读取 PRE-AMP/IPO 状态（按频段）

        band:
            - "HF", "HF50", "HF/50" -> HF/50MHz
            - "VHF"                 -> VHF
            - "UHF"                 -> UHF

        返回:
            (level, 原始应答)

        HF/50 下:
            level ∈ {"IPO", "AMP1", "AMP2"}

        VHF/UHF 下:
            level ∈ {"OFF", "ON"}
        """
        # 规范化 band 字符串
        b = band.upper()
        if b not in BAND_TO_P1:
            raise ValueError(DISPLAY_TEXT["err_invalid_band_fmt"].format(band=band))

        p1 = BAND_TO_P1[b]

    
        # Read: PA P1 ;
        resp = self._send_cat(f"PA{p1}")
        r = resp.strip()
        if not (r.startswith("PA") and r.endswith(";")):
            return None, resp

        body = r[2:-1]
        digits = "".join(ch for ch in body if ch.isdigit())
        if len(digits) < 2:
            return None, resp

        recv_p1 = digits[0]
        recv_p2 = digits[1]

        # 确认返回的 band 和请求一致
        if recv_p1 != p1:
            return None, resp

        band_canon = P1_TO_BAND_CANON.get(recv_p1)
        if band_canon == "HF50":
            level = HF50_P2_TO_PREAMP.get(recv_p2)
        else:
            # VHF/UHF 都是 OFF/ON
            level = VU_P2_TO_PREAMP.get(recv_p2)

        return level, resp

    def set_preamp(self, band: str, level: str) -> str:
        """
        设置 PRE-AMP/IPO 状态（按频段）

        band:
            - "HF", "HF50", "HF/50" -> HF/50MHz
            - "VHF"                 -> VHF
            - "UHF"                 -> UHF

        level:
            HF/50 下:
                "IPO", "AMP1", "AMP2"
            VHF/UHF 下:
                "OFF", "ON"
        """
        b = band.upper()
        if b not in BAND_TO_P1:
            raise ValueError(DISPLAY_TEXT["err_invalid_band_fmt"].format(band=band))

        p1 = BAND_TO_P1[b]

        lvl = level.upper()
        # 根据 band 选择不同的合法值
        if p1 == "0":
            # HF/50
            if lvl not in HF50_PREAMP_TO_P2:
                raise ValueError(DISPLAY_TEXT["err_hf50_preamp_level_fmt"].format(opts=list(HF50_PREAMP_TO_P2.keys()), level=level))
            p2 = HF50_PREAMP_TO_P2[lvl]
        else:
            # VHF/UHF
            if lvl not in VU_PREAMP_TO_P2:
                raise ValueError(DISPLAY_TEXT["err_vu_preamp_level_fmt"].format(opts=list(VU_PREAMP_TO_P2.keys()), level=level))
            p2 = VU_PREAMP_TO_P2[lvl]

        cmd = f"PA{p1}{p2}"

        # Set: PA P1 P2 ;
        return self._send_cat(cmd)