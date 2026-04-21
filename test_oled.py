#!/usr/bin/env python3
# =============================================
# TEST OLED - Minimal diagnostic for Raspberry Pi Zero 2W
# Comments in English as requested
# =============================================
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306, sh1106
from PIL import Image, ImageDraw, ImageFont
import time

print("🧪 Starting OLED diagnostic test...")

PORT = 1
ADDRESS = 0x3C

def test_driver(driver_name, driver_class):
    print(f"Testing driver: {driver_name}")
    try:
        serial = i2c(port=PORT, address=ADDRESS)
        device = driver_class(serial_interface=serial, width=128, height=64, rotate=0)
        
        # Max contrast (many cheap OLEDs come with very low contrast)
        device.contrast(255)
        
        # Create a clear test image
        img = Image.new("1", (device.width, device.height), 0)
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        
        draw.text((5, 8), "OLED WORKING!", fill=255, font=font)
        draw.text((5, 28), f"Driver: {driver_name}", fill=255, font=font)
        draw.text((5, 43), f"Addr: 0x{ADDRESS:02X}", fill=255, font=font)
        
        device.display(img)
        print(f"✅ SUCCESS with {driver_name} - Screen should be ON now!")
        time.sleep(10)   # 10 seconds so you can read it clearly
        device.clear()
        return True
    except Exception as e:
        print(f"❌ {driver_name} failed: {e}")
        return False

# Try SSD1306 first (most common for these cheap 0.96" displays)
if test_driver("SSD1306", ssd1306):
    print("\n🎉 SSD1306 worked! This is the correct driver.")
elif test_driver("SH1106", sh1106):
    print("\n🎉 SH1106 worked! Use this driver.")
else:
    print("\n❌ No driver worked. We will need more info.")

print("\nTest finished.")
