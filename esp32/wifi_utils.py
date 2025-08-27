# wifi_connect.py
import network
import time


def connect_to_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
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
