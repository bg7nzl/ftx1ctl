**Consola FTX-1 (ftx1gui)**

***

# Manual de Usuario de la Consola FTX-1

Este manual proporciona una guía completa para el uso del software `ftx1gui` para controlar el transceptor FTX-1. Cubre la configuración de la conexión, la gestión de frecuencias, los controles de transmisión y las funciones avanzadas de procesamiento de audio.

## 1. Configuración de la Conexión (Panel Superior)

La sección superior de la aplicación está dedicada a establecer la comunicación con la radio y el software externo.

### Control CAT (Computer Aided Transceiver)
*   **Puerto CAT (CAT Port)**: Selecciona el puerto COM utilizado para enviar comandos (frecuencia, modo, etc.) a la radio.
    *   *Lógica predeterminada*: El software busca automáticamente los puertos disponibles. Prioriza los puertos llamados "**Enhanced COM Port**" (común con los controladores Silicon Labs utilizados en radios Yaesu). Si no se encuentra, utiliza por defecto el primer puerto disponible.
*   **Baudios (Baud)**: Establece la velocidad de comunicación.
    *   *Predeterminado*: **38400** bps. Asegúrese de que esto coincida con la configuración en el menú de su radio (CAT RATE).

### Control PTT (Push-To-Talk)
*   **Puerto PTT (PTT Port)**: Selecciona el puerto COM utilizado para activar la transmisión a través de la señal RTS (Request to Send).
    *   *Lógica predeterminada*: Prioriza los puertos llamados "**Standard COM Port**". Si tiene dos puertos (Enhanced y Standard), el puerto Standard se utiliza generalmente para la manipulación PTT/CW.
*   **Baudios (Baud)**: Establece la velocidad para el puerto PTT (generalmente menos crítico que CAT).
    *   *Predeterminado*: **38400** bps.

### Botones de Conexión
*   **Conectar (Connect)**: Abre los puertos COM y comienza a sondear la radio.
*   **Desconectar (Disconnect)**: Cierra la conexión y detiene el sondeo.
*   **Lectura Completa (Full Read)**: Fuerza una sincronización completa de todas las configuraciones de la radio a la interfaz de usuario.
    *   *Nota*: El software programa automáticamente una lectura completa después de configurar parámetros, pero este botón es útil si la interfaz de usuario se desincroniza.

### Servidor Rigctl (Control de Red)
*   **Puerto TCP rigctl**: El número de puerto para el servidor TCP integrado compatible con Hamlib.
    *   *Predeterminado*: **4532**.
    *   *Uso*: Permite que software de terceros (como WSJT-X, N1MM o Log4OM) controle la radio *a través* de esta aplicación conectándose a `localhost:4532` utilizando el modelo "Hamlib NET rigctl" (ID de modelo 2).

---

## 2. Frecuencia y Modo (Panel Izquierdo)

### Visualización de Frecuencia
*   **Pantalla**: Muestra la frecuencia actual en Hz.

*  **Sintonización Dígito a Dígito**: 
    1. Pase el cursor del ratón sobre el dígito específico que desea cambiar.
    2. **Rueda del ratón**: Desplace hacia arriba para aumentar el valor o hacia abajo para disminuirlo.
    3. **Botones de flecha**: Haga clic en las pequeñas **flechas arriba/abajo** situadas encima y debajo de cada dígito para un ajuste paso a paso.

### Selección de Modo
Una cuadrícula de botones le permite cambiar el modo de operación.
*   **Modo Activo**: El modo seleccionado actualmente se resalta en **Verde**.
*   **Modos Soportados**:
    *   **Fila 1**: USB, DATA-U, CW-U, RTTY-U, AM, FM, FM-N, C4FM-DN, PSK
    *   **Fila 2**: LSB, DATA-L, CW-L, RTTY-L, AM-N, DATA-FM, DATA-FM-N, C4FM-VW

---

## 3. Control de Transmisión (Panel Central)

### PTT (Push-To-Talk)
*   **Botón Transmitir (Transmit)**: Alterna el estado de transmisión de la radio.
    *   **Blanco**: Estado de recepción (RX).
    *   **Rojo**: Estado de transmisión (TX).
    *   *Mecanismo*: Esto alterna la señal RTS en el **Puerto PTT** seleccionado.

### Control de Potencia
*   **Potencia (W)**: Un control deslizante para ajustar la potencia de salida de RF.
*   **Visualización de Valor**: Muestra la potencia objetivo en Vatios.
*   **Indicador de Tipo de Dispositivo**: Muestra la clase de potencia detectada de la radio (por ejemplo, "FIELD", "SPA1").
    *   **FIELD**: Rango 1–10 W.
    *   **SPA1**: Rango 5–100 W.
    *   **Standard**: Rango 1–100 W.

---

## 4. Preprocesamiento de Recepción (Panel Central)

Esta sección controla la ganancia del receptor y la configuración del control automático de ganancia (AGC).

### AGC (Control Automático de Ganancia)
Controla cómo la radio maneja las variaciones en la intensidad de la señal.
*   **Opciones**: OFF (Apagado), FAST (Rápido), MID (Medio), SLOW (Lento), AUTO.
*   **Lógica de Visualización**:
    *   Si selecciona **AUTO**, la radio determina la mejor velocidad basada en el modo actual (por ejemplo, CW predeterminado FAST, SSB predeterminado SLOW).
    *   **Indicador Visual**: Si la radio está en modo AUTO y ha seleccionado "MID" internamente, **ambos** botones `AUTO` y `MID` se resaltarán. Esto le permite saber que está en modo Auto *y* cuál es la velocidad efectiva actual.

### Preamplificador (Preamp)
Ajusta la ganancia del front-end del receptor para diferentes bandas.
*   **HF/50 MHz**:
    *   **IPO**: Optimización del Punto de Intercepción (Preamplificador OFF). Mejor para entornos de señal fuerte.
    *   **AMP1**: Preamplificador de baja ganancia.
    *   **AMP2**: Preamplificador de alta ganancia.
*   **VHF / UHF**:
    *   **OFF / ON**: Alterna el preamplificador para estas bandas.

---

## 5. Control Manual de Notch (Panel Derecho/Inferior)

Este panel avanzado le permite visualizar el audio y eliminar manualmente los tonos interferentes (Notch).

### Controles
*   **Activar Notch (Enable Notch)**: Casilla de verificación para activar el filtro notch manual en la radio.
*   **Frec (Hz)**:
    *   **Cuadro de Entrada**: Escriba una frecuencia específica (10–3200 Hz) y haga clic en **Establecer (Set)**.
    *   **Actual (Current)**: Muestra el valor actualmente activo en la radio.
    *   **Leer (Read)**: Actualiza el valor mostrado desde la radio.

### Cascada de Audio / Espectro
*   **Dispositivo de Entrada (Input Device)**: Selecciona la fuente de audio para la visualización de la cascada.
    *   *Lógica predeterminada*: El software escanea los dispositivos de audio y prefiere uno que contenga "**USB Audio Device**" en su nombre (típico para tarjetas de sonido de radio integradas).
*   **Visualización de Cascada**: Muestra un espectrograma en tiempo real del audio recibido.
    *   **Eje X**: Tiempo (historial de desplazamiento).
    *   **Eje Y**: Frecuencia de audio (0–4000 Hz).
*   **Interacción**:
    *   **Clic para Notch**: Hacer clic en cualquier lugar de la cascada establecerá automáticamente la frecuencia del Notch manual en ese tono.
    *   **Retroalimentación Visual**: Dos líneas horizontales rojas aparecen en la cascada para indicar la posición y el ancho (aprox. 100 Hz) del filtro notch activo.

---

## 6. Medidores (Panel Inferior)

Una fila de barras de medidores proporciona telemetría en tiempo real desde la radio. Cada medidor tiene una línea roja de "umbral" que indica un valor nominal o límite.

| Medidor | Descripción | Unidad | Umbral (Línea Roja) |
| :--- | :--- | :--- | :--- |
| **S_MAIN** | Intensidad de Señal | Unidades-S / dB | S9 |
| **COMP** | Nivel de Compresión de Voz | dB | 15 dB |
| **ALC** | Voltaje de Control Automático de Nivel | % | 100% |
| **PO** | Potencia de Salida | Vatios | 10 W (variable) |
| **SWR** | Relación de Onda Estacionaria (ROE) | Relación | 3.0 |
| **IDD** | Corriente de Drenaje | Amperios | 2 A |
| **VDD** | Voltaje de Alimentación | Voltios | 13.8 V |

*   **Tasa de Refresco**: Los medidores se actualizan aproximadamente una vez por segundo (predeterminado) para minimizar el tráfico del bus CAT.

---

## 7. Solución de Problemas

*   **"Need CAT and PTT ports" (Se necesitan puertos CAT y PTT)**: Debe seleccionar un puerto COM para ambos campos. Si solo tiene un cable, es posible que deba seleccionar el mismo puerto para ambos, o verificar si su controlador crea dos puertos virtuales (Standard y Enhanced).
*   **Los medidores no se mueven**: Asegúrese de que la conexión esté activa (la barra de estado dice "Connected"). Verifique si otro programa está ocupando el puerto COM.
*   **La cascada está negra**: Asegúrese de que esté seleccionado el **Dispositivo de Entrada** correcto. Debe coincidir con el dispositivo "Line In" o "Microphone" asociado con la conexión USB de su radio.
*   **Rigctl no funciona**: Asegúrese de que ningún otro software esté utilizando el puerto 4532. Si cambia el puerto en la interfaz de usuario, actualice su software/registrador externo para que coincida.


## 7. Limitaciones de Hardware y Calibración

### Nota Importante para Usuarios de SPA-1 / Optima
Dado que el desarrollador utiliza actualmente la versión **FTX-1 Field** (autónoma de 10W), el sistema de telemetría está ajustado específicamente para operaciones portátiles de baja potencia.

* **Precisión de PO (Potencia de Salida)**: La escala de vatios y la desviación del medidor están calibradas para el PA interno de 10W. Para usuarios de 100W, el medidor puede alcanzar el techo prematuramente o mostrar una escala incorrecta.
* **Precisión de IDD (Corriente de Drenaje)**: El medidor IDD está calibrado actualmente para el consumo típico de la unidad Field (máx. alrededor de 2A). La operación a 100W requiere una corriente significativamente mayor, que aún no está mapeada con precisión en esta interfaz.

---

## 8. Nota sobre la Calibración de SPA-1 (100W)

Actualmente, este software se desarrolla y prueba utilizando la versión **FTX-1 Field (10W autónoma)**. Debido a que no tengo el amplificador **Optima SPA-1 (100W)** en mi escritorio, los medidores de **Potencia (PO)** y **Corriente (IDD)** aún no están completamente calibrados para operaciones de alta potencia.

**¡Necesito tu ayuda!** Si estás utilizando la configuración Optima SPA-1, el software podría mostrar lecturas de potencia y corriente inexactas. Si deseas ayudarme a mejorar esto para toda la comunidad, te estaría increíblemente agradecido si pudieras compartir algunas fotos o un clip corto de la pantalla de tu radio mostrando las lecturas de PO e IDD en diferentes niveles de potencia.

Tus datos me ayudarán a ajustar las matemáticas detrás de estos medidores para que funcionen perfectamente para cada propietario de FTX-1. ¡No dudes en contactar a través del repositorio del proyecto!

---
