# SQC
Sistema portátil para captura automática de fotografías del cielo nocturno orientado a análisis de contaminación lumínica. Desarrollado por Daniel Rengifo para el laboratorio LabSens de la PUCV, Chile.
<p align="center">
  <img width="525" height="534" alt="imagen" src="https://github.com/user-attachments/assets/d067a695-7ffe-4a9d-86c5-7e247ae3b2f9" />
</p>  
El equipo fue concebido como un maletín autónomo que integra:
  - Raspberry Pi
  - Cámara Canon
  - Batería interna
  - LED RGB
  - Display OLED (ZJY 1.14' 135x240)
  - interfaz web local para control del sistema
    
La idea de este repositorio es que cualquiera pueda reconstruir el sistema desde cero.

## 1. Función general del sistema
Cuando el equipo enciende:
  1. la Raspberry Pi inicia el sistema
  2. se conecta a una red WiFi conocida si está disponible
  3. si no encuentra una red conocida, genera un AP para acceso remoto.
  4. se levanta una aplicación web local
  5. el usuario entra desde el celular o notebook a la página del sistema
  6. desde esa página puede:
     - tomar una foto manual
     - iniciar modo automático por intervalos
     - detener el modo automático
     - definir tiempo de exposición
     - activar modo “Solo Noche”
     - visualizar la última foto tomada
  7. el equipo informa estados mediante LED RGB y display

## 2. Software usado
  - Python 3.13
  - Flask
  - gphoto2
  - nginx
  - systemd
  - RPi.GPIO
  - luma.lcd
  - Pillow
  - AccessPopup

## 3. Funcionalidades implementadas
  ### Interfaz web
  - La aplicación Flask entrega una página web simple para controlar el sistema.
  ### Captura manual
  - Permite disparar una fotografía desde la web.
  ### Modo automático
  - Permite definir un intervalo en minutos para capturar fotos automáticamente.
  ### Tiempo de exposición
  - El usuario puede fijar el tiempo de exposición en segundos. 
  ### Modo “Solo Noche”
  - Si esta opción está activa, el sistema bloquea fotografías durante el día según la ventana horaria definida en el código.
  ### Visualización de la última foto
  - La web muestra la última imagen disponible en la carpeta de fotos.
  ### LED RGB y display
  - El equipo comunica estados locales del sistema mediante hardware conectado a la Raspberry.
  ### Arranque automático
  - La aplicación queda configurada como servicio `systemd`, por lo que inicia automáticamente al encender la Raspberry.
  ### Acceso de red
  - La gestión de reconexión WiFi y modo AP fue delegada a AccessPopup.
    
## 4. Flujo de instalación
  La guía completa está en:
  - `docs/01_instalacion_desde_ceroV1.2.md`

  
  
