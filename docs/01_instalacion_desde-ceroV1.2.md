# Instalación desde cero
Esta guía describe cómo montar el sistema desde cero.

## 1. Supuestos
  Se asume:
  - Raspberry Pi Zero 2 W con Debian Trixie o superior, sin entorno de escritorio.
    <img width="676" height="476" alt="imagen" src="https://github.com/user-attachments/assets/c3a83cf4-9124-4f72-8173-945c96ec8969" />
  - usuario del sistema: `sqc`
  - proyecto ubicado en `/home/sqc/sqc-main`
  - conexión a internet disponible al menos durante la instalación inicial

## 2. Configuración inicial
  Acceder via SSH y configurar Raspi-config
  ```bash
  sudo raspi-config
  ```
  Habilitar I2C
    <img width="661" height="418" alt="imagen" src="https://github.com/user-attachments/assets/68a9e5b0-c161-4b4a-a834-ba5a4c475339" />

## 3.Instalar paquetes del sistema
  ```bash
  sudo apt update
  sudo apt full-upgrade -y
  sudo apt install -y i2c-tools
  sudo reboot
   ```
  luego de reiniciar, instalar dependencias
  ```bash
  sudo apt update
  sudo apt install -y \
  nginx \
  git \
  python3 \
  python3-venv \
  python3-pip \
  python3-dev \
  gphoto2 \
  libexif12 \
  libgphoto2-6 \
  libgphoto2-port12 \
  libltdl7 \
  libjpeg-dev \
  zlib1g-dev \
  libopenjp2-7 \
  libtiff6 \
  libfreetype6 \
  liblcms2-2 \
  libwebp7 \
  libharfbuzz0b \
  libfribidi0 \
  libxcb1 \
  fonts-liberation \
  ttf-mscorefonts-installer \
  i2c-tools \
  network-manager \
  usbutils \
  curl
  ```

## 4. Crear estructura de carpetas y descargar el proyecto
  ```bash
  cd /home/sqc
  git clone https://github.com/Drengifo/SQC.git
  ```
Copiar todo el contenido 
  ```bash
  cp -R /home/sqc/SQC/sqc-main /home/sqc/
  ```
Crear carpeta de fotos y asignar permisos
  ```bash
  mkdir -p /home/sqc/sqc-main/fotos
  sudo chown -R sqc:sqc /home/sqc/sqc-main
  chmod -R 755 /home/sqc/sqc-main/fotos
  ```
    
## 5. Crear entorno virtual
  ```bash
  cd /home/qwid94/sqc-main/webapp
  python3 -m venv .venv
  source .venv/bin/activate
  ```
  ```bash
  pip install --upgrade pip wheel setuptools
  ```
  ```bash
  pip install \
  blinker \
  cbor2 \
  certifi \
  charset-normalizer \
  click \
  Flask \
  gphoto2 \
  idna \
  itsdangerous \
  Jinja2 \
  luma.core \
  luma.oled \
  MarkupSafe \
  pillow \
  requests \
  RPi.GPIO \
  smbus2 \
  urllib3 \
  Werkzeug
  ```
  ```bash
  deactivate
  ```

## 6. Permisos de hardware
  Agregar el usuario a grupos requeridos:
  ```bash
  sudo usermod -aG gpio,i2c,spi,dialout,video,plugdev sqc
  sudo reboot
  ```

## 7.Probar cámara Canon por USB
  Conecta la cámara usando el puerto OTG de datos.
  ```bash
    lsusb
    gphoto2 --auto-detect
    gphoto2 --summary
  ```
  Si gphoto2 --auto-detect ve la cámara, esta todo ok.
  
## 8. Instalar AccessPopup
  La instalación se realiza de forma simple siguiendo las instrucciones del repo oficial (https://github.com/RaspberryConnect/AccessPopup)
  ```bash
  cd /home/sqc/sqc-main/deploy/AccessPopup
  sudo chmod +x ./installconfig.sh
  sudo ./installconfig.sh
  ```
  Seleccione opcion 1
  <img width="661" height="418" alt="imagen" src="https://github.com/user-attachments/assets/05713557-ed55-47a1-8f8f-a07a1b6524c5" />
  finalizara con este mensaje:
  <img width="661" height="418" alt="imagen" src="https://github.com/user-attachments/assets/8954c9b6-3fce-41bf-ac56-3dd8f6f13ab1" />
  luego con la opcion 2 cambie el SSID y password del wifi AP.
  <img width="661" height="418" alt="imagen" src="https://github.com/user-attachments/assets/50f7496c-cb1a-4848-8564-7e9af493a5af" />
  Pruebe el sistema usando la opcion 4. Acceda a la red SQC-AP con la ip 192.168.50.5
  Una vez instalado, AccessPopup se encarga de:
    1. intentar conectarse a redes conocidas
    2. habilitar modo Access Point si no encuentra una red usable
    3. Intenta reconectar si encuentra una red conocida
  
## 9.Configurar servicio SQC
  Copiar archivo de configuracion y habilitar servicio SQC:
  ```bash
  sudo cp /home/sqc/sqc-main/deploy/sqc.service /etc/systemd/system/sqc.service
  sudo systemctl daemon-reload
  sudo systemctl enable sqc
  sudo systemctl start sqc
  sudo systemctl status sqc --no-pager
  sudo systemctl stop sqc
  ```

## 10.Configurar nginx
  Copiar configuración y arrancar nginx:
  ```bash
  sudo cp /home/sqc/sqc-main/deploy/nginx-sqc.conf /etc/nginx/sites-available/sqc
  sudo ln -sf /etc/nginx/sites-available/sqc /etc/nginx/sites-enabled/sqc
  sudo rm -f /etc/nginx/sites-enabled/default
  sudo nginx -t
  sudo systemctl restart nginx
  ```

Reiniciar la Raspberry para aplicar los cambios.
  ```bash
  sudo reboot
  ```
## 10.Pruebas finales
  Active el entorno virtual y ejecute app.py manualmente. Deben estar conectado Display, RGB y camara para q el sistema arranque.
  ```bash
  cd /home/sqc/sqc-main/webapp
  source .venv/bin/activate
  python app.py
  ```
  <img width="661" height="418" alt="imagen" src="https://github.com/user-attachments/assets/e0c39783-fe17-4d06-b8b7-e2b63fe569a5" />
  Ingrese desde el navegador web a la direccion sqc.local o a la direccion IP que muestra en el display.
  <img width="820" height="905" alt="imagen" src="https://github.com/user-attachments/assets/8dc0e923-3a11-4d96-a32e-3317704a0097" />

  
