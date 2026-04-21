# config/display_config.py
# All OLED messages in English - easy to modify

OLED_MESSAGES = {
    "welcome": "LabSens Hub",
    "ip": "IP: {}",
    "mode": "Mode: {}",
    "last_action": "Last: {}",
    "hardware_single": "Hardware: Single Press",
    "hardware_triple": "Hardware: Triple Press",
    "hardware_long_ap": "Hardware: Long Press (AP)",
    "hardware_reboot": "Hardware: Reboot",
    "web_oled_status": "Web: Show Status",
    "web_oled_custom": "Web: Custom Message",
    "web_oled_off": "Web: OLED Off",
    "web_oled_on": "Web: OLED On",
    "web_led_green": "Web: Green Blink",
    "web_led_blue": "Web: Blue Blink",
    "web_led_red": "Web: Red Solid",
    "web_led_off": "Web: LED Off",
    "web_relay1_on": "Web: Relay 1 ON",
    "web_relay1_off": "Web: Relay 1 OFF",
}

# Default values shown on OLED
DEFAULT_DISPLAY = {
    "show_ip": True,
    "show_cpu_temp": True,
    "show_uptime": True,
    "show_last_action": True,
    "timeout_seconds": 5,          # how long to show action message
}

# LED blink patterns (configurable)
LED_PATTERNS = {
    "green_blink": (0.08, 2.0),   # on_time, period
    "blue_blink": (0.08, 2.0),
}
