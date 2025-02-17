import socket
import threading
import struct
import json

# Configuración del servidor
HOST = '0.0.0.0'  # Escucha en todas las interfaces de red
PORT = 65432       # Puerto de conexión

# Base de datos simulada para almacenar los kilómetros por vehículo

lock = threading.Lock()  # Para evitar condiciones de carrera
datos_kilometros = 0

def manejar_cliente(conn, addr):
    """ Maneja la conexión de un cliente. """
    global datos_kilometros
    print(f"Conexión establecida con {addr}")
    
    try:
        # Recibir datos en paquetes bien definidos
        data = conn.recv(1024)
        if not data:
            return
        
        # Decodificar datos JSON para evitar problemas de desbordamiento
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
            with lock:
                print(datos_kilometros)
                datos_kilometros += kilometros
                print(f"Kilómetros totales: {datos_kilometros}")
    
    except Exception as e:
        print(f"Error al manejar cliente {addr}: {e}")
    
    finally:
        conn.close()

# Configurar y arrancar el servidor
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Servidor escuchando en {HOST}:{PORT}")
    
    while True:
        conn, addr = server.accept()
        threading.Thread(target=manejar_cliente, args=(conn, addr)).start()