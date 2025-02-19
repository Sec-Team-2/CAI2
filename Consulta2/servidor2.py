import asyncio
import websockets
import json
import time
import re

# Diccionario para almacenar datos de cada cliente.
# Clave: IP del cliente (obtenida de websocket.remote_address[0])
# Valor: diccionario con:
#   "route": lista de palabras de la ruta,
#   "websocket": conexión actual (o None si está desconectado),
#   "buffer": lista de mensajes pendientes,
#   "last_seen": marca de tiempo de la última actividad.
client_data = {}

# Conjuntos para almacenar rutas abiertas y cerradas.
open_routes = set()
closed_routes = set()

client_lock = asyncio.Lock()

def validate_route(route):
    """ Solo permite letras, números y guion bajo, y limita a 60 caracteres. """
    patron = re.compile(r"^[a-zA-ZáéíóúÁÉÍÓÚüÜ\s]{1,60}$")
    if not bool(patron.match(route)):
       raise ValueError("Ruta no válida: máximo 60 caracteres alfabéticos y espacios.")
    return route

def register_places_return_closed(route):
    """
    Registra los lugares de la ruta en los conjuntos open_routes y closed_routes.
    """
    # Se asume que la ruta es una cadena de texto con palabras separadas por espacios.
    res = set()
    for place in route:
        # Si el lugar no está en open_routes ni en closed_routes, se asume que está abierto.
        if place not in open_routes and place not in closed_routes:
            open_routes.add(place)
        elif place in closed_routes:
            res.add(place)
    return res

def create_traffic_message(active, carretera, tramo, motivo, estado):
    """
    Crea un mensaje en formato JSON con la información del corte de tráfico.
    """
    return json.dumps({
        "activo": active,
        "carretera": carretera,
        "tramo_afectado": tramo,
        "motivo": motivo,
        "estado": estado,
    })

async def send_notification(message):
    """
    Intenta enviar 'message' a cada cliente.
    Si la conexión falla, se almacena en el buffer para reenvío posterior.
    """
    async with client_lock:
        for client_id, client in list(client_data.items()):
            ws = client.get("websocket")
            if ws is not None:
                try:
                    # Primero, intenta enviar mensajes pendientes
                    if client["buffer"]:
                        for buffered_message in client["buffer"]:
                            await ws.send(buffered_message)
                        client["buffer"].clear()
                    await ws.send(message)
                    client["last_seen"] = time.time()  # Actualiza la última actividad
                except websockets.exceptions.ConnectionClosed:
                    client["buffer"].append(message)
                    client["websocket"] = None
            else:
                client["buffer"].append(message)

async def handle_connection(websocket, path=None):
    """
    Maneja la conexión de un cliente.
    Puede recibir comandos especiales para agregar zonas abiertas o cerradas.
    """
    client_id = None
    try:
        message = await websocket.recv()

        # Comando para abrir una zona
        if message.startswith("ADD_OPEN:"):
            zone = message[len("ADD_OPEN:"):].strip()
            zone = validate_route(zone)  # Validar la zona
            async with client_lock:
                open_routes.add(zone)
                if zone in closed_routes:
                    closed_routes.remove(zone)
                await websocket.send(f"Zona '{zone}' añadida a rutas abiertas.")
                
        # Comando para cerrar una zona
        elif message.startswith("ADD_CLOSED:"):
            zone = message[len("ADD_CLOSED:"):].strip()
            zone = validate_route(zone)  # Validar la zona
            async with client_lock:
                if zone in open_routes:
                    open_routes.remove(zone)
                    closed_routes.add(zone)
                    # Notificar a todos los clientes
                    notification = create_traffic_message(
                        True, "A-4", zone, "Cierre de vía", "Tránsito interrumpido"
                    )
                    await websocket.send(notification)
                else:
                    await websocket.send(f"Error: La zona '{zone}' no existe.")
        else:
            # Si no es un comando especial, asumimos que es una ruta normal
            route = validate_route(message)
            client_id = websocket.remote_address[0]
            now = time.time()
            async with client_lock:
                if client_id in client_data:
                    client_entry = client_data[client_id]
                    client_entry["websocket"] = websocket
                    client_entry["route"] = route.split()
                    client_entry["last_seen"] = now
                else:
                    client_data[client_id] = {
                        "route": route.split(),
                        "websocket": websocket,
                        "buffer": [],
                        "last_seen": now
                    }
                    client_entry = client_data[client_id]

            await websocket.send("Conexión establecida. Monitoreando cortes en tu ruta.")
        
            # Registra los lugares de la ruta en los conjuntos open_routes y closed_routes y devuelve los lugares cerrados.
            closed_places = register_places_return_closed(client_entry["route"])
            print("ruta del cliente: " + str(client_entry["route"]))
            print("lugares cerrados: " + str(closed_places))
            print("rutas cerradas: " + str(closed_routes))
            if closed_places:
                for place in client_entry["route"]:
                    if place in closed_places:
                        message = create_traffic_message(
                            True, "A-4", place, "Obras en la vía", "Tránsito interrumpido"
                        )
                        # Si alguno de los lugares de la ruta está cerrado, se envía un mensaje al cliente.
                        await websocket.send(message)

            # Si existen mensajes pendientes, se envían al reconectar.
            if client_entry["buffer"]:
                for buffered_message in client_entry["buffer"]:
                    try:
                        await websocket.send(buffered_message)
                    except websockets.exceptions.ConnectionClosed:
                        break
                client_entry["buffer"].clear()

            # Espera a que la conexión se cierre.
            await websocket.wait_closed()


    except websockets.exceptions.ConnectionClosed:
        print(f"Conexión cerrada para cliente: {client_id}")
    except ValueError as e:
        await websocket.send(f"Error: {e}")
    finally:
        # Al cerrar la conexión, marca la conexión como None y actualiza last_seen.
        async with client_lock:
            if client_id in client_data:
                client_data[client_id]["websocket"] = None
                client_data[client_id]["last_seen"] = time.time()

async def broadcast_messages():
    """
    Tarea en segundo plano que cada 10 segundos genera un mensaje de tráfico
    y lo envía (o acumula en el buffer si el cliente está desconectado).
    """
    while True:
        await asyncio.sleep(10)
        message = create_traffic_message(
            True, "A-4", "Km 127 al 135", "Obras en la vía", "Tránsito interrumpido"
        )
        await send_notification(message)

async def cleanup_ghost_connections():
    """
    Tarea en segundo plano que limpia las entradas de clientes que estén
    desconectados y cuya última actividad haya sido hace más de 60 segundos.
    """
    while True:
        await asyncio.sleep(30)
        async with client_lock:
            current_time = time.time()
            threshold = 60  # Tiempo en segundos para considerar una conexión como fantasma.
            ghost_clients = [
                client_id 
                for client_id, client in client_data.items() 
                if client["websocket"] is None and current_time - client["last_seen"] > threshold
            ]
            for client_id in ghost_clients:
                del client_data[client_id]
                print(f"Se eliminó la conexión fantasma del cliente: {client_id}")

async def main():
    # Se establecen ping_interval y ping_timeout para detectar desconexiones de forma proactiva.
    server = await websockets.serve(handle_connection, "localhost", 8765,
                                    ping_interval=20, ping_timeout=20)
    print("Servidor WebSocket en ejecución en ws://localhost:8765")
    broadcaster = asyncio.create_task(broadcast_messages())
    cleanup_task = asyncio.create_task(cleanup_ghost_connections())
    await asyncio.Future()  # Mantiene el servidor en ejecución indefinidamente

if __name__ == "__main__":
    asyncio.run(main())