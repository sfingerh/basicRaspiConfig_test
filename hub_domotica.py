#!/usr/bin/env python3
# =============================================
# Hub Domótica - Raspberry Pi Zero 2W
# Modular + Clean Architecture
# Comments in English as requested
# =============================================

from modules.oled_manager import OLEDManager
import RPi.GPIO as GPIO
from flask import Flask, render_template_string, request
import threading
import time
from datetime import datetime

# ==========================================================
# Configuration
# ==========================================================
BUTTON_PIN = 26
LED_R_PIN = 23
LED_G_PIN = 24
LED_B_PIN = 12
LED_ON = GPIO.LOW
LED_OFF = GPIO.HIGH

# ==========================================================
# Global objects
# ==========================================================
app = Flask(__name__)
oled = OLEDManager()
led_state = "off"

# ==========================================================
# GPIO Setup
# ==========================================================
def setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(LED_R_PIN, GPIO.OUT)
    GPIO.setup(LED_G_PIN, GPIO.OUT)
    GPIO.setup(LED_B_PIN, GPIO.OUT)
    led_off_all()

def led_off_all():
    GPIO.output(LED_R_PIN, LED_OFF)
    GPIO.output(LED_G_PIN, LED_OFF)
    GPIO.output(LED_B_PIN, LED_OFF)

def led_set(color: str):
    global led_state
    led_off_all()
    if color == "red":
        GPIO.output(LED_R_PIN, LED_ON)
        led_state = "red"
    elif color == "green":
        GPIO.output(LED_G_PIN, LED_ON)
        led_state = "green"
    elif color == "blue":
        GPIO.output(LED_B_PIN, LED_ON)
        led_state = "blue"
    elif color == "off":
        led_state = "off"

# ==========================================================
# Button handling
# ==========================================================
button_press_count = 0
last_press_time = 0

def button_task():
    global button_press_count, last_press_time
    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
            now = time.monotonic()
            if now - last_press_time > 1.2:
                button_press_count = 1
            else:
                button_press_count += 1
            last_press_time = now
            oled.show_button_presses(button_press_count)
            while GPIO.input(BUTTON_PIN) == GPIO.LOW:
                time.sleep(0.01)
        time.sleep(0.05)

# ==========================================================
# Web Interface
# ==========================================================
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Hub Domótica</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; text-align: center; }
        .status { background: #ecf0f1; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .led-buttons { display: flex; gap: 10px; margin: 20px 0; }
        button { padding: 14px 24px; font-size: 16px; border: none; border-radius: 8px; cursor: pointer; flex: 1; }
        .btn-green { background: #27ae60; color: white; }
        .btn-red { background: #e74c3c; color: white; }
        .btn-blue { background: #3498db; color: white; }
        .btn-off { background: #7f8c8d; color: white; }
        input, button { width: 100%; margin: 8px 0; box-sizing: border-box; }
        .message-form { margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏠 Hub Domótica</h1>
        
        <div class="status">
            <strong>IP:</strong> 192.168.0.106<br>
            <strong>Estado:</strong> {{ status }}<br>
            <strong>LED:</strong> {{ led_state }}
        </div>

        <h3>Control de LED RGB</h3>
        <div class="led-buttons">
            <form action="/led" method="post" style="flex:1">
                <input type="hidden" name="color" value="green">
                <button type="submit" class="btn-green">LED VERDE ON</button>
            </form>
            <form action="/led" method="post" style="flex:1">
                <input type="hidden" name="color" value="red">
                <button type="submit" class="btn-red">LED ROJO ON</button>
            </form>
        </div>
        <div class="led-buttons">
            <form action="/led" method="post" style="flex:1">
                <input type="hidden" name="color" value="blue">
                <button type="submit" class="btn-blue">LED AZUL ON</button>
            </form>
            <form action="/led" method="post" style="flex:1">
                <input type="hidden" name="color" value="off">
                <button type="submit" class="btn-off">APAGAR LED</button>
            </form>
        </div>

        <div class="message-form">
            <h3>Enviar mensaje a la pantalla OLED</h3>
            <form action="/send_message" method="post">
                <input type="text" name="message" placeholder="Escribe tu mensaje..." required>
                <button type="submit">Enviar a la OLED</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE, status="Activo", led_state=led_state)

@app.route("/led", methods=["POST"])
def control_led():
    global led_state
    color = request.form.get("color", "off")
    led_set(color)
    return render_template_string(HTML_PAGE, status="LED actualizado", led_state=led_state)

@app.route("/send_message", methods=["POST"])
def send_message():
    message = request.form.get("message", "")
    if message:
        oled.show_custom_message(message)
        return render_template_string(HTML_PAGE, status="Mensaje enviado ✓", led_state=led_state)
    return "Error", 400

# ==========================================================
# Main
# ==========================================================
if __name__ == "__main__":
    print("🚀 Iniciando Hub Domótica...")
    setup_gpio()
    led_set("green")
    threading.Thread(target=button_task, daemon=True).start()
    app.run(host="0.0.0.0", port=5002, debug=False)
