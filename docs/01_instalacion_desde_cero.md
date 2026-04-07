# Instalación desde cero
Esta guía describe cómo montar el sistema desde cero.

## 1. Supuestos
  Se asume:
  - Raspberry Pi OS instalado
  - usuario del sistema: `sqc`
  - proyecto ubicado en `/home/sqc/sqc-main`
  - conexión a internet disponible al menos durante la instalación inicial

## 2. Configuración inicial
  Configurar Raspi-config
  ```bash
  sudo raspi-config
  ```
  Habilitar al menos:
  - SPI
  - I2C

## 3.Instalar paquetes del sistema
  ```bash
  sudo apt update
  sudo apt install -y nginx python3 python3-venv python3-pip python3-dev git gphoto2 \
    libexif12 libgphoto2-6 libgphoto2-port12 libltdl7 \
    fonts-liberation ttf-mscorefonts-installer
   ```

## 4. Crear estructura de carpetas
  ```bash
  mkdir -p /home/sqc/sqc-main/webapp/templates
  mkdir -p /home/sqc/sqc-main/webapp/static
  mkdir -p /home/sqc/sqc-main/fotos
  sudo chown -R sqc:sqc /home/sqc/sqc-main
  chmod -R 755 /home/sqc/sqc-main/fotos
  ```

## 5. Crear entorno virtual
  ```bash
  cd /home/sqc/sqc-main/webapp
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  deactivate
  ```

## 6. Permisos de hardware
  Agregar el usuario a grupos requeridos:
  ```bash
  sudo usermod -aG gpio,spi,i2c sqc
  ```
  Reiniciar la Raspberry para aplicar los grupos.

## 7.Copiar archivos del proyecto
  Copiar:
  /home/sqc/sqc-main/app.py
  templates/index.html
  static/logo.png
