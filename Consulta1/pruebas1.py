import socket
import threading
import json
import random

# Configuración del servidor al que nos vamos a conectar
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 65432
NUM_CONNECTIONS = 100  # Número de conexiones simultáneas

def client_task(i):
    kilometros = random.randint(0, 16000)
    """ Envía los kilómetros recorridos por un vehículo al servidor """
    mensaje = {
        "kilometros": kilometros
    }

    try:
        # Crear socket TCP/IP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect((SERVER_HOST, SERVER_PORT))  # Conectar al servidor
            client.sendall(json.dumps(mensaje).encode('utf-8'))  # Enviar datos

    except Exception as e:
        print(f"Error al conectar con el servidor: {e}")

# Lanzar múltiples clientes en hilos
threads = []
for i in range(NUM_CONNECTIONS):
    t = threading.Thread(target=client_task, args=(i,))
    t.start()
    threads.append(t)

# Esperar a que todos terminen
for t in threads:
    t.join()
