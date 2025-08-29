import network
import time

wlan = network.WLAN(network.STA_IF)

def connect_to_wifi(ssid, password):
    wlan.active(True)
    if not wlan.isconnected():
        print("[WiFi] Conectando a la red...")
        wlan.connect(ssid, password)

        timeout = 15  # segundos
        start = time.time()
        while not wlan.isconnected():
            if time.time() - start > timeout:
                print("[WiFi] Tiempo agotado, no se pudo conectar.")
                return False
            time.sleep(1)

    print("[WiFi] Conectado correctamente:", wlan.ifconfig())
    return True


def ensure_wifi(ssid, password):
    """Verifica que el WiFi siga conectado. Si no, reconecta."""
    if not wlan.isconnected():
        print("[WiFi] ⚠️ Conexión perdida, intentando reconectar...")
        return connect_to_wifi(ssid, password)
    return True
