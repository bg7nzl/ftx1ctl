# FTX-1 Console (ftx1ctl)

**FTX-1 Console** is a modern control software designed for the **Yaesu FTX-1** transceiver. It provides a user-friendly GUI for CAT control, real-time meter monitoring, and advanced features like an audio waterfall for manual notch filter tuning.

Additionally, it features a built-in **Hamlib NET rigctl server**, allowing seamless integration with digital mode software like **WSJT-X** or **JTDX** without port conflicts.

**Author:** BG7NZL

---

<img width="1333" height="857" alt="2025-12-13 152319" src="https://github.com/user-attachments/assets/ff233183-806b-4d72-9d70-6706687a3bbd" />


---

## 🇬🇧 English

### Key Features

* **Dual Serial Control:** Supports separate COM ports for CAT commands and PTT (RTS), ensuring reliable operation.
* **Real-time Meters:** High-speed graphical monitoring of S-Meter, Power (Po), ALC, SWR, IDD, and VDD.
* **Audio Waterfall & Notch:**
    * Visualizes microphone/audio input using a real-time FFT waterfall.
    * **Click-to-Notch:** simply click on an interference spike on the waterfall to instantly set the FTX-1's Manual Notch filter to that frequency.
* **Hamlib Rigctl Server:**
    * Emulates a Hamlib network radio (`model 2`).
    * Allows WSJT-X/JTDX to control frequency and PTT via TCP (default port 4532) while the console is running.
* **Comprehensive Controls:**
    * Frequency & Mode (SSB, CW, FM, C4FM, DATA, etc.).
    * Preamp/IPO settings per band (HF/VHF/UHF).
    * AGC and Power Output control.
* **Multi-language Support:** Interface available in English, Chinese, Japanese, Russian, German, French, and Spanish.

### Requirements

* Windows 10/11 (Recommended)
* **Python 3.12** (Required for the provided build scripts).
* Yaesu FTX-1 Transceiver connected via USB (Virtual COM ports).

### Installation & Running

1.  **Clone or Download** the repository.
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the GUI**:
    ```bash
    python ftx1gui.py
    ```

### WSJT-X Configuration Guide

To use this software simultaneously with WSJT-X:

1.  Open **FTX-1 Console** and connect to your radio.
2.  Open **WSJT-X** -> **Settings** -> **Radio**.
3.  **Rig:** Select `Hamlib NET rigctl`.
4.  **Network Server:** `127.0.0.1:4532` (Default).
5.  **PTT Method:** `CAT`.
6.  Click **Test CAT** and **Test PTT**.

### Building from Source

Two build scripts are provided for creating a standalone `.exe`:

* **Recommended (Nuitka):** Run `build_nuitka.bat`. This produces a highly optimized, single-file executable.
* **Alternative (PyInstaller):** Run `build.bat`.

---

## 🇨🇳 中文 (Chinese)

### 主要功能

**FTX-1 Console** 是一款专为 **八重洲 (Yaesu) FTX-1** 电台设计的现代化控制软件。它不仅提供了直观的 CAT 控制界面和实时仪表监测，还加入了音频瀑布图等高级功能，用于辅助手动陷波器（Notch）的调节。

此外，软件内置了 **Hamlib NET rigctl 服务器**，允许 **WSJT-X** 或 **JTDX** 等数字模式软件通过网络协议共享电台控制，完美解决了串口独占冲突的问题。

* **双串口控制：** 支持分别设置 CAT指令 和 PTT (RTS) 的 COM 端口，操作更稳定 。
* **实时仪表盘：** 高速图形化显示 S表、功率 (Po)、ALC、驻波比 (SWR)、电流 (IDD) 和 电压 (VDD) 。
* **音频瀑布图与陷波器：**
    * 通过麦克风/线路输入实时绘制 FFT 音频瀑布图。
    * **点击即陷波：** 在瀑布图上点击干扰信号的波峰，即可自动将 FTX-1 的手动陷波器（Manual Notch）设置到该频率 。
* **Hamlib Rigctl 服务器：**
    * 模拟 Hamlib 网络电台协议（`model 2`）。
    * 允许 WSJT-X 通过 TCP（默认端口 4532）控制频率和发射，无需关闭本软件 。
* **全面控制：**
    * 频率与模式管理（SSB, CW, FM, C4FM, DATA 等）。
    * 分波段前置放大器 (Preamp/IPO) 设置 。
    * AGC 和 发射功率调节 。
* **多语言支持：** 内置 英语、简体中文、日语、俄语、德语、法语、西班牙语 。

### 运行环境

* Windows 10/11 (推荐)
* **Python 3.12** (提供的构建脚本基于此版本) 。
* 通过 USB 连接的 Yaesu FTX-1 电台。

### 安装与运行

1.  **下载** 项目代码。
2.  **安装依赖库**：
    ```bash
    pip install -r requirements.txt
    ```
3.  **启动软件**：
    ```bash
    python ftx1gui.py
    ```

### WSJT-X 联动设置指南

如果您需要同时运行 WSJT-X 进行数字通联：

1.  打开 **FTX-1 Console** 并点击连接电台。
2.  打开 **WSJT-X** -> **Settings (设置)** -> **Radio (电台)**。
3.  **Rig (电台型号):** 选择 `Hamlib NET rigctl`。
4.  **Network Server (网络服务器):** 填写 `127.0.0.1:4532` (默认端口) 。
5.  **PTT Method (PTT方式):** 选择 `CAT`。
6.  点击 **Test CAT** 和 **Test PTT** 验证连接。

### 编译打包

项目提供了两个脚本用于将 Python 代码打包为独立的 `.exe` 可执行文件：

* **推荐 (Nuitka):** 运行 `build_nuitka.bat`。这将生成一个体积更小、运行效率更高的单文件程序 。
* **备选 (PyInstaller):** 运行 `build.bat` 。

---
