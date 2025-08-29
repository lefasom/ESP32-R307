# main.py
from wifi_utils import connect_to_wifi, ensure_wifi
from firebase_utils import get_data, send_data
import r307_sensor
import time

SSID = "HUAWEI-2.4G-94Df"
PASSWORD = "xqTKH4X5"

if connect_to_wifi(SSID, PASSWORD):
    print("✅ Conectado a Wi-Fi")

# Bucle principal
while True:
    if ensure_wifi(SSID, PASSWORD):
        print("📡 WiFi OK")
        
        # Leer el objeto de comando completo de Firebase
        comando_data = get_data("commands/esp32_command", silent=True)
        
        if comando_data:
            comando = comando_data.get("command")
            status = comando_data.get("status")

            if status == "pending":
                if comando == "agregar_huella":
                    print("🚀 Ejecutando comando: AGREGAR HUELLA")
                    # Llamar a la función del sensor
                    resultado = r307_sensor.agregar_huella()
                    # Actualizar el estado en Firebase
                    send_data("commands/esp32_command/status", "completed")
                    send_data("commands/esp32_command/result", "success" if resultado else "failure")
                    
                elif comando == "detectar_huella":
                    print("🚀 Ejecutando comando: DETECTAR HUELLA")
                    # Llamar a la función del sensor
                    resultado = r307_sensor.detectar_huella()
                    # Actualizar el estado en Firebase
                    send_data("commands/esp32_command/status", "completed")
                    send_data("commands/esp32_command/result", "success" if resultado else "failure")
                    
                # Agrega más condiciones para otros comandos aquí
                elif comando == "sincronizar_datos":
                    print("🚀 Ejecutando comando: SINCRONIZAR DATOS")
                    r307_sensor.sincronizar_datos()
                    send_data("commands/esp32_command/status", "completed")
                    send_data("commands/esp32_command/result", "success")

            else:
                print("💤 Esperando nuevos comandos...")
        
        # Pausa para no sobrecargar el sistema
        time.sleep(5)