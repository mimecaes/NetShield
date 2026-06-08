import re
import socket
import struct
import threading

from filter import is_blocked
from logger import log_request

PUERTO_PROXY = 8080
BUFFER = 4096


def cerrar_socket(sock):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except:
        pass
    try:
        sock.close()
    except:
        pass


def enviar_error(sock, codigo, mensaje):
    cuerpo = mensaje.encode()
    respuesta = (
        f"HTTP/1.1 {codigo} {mensaje}\r\n"
        f"Content-Type: text/plain\r\n"
        f"Content-Length: {len(cuerpo)}\r\n"
        f"Connection: close\r\n\r\n"
    ).encode() + cuerpo
    try:
        sock.sendall(respuesta)
    except:
        pass


def enviar_bloqueado(sock, host):
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Sitio bloqueado</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; background: #F1F7D4; color: #4A4466;
           display: flex; justify-content: center; align-items: center; height: 100vh; }}
    .caja {{ background: white; border-radius: 16px; padding: 48px 56px; text-align: center;
             box-shadow: 0 4px 20px rgba(74,68,102,0.12); max-width: 480px; }}
    .icono {{ font-size: 3.5rem; margin-bottom: 16px; }}
    h1 {{ font-size: 1.6rem; margin-bottom: 10px; color: #4A4466; }}
    p {{ color: #6EADBC; margin-bottom: 6px; }}
    .dominio {{ font-weight: bold; color: #4A4466; font-size: 1.05rem; }}
  </style>
</head>
<body>
  <div class="caja">
    <div class="icono">🚫</div>
    <h1>Acceso bloqueado</h1>
    <p>El proxy ha bloqueado el acceso a:</p>
    <p class="dominio">{host}</p>
    <p style="margin-top:16px;font-size:0.9rem;">Este sitio esta en la lista de dominios restringidos.</p>
  </div>
</body>
</html>""".encode("utf-8")
    respuesta = (
        f"HTTP/1.1 403 Forbidden\r\n"
        f"Content-Type: text/html; charset=utf-8\r\n"
        f"Content-Length: {len(html)}\r\n"
        f"Connection: close\r\n\r\n"
    ).encode() + html
    try:
        sock.sendall(respuesta)
    except:
        pass


def separar_host_puerto(autoridad, puerto_default):
    autoridad = autoridad.strip()
    if ":" in autoridad:
        partes = autoridad.rsplit(":", 1)
        if partes[1].isdigit():
            return partes[0], int(partes[1])
    return autoridad, puerto_default


def parsear_peticion(data):
    try:
        texto = data.decode("iso-8859-1", errors="replace")
        lineas = texto.split("\r\n")
        partes = lineas[0].split()
        if len(partes) < 2:
            return None, None, 80, data

        metodo = partes[0].upper()
        objetivo = partes[1]
        host = None
        puerto = 80

        if metodo == "CONNECT":
            host, puerto = separar_host_puerto(objetivo, 443)
            return metodo, host, puerto, data

        if objetivo.startswith("http://") or objetivo.startswith("https://"):
            m = re.match(r"^(https?)://([^/\s]+)", objetivo, re.IGNORECASE)
            if m:
                esquema = m.group(1).lower()
                host, puerto = separar_host_puerto(m.group(2), 443 if esquema == "https" else 80)
                return metodo, host, puerto, data

        for linea in lineas[1:]:
            if linea.lower().startswith("host:"):
                host, puerto = separar_host_puerto(linea.split(":", 1)[1].strip(), 80)
                return metodo, host, puerto, data

        return metodo, None, puerto, data
    except:
        return None, None, 80, data


def construir_url(metodo, host, puerto, data):
    try:
        texto = data.decode("iso-8859-1", errors="replace")
        objetivo = texto.split("\r\n", 1)[0].split()[1]
        if metodo == "CONNECT":
            return f"https://{host}:{puerto}/"
        if objetivo.startswith("http://") or objetivo.startswith("https://"):
            return objetivo
        if objetivo.startswith("/"):
            return f"http://{host}{objetivo}"
    except:
        pass
    return f"http://{host}/"


def leer_peticion(sock):
    data = b""
    try:
        sock.settimeout(5)
        while b"\r\n\r\n" not in data:
            chunk = sock.recv(BUFFER)
            if not chunk:
                break
            data += chunk

        fin_cabecera = data.find(b"\r\n\r\n")
        if fin_cabecera != -1:
            cabeceras = data[:fin_cabecera].decode("iso-8859-1", errors="replace")
            for linea in cabeceras.split("\r\n"):
                if linea.lower().startswith("content-length:"):
                    longitud = int(linea.split(":", 1)[1].strip())
                    inicio = fin_cabecera + 4
                    while len(data) < inicio + longitud:
                        chunk = sock.recv(BUFFER)
                        if not chunk:
                            break
                        data += chunk
                    break
    except:
        pass
    return data


def leer_respuesta(sock):
    data = b""
    sock.settimeout(5)
    try:
        while b"\r\n\r\n" not in data:
            chunk = sock.recv(BUFFER)
            if not chunk:
                return data
            data += chunk

        fin_cabecera = data.find(b"\r\n\r\n")
        cabeceras = data[:fin_cabecera].decode("iso-8859-1", errors="replace")
        for linea in cabeceras.split("\r\n"):
            if linea.lower().startswith("content-length:"):
                longitud = int(linea.split(":", 1)[1].strip())
                while len(data) < fin_cabecera + 4 + longitud:
                    chunk = sock.recv(BUFFER)
                    if not chunk:
                        break
                    data += chunk
                return data

        # Sin Content-Length: leer hasta que cierre la conexion o timeout
        while True:
            try:
                chunk = sock.recv(BUFFER)
                if not chunk:
                    break
                data += chunk
            except socket.timeout:
                break
    except:
        pass
    return data


def manejar_http(cliente, host, puerto, peticion):
    upstream = None
    try:
        upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        upstream.settimeout(5)
        upstream.connect((host, puerto))
        upstream.sendall(peticion)
        respuesta = leer_respuesta(upstream)
        if not respuesta:
            enviar_error(cliente, 502, "Bad Gateway")
            return "502", 0
        cliente.sendall(respuesta)
        return "200", len(respuesta)
    except:
        enviar_error(cliente, 502, "Bad Gateway")
        return "502", 0
    finally:
        if upstream:
            cerrar_socket(upstream)


def relay(origen, destino, contador=None, lock=None):
    try:
        while True:
            data = origen.recv(BUFFER)
            if not data:
                break
            destino.sendall(data)
            if contador is not None:
                with lock:
                    contador[0] += len(data)
    except:
        pass


def extraer_sni(data):
    # Parsear el ClientHello TLS para obtener el SNI (Server Name Indication)
    try:
        if len(data) < 5 or data[0] != 22:
            return None

        # TLS record (5B) + Handshake header (4B) + client_version (2B) + random (32B) = offset 43
        offset = 43
        if offset >= len(data):
            return None

        # Session ID
        offset += 1 + data[offset]

        # Cipher Suites
        if offset + 2 > len(data):
            return None
        offset += 2 + struct.unpack("!H", data[offset:offset + 2])[0]

        # Compression Methods
        if offset >= len(data):
            return None
        offset += 1 + data[offset]

        # Extensions
        if offset + 2 > len(data):
            return None
        total_ext = struct.unpack("!H", data[offset:offset + 2])[0]
        offset += 2
        fin = offset + total_ext

        while offset + 4 <= fin and offset + 4 <= len(data):
            tipo = struct.unpack("!H", data[offset:offset + 2])[0]
            tam = struct.unpack("!H", data[offset + 2:offset + 4])[0]
            offset += 4
            if tipo == 0 and offset + 5 <= len(data):  # SNI extension
                longitud_nombre = struct.unpack("!H", data[offset + 3:offset + 5])[0]
                if offset + 5 + longitud_nombre <= len(data):
                    return data[offset + 5:offset + 5 + longitud_nombre].decode("ascii", errors="ignore")
            offset += tam
    except:
        pass
    return None


def manejar_https(cliente, host, puerto):
    upstream = None
    bytes_al_cliente = [0]
    lock = threading.Lock()

    try:
        cliente.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")

        # Leer el primer paquete TLS para extraer el SNI
        cliente.settimeout(3)
        primer_paquete = b""
        try:
            primer_paquete = cliente.recv(BUFFER)
        except:
            pass

        sni = extraer_sni(primer_paquete)
        host_real = sni if sni else host
        url = f"https://{host_real}:{puerto}/"

        if is_blocked(host_real, url):
            # Enviar TLS Alert fatal para que el navegador muestre error de conexion
            try:
                cliente.sendall(bytes([21, 3, 3, 0, 2, 2, 40]))
            except:
                pass
            return "403", 0

        upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        upstream.settimeout(5)
        upstream.connect((host_real, puerto))

        if primer_paquete:
            upstream.sendall(primer_paquete)

        t1 = threading.Thread(target=relay, args=(cliente, upstream), daemon=True)
        t2 = threading.Thread(target=relay, args=(upstream, cliente, bytes_al_cliente, lock), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        return "200", bytes_al_cliente[0]
    except:
        return "502", 0
    finally:
        if upstream:
            cerrar_socket(upstream)


def atender_cliente(cliente, direccion):
    metodo = ""
    host = None
    url = ""

    try:
        data = leer_peticion(cliente)
        if not data:
            return

        metodo, host, puerto, peticion = parsear_peticion(data)
        if not metodo or not host:
            enviar_error(cliente, 400, "Bad Request")
            return

        url = construir_url(metodo, host, puerto, data)

        if is_blocked(host, url):
            enviar_bloqueado(cliente, host)
            log_request(direccion[0], host, url, metodo, "403", 0)
            print(f"[BLOQUEADO] {host}")
            return

        if metodo == "CONNECT":
            estado, bytes_enviados = manejar_https(cliente, host, puerto)
        elif metodo in ("GET", "POST"):
            estado, bytes_enviados = manejar_http(cliente, host, puerto, peticion)
        else:
            enviar_error(cliente, 405, "Method Not Allowed")
            estado, bytes_enviados = "405", 0

        log_request(direccion[0], host, url, metodo, estado, bytes_enviados)
        print(f"[{metodo}] {host} -> {estado}")
    except:
        pass
    finally:
        cerrar_socket(cliente)


def main():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(("0.0.0.0", PUERTO_PROXY))
    servidor.listen(50)
    print(f"Proxy escuchando en puerto {PUERTO_PROXY}")

    while True:
        try:
            cliente, direccion = servidor.accept()
            t = threading.Thread(target=atender_cliente, args=(cliente, direccion), daemon=True)
            t.start()
        except:
            pass


if __name__ == "__main__":
    main()
