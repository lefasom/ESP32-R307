# websocket_server.py
# Servidor WebSocket para ESP32
import usocket as socket
import ujson
import uselect
import time
from firebase_utils import send_data, get_data
from r307_sensor import (
    agregar_huella,
    detectar_huella,
    mostrar_estadisticas,
    mostrar_posiciones,
    eliminar_huella,
)


class WebSocketServer:
    def __init__(self, port=8765):
        self.port = port
        self.clients = []
        self.server_socket = None
        self.running = False
        self.poller = uselect.poll()

    def start(self):
        """Inicia el servidor WebSocket"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(("0.0.0.0", self.port))
            self.server_socket.listen(5)
            self.poller.register(self.server_socket, uselect.POLLIN)
            self.running = True
            print(f"🌐 Servidor WebSocket iniciado en puerto {self.port}")
            self._update_device_status("online")

            self._server_loop()
        except Exception as e:
            print(f"❌ Error al iniciar el servidor: {e}")
            self.stop()

    def _server_loop(self):
        """Loop principal del servidor"""
        while self.running:
            self._check_firebase_commands()
            events = self.poller.poll(1000)  # 1 segundo de timeout

            for sock, event in events:
                if sock == self.server_socket and event == uselect.POLLIN:
                    self._handle_new_connection()
                else:
                    self._handle_client_data(sock)

            self._cleanup_clients()

    def _handle_new_connection(self, client_socket):
        """Maneja nuevas conexiones"""
        try:
            client_socket, addr = self.server_socket.accept()
            print(f"📱 Cliente conectado desde {addr}")
            if self._handle_websocket_handshake(client_socket):
                self.clients.append(client_socket)
                self.poller.register(client_socket, uselect.POLLIN)
                self._send_welcome_message(client_socket)
        except Exception as e:
            print(f"❌ Error al aceptar cliente: {e}")

    def _handle_client_data(self, client_socket):
        """Maneja datos de un cliente existente"""
        pass

    def _handle_websocket_handshake(self, client_socket):
        """Maneja el handshake WebSocket (simplificado)"""
        try:
            request = client_socket.recv(1024).decode("utf-8")
            if "Upgrade: websocket" in request:
                key_start = request.find("Sec-WebSocket-Key:") + len(
                    "Sec-WebSocket-Key:"
                )
                key_end = request.find("\r\n", key_start)
                key = request[key_start:key_end].strip()

                if key:
                    response = (
                        "HTTP/1.1 101 Switching Protocols\r\n"
                        "Upgrade: websocket\r\n"
                        "Connection: Upgrade\r\n"
                        f"Sec-WebSocket-Accept: {key}258EAFA5\r\n"
                        "\r\n"
                    )
                    client_socket.send(response.encode())
                    return True
            return False
        except Exception as e:
            print(f"❌ Error en handshake: {e}")
            return False

    def _send_welcome_message(self, client_socket):
        """Envía mensaje de bienvenida al cliente"""
        welcome_msg = {
            "type": "connection",
            "status": "connected",
            "device_id": "ESP32_R307",
            "timestamp": time.ticks_ms(),
        }
        self._send_websocket_message(client_socket, welcome_msg)

    def _send_websocket_message(self, client_socket, message):
        """Envía un mensaje WebSocket al cliente"""
        try:
            data = ujson.dumps(message)
            frame = bytearray()
            frame.append(0x81)
            if len(data) < 126:
                frame.append(len(data))
            else:
                frame.append(126)
                frame.extend(len(data).to_bytes(2, "big"))
            frame.extend(data.encode())
            client_socket.send(frame)
        except Exception as e:
            print(f"❌ Error enviando mensaje WebSocket: {e}")

    def _check_firebase_commands(self):
        """Verifica comandos pendientes desde Firebase"""
        try:
            command_path = "commands/esp32_command"
            command = get_data(command_path)

            if not command:
                # Si el nodo no existe, lo crea en estado de espera
                print(
                    "⏳ Nodo de comando no encontrado. Creando y entrando en modo de espera..."
                )
                waiting_command = {
                    "action": "waiting",
                    "status": "waiting",
                    "message": "En modo de espera, esperando instrucciones.",
                    "timestamp": time.ticks_ms(),
                }
                send_data(command_path, waiting_command)
                self._broadcast_to_clients(waiting_command)
                return

            if command and command.get("status") == "pending":
                print(f"📨 Comando recibido: {command}")
                result = self._process_command(command)

                command["status"] = "completed"
                command["result"] = result
                command["completed_at"] = time.ticks_ms()
                send_data(command_path, command)
                self._broadcast_to_clients(
                    {
                        "type": "command_result",
                        "command": command["action"],
                        "result": result,
                    }
                )

        except Exception as e:
            print(f"❌ Error verificando comandos: {e}")

    def _process_command(self, command):
        """Procesa un comando recibido y llama a las funciones del sensor"""
        action = command.get("action")
        result = {"success": False, "message": "Comando desconocido"}

        if action == "detect_fingerprint":
            print("🔍 Iniciando detección de huella...")
            self._broadcast_to_clients(
                {"type": "status", "message": "Coloque el dedo en el sensor..."}
            )
            detection_result = detectar_huella()
            if detection_result:
                result = {
                    "success": True,
                    "message": "Huella detectada",
                    "data": detection_result,
                }
            else:
                result = {"success": False, "message": "Huella no encontrada"}

        elif action == "add_fingerprint":
            print("➕ Iniciando registro de huella...")
            self._broadcast_to_clients(
                {"type": "status", "message": "Iniciando registro de huella..."}
            )
            if agregar_huella():
                result = {"success": True, "message": "Huella agregada exitosamente"}
            else:
                result = {"success": False, "message": "Error al agregar la huella"}

        elif action == "get_statistics":
            print("📊 Obteniendo estadísticas...")
            stats = mostrar_estadisticas()
            result = {"success": True, "statistics": stats}

        elif action == "delete_fingerprint":
            print("🗑️ Eliminando huella...")
            fingerprint_id = command.get("fingerprint_id")
            if eliminar_huella(id_a_eliminar=fingerprint_id):
                result = {
                    "success": True,
                    "message": f"Huella {fingerprint_id} eliminada",
                }
            else:
                result = {"success": False, "message": "Error al eliminar la huella"}

        return result

    def _broadcast_to_clients(self, message):
        """Envía un mensaje a todos los clientes conectados"""
        for client in self.clients[:]:
            try:
                self._send_websocket_message(client, message)
            except:
                pass

    def _cleanup_clients(self):
        """Limpia clientes desconectados"""
        active_clients = []
        for client in self.clients:
            try:
                client.send(b"")
                active_clients.append(client)
            except:
                try:
                    client.close()
                except:
                    pass
        self.clients = active_clients

    def _update_device_status(self, status):
        """Actualiza el estado del dispositivo en Firebase"""
        device_status = {
            "status": status,
            "last_seen": time.ticks_ms(),
            "clients_connected": len(self.clients),
        }
        send_data("devices/ESP32_R307/status", device_status)

    def stop(self):
        """Detiene el servidor"""
        self.running = False
        self._update_device_status("offline")
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        if self.server_socket:
            self.server_socket.close()
        print("🛑 Servidor WebSocket detenido")


def start_websocket_server():
    """Inicia el servidor WebSocket"""
    server = WebSocketServer(port=8765)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n⏹️ Deteniendo servidor...")
        server.stop()
