#!/usr/bin/env python3
# =============================================
# Test OLED estable - Solo para verificar que funciona
# =============================================
from modules.oled_manager import OLEDManager
import time

print("Iniciando prueba OLED estable...")

# Crear el manager (esto ya prende la pantalla)
oled = OLEDManager()

print("✅ Pantalla inicializada. Manteniendo encendida...")

# Mantener la pantalla con la información básica
try:
    while True:
        oled.show_basic_screen()
        time.sleep(2)  # Actualiza cada 2 segundos
except KeyboardInterrupt:
    print("\n✅ Prueba terminada. Pantalla apagada.")
