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
    sincronizar_datos,
)


class WebSocketServer:
    def __init__(self, port=8765):
        self.port = port
        self.clients = []
        self.server_socket = None
        self.running = False
        self.poller = uselect.poll()
        self.last_command_snapshot = None

    def start(self):
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
        while self.running:
            self._check_firebase_commands()
            events = self.poller.poll(1000)
            for sock, event in events:
                if sock == self.server_socket and event == uselect.POLLIN:
                    self._handle_new_connection()
                else:
                    self._handle_client_data(sock)
            self._cleanup_clients()

    def _handle_new_connection(self, client_socket=None):
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
        pass

    def _handle_websocket_handshake(self, client_socket):
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
        welcome_msg = {
            "type": "connection",
            "status": "connected",
            "device_id": "ESP32_R307",
            "timestamp": time.ticks_ms(),
        }
        self._send_websocket_message(client_socket, welcome_msg)

    def _send_websocket_message(self, client_socket, message):
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
        try:
            command_path = "commands/esp32_command"
            command = get_data(command_path, silent=True)

            if not command:
                print("⏳ Nodo de comando no encontrado. Creando y esperando...")
                waiting_command = {
                    "action": "waiting",
                    "status": "waiting",
                    "message": "En modo de espera, esperando instrucciones.",
                    "timestamp": time.ticks_ms(),
                }
                send_data(command_path, waiting_command)
                self._broadcast_to_clients(waiting_command)
                self.last_command_snapshot = waiting_command
                return

            # Evitar procesar el mismo comando múltiples veces
            command_signature = f"{command.get('action')}_{command.get('timestamp')}_{command.get('status')}"
            last_signature = f"{self.last_command_snapshot.get('action') if self.last_command_snapshot else ''}_{self.last_command_snapshot.get('timestamp') if self.last_command_snapshot else ''}_{self.last_command_snapshot.get('status') if self.last_command_snapshot else ''}"

            if command_signature == last_signature:
                return

            self.last_command_snapshot = command

            if command.get("status") == "pending":
                print(f"📨 Comando recibido: {command}")

                # Marcar como procesando inmediatamente
                command_processing = command.copy()
                command_processing["status"] = "processing"
                command_processing["processing_started"] = time.ticks_ms()
                send_data(command_path, command_processing)

                # Procesar el comando
                result = self._process_command(command)

                # Marcar como completado
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
            # En caso de error, resetear a estado de espera
            try:
                error_command = {
                    "action": "error",
                    "status": "completed",
                    "message": f"Error procesando comando: {str(e)}",
                    "timestamp": time.ticks_ms(),
                    "result": {"success": False, "message": f"Error: {str(e)}"},
                }
                send_data("commands/esp32_command", error_command)
            except:
                pass

    def _process_command(self, command):
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
            user_data = agregar_huella()
            if user_data:
                result = {
                    "success": True,
                    "message": "Huella agregada exitosamente",
                    "data": user_data,
                }
            else:
                result = {"success": False, "message": "Error al agregar la huella"}

        elif action == "get_statistics":
            print("📊 Obteniendo estadísticas...")
            self._broadcast_to_clients(
                {"type": "status", "message": "Obteniendo estadísticas del sistema..."}
            )
            try:
                mostrar_estadisticas()
                result = {
                    "success": True,
                    "message": "Estadísticas obtenidas correctamente",
                    "data": {
                        "timestamp": time.ticks_ms(),
                        "action_completed": "get_statistics",
                    },
                }
            except Exception as e:
                print(f"❌ Error obteniendo estadísticas: {e}")
                result = {
                    "success": False,
                    "message": f"Error al obtener estadísticas: {str(e)}",
                }

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

        elif action == "sync_fingerprint_data":
            print("🔄 Iniciando sincronización de datos...")
            self._broadcast_to_clients(
                {
                    "type": "status",
                    "message": "Sincronizando datos del sensor con Firebase...",
                }
            )

            try:
                sync_report = sincronizar_datos()
                if sync_report["sincronizacion_exitosa"]:
                    result = {
                        "success": True,
                        "message": f"Sincronización completada. {sync_report['huellas_eliminadas_exitosamente']} huellas eliminadas del sensor.",
                        "data": {
                            "posiciones_sensor_inicial": sync_report[
                                "posiciones_sensor_inicial"
                            ],
                            "posiciones_firebase": sync_report["posiciones_firebase"],
                            "huellas_eliminadas": sync_report[
                                "huellas_eliminadas_exitosamente"
                            ],
                            "posiciones_sensor_final": sync_report[
                                "posiciones_sensor_final"
                            ],
                            "errores": sync_report["errores_eliminacion"],
                        },
                    }
                else:
                    result = {
                        "success": False,
                        "message": f"Sincronización incompleta. {sync_report['errores_eliminacion']} errores encontrados.",
                        "data": sync_report,
                    }
            except Exception as e:
                print(f"❌ Error durante sincronización: {e}")
                result = {
                    "success": False,
                    "message": f"Error durante la sincronización: {str(e)}",
                }

        return result

    def _broadcast_to_clients(self, message):
        for client in self.clients[:]:
            try:
                self._send_websocket_message(client, message)
            except:
                pass

    def _cleanup_clients(self):
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
        device_status = {
            "status": status,
            "last_seen": time.ticks_ms(),
            "clients_connected": len(self.clients),
        }
        send_data("devices/ESP32_R307/status", device_status)

    def stop(self):
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
    server = WebSocketServer(port=8765)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nℹ️ Deteniendo servidor...")
        server.stop()
