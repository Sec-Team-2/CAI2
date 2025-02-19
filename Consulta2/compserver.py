import asyncio
import websockets
import json
import time
import re

# Diccionario para almacenar datos de cada cliente.
# Usamos una clave única formada por IP y puerto para evitar colisiones.
client_data = {}

# Conjuntos para almacenar rutas abiertas y cerradas.
open_routes = set()
closed_routes = set()

client_lock = asyncio.Lock()

def validate_route(route):
    """Permite únicamente letras (con acentos), espacios y limita a 60 caracteres."""
    patron = re.compile(r"^[a-zA-ZáéíóúÁÉÍÓÚüÜ\s]{1,60}$")
    if not patron.match(route):
        raise ValueError("Ruta no válida: máximo 60 caracteres alfabéticos y espacios.")
    return route

def register_places_return_closed(route_list):
    """
    Registra los lugares de la ruta en los conjuntos open_routes y closed_routes.
    Devuelve el conjunto de lugares que están cerrados.
    """
    closed = set()
    for place in route_list:
        if place not in open_routes and place not in closed_routes:
            open_routes.add(place)
        elif place in closed_routes:
            closed.add(place)
    return closed

def create_traffic_message(active, carretera, tramo, motivo, estado):
    """Crea un mensaje JSON con la información del corte de tráfico."""
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
    Si la conexión falla, almacena el mensaje en el buffer para reenvío posterior.
    """
    async with client_lock:
        for client_id, client in list(client_data.items()):
            ws = client.get("websocket")
            if ws is not None:
                try:
                    # Envía primero los mensajes pendientes.
                    while client["buffer"]:
                        buffered_message = client["buffer"].pop(0)
                        await ws.send(buffered_message)
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
    Se procesa cada mensaje recibido en un bucle para permitir múltiples interacciones.
    Puede recibir comandos especiales para agregar zonas abiertas o cerradas,
    o una ruta para monitorizar.
    """
    # Generamos un ID único usando IP y puerto
    client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    async with client_lock:
        if client_id not in client_data:
            client_data[client_id] = {
                "route": [],
                "websocket": websocket,
                "buffer": [],
                "last_seen": time.time()
            }
        else:
            client_data[client_id]["websocket"] = websocket
            client_data[client_id]["last_seen"] = time.time()

    try:
        async for message in websocket:
            try:
                # Comando para abrir una zona
                if message.startswith("ADD_OPEN:"):
                    zone = message[len("ADD_OPEN:"):].strip()
                    zone = validate_route(zone)
                    async with client_lock:
                        open_routes.add(zone)
                        closed_routes.discard(zone)
                    await websocket.send(f"Zona '{zone}' añadida a rutas abiertas.")
                
                # Comando para cerrar una zona
                elif message.startswith("ADD_CLOSED:"):
                    zone = message[len("ADD_CLOSED:"):].strip()
                    zone = validate_route(zone)
                    async with client_lock:
                        if zone in open_routes:
                            open_routes.remove(zone)
                            closed_routes.add(zone)
                            # Notificar a todos los clientes del cierre
                            notification = create_traffic_message(
                                True, "A-4", zone, "Cierre de vía", "Tránsito interrumpido"
                            )
                            await send_notification(notification)
                            await websocket.send(f"Zona '{zone}' cerrada.")
                        else:
                            await websocket.send(f"Error: La zona '{zone}' no existe en rutas abiertas.")
                
                # Caso: mensaje con una ruta normal.
                else:
                    route = validate_route(message)
                    route_list = route.split()
                    async with client_lock:
                        client_data[client_id]["route"] = route_list
                        client_data[client_id]["last_seen"] = time.time()
                    await websocket.send("Conexión establecida. Monitoreando cortes en tu ruta.")

                    # Registra los lugares de la ruta y determina cuáles están cerrados.
                    closed_places = register_places_return_closed(route_list)
                    if closed_places:
                        for place in route_list:
                            if place in closed_places:
                                msg = create_traffic_message(
                                    True, "A-4", place, "Obras en la vía", "Tránsito interrumpido"
                                )
                                await websocket.send(msg)
                    
                    # Envía cualquier mensaje pendiente almacenado en el buffer.
                    async with client_lock:
                        while client_data[client_id]["buffer"]:
                            buffered_message = client_data[client_id]["buffer"].pop(0)
                            await websocket.send(buffered_message)
            
            except ValueError as e:
                await websocket.send(f"Error: {e}")
    
    except websockets.exceptions.ConnectionClosed:
        print(f"Conexión cerrada para cliente: {client_id}")
    
    finally:
        # Al cerrar la conexión, se marca el websocket como None y se actualiza la última actividad.
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
    Tarea en segundo plano que limpia las entradas de clientes desconectados cuya
    última actividad haya sido hace más de 60 segundos.
    """
    while True:
        await asyncio.sleep(30)
        async with client_lock:
            current_time = time.time()
            threshold = 60  # segundos para considerar una conexión como fantasma.
            ghost_clients = [
                cid for cid, client in client_data.items()
                if client["websocket"] is None and current_time - client["last_seen"] > threshold
            ]
            for cid in ghost_clients:
                del client_data[cid]
                print(f"Se eliminó la conexión fantasma del cliente: {cid}")

async def main():
    # Se establecen ping_interval y ping_timeout para detectar desconexiones proactivamente.
    server = await websockets.serve(
        handle_connection, "localhost", 8765, ping_interval=20, ping_timeout=20
    )
    print("Servidor WebSocket en ejecución en ws://localhost:8765")
    asyncio.create_task(broadcast_messages())
    asyncio.create_task(cleanup_ghost_connections())
    await asyncio.Future()  # Mantiene el servidor en ejecución indefinidamente

if __name__ == "__main__":
    asyncio.run(main())
