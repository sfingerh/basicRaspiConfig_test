# Descripcion del sistema
El equipo electronico se compone de una Raspberry Pi Zero 2 y la placa PCB SQCv1.2
<p align="center">
  <img width="845" height="534" alt="imagen" src="https://github.com/user-attachments/assets/85791c1f-d3c9-46ad-a3cb-5992ccae93de" />  
</p>

## 1. Funciones PCB SQCv1.2
  La placa contiene un display 0.96 por i2c, boton (en pull-up), led rgb mas selector de modo anodo comun o cátodo comun y resistencia 10k.
  <p align="center">
    <img width="475" height="437" alt="imagen" src="https://github.com/user-attachments/assets/5122cf29-7727-429f-afbe-97a59cdcfd5c" />
  <p
    
  En la siguiente imagen se ilustra el diagrama de conexiones y funciones:
  <p align="center">
    <img width="882" height="477" alt="imagen" src="https://github.com/user-attachments/assets/f0df3cfb-d19a-4044-ba84-672877dbfbc5" />
  </p>

  
<img width="525" height="534" alt="imagen" src="https://github.com/user-attachments/assets/d067a695-7ffe-4a9d-86c5-7e247ae3b2f9" />


  - Raspberry Pi
  - usuario del sistema: `sqc`
  - proyecto ubicado en `/home/sqc/sqc-main`
  - conexión a internet disponible al menos durante la instalación inicial

## 2. Configuración inicial
  Acceder via SSH y configurar Raspi-config
  ```bash
  sudo raspi-config
  ```


