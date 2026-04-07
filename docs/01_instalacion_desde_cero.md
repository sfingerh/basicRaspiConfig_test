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

## 4.Copiar archivos del proyecto
  Copiar todo el contenido de 
    - SQC/sqc-main/
  en:
    - /home/sqc/sqc-main/  

## 6. Crear entorno virtual
  ```bash
  cd /home/sqc/sqc-main/webapp
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install blinker cbor2 certifi charset-normalizer click Flask gphoto2 idna itsdangerous Jinja2 luma.core luma.lcd MarkupSafe pillow requests RPi.GPIO smbus2 spidev urllib3 Werkzeug
  deactivate
  ```

## 7. Permisos de hardware
  Agregar el usuario a grupos requeridos:
  ```bash
  sudo usermod -aG gpio,spi,i2c sqc
  ```
  Reiniciar la Raspberry para aplicar los grupos.

## 8. Instalar AccessPopup
  La instalación se realiza de forma simple siguiendo las instrucciones del repo oficial (https://github.com/RaspberryConnect/AccessPopup)
  ```bash
  cd /home/sqc/sqc-main/webapp/AccessPopup
  sudo chmod +x ./installconfig.sh
  sudo ./installconfig.sh
  ```
Una vez instalado, AccessPopup se encarga de:
  1. intentar conectarse a redes conocidas
  2. habilitar modo Access Point si no encuentra una red usable
  3. Intenta reconectar si encuentra una red conocida

## 9.Configurar servicio SQC
  Copiar archivo de servicio:
  ```bash
  sudo cp /home/sqc/sqc-main/deploy/sqc.service /etc/systemd/system/sqc.service
  sudo systemctl daemon-reload
  sudo systemctl enable sqc
  sudo systemctl start sqc
  sudo systemctl status sqc --no-pager
  ```

## 10.Configurar nginx
  Copiar configuración:
  ```bash
  sudo cp /home/sqc/sqc-main/deploy/nginx-sqc.conf /etc/nginx/sites-available/sqc
  sudo ln -sf /etc/nginx/sites-available/sqc /etc/nginx/sites-enabled/sqc
  sudo rm -f /etc/nginx/sites-enabled/default
  sudo nginx -t
  sudo systemctl restart nginx
  ```

 


