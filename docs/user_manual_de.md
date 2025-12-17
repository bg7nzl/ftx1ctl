**FTX-1 Konsole (ftx1gui)**

***

# FTX-1 Konsole Benutzerhandbuch

Dieses Handbuch bietet eine umfassende Anleitung zur Verwendung der Software `ftx1gui` zur Steuerung des FTX-1 Transceivers. Es behandelt die Verbindungseinrichtung, Frequenzverwaltung, Sendesteuerung und erweiterte Audioverarbeitungsfunktionen.

## 1. Verbindungseinrichtung (Oberes Panel)

Der obere Bereich der Anwendung dient dazu, die Kommunikation mit dem Funkgerät und externer Software herzustellen.

### CAT-Steuerung (Computer Aided Transceiver)
*   **CAT-Port**: Wählt den COM-Port aus, der zum Senden von Befehlen (Frequenz, Modus usw.) an das Funkgerät verwendet wird.
    *   *Standardlogik*: Die Software scannt automatisch nach verfügbaren Ports. Sie priorisiert Ports mit dem Namen "**Enhanced COM Port**" (üblich bei Silicon Labs Treibern, die in Yaesu-Funkgeräten verwendet werden). Wenn nicht gefunden, wird standardmäßig der erste verfügbare Port verwendet.
*   **Baud**: Legt die Kommunikationsgeschwindigkeit fest.
    *   *Standard*: **38400** bps. Stellen Sie sicher, dass dies mit der Einstellung im Menü Ihres Funkgeräts (CAT RATE) übereinstimmt.

### PTT-Steuerung (Push-To-Talk)
*   **PTT-Port**: Wählt den COM-Port aus, der verwendet wird, um die Übertragung über das RTS-Signal (Request to Send) auszulösen.
    *   *Standardlogik*: Priorisiert Ports mit dem Namen "**Standard COM Port**". Wenn Sie zwei Ports haben (Enhanced & Standard), wird der Standard-Port normalerweise für PTT/CW-Tastung verwendet.
*   **Baud**: Legt die Geschwindigkeit für den PTT-Port fest (normalerweise weniger kritisch als CAT).
    *   *Standard*: **38400** bps.

### Verbindungsschaltflächen
*   **Verbinden (Connect)**: Öffnet die COM-Ports und beginnt mit der Abfrage des Funkgeräts.
*   **Trennen (Disconnect)**: Schließt die Verbindung und stoppt die Abfrage.
*   **Vollständig lesen (Full Read)**: Erzwingt eine vollständige Synchronisierung aller Einstellungen vom Funkgerät zur Benutzeroberfläche.
    *   *Hinweis*: Die Software plant automatisch ein vollständiges Lesen nach dem Einstellen von Parametern, aber diese Schaltfläche ist nützlich, wenn die Benutzeroberfläche nicht mehr synchron ist.

### Rigctl Server (Netzwerksteuerung)
*   **rigctl TCP-Port**: Die Portnummer für den integrierten Hamlib-kompatiblen TCP-Server.
    *   *Standard*: **4532**.
    *   *Verwendung*: Ermöglicht Drittanbietersoftware (wie WSJT-X, N1MM oder Log4OM), das Funkgerät *durch* diese Anwendung zu steuern, indem sie sich mit `localhost:4532` unter Verwendung des Modells "Hamlib NET rigctl" (Modell-ID 2) verbindet.

---

## 2. Frequenz & Modus (Linkes Panel)

### Frequenzanzeige
*   **Anzeige**: Zeigt die aktuelle Frequenz in Hz an.

*  **Ziffernweise Abstimmung**: 
    1. Bewegen Sie den Mauszeiger über die spezifische Ziffer, die Sie ändern möchten.
    2. **Mausrad**: Scrollen Sie nach oben, um den Wert zu erhöhen, oder nach unten, um ihn zu verringern.
    3. **Pfeiltasten**: Klicken Sie auf die kleinen **Auf-/Ab-Pfeile** über und unter jeder Ziffer für eine schrittweise Anpassung.

### Modusauswahl
Ein Raster von Schaltflächen ermöglicht es Ihnen, den Betriebsmodus zu ändern.
*   **Aktiver Modus**: Der aktuell ausgewählte Modus ist **Grün** hervorgehoben.
*   **Unterstützte Modi**:
    *   **Reihe 1**: USB, DATA-U, CW-U, RTTY-U, AM, FM, FM-N, C4FM-DN, PSK
    *   **Reihe 2**: LSB, DATA-L, CW-L, RTTY-L, AM-N, DATA-FM, DATA-FM-N, C4FM-VW

---

## 3. Sendesteuerung (Mittleres Panel)

### PTT (Push-To-Talk)
*   **Sende-Taste (Transmit)**: Schaltet den Sendestatus des Funkgeräts um.
    *   **Weiß**: Empfangsstatus (RX).
    *   **Rot**: Sendestatus (TX).
    *   *Mechanismus*: Dies schaltet das RTS-Signal am ausgewählten **PTT-Port** um.

### Leistungssteuerung
*   **Leistung (W)**: Ein Schieberegler zum Einstellen der HF-Ausgangsleistung.
*   **Wertanzeige**: Zeigt die Zielleistung in Watt an.
*   **Gerätetyp-Anzeige**: Zeigt die erkannte Leistungsklasse des Funkgeräts an (z. B. "FIELD", "SPA1").
    *   **FIELD**: Bereich 1–10 W.
    *   **SPA1**: Bereich 5–100 W.
    *   **Standard**: Bereich 1–100 W.

---

## 4. Empfangs-Vorverarbeitung (Mittleres Panel)

Dieser Abschnitt steuert die Verstärkung des Empfängers und die Einstellungen der automatischen Verstärkungsregelung (AGC).

### AGC (Automatische Verstärkungsregelung)
Steuert, wie das Funkgerät mit unterschiedlichen Signalstärken umgeht.
*   **Optionen**: OFF (Aus), FAST (Schnell), MID (Mittel), SLOW (Langsam), AUTO.
*   **Anzeigelogik**:
    *   Wenn Sie **AUTO** wählen, bestimmt das Funkgerät die beste Geschwindigkeit basierend auf dem aktuellen Modus (z. B. CW standardmäßig FAST, SSB standardmäßig SLOW).
    *   **Visueller Indikator**: Wenn sich das Funkgerät im AUTO-Modus befindet und intern "MID" gewählt hat, werden **sowohl** die `AUTO`-Taste als auch die `MID`-Taste hervorgehoben. So wissen Sie, dass Sie sich im Auto-Modus befinden *und* was die aktuelle effektive Geschwindigkeit ist.

### Vorverstärker (Preamp)
Passt die Empfänger-Frontend-Verstärkung für verschiedene Bänder an.
*   **HF/50 MHz**:
    *   **IPO**: Intercept Point Optimization (Vorverstärker AUS). Am besten für Umgebungen mit starken Signalen.
    *   **AMP1**: Vorverstärker mit niedriger Verstärkung.
    *   **AMP2**: Vorverstärker mit hoher Verstärkung.
*   **VHF / UHF**:
    *   **OFF / ON**: Schaltet den Vorverstärker für diese Bänder um.

---

## 5. Manuelle Notch-Steuerung (Rechtes/Unteres Panel)

Dieses erweiterte Panel ermöglicht es Ihnen, Audio zu visualisieren und Störtöne manuell herauszufiltern (Notch).

### Steuerung
*   **Notch aktivieren (Enable Notch)**: Kontrollkästchen zum Aktivieren des manuellen Notch-Filters am Funkgerät.
*   **Freq (Hz)**:
    *   **Eingabefeld**: Geben Sie eine bestimmte Frequenz (10–3200 Hz) ein und klicken Sie auf **Setzen (Set)**.
    *   **Aktuell (Current)**: Zeigt den aktuell im Funkgerät aktiven Wert an.
    *   **Lesen (Read)**: Aktualisiert den angezeigten Wert vom Funkgerät.

### Audio-Wasserfall / Spektrum
*   **Eingabegerät (Input Device)**: Wählt die Audioquelle für die Wasserfallanzeige aus.
    *   *Standardlogik*: Die Software scannt Audiogeräte und bevorzugt eines, das "**USB Audio Device**" im Namen enthält (typisch für eingebaute Funkgerät-Soundkarten).
*   **Wasserfallanzeige**: Zeigt ein Echtzeit-Spektrogramm des empfangenen Audios an.
    *   **X-Achse**: Zeit (scrollender Verlauf).
    *   **Y-Achse**: Audiofrequenz (0–4000 Hz).
*   **Interaktion**:
    *   **Klicken für Notch**: Ein Klick irgendwo auf den Wasserfall setzt die manuelle Notch-Frequenz automatisch auf diesen Ton.
    *   **Visuelles Feedback**: Zwei rote horizontale Linien erscheinen auf dem Wasserfall, um die Position und Breite (ca. 100 Hz) des aktiven Notch-Filters anzuzeigen.

---

## 6. Meter (Unteres Panel)

Eine Reihe von Balkenanzeigen liefert Echtzeit-Telemetrie vom Funkgerät. Jedes Meter hat eine rote "Schwellenwert"-Linie, die einen Nenn- oder Grenzwert anzeigt.

| Meter | Beschreibung | Einheit | Schwellenwert (Rote Linie) |
| :--- | :--- | :--- | :--- |
| **S_MAIN** | Signalstärke | S-Einheiten / dB | S9 |
| **COMP** | Sprachkompressionspegel | dB | 15 dB |
| **ALC** | Automatische Pegelregelungsspannung | % | 100% |
| **PO** | Ausgangsleistung | Watt | 10 W (variiert) |
| **SWR** | Stehwellenverhältnis | Verhältnis | 3.0 |
| **IDD** | Drain-Strom | Ampere | 2 A |
| **VDD** | Versorgungsspannung | Volt | 13.8 V |

*   **Aktualisierungsrate**: Die Meter werden etwa einmal pro Sekunde aktualisiert (Standard), um den CAT-Bus-Verkehr zu minimieren.

---

## 7. Fehlerbehebung

*   **"Need CAT and PTT ports" (CAT- und PTT-Ports benötigt)**: Sie müssen für beide Felder einen COM-Port auswählen. Wenn Sie nur ein Kabel haben, müssen Sie möglicherweise für beide denselben Port auswählen oder prüfen, ob Ihr Treiber zwei virtuelle Ports (Standard & Enhanced) erstellt.
*   **Meter bewegen sich nicht**: Stellen Sie sicher, dass die Verbindung aktiv ist (Statusleiste sagt "Connected"). Prüfen Sie, ob ein anderes Programm den COM-Port blockiert.
*   **Wasserfall ist schwarz**: Stellen Sie sicher, dass das richtige **Eingabegerät** ausgewählt ist. Es sollte mit dem "Line In"- oder "Mikrofon"-Gerät übereinstimmen, das mit der USB-Verbindung Ihres Funkgeräts verbunden ist.
*   **Rigctl funktioniert nicht**: Stellen Sie sicher, dass keine andere Software Port 4532 verwendet. Wenn Sie den Port in der Benutzeroberfläche ändern, aktualisieren Sie Ihre externe Logger-/Software entsprechend.


## 7. Hardware-Einschränkungen & Kalibrierung

### Wichtiger Hinweis für SPA-1 / Optima Benutzer
Da der Entwickler derzeit die **FTX-1 Field** Version (eigenständig 10W) verwendet, ist das Telemetriesystem speziell für den Betrieb mit geringer Leistung im portablen Einsatz abgestimmt.

* **PO (Ausgangsleistung) Genauigkeit**: Die Watt-Skala und der Meterausschlag sind für den internen 10W PA kalibriert. Für 100W-Benutzer kann das Meter vorzeitig den Höchstwert erreichen oder eine falsche Skalierung anzeigen.
* **IDD (Drain-Strom) Genauigkeit**: Das IDD-Meter ist derzeit für den typischen Verbrauch der Field-Einheit kalibriert (max. ca. 2A). Der 100W-Betrieb erfordert deutlich höheren Strom, der in dieser Benutzeroberfläche noch nicht genau abgebildet ist.

---

## 8. Hinweis zur SPA-1 (100W) Kalibrierung

Derzeit wird diese Software unter Verwendung der **FTX-1 Field (10W eigenständig)** Version entwickelt und getestet. Da ich den **Optima SPA-1 (100W)** Verstärker nicht auf meinem Schreibtisch habe, sind die **Leistungs- (PO)** und **Strom- (IDD)** Meter noch nicht vollständig für den Hochleistungsbetrieb kalibriert.

**Ich brauche Ihre Hilfe!** Wenn Sie das Optima SPA-1 Setup verwenden, zeigt die Software möglicherweise ungenaue Leistungs- und Stromwerte an. Wenn Sie mir helfen möchten, dies für die gesamte Community zu verbessern, wäre ich Ihnen unglaublich dankbar, wenn Sie ein paar Fotos oder einen kurzen Clip Ihres Funkgerätebildschirms teilen könnten, der die PO- und IDD-Werte bei verschiedenen Leistungsstufen zeigt.

Ihre Daten helfen mir, die Mathematik hinter diesen Metern fein abzustimmen, damit sie für jeden FTX-1 Besitzer perfekt funktionieren. Zögern Sie nicht, sich über das Projekt-Repository zu melden!

---
