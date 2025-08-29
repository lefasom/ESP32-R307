# main.py
import r307_sensor
from time import sleep
from wifi_utils import connect_to_wifi, ensure_wifi
from firebase_utils import get_data, send_data

# Variables
PORT = 80
SSID = "HUAWEI-2.4G-94Df"
PASSWORD = "xqTKH4X5"

# Wifi
if connect_to_wifi(SSID, PASSWORD):
    print("✅ Conectado a Wi-Fi")

# Bucle principal
while True:
    try:
        if ensure_wifi(SSID, PASSWORD):
            # Leer el objeto de comando completo de Firebase
             
            comando_data = get_data("commands/esp32_command", silent=True)

            if comando_data:
                comando = comando_data.get("command")
                status = comando_data.get("status")

                if status == "pending":
                    if comando == "agregar_huella":
                        print("🚀 Ejecutando comando: AGREGAR HUELLA")
                        # Llamar a la función del sensor
                        # send_data("display", {"mensaje": "..."})
                        resultado = r307_sensor.agregar_huella()
                        
                        # Actualizar el estado en Firebase
                        send_data("commands/esp32_command/status", "completed")
                        send_data("display2",{ "result":"Se agrego con EXITO"} if resultado else {"result":"ERROR repite los pasos"})
                        sleep(3) 
                        
                        send_data("display2",{ "result":""})


                    elif comando == "detectar_huella":
                        print("🚀 Ejecutando comando: DETECTAR HUELLA")
                        
                        # Llamar a la función del sensor
                        resultado = r307_sensor.detectar_huella()
                        
                        # Actualizar el estado en Firebase
                        send_data("commands/esp32_command/status", "completed")
                        send_data("display2",{ "result":"PASE"} if resultado else {"result":"STOP"})
                        
                        sleep(3) 
                        send_data("display", {"mensaje": "Esperando nuevos comandos"})
                        
                        send_data("display2",{ "result":""})
                    # Agrega más condiciones para otros comandos aquí
                    elif comando == "sincronizar_datos":
                        print("🚀 Ejecutando comando: SINCRONIZAR DATOS")
                        r307_sensor.sincronizar_datos()
                        send_data("commands/esp32_command/status", "completed")
                        # send_data("commands/esp32_command/result", "success")

                else:
                    print("💤 Esperando nuevos comandos...")

    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")

    finally:
        # Pausa para no sobrecargar el sistema
        sleep(3)