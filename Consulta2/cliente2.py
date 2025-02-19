import asyncio
import websockets

async def listen():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        valid_option = False
        option = None
        while not valid_option:
            option = input("Introduzca el número de la acción que desea realizar:\n"
                           "1. Registrar una ruta para monitoreo.\n"
                           "2. Abrir una zona\n"
                            "3. Cerrar una zona\n" 
                            )
            if option in ["1", "2", "3"]:
                valid_option = True
            else:
                print("Opción inválida.")

        if option == "1":
            route = input("Ingresa la ruta a monitorear (ejemplo: 'Sevilla'): ")
            await websocket.send(route)
            while True:
                try:
                    message = await websocket.recv()
                    print(f"Mensaje recibido: {message}")
                except websockets.exceptions.ConnectionClosed:
                    print("Conexión cerrada por el servidor.")
                    break
        elif option == "2":
            zone = input("Ingresa la zona a abrir (ejemplo: 'Sevilla'): ")
            await websocket.send(f"ADD_OPEN:{zone}")
            message = await websocket.recv()
            print(f"Mensaje recibido: {message}")
        elif option == "3":
            zone = input("Ingresa la zona a cerrar (ejemplo: 'Sevilla'): ")
            await websocket.send(f"ADD_CLOSED:{zone}")
            message = await websocket.recv()
            print(f"Mensaje recibido: {message}")


if __name__ == "__main__":
    asyncio.run(listen())