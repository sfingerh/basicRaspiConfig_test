from __future__ import annotations

import os
import socket
import threading
import time
from collections import deque
from datetime import datetime, time as dt_time
from subprocess import check_output

import RPi.GPIO as GPIO
import requests
from flask import Flask, jsonify, render_template, request, send_from_directory

from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# === Rutas (según tu proyecto) ===
BASE_DIR = "/home/qwid94/sqc-main"
PHOTO_FOLDER = f"{BASE_DIR}/fotos"

# === Estado global ===
auto = False
t = 0                 # intervalo en ms
t_exp = 1             # exposición (seg)
n_foto = 0
txt = ""
ssid = ""
ip = ""

# Solo noche
dia = True
dia_block = True
horario_dia_inicio = dt_time(6, 0, 0)
horario_dia_fin = dt_time(20, 30, 0)

# Loop timers
now_pre3 = 0

# === Mensajería web (para /send_message) ===
MSG_LOCK = threading.Lock()
MSG_QUEUE = deque(maxlen=200)  # mensajes pendientes para el browser


def push_msg(msg: str) -> None:
    with MSG_LOCK:
        MSG_QUEUE.append(f"{datetime.now().strftime('%H:%M:%S')} | {msg}")


def pop_msg() -> str:
    with MSG_LOCK:
        if MSG_QUEUE:
            return MSG_QUEUE.popleft()
    return ""


# === Display OLED I2C 0.96" ===
# OJO:
# - Muchos módulos indican 0x78 impreso, pero en Python/luma normalmente se usa 0x3C.
# - Si no responde, revisar con: i2cdetect -y 1
# - Si aparece 3d, cambiar address=0x3D
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial, width=128, height=64, rotate=0)


def get_latest_photo() -> str | None:
    try:
        latest_photo = max(
            (
                os.path.join(PHOTO_FOLDER, f)
                for f in os.listdir(PHOTO_FOLDER)
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".cr2"))
            ),
            key=os.path.getctime,
        )
        return os.path.basename(latest_photo)
    except ValueError:
        return None


@app.route("/")
def index():
    photo_name = get_latest_photo()
    return render_template("index.html", photo_name=photo_name)


@app.route("/photos/<filename>")
def get_photo(filename):
    return send_from_directory(PHOTO_FOLDER, filename)


@app.route("/latest_photo")
def latest_photo():
    return jsonify({"photo_name": get_latest_photo()})


@app.route("/send_message", methods=["POST"])
def send_message():
    """
    - Si llega {"message": "..."} -> lo encola (push)
    - Si llega vacío -> responde con el siguiente mensaje pendiente (pop)
    """
    data = request.get_json(silent=True) or {}
    incoming = data.get("message")

    if incoming:
        push_msg(str(incoming))
        return jsonify({"ok": True}), 200

    out = pop_msg()
    return jsonify({"message": out}), 200


@app.route("/action", methods=["POST"])
def action():
    global auto, t, t_exp, n_foto, txt, dia_block, now_pre3

    data = request.get_json(silent=True) or {}
    button = data.get("button")
    tiempo_min = data.get("time")               # minutos
    exposure_time = data.get("exposureTime")    # segundos
    night_mode = data.get("nightMode")          # bool

    if exposure_time is not None:
        try:
            t_exp = int(exposure_time)
        except Exception:
            pass

    # night_mode=True => "Solo Noche" activado => bloquea de día
    if night_mode is not None:
        dia_block = bool(night_mode)

    if button == "Button 1":
        name = Foto()
        n_foto += 1
        message = f"Foto: {name}"
        txt = f"Foto n° {n_foto}"
        push_msg(message)

    elif button == "Button 2":
        auto = True
        try:
            t = int(tiempo_min) * 60 * 1000
        except Exception:
            t = 5 * 60 * 1000  # default 5 min

        now_pre3 = 0
        n_foto = 0
        message = f"Auto ON | cada {t//60000} min | exposición {t_exp}s | Solo Noche={dia_block}"
        txt = "Auto ON"
        push_msg(message)

    elif button == "Button 3":
        auto = False
        message = "Auto OFF"
        txt = "Auto OFF"
        push_msg(message)

    elif button == "Shutdown":
        message = "Apagando sistema..."
        txt = "Apagando ..."
        push_msg(message)

    elif button == "Reboot":
        message = "Reiniciando sistema..."
        txt = "Reiniciando ..."
        push_msg(message)

    else:
        message = "Acción desconocida"
        push_msg(message)

    return jsonify({"message": message}), 200


def background_task():
    global auto, t, txt, ssid, ip, now_pre3

    time.sleep(1)

    # === GPIO RGB (según tu app original) ===
    LED_B = 5
    LED_R = 26
    LED_G = 6

    LED_def = LED_R
    LED_state = False
    LED_P = False
    LED_interval = 2000
    texto_interval = 1000

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_B, GPIO.OUT)
    GPIO.setup(LED_R, GPIO.OUT)
    GPIO.setup(LED_G, GPIO.OUT)

    # Lógica active-low:
    # HIGH = apagado
    # LOW = encendido
    GPIO.output(LED_B, GPIO.HIGH)
    GPIO.output(LED_R, GPIO.HIGH)
    GPIO.output(LED_G, GPIO.HIGH)

    txt = "Iniciando..."
    texto_medio(device, txt)
    LED_P = False
    LED_def = LED_R
    LED_state = False
    LED_act(LED_def, LED_state)
    time.sleep(3)

    now_pre = 0
    now_pre2 = 0
    now_pre3 = 0
    now_pre4 = 0

    last_wifi = ""
    last_ip = ""
    last_txt = ""
    cambio = False

    while True:
        now = millis()
        if (now - now_pre) >= LED_interval:
            now_pre = now
            if LED_P:
                LED_state = not LED_state
            LED_act(LED_def, LED_state)

        now2 = millis()
        if (now2 - now_pre2) >= texto_interval:
            now_pre2 = now2

            if txt == "Apagando ...":
                texto_medio(device, txt)
                time.sleep(2)
                os.system("sudo shutdown -h 0")

            elif txt == "Reiniciando ...":
                texto_medio(device, txt)
                time.sleep(2)
                os.system("sudo reboot")

            if ssid != last_wifi:
                last_wifi = ssid
                os.system("sudo systemctl restart nginx")
                cambio = True

            if ip != last_ip:
                last_ip = ip
                cambio = True

            if txt != last_txt:
                last_txt = txt
                cambio = True

            if cambio:
                cambio = False
                txt1 = f"WIFI:{ssid}"
                txt2 = f"IP:{ip}"
                txt3 = f"SYS:{txt}"
                texto_act(device, txt1, txt2, txt3)
                time.sleep(1.5)
                txt = "OK"
                texto_act(device, f"WIFI:{ssid}", f"IP:{ip}", f"SYS:{txt}")

        now3 = millis()
        if auto and t > 0 and (now3 - now_pre3) >= t:
            name = Foto()
            msg = f"Foto: {name}"
            now_pre3 = now3
            push_msg(msg)

        now4 = millis()
        if (now4 - now_pre4) >= 10000:
            now_pre4 = now4
            ssid, ip = CheqRed()

            if ssid == "WiFi-not":
                if ip == "192.168.50.5":
                    GPIO.output(LED_def, GPIO.HIGH)
                    LED_P = False
                    LED_def = LED_B
                    LED_state = False
                    LED_act(LED_def, LED_state)
                    ssid = "SQC01"
                    txt = "Modo AP"
                else:
                    GPIO.output(LED_def, GPIO.HIGH)
                    LED_P = True
                    LED_def = LED_R
                    LED_state = True
                    LED_act(LED_def, LED_state)
                    ssid = " - "
                    ip = " - "
                    txt = "Sin RED"
            else:
                GPIO.output(LED_def, GPIO.HIGH)
                LED_P = False
                LED_def = LED_G
                LED_state = False
                LED_act(LED_def, LED_state)


def LED_act(pin, state):
    GPIO.output(pin, state)


def get_font():
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def texto_medio(device, txt1):
    image = Image.new("1", (device.width, device.height), 0)
    draw = ImageDraw.Draw(image)
    font = get_font()

    txt1 = str(txt1)[:20]
    x = 8
    y = 28
    draw.text((x, y), txt1, fill=255, font=font)
    device.display(image)


def texto_act(device, txt1, txt2, txt3):
    image = Image.new("1", (device.width, device.height), 0)
    draw = ImageDraw.Draw(image)
    font = get_font()

    # Máximo aprox 21 caracteres por línea con la fuente por defecto
    draw.text((0, 0),  str(txt1)[:21], fill=255, font=font)
    draw.text((0, 20), str(txt2)[:21], fill=255, font=font)
    draw.text((0, 40), str(txt3)[:21], fill=255, font=font)
    device.display(image)


def millis():
    return int(round(time.time() * 1000))


def es_dia_o_noche():
    global dia
    ahora = datetime.now().time()
    dia = horario_dia_inicio <= ahora <= horario_dia_fin


def Foto():
    global dia, dia_block, t_exp

    # Si "Solo Noche" está activo y es de día => bloquea
    if dia_block:
        es_dia_o_noche()
        if dia:
            return "block"

    os.makedirs(PHOTO_FOLDER, exist_ok=True)

    # Evita bloqueos de procesos gphoto2
    os.system("pkill -f gphoto2 >/dev/null 2>&1")
    time.sleep(0.5)

    now = datetime.now()
    stamp = now.strftime("%Y-%m-%d_%H-%M-%S")

    # OJO: CR2 no se ve en navegador. Si quieres vista web, guarda JPG o preview.
    filename = os.path.join(PHOTO_FOLDER, f"{stamp}.cr2")

    # Disparo / descarga
    os.system('gphoto2 --set-config eosremoterelease=Immediate')
    os.system(f"sleep {int(t_exp)}")
    os.system('gphoto2 --set-config eosremoterelease="Release Full"')
    os.system(f'gphoto2 --wait-event-and-download=30s --filename="{filename}" --force-overwrite')

    return os.path.basename(filename)


def CheqRed():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_local = str(s.getsockname()[0])
        s.close()
        try:
            red = check_output(["iwgetid", "-r"]).decode("utf-8").strip()
            if not red:
                red = "WiFi-not"
            return red, ip_local
        except Exception:
            return "WiFi-not", ip_local
    except Exception:
        return "WiFi-not", "1.1.1.1"


if __name__ == "__main__":
    try:
        thread = threading.Thread(target=background_task, daemon=True)
        thread.start()
        app.run(host="0.0.0.0", port=5001, debug=False)
    finally:
        GPIO.cleanup()
