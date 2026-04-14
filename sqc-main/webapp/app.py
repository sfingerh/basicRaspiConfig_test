from __future__ import annotations

import os
import socket
import subprocess
import threading
import time
from collections import deque
from datetime import datetime, time as dt_time
from typing import Optional

import RPi.GPIO as GPIO
from flask import Flask, jsonify, render_template, request, send_from_directory
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# ==========================================================
# Rutas y configuración general
# ==========================================================
BASE_DIR = "/home/sqc/sqc-main"
WEBAPP_DIR = os.path.join(BASE_DIR, "webapp")
PHOTO_FOLDER = os.path.join(BASE_DIR, "fotos")
ACCESSPOPUP_LOCAL_BIN = os.path.join(WEBAPP_DIR, "AccessPopup", "accesspopup")
ACCESSPOPUP_SYSTEM_BIN = "accesspopup"

DISPLAY_I2C_PORT = 1
DISPLAY_I2C_ADDRESS = 0x3C
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
DISPLAY_ROTATE = 0

# Botón a GND con pull-up interno
BUTTON_PIN = 26

# LED RGB ánodo común
LED_R_PIN = 23
LED_G_PIN = 24
LED_B_PIN = 12

# En ánodo común: LOW = encendido, HIGH = apagado
LED_ON = GPIO.LOW
LED_OFF = GPIO.HIGH

DISPLAY_TIMEOUT_S = 120.0
LED_TIMEOUT_S = 120.0
LED_FLASH_PERIOD_S = 2.0
LED_FLASH_WIDTH_S = 0.08
BUTTON_DEBOUNCE_S = 0.03
BUTTON_LONGPRESS_AP_S = 3.0
BUTTON_LONGPRESS_REBOOT_S = 10.0
TRIPLE_PRESS_WINDOW_S = 1.2

SUDO_REBOOT_CMD = ["sudo", "-n", "/usr/sbin/reboot"]
SUDO_SHUTDOWN_CMD = ["sudo", "-n", "/usr/sbin/shutdown", "-h", "now"]

# Solo noche
horario_dia_inicio = dt_time(6, 0, 0)
horario_dia_fin = dt_time(20, 30, 0)

# ==========================================================
# Estado global
# ==========================================================
STATE_LOCK = threading.Lock()
MSG_LOCK = threading.Lock()
PHOTO_LOCK = threading.Lock()

MSG_QUEUE = deque(maxlen=200)

serial_if = None
oled = None
font_default = None
font_big = None

auto = False
interval_ms = 5 * 60 * 1000
next_auto_shot_ms = 0
exposure_s = 1
photo_count = 0
night_only = False

status_text = "Iniciando..."
status_until_monotonic = 0.0
system_error_latched = False

ssid = "-"
ip_addr = "-"
network_mode = "OFF"   # WIFI / AP / OFF

startup_ready = False
startup_fault_latched = False
startup_fault_reason = ""
shutdown_in_progress = False

camera_detected_on_boot = False
display_detected_on_boot = False

display_available = False
camera_available = False

last_user_activity = time.monotonic()
last_led_flash = 0.0


# ==========================================================
# Utilidades básicas
# ==========================================================
def now_ms() -> int:
    return int(time.monotonic() * 1000)


def trim(txt: object, max_len: int = 21) -> str:
    s = str(txt)
    return s[:max_len]


def push_msg(msg: str) -> None:
    with MSG_LOCK:
        MSG_QUEUE.append(f"{datetime.now().strftime('%H:%M:%S')} | {msg}")


def pop_msg() -> str:
    with MSG_LOCK:
        if MSG_QUEUE:
            return MSG_QUEUE.popleft()
    return ""


def get_font():
    global font_default
    if font_default is None:
        try:
            font_default = ImageFont.load_default()
        except Exception:
            font_default = None
    return font_default


def get_big_font():
    global font_big
    if font_big is None:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    font_big = ImageFont.truetype(path, 22)
                    break
                except Exception:
                    pass
        if font_big is None:
            try:
                font_big = ImageFont.load_default()
            except Exception:
                font_big = None
    return font_big


def outputs_awake() -> bool:
    if shutdown_in_progress:
        return True
    if startup_fault_latched:
        return True
    if not startup_ready:
        return True
    return (time.monotonic() - last_user_activity) < max(DISPLAY_TIMEOUT_S, LED_TIMEOUT_S)


def touch_user_activity() -> None:
    global last_user_activity
    last_user_activity = time.monotonic()
    update_display(force=True)


def current_mode_label() -> str:
    if auto:
        mins = max(1, interval_ms // 60000)
        return f"AUTO {mins}m"
    return "MANUAL"


def safe_run(cmd: list[str], timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# ==========================================================
# Display OLED
# ==========================================================
def init_display() -> tuple[bool, str]:
    global serial_if, oled, display_available, display_detected_on_boot
    try:
        serial_if = i2c(port=DISPLAY_I2C_PORT, address=DISPLAY_I2C_ADDRESS)
        oled = ssd1306(serial_if, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, rotate=DISPLAY_ROTATE)
        display_available = True
        display_detected_on_boot = True
        clear_display(force=True)
        return True, "Display OK"
    except Exception as exc:
        display_available = False
        oled = None
        display_detected_on_boot = False
        return False, f"Display no detectado: {exc}"


def clear_display(force: bool = False) -> None:
    if not display_available or oled is None:
        return
    if not force and not outputs_awake():
        return
    try:
        image = Image.new("1", (oled.width, oled.height), 0)
        oled.display(image)
    except Exception:
        pass


def shutdown_display() -> None:
    if not display_available or oled is None:
        return
    try:
        image = Image.new("1", (oled.width, oled.height), 0)
        oled.display(image)
    except Exception:
        pass


def draw_center_message(line1: str, line2: str = "", line3: str = "") -> None:
    if not display_available or oled is None:
        return
    try:
        image = Image.new("1", (oled.width, oled.height), 0)
        draw = ImageDraw.Draw(image)
        font = get_font()
        lines = [trim(line1, 20), trim(line2, 20), trim(line3, 20)]
        y_positions = [8, 26, 44]
        for y, txt in zip(y_positions, lines):
            if txt:
                draw.text((6, y), txt, fill=255, font=font)
        oled.display(image)
    except Exception:
        pass


def draw_big_message(msg: str) -> None:
    if not display_available or oled is None:
        return
    try:
        image = Image.new("1", (oled.width, oled.height), 0)
        draw = ImageDraw.Draw(image)
        font = get_big_font()

        raw = str(msg).strip()
        if " " in raw:
            words = raw.split()
            mid = max(1, len(words) // 2)
            lines = [" ".join(words[:mid]), " ".join(words[mid:])]
        elif len(raw) > 10:
            mid = len(raw) // 2
            lines = [raw[:mid], raw[mid:]]
        else:
            lines = [raw]

        lines = [trim(line, 12) for line in lines if line]

        if len(lines) == 1:
            y_positions = [20]
        else:
            y_positions = [10, 34]

        for y, line in zip(y_positions, lines[:2]):
            if hasattr(draw, "textbbox") and font is not None:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
            else:
                text_w = len(line) * 12
                text_h = 16

            x = max(0, (oled.width - text_w) // 2)
            draw.text((x, y), line, fill=255, font=font)

        oled.display(image)
    except Exception:
        pass


def update_display(force: bool = False) -> None:
    if not display_available or oled is None:
        return

    if not force and not outputs_awake():
        shutdown_display()
        return

    try:
        image = Image.new("1", (oled.width, oled.height), 0)
        draw = ImageDraw.Draw(image)
        font = get_font()

        if network_mode == "WIFI" and ssid not in ("", "-"):
            net_label = f"SSID:{ssid}"
        elif network_mode == "AP":
            net_label = f"NET:{ssid}" if ssid not in ("", "-") else "NET:AP"
        else:
            net_label = f"NET:{network_mode}"
        ip_label = f"IP:{ip_addr}"
        mode_label = f"MODO:{current_mode_label()}"
        msg_label = effective_status_line()

        draw.text((0, 0), trim(net_label, 21), fill=255, font=font)
        draw.text((0, 16), trim(ip_label, 21), fill=255, font=font)
        draw.text((0, 32), trim(mode_label, 21), fill=255, font=font)
        draw.text((0, 48), msg_label, fill=255, font=font)
        oled.display(image)
    except Exception:
        pass


# ==========================================================
# LED RGB ánodo común
# ==========================================================
def init_gpio() -> None:
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    GPIO.setup(LED_R_PIN, GPIO.OUT)
    GPIO.setup(LED_G_PIN, GPIO.OUT)
    GPIO.setup(LED_B_PIN, GPIO.OUT)
    led_off_all()


def led_off_all() -> None:
    GPIO.output(LED_R_PIN, LED_OFF)
    GPIO.output(LED_G_PIN, LED_OFF)
    GPIO.output(LED_B_PIN, LED_OFF)


def led_set(color: str) -> None:
    led_off_all()
    if color == "red":
        GPIO.output(LED_R_PIN, LED_ON)
    elif color == "green":
        GPIO.output(LED_G_PIN, LED_ON)
    elif color == "blue":
        GPIO.output(LED_B_PIN, LED_ON)


def led_short_flash(color: str, width_s: float = LED_FLASH_WIDTH_S) -> None:
    if startup_fault_latched or shutdown_in_progress:
        return
    if not outputs_awake():
        led_off_all()
        return
    led_set(color)
    time.sleep(width_s)
    led_off_all()


# ==========================================================
# Estado y mensajes
# ==========================================================
def default_system_status_line() -> str:
    if startup_fault_latched or system_error_latched:
        return "Sistema: Error"
    return "Sistema: OK"


def effective_status_line() -> str:
    if shutdown_in_progress:
        return trim(status_text, 21)
    if time.monotonic() < status_until_monotonic:
        return trim(status_text, 21)
    return trim(default_system_status_line(), 21)


def set_status(
    msg: str,
    *,
    notify_web: bool = False,
    wake_outputs: bool = False,
    transient_s: Optional[float] = None,
    error_state: Optional[bool] = None,
) -> None:
    global status_text, status_until_monotonic, system_error_latched

    status_text = msg

    if transient_s is not None:
        status_until_monotonic = time.monotonic() + max(0.0, transient_s)
    else:
        status_until_monotonic = 0.0

    if error_state is True:
        system_error_latched = True
    elif error_state is False:
        system_error_latched = False

    if notify_web:
        push_msg(msg)

    if wake_outputs:
        touch_user_activity()
    else:
        update_display(force=False)



def latch_startup_fault(reason: str) -> None:
    global startup_fault_latched, startup_fault_reason
    startup_fault_latched = True
    startup_fault_reason = reason
    set_status(f"FALLO: {reason}", notify_web=True, wake_outputs=True, transient_s=3.0, error_state=True)
    led_set("red")


# ==========================================================
# Cámara y fotos
# ==========================================================
def detect_camera() -> tuple[bool, str]:
    global camera_available, camera_detected_on_boot
    try:
        proc = safe_run(["gphoto2", "--auto-detect"], timeout=20)
        text = (proc.stdout or "") + "\n" + (proc.stderr or "")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        found = any(
            ("usb:" in ln.lower()) or ("ptp" in ln.lower()) or ("canon" in ln.lower())
            for ln in lines
        )

        camera_available = found and proc.returncode == 0
        camera_detected_on_boot = camera_available
        if camera_available:
            return True, "Camara OK"
        return False, "Camara no detectada"
    except Exception as exc:
        camera_available = False
        camera_detected_on_boot = False
        return False, f"Camara no detectada: {exc}"


def is_daytime() -> bool:
    now_t = datetime.now().time()
    return horario_dia_inicio <= now_t <= horario_dia_fin


def get_latest_photo() -> Optional[str]:
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
    except Exception:
        return None


def take_photo(*, source: str = "manual", wake_outputs: bool = True) -> tuple[bool, str, Optional[str]]:
    global photo_count, camera_available

    if night_only and is_daytime():
        msg = "Foto bloqueada: modo solo noche"
        set_status("Bloq. por dia", notify_web=True, wake_outputs=wake_outputs, transient_s=3.0)
        return False, msg, None

    if not PHOTO_LOCK.acquire(blocking=False):
        msg = "Foto no ejecutada: captura en curso"
        set_status("Foto ocupada", notify_web=True, wake_outputs=wake_outputs, transient_s=3.0)
        return False, msg, None

    try:
        os.makedirs(PHOTO_FOLDER, exist_ok=True)
        set_status("Tomando foto...", notify_web=True, wake_outputs=wake_outputs, transient_s=3.0)

        try:
            subprocess.run(
                ["pkill", "-f", "gphoto2"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
        except Exception:
            pass

        time.sleep(0.5)

        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(PHOTO_FOLDER, f"{stamp}.cr2")

        step1 = safe_run(["gphoto2", "--set-config", "eosremoterelease=Immediate"], timeout=20)
        if step1.returncode != 0:
            msg = "No se pudo iniciar el disparo"
            set_status("Error en camara", notify_web=True, wake_outputs=wake_outputs, transient_s=3.0, error_state=True)
            camera_available = False
            return False, msg, None

        time.sleep(max(1, int(exposure_s)))

        step2 = safe_run(["gphoto2", "--set-config", "eosremoterelease=Release Full"], timeout=20)
        if step2.returncode != 0:
            msg = "No se pudo liberar el disparo"
            set_status("Error release", notify_web=True, wake_outputs=wake_outputs, transient_s=3.0, error_state=True)
            camera_available = False
            return False, msg, None

        step3 = safe_run(
            [
                "gphoto2",
                "--wait-event-and-download=30s",
                f"--filename={filename}",
                "--force-overwrite",
            ],
            timeout=45,
        )

        file_ok = os.path.exists(filename) and os.path.getsize(filename) > 0
        if step3.returncode == 0 and file_ok:
            photo_count += 1
            camera_available = True
            msg = f"Foto OK: {os.path.basename(filename)}"
            set_status("Foto tomada", notify_web=True, wake_outputs=wake_outputs, transient_s=3.0, error_state=False)
            return True, msg, os.path.basename(filename)

        stderr_text = (step3.stderr or "").strip()
        stdout_text = (step3.stdout or "").strip()
        detail = stderr_text or stdout_text or "sin detalle"
        msg = f"No se pudo tomar la foto: {detail}"
        set_status("Foto fallida", notify_web=True, wake_outputs=wake_outputs, transient_s=3.0, error_state=True)
        camera_available = False
        return False, msg, None

    except Exception as exc:
        msg = f"No se pudo tomar la foto: {exc}"
        set_status("Foto fallida", notify_web=True, wake_outputs=wake_outputs, transient_s=3.0, error_state=True)
        camera_available = False
        return False, msg, None

    finally:
        PHOTO_LOCK.release()


# ==========================================================
# Red y AccessPopup
# ==========================================================
def check_network() -> tuple[str, str, str]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = str(s.getsockname()[0])
        s.close()
    except Exception:
        local_ip = "-"

    try:
        ssid_now = subprocess.check_output(["iwgetid", "-r"], text=True, timeout=5).strip()
    except Exception:
        ssid_now = ""

    if ssid_now:
        return ssid_now, local_ip, "WIFI"

    if local_ip.startswith("192.168.50."):
        return "SQC-AP", local_ip, "AP"

    return "-", local_ip, "OFF"


def refresh_network_state() -> None:
    global ssid, ip_addr, network_mode
    ssid, ip_addr, network_mode = check_network()
    update_display(force=False)


def apply_runtime_settings(
    *,
    tiempo_min: Optional[object] = None,
    exposure_time: Optional[object] = None,
    night_mode: Optional[object] = None,
) -> dict[str, object]:
    global interval_ms, exposure_s, night_only, next_auto_shot_ms

    changed = {
        "interval_changed": False,
        "exposure_changed": False,
        "night_changed": False,
    }

    if exposure_time is not None:
        try:
            new_exposure = max(1, int(exposure_time))
            if new_exposure != exposure_s:
                exposure_s = new_exposure
                changed["exposure_changed"] = True
        except Exception:
            pass

    if tiempo_min is not None:
        try:
            new_interval_ms = max(1, int(tiempo_min)) * 60 * 1000
            if new_interval_ms != interval_ms:
                interval_ms = new_interval_ms
                changed["interval_changed"] = True
                if auto:
                    next_auto_shot_ms = now_ms() + interval_ms
        except Exception:
            pass

    if night_mode is not None:
        try:
            new_night_only = bool(night_mode)
            if new_night_only != night_only:
                night_only = new_night_only
                changed["night_changed"] = True
        except Exception:
            pass

    return changed


def run_accesspopup(args: list[str]) -> tuple[bool, str]:
    candidates = []
    if os.path.exists(ACCESSPOPUP_LOCAL_BIN):
        candidates.append(["sudo", "-n", ACCESSPOPUP_LOCAL_BIN] + args)
    candidates.append(["sudo", "-n", ACCESSPOPUP_SYSTEM_BIN] + args)

    last_error = "accesspopup no disponible"
    for cmd in candidates:
        try:
            proc = safe_run(cmd, timeout=40)
            if proc.returncode == 0:
                return True, (proc.stdout or proc.stderr or "OK").strip()
            last_error = (proc.stderr or proc.stdout or f"codigo {proc.returncode}").strip()
        except Exception as exc:
            last_error = str(exc)
    return False, last_error


def toggle_ap_wifi() -> tuple[bool, str]:
    set_status("Conmutando red...", notify_web=True, wake_outputs=True, transient_s=3.0)
    refresh_network_state()

    if network_mode == "AP":
        ok, detail = run_accesspopup([])
        action_name = "AP -> WIFI"
    else:
        ok, detail = run_accesspopup(["-a"])
        action_name = "WIFI -> AP"

    if ok:
        time.sleep(5)
        refresh_network_state()
        msg = f"{action_name}"
        set_status(msg, notify_web=True, wake_outputs=True, transient_s=3.0, error_state=False)
        return True, msg

    msg = f"No se pudo conmutar red: {detail}"
    set_status("Error AccessPopup", notify_web=True, wake_outputs=True, transient_s=3.0, error_state=True)
    return False, msg


# ==========================================================
# Acciones del sistema
# ==========================================================
def run_privileged_command(cmd: list[str]) -> tuple[bool, str]:
    try:
        proc = safe_run(cmd, timeout=20)
        if proc.returncode == 0:
            return True, (proc.stdout or proc.stderr or "OK").strip()
        return False, (proc.stderr or proc.stdout or f"codigo {proc.returncode}").strip()
    except Exception as exc:
        return False, str(exc)


def system_power_action(action: str) -> None:
    global shutdown_in_progress

    if shutdown_in_progress:
        return

    shutdown_in_progress = True

    if action == "reboot":
        web_msg = "Reiniciando sistema..."
        display_msg = "REINICIANDO ..."
        cmd = SUDO_REBOOT_CMD
        fallback_status = "Error reboot"
    elif action == "shutdown":
        web_msg = "Apagando sistema..."
        display_msg = "APAGANDO ..."
        cmd = SUDO_SHUTDOWN_CMD
        fallback_status = "Error apagado"
    else:
        shutdown_in_progress = False
        return

    push_msg(web_msg)
    set_status(display_msg, notify_web=False, wake_outputs=True, transient_s=3.0)
    draw_big_message(display_msg)
    time.sleep(2)
    shutdown_display()
    led_off_all()

    ok, detail = run_privileged_command(cmd)
    if not ok:
        shutdown_in_progress = False
        set_status(fallback_status, notify_web=True, wake_outputs=True, transient_s=3.0, error_state=True)
        push_msg(f"No se pudo ejecutar {action}: {detail}")
        led_set("red")


# ==========================================================
# Botón local
# ==========================================================
def start_manual_photo_from_button() -> None:
    threading.Thread(
        target=take_photo,
        kwargs={"source": "button", "wake_outputs": True},
        daemon=True,
    ).start()


def button_task() -> None:
    press_start = None
    reboot_sent = False
    click_times: deque[float] = deque(maxlen=3)
    last_state = GPIO.input(BUTTON_PIN)

    while True:
        try:
            state = GPIO.input(BUTTON_PIN)
            now = time.monotonic()

            # Pulsado (pull-up, presionado = LOW)
            if last_state == GPIO.HIGH and state == GPIO.LOW:
                press_start = now
                reboot_sent = False
                touch_user_activity()

            # Mantenido pulsado
            if state == GPIO.LOW and press_start is not None:
                held = now - press_start
                if held >= BUTTON_LONGPRESS_REBOOT_S and not reboot_sent:
                    reboot_sent = True
                    click_times.clear()
                    threading.Thread(target=system_power_action, args=("reboot",), daemon=True).start()

            # Soltado
            if last_state == GPIO.LOW and state == GPIO.HIGH and press_start is not None:
                held = now - press_start
                press_start = None

                if reboot_sent:
                    last_state = state
                    time.sleep(0.02)
                    continue

                if held >= BUTTON_LONGPRESS_AP_S:
                    click_times.clear()
                    threading.Thread(target=toggle_ap_wifi, daemon=True).start()
                elif held >= BUTTON_DEBOUNCE_S:
                    click_times.append(now)
                    while click_times and (now - click_times[0]) > TRIPLE_PRESS_WINDOW_S:
                        click_times.popleft()
                    if len(click_times) == 3:
                        click_times.clear()
                        start_manual_photo_from_button()

            last_state = state
            time.sleep(0.02)

        except Exception as exc:
            push_msg(f"Error boton: {exc}")
            time.sleep(0.2)


# ==========================================================
# Supervisor principal
# ==========================================================
def startup_animation_task() -> None:
    colors = ["red", "green", "blue"]
    idx = 0

    while not startup_ready and not startup_fault_latched and not shutdown_in_progress:
        led_set(colors[idx])
        time.sleep(1.0)
        led_off_all()
        idx = (idx + 1) % len(colors)

    if startup_fault_latched:
        led_set("red")
    else:
        led_off_all()


def heartbeat_led_task() -> None:
    global last_led_flash

    while True:
        if shutdown_in_progress:
            led_off_all()
            time.sleep(0.2)
            continue

        if startup_fault_latched:
            led_set("red")
            time.sleep(0.2)
            continue

        if not startup_ready:
            time.sleep(0.2)
            continue

        if not outputs_awake():
            led_off_all()
            time.sleep(0.2)
            continue

        now = time.monotonic()
        if (now - last_led_flash) >= LED_FLASH_PERIOD_S:
            last_led_flash = now
            if network_mode == "WIFI":
                led_short_flash("green")
            elif network_mode == "AP":
                led_short_flash("blue")
            else:
                led_short_flash("red")
        else:
            time.sleep(0.05)


def supervisor_task() -> None:
    global startup_ready, next_auto_shot_ms

    anim_thread = threading.Thread(target=startup_animation_task, daemon=True)
    anim_thread.start()

    set_status("Iniciando...", notify_web=True, wake_outputs=True, transient_s=3.0)

    ok_display, msg_display = init_display()
    if ok_display:
        draw_center_message("Iniciando...", "Display OK", "")
    else:
        push_msg(msg_display)

    ok_camera, msg_camera = detect_camera()
    push_msg(msg_camera)

    refresh_network_state()

    # Sin cámara se permite iniciar; sin display sí queda en fallo.
    if not ok_display:
        latch_startup_fault("display")
    else:
        set_status("Sistema listo", notify_web=True, wake_outputs=True, transient_s=3.0, error_state=False)
        if not ok_camera:
            push_msg("Aviso: sistema iniciado sin camara")

    startup_ready = True
    next_auto_shot_ms = now_ms() + interval_ms
    update_display(force=True)

    last_net_check = 0.0
    last_display_refresh = 0.0

    while True:
        try:
            now = time.monotonic()

            if (now - last_net_check) >= 5.0:
                last_net_check = now
                refresh_network_state()

            if (now - last_display_refresh) >= 0.5:
                last_display_refresh = now
                update_display(force=False)

            if auto and not shutdown_in_progress and interval_ms > 0 and now_ms() >= next_auto_shot_ms:
                next_auto_shot_ms = now_ms() + interval_ms
                threading.Thread(
                    target=take_photo,
                    kwargs={"source": "auto", "wake_outputs": False},
                    daemon=True,
                ).start()

            time.sleep(0.1)

        except Exception as exc:
            push_msg(f"Supervisor error: {exc}")
            time.sleep(1.0)


# ==========================================================
# Rutas Flask
# ==========================================================
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
    data = request.get_json(silent=True) or {}
    incoming = data.get("message")

    if incoming:
        push_msg(str(incoming))
        return jsonify({"ok": True}), 200

    out = pop_msg()
    return jsonify({"message": out}), 200


@app.route("/settings", methods=["POST"])
def update_settings():
    data = request.get_json(silent=True) or {}
    tiempo_min = data.get("time")
    exposure_time = data.get("exposureTime")
    night_mode = data.get("nightMode")

    touch_user_activity()
    changed = apply_runtime_settings(
        tiempo_min=tiempo_min,
        exposure_time=exposure_time,
        night_mode=night_mode,
    )

    parts = []
    if changed["night_changed"]:
        parts.append(f"Solo noche={'ON' if night_only else 'OFF'}")
    if changed["exposure_changed"]:
        parts.append(f"Exp={exposure_s}s")
    if changed["interval_changed"]:
        parts.append(f"Auto={interval_ms // 60000} min")

    if not parts:
        msg = "Configuracion sin cambios"
    else:
        msg = "Configuracion actualizada | " + " | ".join(parts)

    set_status(msg, notify_web=True, wake_outputs=True, transient_s=3.0, error_state=False)
    return jsonify(
        {
            "message": msg,
            "ok": True,
            "nightOnly": night_only,
            "exposureTime": exposure_s,
            "intervalMin": interval_ms // 60000,
        }
    ), 200


@app.route("/action", methods=["POST"])
def action():
    global auto, interval_ms, exposure_s, night_only, next_auto_shot_ms

    data = request.get_json(silent=True) or {}
    button = data.get("button")
    tiempo_min = data.get("time")
    exposure_time = data.get("exposureTime")
    night_mode = data.get("nightMode")

    touch_user_activity()

    apply_runtime_settings(
        tiempo_min=tiempo_min,
        exposure_time=exposure_time,
        night_mode=night_mode,
    )

    if button == "Button 1":
        ok, msg, _ = take_photo(source="web", wake_outputs=True)
        return jsonify({"message": msg, "ok": ok}), 200

    if button == "Button 2":
        auto = True
        try:
            interval_ms = max(1, int(tiempo_min)) * 60 * 1000
        except Exception:
            interval_ms = 5 * 60 * 1000
        next_auto_shot_ms = now_ms() + interval_ms
        msg = f"Auto ON | cada {interval_ms // 60000} min | exp {exposure_s}s | solo noche={night_only}"
        set_status("Modo automatico", notify_web=True, wake_outputs=True, transient_s=3.0, error_state=False)
        push_msg(msg)
        return jsonify({"message": msg, "ok": True}), 200

    if button == "Button 3":
        auto = False
        msg = "Auto OFF"
        set_status("Modo manual", notify_web=True, wake_outputs=True, transient_s=3.0, error_state=False)
        return jsonify({"message": msg, "ok": True}), 200

    if button == "Shutdown":
        threading.Thread(target=system_power_action, args=("shutdown",), daemon=True).start()
        return jsonify({"message": "Apagando sistema...", "ok": True}), 200

    if button == "Reboot":
        threading.Thread(target=system_power_action, args=("reboot",), daemon=True).start()
        return jsonify({"message": "Reiniciando sistema...", "ok": True}), 200

    msg = "Accion desconocida"
    return jsonify({"message": msg, "ok": False}), 200


# ==========================================================
# Main
# ==========================================================
if __name__ == "__main__":
    try:
        init_gpio()

        threading.Thread(target=supervisor_task, daemon=True).start()
        threading.Thread(target=heartbeat_led_task, daemon=True).start()
        threading.Thread(target=button_task, daemon=True).start()

        app.run(host="0.0.0.0", port=5001, debug=False)
    finally:
        try:
            shutdown_display()
            led_off_all()
        finally:
            GPIO.cleanup()
