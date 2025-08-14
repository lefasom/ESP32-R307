# main.py
from wifi_utils import connect_to_wifi
from firebase_utils import send_data, get_data
from r307_sensor import (
    test_connection,
    agregar_huella,
    detectar_huella,
    mostrar_estadisticas,
    mostrar_posiciones,
    eliminar_huella,
)
from websocket_server import WebSocketServer, start_websocket_server

SSID = "HUAWEI-2.4G-94Df"
PASSWORD = "xqTKH4X5"

# Conexión a WiFi
if connect_to_wifi(SSID, PASSWORD):
    print("✅ Conectado a Wi-Fi")
    # Iniciar el servidor WebSocket
    start_websocket_server()
else:
    print("No se pudo inicializar el sistema")
