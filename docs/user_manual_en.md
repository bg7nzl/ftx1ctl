**FTX-1 Control Console (ftx1gui)**

***

# FTX-1 Control Console User Manual

This manual provides a comprehensive guide to using the `ftx1gui` software for controlling the FTX-1 transceiver. It covers connection setup, frequency management, transmit controls, and advanced audio processing features.

## 1. Connection Setup (Top Panel)

The top section of the application is dedicated to establishing communication with the radio and external software.

### CAT Control (Computer Aided Transceiver)
*   **CAT Port**: Selects the COM port used for sending commands (frequency, mode, etc.) to the radio.
    *   *Default Logic*: The software automatically scans for available ports. It prioritizes ports named "**Enhanced COM Port**" (common with Silicon Labs drivers used in Yaesu radios). If not found, it defaults to the first available port.
*   **Baud**: Sets the communication speed.
    *   *Default*: **38400** bps. Ensure this matches the setting in your radio's menu (CAT RATE).

### PTT Control (Push-To-Talk)
*   **PTT Port**: Selects the COM port used to trigger transmission via the RTS (Request to Send) signal.
    *   *Default Logic*: Prioritizes ports named "**Standard COM Port**". If you have two ports (Enhanced & Standard), the Standard port is usually used for PTT/CW keying.
*   **Baud**: Sets the speed for the PTT port (usually less critical than CAT).
    *   *Default*: **38400** bps.

### Connection Buttons
*   **Connect**: Opens the COM ports and starts polling the radio.
*   **Disconnect**: Closes the connection and stops polling.
*   **Full Read**: Forces a complete synchronization of all settings from the radio to the UI.
    *   *Note*: The software automatically schedules a full read after setting parameters, but this button is useful if the UI falls out of sync.

### Rigctl Server (Network Control)
*   **rigctl TCP Port**: The port number for the built-in Hamlib-compatible TCP server.
    *   *Default*: **4532**.
    *   *Usage*: Allows third-party software (like WSJT-X, N1MM, or Log4OM) to control the radio *through* this application by connecting to `localhost:4532` using the "Hamlib NET rigctl" model (Model ID 2).

---

## 2. Frequency & Mode (Left Panel)

### Frequency Display
*   **Display**: Shows the current frequency in Hz.

*  **Digit-Wise Tuning**: 
    1. Hover your mouse cursor over the specific digit you wish to change.
    2. **Mouse Wheel**: Scroll up to increase or down to decrease the value of that digit.
    3. **Arrow Buttons**: Click the small **Up/Down arrows** located above and below each digit for step-by-step adjustment.

### Mode Selection
A grid of buttons allows you to change the operating mode.
*   **Active Mode**: The currently selected mode is highlighted in **Green**.
*   **Supported Modes**:
    *   **Row 1**: USB, DATA-U, CW-U, RTTY-U, AM, FM, FM-N, C4FM-DN, PSK
    *   **Row 2**: LSB, DATA-L, CW-L, RTTY-L, AM-N, DATA-FM, DATA-FM-N, C4FM-VW

---

## 3. Transmit Control (Center Panel)

### PTT (Push-To-Talk)
*   **Transmit Button**: Toggles the radio's transmission state.
    *   **White**: Receive (RX) state.
    *   **Red**: Transmit (TX) state.
    *   *Mechanism*: This toggles the RTS signal on the selected **PTT Port**.

### Power Control
*   **Power (W)**: A slider to adjust the RF output power.
*   **Value Display**: Shows the target power in Watts.
*   **Device Type Indicator**: Displays the detected power class of the radio (e.g., "FIELD", "SPA1").
    *   **FIELD**: Range 1–10 W.
    *   **SPA1**: Range 5–100 W.
    *   **Standard**: Range 1–100 W.

---

## 4. Receive Preprocessing (Center Panel)

This section controls the receiver's gain and automatic gain control settings.

### AGC (Automatic Gain Control)
Controls how the radio handles varying signal strengths.
*   **Options**: OFF, FAST, MID, SLOW, AUTO.
*   **Display Logic**:
    *   If you select **AUTO**, the radio determines the best speed based on the current mode (e.g., CW defaults to FAST, SSB to SLOW).
    *   **Visual Indicator**: If the radio is in AUTO mode and has selected "MID" internally, **both** the `AUTO` button and the `MID` button will be highlighted. This lets you know you are in Auto mode *and* what the current effective speed is.

### Preamp (Preamplifier)
Adjusts the receiver front-end gain for different bands.
*   **HF/50 MHz**:
    *   **IPO**: Intercept Point Optimization (Preamp OFF). Best for strong signal environments.
    *   **AMP1**: Low gain preamp.
    *   **AMP2**: High gain preamp.
*   **VHF / UHF**:
    *   **OFF / ON**: Toggles the preamp for these bands.

---

## 5. Manual Notch Control (Right/Bottom Panel)

This advanced panel allows you to visualize audio and manually notch out interfering tones.

### Controls
*   **Enable Notch**: Checkbox to activate the manual notch filter on the radio.
*   **Freq (Hz)**:
    *   **Input Box**: Type a specific frequency (10–3200 Hz) and click **Set**.
    *   **Current**: Displays the value currently active in the radio.
    *   **Read**: Refreshes the displayed value from the radio.

### Audio Waterfall / Spectrum
*   **Input Device**: Selects the audio source for the waterfall display.
    *   *Default Logic*: The software scans audio devices and prefers one containing "**USB Audio Device**" in its name (typical for built-in radio sound cards).
*   **Waterfall Display**: Shows a real-time spectrogram of the received audio.
    *   **X-Axis**: Time (scrolling history).
    *   **Y-Axis**: Audio Frequency (0–4000 Hz).
*   **Interaction**:
    *   **Click to Notch**: Clicking anywhere on the waterfall will automatically set the Manual Notch frequency to that pitch.
    *   **Visual Feedback**: Two red horizontal lines appear on the waterfall to indicate the position and width (approx. 100 Hz) of the active notch filter.

---

## 6. Meters (Bottom Panel)

A row of bar meters provides real-time telemetry from the radio. Each meter has a red "threshold" line indicating a nominal or limit value.

| Meter | Description | Unit | Threshold (Red Line) |
| :--- | :--- | :--- | :--- |
| **S_MAIN** | Signal Strength | S-Units / dB | S9 |
| **COMP** | Speech Compression Level | dB | 15 dB |
| **ALC** | Auto Level Control Voltage | % | 100% |
| **PO** | Power Output | Watts | 10 W (varies) |
| **SWR** | Standing Wave Ratio | Ratio | 3.0 |
| **IDD** | Drain Current | Amps | 2 A |
| **VDD** | Supply Voltage | Volts | 13.8 V |

*   **Refresh Rate**: The meters update approximately once per second (default) to minimize CAT bus traffic.

---

## 7. Troubleshooting

*   **"Need CAT and PTT ports"**: You must select a COM port for both fields. If you only have one cable, you may need to select the same port for both, or check if your driver creates two virtual ports (Standard & Enhanced).
*   **Meters not moving**: Ensure the connection is active (Status bar says "Connected"). Check if another program is hogging the COM port.
*   **Waterfall is black**: Ensure the correct **Input Device** is selected. It should match the "Line In" or "Microphone" device associated with your radio's USB connection.
*   **Rigctl not working**: Ensure no other software is using port 4532. If you change the port in the UI, update your external logger/software to match.


## 7. Hardware Limitations & Calibration

### Important Note for SPA-1 / Optima Users
As the developer currently operates the **FTX-1 Field** version (standalone 10W), the telemetry system is specifically tuned for low-power portable operation.

* **PO (Power Output) Accuracy**: The wattage scale and meter deflection are calibrated for the 10W internal PA. For 100W users, the meter may hit the ceiling prematurely or show incorrect scaling.
* **IDD (Drain Current) Accuracy**: The IDD meter is currently calibrated for the Field unit's typical draw (maxing around 2A). 100W operation requires significantly higher current, which is not yet accurately mapped in this UI.

---

## 8. A Note on SPA-1 (100W) Calibration

Currently, this software is developed and tested using the **FTX-1 Field (10W standalone)** version. Because I don't have the **Optima SPA-1 (100W)** amplifier on my desk, the **Power (PO)** and **Current (IDD)** meters are not yet fully calibrated for high-power operation.

**I would love your help!** If you are using the Optima SPA-1 setup, the software might show inaccurate scale readings for power and current. If you'd like to help me improve this for the whole community, I would be incredibly grateful if you could share a few photos or a quick clip of your radio's screen showing the PO and IDD readings at different power levels. 

Your data will help me fine-tune the math behind these meters so they work perfectly for every FTX-1 owner. Feel free to reach out via the project repository!

---