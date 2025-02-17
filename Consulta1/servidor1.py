import asyncio
import json

# Base de datos simulada para almacenar los kilómetros por vehículo
datos_kilometros = 0
lock = asyncio.Lock()  # Usar Lock asincrónico para evitar condiciones de carrera

async def manejar_cliente(reader, writer):
    """ Maneja la conexión de un cliente. """
    global datos_kilometros
    addr = writer.get_extra_info('peername')
    print(f"Conexión establecida con {addr}")
    
    try:
        # Recibir datos
        data = await reader.read(1024)
        if not data:
            return
        
        # Decodificar los datos JSON
        try:
            mensaje = json.loads(data.decode('utf-8'))
            kilometros = mensaje.get("kilometros")
        except json.JSONDecodeError:
            print("Datos mal formateados recibidos")
            return
        
        # Validaciones de integridad
        if isinstance(kilometros, int) and kilometros >= 0 and kilometros <= 16000:
            print(f"Datos recibidos: {kilometros}")
    
            # Evitar condiciones de carrera con lock
            async with lock:
                print(datos_kilometros)
                datos_kilometros += kilometros
                print(f"Kilómetros totales: {datos_kilometros}")
    
    except Exception as e:
        print(f"Error al manejar cliente {addr}: {e}")
    
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    server = await asyncio.start_server(
        manejar_cliente, '0.0.0.0', 65432
    )
    addr = server.sockets[0].getsockname()
    print(f"Servidor escuchando en {addr}")

    async with server:
        await server.serve_forever()

# Ejecutar el servidor
asyncio.run(main())
