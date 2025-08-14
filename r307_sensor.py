from r307_uart import send_command
from firebase_utils import send_data, get_data
import time
import urandom

# Constantes para el tiempo de espera
TIMEOUT_SEGUNDOS = 20
PAUSA_CORTA = 0.5  # Pausa entre comandos para estabilidad


def calculate_checksum(packet_data):
    """Calcula el checksum para el paquete de datos del sensor R307."""
    checksum = sum(packet_data)
    return checksum & 0xFFFF  # Asegurarse de que el checksum sea de 2 bytes


def test_connection():
    packet = bytes(
        [
            0xEF,
            0x01,
            0xFF,
            0xFF,
            0xFF,
            0xFF,
            0x01,
            0x00,
            0x03,  # Longitud del paquete corregida
            0x13,
            0x00,
            0x17,  # Checksum corregido
        ]
    )
    response = send_command(packet)
    time.sleep(PAUSA_CORTA)
    return response and len(response) >= 12 and response[9] == 0x00


def obtener_siguiente_posicion():
    """Obtiene la siguiente posición libre en el sensor R307"""
    packet_get_index = bytes(
        [0xEF, 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0x01, 0x00, 0x03, 0x1F, 0x00, 0x23]
    )
    response = send_command(packet_get_index)
    time.sleep(1)

    if response and response[9] == 0x00:
        for i in range(256):
            byte_index = 10 + (i // 8)
            bit_position = i % 8
            if byte_index < len(response):
                byte_value = response[byte_index]
                if not ((byte_value >> bit_position) & 1):
                    return i
    return 1


def generar_timestamp():
    """Genera un timestamp simple basado en time.ticks_ms()"""
    return time.ticks_ms()


def wait_for_finger_press(timeout, message):
    """Espera activamente a que un dedo sea colocado en el sensor."""
    print(f"⏳ {message} ({timeout}s)...")
    start_time = time.time()
    packet_get_image = bytes(
        [0xEF, 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0x01, 0x00, 0x03, 0x01, 0x00, 0x05]
    )

    while (time.time() - start_time) < timeout:
        response = send_command(packet_get_image)
        if response and response[9] == 0x00:
            print("✅ ¡Huella detectada!")
            return True, response
        elif response and response[9] == 0x02:
            time.sleep(PAUSA_CORTA)
        else:
            time.sleep(PAUSA_CORTA)

    print("❌ Tiempo de espera agotado.")
    return False, None


def wait_for_finger_release(timeout, message):
    """Espera activamente a que un dedo sea levantado del sensor."""
    print(f"☝️ {message} ({timeout}s)...")
    start_time = time.time()
    packet_get_image = bytes(
        [0xEF, 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0x01, 0x00, 0x03, 0x01, 0x00, 0x05]
    )

    while (time.time() - start_time) < timeout:
        response = send_command(packet_get_image)
        if response and response[9] == 0x02:
            print("✅ Dedo levantado.")
            return True
        elif response and response[9] == 0x00:
            time.sleep(PAUSA_CORTA)
        else:
            time.sleep(PAUSA_CORTA)

    print("❌ Tiempo de espera agotado. El dedo no fue levantado.")
    return False


def agregar_huella():
    print("=== AGREGAR NUEVA HUELLA ===")
    posicion = obtener_siguiente_posicion()
    print(f"Usando posición: {posicion}")

    # 1. Capturar la primera imagen (con timeout)
    success, _ = wait_for_finger_press(
        TIMEOUT_SEGUNDOS, "Coloque el dedo para la primera imagen"
    )
    if not success:
        return False

    # 2. Generar la plantilla de la primera imagen
    packet_generate_template = bytes(
        [0xEF, 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0x01, 0x00, 0x04, 0x02, 0x01, 0x00, 0x08]
    )
    response = send_command(packet_generate_template)
    time.sleep(PAUSA_CORTA)
    if response and response[9] == 0x00:
        print("Plantilla 1 generada.")
    else:
        print("Error al generar la plantilla 1.")
        return False

    # 3. Esperar que se levante el dedo y luego capturar la segunda imagen (con timeout)
    if not wait_for_finger_release(TIMEOUT_SEGUNDOS, "Levante el dedo"):
        return False

    success, _ = wait_for_finger_press(
        TIMEOUT_SEGUNDOS, "Vuelva a colocar el mismo dedo para la segunda imagen"
    )
    if not success:
        return False

    # 4. Generar la plantilla de la segunda imagen
    packet_generate_template_2 = bytes(
        [0xEF, 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0x01, 0x00, 0x04, 0x02, 0x02, 0x00, 0x09]
    )
    response = send_command(packet_generate_template_2)
    time.sleep(PAUSA_CORTA)
    if response and response[9] == 0x00:
        print("Plantilla 2 generada.")
    else:
        print("Error al generar la plantilla 2.")
        return False

    # 5. Unir las dos plantillas en un modelo
    packet_combine_templates = bytes(
        [0xEF, 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0x01, 0x00, 0x03, 0x05, 0x00, 0x09]
    )
    response = send_command(packet_combine_templates)
    time.sleep(PAUSA_CORTA)
    if response and response[9] == 0x00:
        print("Modelos combinados.")
    else:
        print("Error al combinar plantillas.")
        return False

    # 6. Almacenar el modelo en la posición específica (PAQUETE CORREGIDO)
    pos_high = (posicion >> 8) & 0xFF
    pos_low = posicion & 0xFF

    # Nuevo paquete con longitud y checksum correctos
    data_to_checksum = [0x01, 0x00, 0x06, 0x06, 0x01, pos_high, pos_low]
    checksum = calculate_checksum(data_to_checksum)
    checksum_high = (checksum >> 8) & 0xFF
    checksum_low = checksum & 0xFF

    packet_store_model = bytes(
        [
            0xEF,
            0x01,
            0xFF,
            0xFF,
            0xFF,
            0xFF,
            0x01,
            0x00,
            0x06,  # Longitud del paquete corregida a 6 bytes
            0x06,
            0x01,
            pos_high,
            pos_low,
            checksum_high,
            checksum_low,  # Checksum calculado
        ]
    )

    response = send_command(packet_store_model)
    time.sleep(PAUSA_CORTA)

    if response and response[9] == 0x00:
        print("¡Huella guardada exitosamente en el sensor!")
        timestamp = generar_timestamp()
        usuario_id = f"user_{posicion}_{timestamp}"
        datos_usuario = {
            "id_sensor": posicion,
            "usuario_id": usuario_id,
            "nombre": f"Usuario_{posicion}",
            "apellido": "Pendiente",
            "email": "pendiente@email.com",
            "activo": True,
            "fecha_registro": timestamp,
            "registrado_por": "ESP32",
        }

        if send_data(f"usuarios/{usuario_id}", datos_usuario):
            print(f"✅ Usuario registrado en Firebase: {usuario_id}")
            indice_sensor = {
                "usuario_id": usuario_id,
                "nombre": datos_usuario["nombre"],
                "activo": True,
            }
            send_data(f"indices_sensor/{posicion}", indice_sensor)
            return True
        else:
            print("⚠️ Huella guardada pero error al registrar en Firebase")
            return False
    else:
        print("❌ Error al guardar la huella en el sensor.")
        return False


def detectar_huella():
    print("=== DETECTAR HUELLA ===")
    print("Por favor, coloque su dedo para la detección...")
    success, _ = wait_for_finger_press(TIMEOUT_SEGUNDOS, "Esperando huella dactilar")
    if not success:
        print("❌ Detección de huella cancelada por tiempo agotado.")
        return None

    print("Imagen capturada. Procesando...")

    # 2. Generar la plantilla
    packet_generate_template = bytes(
        [0xEF, 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0x01, 0x00, 0x04, 0x02, 0x01, 0x00, 0x08]
    )
    response = send_command(packet_generate_template)
    time.sleep(PAUSA_CORTA)
    if response and response[9] == 0x00:
        print("Plantilla generada. Buscando en la base de datos...")
    else:
        print("Error al generar la plantilla.")
        return None

    # 3. Buscar la huella en la base de datos (PAQUETE CORREGIDO)
    # Nuevo paquete con longitud y checksum correctos
    data_to_checksum = [0x01, 0x00, 0x08, 0x04, 0x01, 0x00, 0x00, 0x00, 0x64]
    checksum = calculate_checksum(data_to_checksum)
    checksum_high = (checksum >> 8) & 0xFF
    checksum_low = checksum & 0xFF

    packet_search = bytes(
        [
            0xEF,
            0x01,
            0xFF,
            0xFF,
            0xFF,
            0xFF,
            0x01,
            0x00,
            0x08,  # Longitud del paquete (8 bytes de datos)
            0x04,
            0x01,
            0x00,
            0x00,
            0x00,
            0x64,  # Datos
            checksum_high,
            checksum_low,  # Checksum calculado
        ]
    )
    response = send_command(packet_search)
    time.sleep(PAUSA_CORTA)

    if response and response[9] == 0x00:
        id_huella = int.from_bytes(response[10:12], "big")
        score = int.from_bytes(response[12:14], "big")
        print(f"¡Huella encontrada! ID: {id_huella}, Puntuación: {score}")
        indice = get_data(f"indices_sensor/{id_huella}")
        if indice:
            usuario_id = indice.get("usuario_id")
            nombre = indice.get("nombre", "Desconocido")
            activo = indice.get("activo", True)
            print(f"👤 Usuario: {nombre}")
            print(f"📋 ID: {usuario_id}")
            print(f"✅ Estado: {'Activo' if activo else 'Inactivo'}")
            timestamp = generar_timestamp()
            datos_acceso = {
                "usuario_id": usuario_id,
                "id_sensor": id_huella,
                "nombre": nombre,
                "timestamp": timestamp,
                "score": score,
                "autorizado": activo,
                "tipo_acceso": "entrada",
            }
            acceso_id = f"acceso_{timestamp}"
            if send_data(f"registros_acceso/{acceso_id}", datos_acceso):
                print("📝 Acceso registrado en Firebase")
            else:
                print("⚠️ Error al registrar acceso en Firebase")
            return {"id": id_huella}
        else:
            print("⚠️ Usuario no encontrado en base de datos")
            return None
    else:
        print("❌ No se encontró ninguna coincidencia.")
        timestamp = generar_timestamp()
        datos_intento = {
            "timestamp": timestamp,
            "resultado": "no_autorizado",
            "tipo_acceso": "entrada_denegada",
        }
        send_data(f"intentos_fallidos/{timestamp}", datos_intento)
        return None


def mostrar_estadisticas():
    # Estadísticas locales del sensor
    packet_get_count = bytes(
        [0xEF, 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0x01, 0x00, 0x03, 0x09, 0x00, 0x0D]
    )
    response = send_command(packet_get_count)
    time.sleep(PAUSA_CORTA)
    if response and response[9] == 0x00:
        count_sensor = int.from_bytes(response[10:12], "big")
        print(f"📊 Huellas en sensor R307: {count_sensor}")
        usuarios_firebase = get_data("usuarios")
        if usuarios_firebase:
            count_firebase = len(usuarios_firebase)
            activos = sum(
                1 for u in usuarios_firebase.values() if u.get("activo", True)
            )
            print(f"👥 Usuarios en Firebase: {count_firebase}")
            print(f"✅ Usuarios activos: {activos}")
            print(f"❌ Usuarios inactivos: {count_firebase - activos}")
        else:
            print("📂 Sin usuarios registrados en Firebase")
    else:
        print("Error al obtener las estadísticas del sensor.")


def mostrar_posiciones():
    # Posiciones ocupadas en el sensor
    packet_get_index = bytes(
        [0xEF, 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0x01, 0x00, 0x03, 0x1F, 0x00, 0x23]
    )
    response = send_command(packet_get_index)
    time.sleep(1)
    if response and response[9] == 0x00:
        print("📍 Posiciones ocupadas en sensor:")
        posiciones_ocupadas = []
        for i in range(256):
            if i % 8 == 0:
                byte_index = 10 + (i // 8)
                if byte_index < len(response):
                    byte_value = response[byte_index]
            if (byte_value >> (i % 8)) & 1:
                posiciones_ocupadas.append(i)
        for pos in posiciones_ocupadas[:10]:
            indice = get_data(f"indices_sensor/{pos}")
            if indice:
                nombre = indice.get("nombre", "Sin nombre")
                estado = "🟢" if indice.get("activo", True) else "🔴"
                print(f"  Pos {pos}: {nombre} {estado}")
            else:
                print(f"  Pos {pos}: Sin datos en Firebase")
        if len(posiciones_ocupadas) > 10:
            print(f"  ... y {len(posiciones_ocupadas) - 10} más")
        print(f"Total: {len(posiciones_ocupadas)} posiciones ocupadas")
    else:
        print("Error al obtener las posiciones.")


def eliminar_huella(id_a_eliminar=None):
    if id_a_eliminar is None:
        opcion = input("¿Eliminar huella específica (1) o todas (2)? ")
        if opcion != "1":
            print("❌ Opción no válida")
            return False

        try:
            id_a_eliminar = int(input("ID de la huella a eliminar: "))
        except ValueError:
            print("❌ ID inválido")
            return False

    indice = get_data(f"indices_sensor/{id_a_eliminar}")
    usuario_info = None
    if indice:
        usuario_id = indice.get("usuario_id")
        if usuario_id:
            usuario_info = get_data(f"usuarios/{usuario_id}")

    pos_high = (id_a_eliminar >> 8) & 0xFF
    pos_low = id_a_eliminar & 0xFF

    data_to_checksum = [0x01, 0x00, 0x07, 0x0C, pos_high, pos_low, 0x00, 0x01]
    checksum = calculate_checksum(data_to_checksum)
    checksum_high = (checksum >> 8) & 0xFF
    checksum_low = checksum & 0xFF

    packet_delete = bytes(
        [
            0xEF,
            0x01,
            0xFF,
            0xFF,
            0xFF,
            0xFF,
            0x01,
            0x00,
            0x07,  # Longitud del paquete corregida
            0x0C,
            pos_high,
            pos_low,
            0x00,
            0x01,
            checksum_high,
            checksum_low,  # Checksum calculado
        ]
    )
    response = send_command(packet_delete)
    time.sleep(PAUSA_CORTA)

    if response and response[9] == 0x00:
        print(f"✅ Huella {id_a_eliminar} eliminada del sensor")
        if usuario_info:
            usuario_info["activo"] = False
            usuario_info["fecha_eliminacion"] = generar_timestamp()
            send_data(f"usuarios/{indice['usuario_id']}", usuario_info)
            indice["activo"] = False
            send_data(f"indices_sensor/{id_a_eliminar}", indice)
            print(
                f"✅ Usuario {usuario_info.get('nombre', 'N/A')} desactivado en Firebase"
            )
        else:
            print("⚠️ No se encontró información del usuario en Firebase")
        return True
    else:
        print("❌ Error al eliminar la huella del sensor")
        return False
