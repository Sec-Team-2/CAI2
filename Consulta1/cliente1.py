import socket
import json

# Configuración del cliente
SERVER_HOST = '127.0.0.1'  # Cambia esto a la IP del servidor si es remoto
SERVER_PORT = 65432

def enviar_kilometros(kilometros):
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

# Ejemplo de uso
if __name__ == "__main__":
    kilometros = int(input("Introduzca los kilómetros recorridos: "))
    enviar_kilometros(kilometros)
