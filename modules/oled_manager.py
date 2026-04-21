#!/usr/bin/env python3
# =============================================
# OLED Manager - Modular and clean
# For Raspberry Pi Zero 2W + SSD1306
# Comments in English as requested
# =============================================
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont
import time
import datetime
import threading
import socket
import subprocess

class OLEDManager:
    def __init__(self):
        self.device = None
        self.font = ImageFont.load_default()
        self.current_message = None
        self.timeout_timer = None
        self.init_display()

    def init_display(self):
        """Initialize OLED with correct driver and high contrast"""
        try:
            serial = i2c(port=1, address=0x3C)
            self.device = ssd1306(serial_interface=serial, width=128, height=64, rotate=0)
            self.device.contrast(255)
            print("✅ OLED initialized successfully (SSD1306)")
            self.show_basic_screen()
        except Exception as e:
            print(f"❌ OLED init failed: {e}")
            self.device = None

    def show_basic_screen(self):
        """Default screen with real IP and WiFi name"""
        if not self.device:
            return
        try:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                real_ip = s.getsockname()[0]
                s.close()
            except:
                real_ip = "No IP"

            try:
                ssid = subprocess.check_output(["iwgetid", "-r"], text=True).strip()
            except:
                ssid = "No WiFi"

            img = Image.new("1", (self.device.width, self.device.height), 0)
            draw = ImageDraw.Draw(img)

            draw.text((5, 5), "LabSens Hub", fill=255, font=self.font)
            draw.text((5, 25), f"IP: {real_ip}", fill=255, font=self.font)
            draw.text((5, 38), f"WiFi: {ssid}", fill=255, font=self.font)
            draw.text((5, 51), f"{datetime.datetime.now().strftime('%H:%M')}", fill=255, font=self.font)

            self.device.display(img)
        except Exception as e:
            print("Error showing basic screen:", e)

    def show_button_presses(self, count: int):
        """Show button press count with 3-second timeout"""
        if not self.device:
            return
        try:
            img = Image.new("1", (self.device.width, self.device.height), 0)
            draw = ImageDraw.Draw(img)
            draw.text((5, 20), "Button presses:", fill=255, font=self.font)
            draw.text((5, 38), f"{count} times", fill=255, font=self.font)
            self.device.display(img)

            if self.timeout_timer and self.timeout_timer.is_alive():
                self.timeout_timer.cancel()

            self.timeout_timer = threading.Timer(3.0, self.show_basic_screen)
            self.timeout_timer.start()
        except Exception as e:
            print("Error showing button presses:", e)

    def show_custom_message(self, message: str):
        """Show custom message sent from web (returns to basic screen after 3 seconds)"""
        if not self.device:
            return
        try:
            img = Image.new("1", (self.device.width, self.device.height), 0)
            draw = ImageDraw.Draw(img)
            draw.text((5, 20), "Message:", fill=255, font=self.font)
            draw.text((5, 38), message[:20], fill=255, font=self.font)
            if len(message) > 20:
                draw.text((5, 51), message[20:40], fill=255, font=self.font)
            self.device.display(img)

            if self.timeout_timer and self.timeout_timer.is_alive():
                self.timeout_timer.cancel()

            self.timeout_timer = threading.Timer(3.0, self.show_basic_screen)
            self.timeout_timer.start()
        except Exception as e:
            print("Error showing custom message:", e)#!/usr/bin/env python3
# =============================================
# OLED Manager - Modular and clean
# For Raspberry Pi Zero 2W + SSD1306
# Comments in English as requested
# =============================================
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont
import time
import datetime
import threading
import socket
import subprocess

class OLEDManager:
    def __init__(self):
        self.device = None
        self.font = ImageFont.load_default()
        self.current_message = None
        self.timeout_timer = None
        self.init_display()

    def init_display(self):
        """Initialize OLED with correct driver and high contrast"""
        try:
            serial = i2c(port=1, address=0x3C)
            self.device = ssd1306(serial_interface=serial, width=128, height=64, rotate=0)
            self.device.contrast(255)
            print("✅ OLED initialized successfully (SSD1306)")
            self.show_basic_screen()
        except Exception as e:
            print(f"❌ OLED init failed: {e}")
            self.device = None

    def show_basic_screen(self):
        """Default screen with real IP and WiFi name"""
        if not self.device:
            return
        try:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                real_ip = s.getsockname()[0]
                s.close()
            except:
                real_ip = "No IP"

            try:
                ssid = subprocess.check_output(["iwgetid", "-r"], text=True).strip()
            except:
                ssid = "No WiFi"

            img = Image.new("1", (self.device.width, self.device.height), 0)
            draw = ImageDraw.Draw(img)

            draw.text((5, 5), "LabSens Hub", fill=255, font=self.font)
            draw.text((5, 25), f"IP: {real_ip}", fill=255, font=self.font)
            draw.text((5, 38), f"WiFi: {ssid}", fill=255, font=self.font)
            draw.text((5, 51), f"{datetime.datetime.now().strftime('%H:%M')}", fill=255, font=self.font)

            self.device.display(img)
        except Exception as e:
            print("Error showing basic screen:", e)

    def show_button_presses(self, count: int):
        """Show button press count with 3-second timeout"""
        if not self.device:
            return
        try:
            img = Image.new("1", (self.device.width, self.device.height), 0)
            draw = ImageDraw.Draw(img)
            draw.text((5, 20), "Button presses:", fill=255, font=self.font)
            draw.text((5, 38), f"{count} times", fill=255, font=self.font)
            self.device.display(img)

            if self.timeout_timer and self.timeout_timer.is_alive():
                self.timeout_timer.cancel()

            self.timeout_timer = threading.Timer(3.0, self.show_basic_screen)
            self.timeout_timer.start()
        except Exception as e:
            print("Error showing button presses:", e)

    def show_custom_message(self, message: str):
        """Show custom message sent from web (returns to basic screen after 3 seconds)"""
        if not self.device:
            return
        try:
            img = Image.new("1", (self.device.width, self.device.height), 0)
            draw = ImageDraw.Draw(img)
            draw.text((5, 20), "Message:", fill=255, font=self.font)
            draw.text((5, 38), message[:20], fill=255, font=self.font)
            if len(message) > 20:
                draw.text((5, 51), message[20:40], fill=255, font=self.font)
            self.device.display(img)

            if self.timeout_timer and self.timeout_timer.is_alive():
                self.timeout_timer.cancel()

            self.timeout_timer = threading.Timer(3.0, self.show_basic_screen)
            self.timeout_timer.start()
        except Exception as e:
            print("Error showing custom message:", e)
