# Núcleo del proxy. Acepta conexiones TCP, parsea HTTP a mano con socket puro, maneja GET/POST y CONNECT para HTTPS.
"""Nucleo del proxy HTTP/HTTPS implementado solo con la biblioteca estandar.

Separa la logica en funciones pequenas para facilitar la integracion con los
modulos de filtrado y registro cuando esten disponibles.
"""

import re
import socket
import struct
import threading


PUERTO_PROXY = 8080
BUFFER_SIZE = 4096
HEADER_END = b"\r\n\r\n"


try:
	from filter import is_blocked as _external_is_blocked
except Exception:
	_external_is_blocked = None


try:
	from logger import log_request as _external_log_request
except Exception:
	_external_log_request = None


def is_blocked(host, url):
	"""Aplica el filtro externo si existe; en caso contrario, permite el acceso."""

	if callable(_external_is_blocked):
		try:
			return bool(_external_is_blocked(host, url))
		except Exception:
			return False
	return False


def log_request(ip, host, method, status, bytes_transferred):
	"""Registra la solicitud si el modulo de logging ya esta listo."""

	if callable(_external_log_request):
		try:
			_external_log_request(ip, host, method, status, bytes_transferred)
		except Exception:
			pass


def safe_close(sock):
	"""Cierra un socket sin propagar errores."""

	if sock is None:
		return
	try:
		sock.shutdown(socket.SHUT_RDWR)
	except Exception:
		pass
	try:
		sock.close()
	except Exception:
		pass


def send_error(client_socket, code, message):
	"""Envio simple de una respuesta HTTP de error."""

	body = (message + "\n").encode("utf-8")
	response = (
		f"HTTP/1.1 {code} {message}\r\n"
		f"Content-Type: text/plain; charset=utf-8\r\n"
		f"Content-Length: {len(body)}\r\n"
		f"Connection: close\r\n\r\n"
	).encode("ascii") + body
	try:
		client_socket.sendall(response)
	except Exception:
		pass


def split_host_port(authority, default_port):
	"""Separa host y puerto manejando hostnames normales e IPv6 entre corchetes."""

	authority = authority.strip()
	if not authority:
		return None, default_port

	if authority.startswith("["):
		cierre = authority.find("]")
		if cierre != -1:
			host = authority[1:cierre]
			resto = authority[cierre + 1 :]
			if resto.startswith(":") and resto[1:].isdigit():
				return host, int(resto[1:])
			return host, default_port

	if authority.count(":") == 1:
		host, port_texto = authority.rsplit(":", 1)
		if port_texto.isdigit():
			return host, int(port_texto)

	if authority.isdigit():
		return authority, default_port

	return authority, default_port


def build_url(method, host, port, data):
	"""Reconstruye la URL completa para el filtrado y el registro."""

	texto = data.decode("iso-8859-1", errors="replace")
	primera_linea = texto.split("\r\n", 1)[0]
	partes = primera_linea.split()

	if method == "CONNECT":
		return f"https://{host}:{port}/"

	if len(partes) >= 2:
		objetivo = partes[1]
		if objetivo.startswith("http://") or objetivo.startswith("https://"):
			return objetivo
		if objetivo.startswith("/"):
			esquema = "https" if port == 443 else "http"
			puerto_visible = ""
			if (esquema == "http" and port != 80) or (esquema == "https" and port != 443):
				puerto_visible = f":{port}"
			return f"{esquema}://{host}{puerto_visible}{objetivo}"

	esquema = "https" if port == 443 else "http"
	puerto_visible = ""
	if (esquema == "http" and port != 80) or (esquema == "https" and port != 443):
		puerto_visible = f":{port}"
	return f"{esquema}://{host}{puerto_visible}/"


def receive_request(client_socket):
	"""Lee la solicitud completa desde el navegador antes de procesarla."""

	data = b""
	try:
		while HEADER_END not in data:
			chunk = client_socket.recv(BUFFER_SIZE)
			if not chunk:
				break
			data += chunk
			if len(data) > 1024 * 1024:
				break

		if not data:
			return b""

		header_end = data.find(HEADER_END)
		if header_end == -1:
			return data

		headers_text = data[:header_end].decode("iso-8859-1", errors="replace")
		first_line = headers_text.split("\r\n", 1)[0]
		method_match = re.match(r"^([A-Z]+)\s+\S+\s+HTTP/\d\.\d$", first_line)
		method = method_match.group(1) if method_match else ""

		content_length = 0
		for line in headers_text.split("\r\n")[1:]:
			if line.lower().startswith("content-length:"):
				value = line.split(":", 1)[1].strip()
				if value.isdigit():
					content_length = int(value)
				break

		total_esperado = header_end + len(HEADER_END) + content_length
		while len(data) < total_esperado:
			chunk = client_socket.recv(BUFFER_SIZE)
			if not chunk:
				break
			data += chunk

		if method == "POST" and len(data) < total_esperado:
			return data

		return data
	except Exception:
		return data


def parse_request(data):
	"""Parsa bytes crudos y retorna (metodo, host, puerto, request_completo)."""

	texto = data.decode("iso-8859-1", errors="replace")
	lineas = texto.split("\r\n")
	if not lineas or not lineas[0].strip():
		return None, None, 80, data

	primera_linea = lineas[0]
	partes = primera_linea.split()
	if len(partes) < 2:
		return None, None, 80, data

	method = partes[0].upper()
	objetivo = partes[1]
	host = None
	puerto = 80

	if method == "CONNECT":
		host, puerto = split_host_port(objetivo, 443)
		return method, host, puerto, data

	if objetivo.startswith("http://") or objetivo.startswith("https://"):
		coincidencia = re.match(r"^(https?)://([^/\s]+)(/.*)?$", objetivo, re.IGNORECASE)
		if coincidencia:
			esquema = coincidencia.group(1).lower()
			autoridad = coincidencia.group(2)
			host, puerto = split_host_port(autoridad, 443 if esquema == "https" else 80)
			return method, host, puerto, data

	for linea in lineas[1:]:
		if linea.lower().startswith("host:"):
			autoridad = linea.split(":", 1)[1].strip()
			host, puerto = split_host_port(autoridad, 80)
			return method, host, puerto, data

	return method, None, puerto, data


def chunked_complete(body):
	"""Verifica de forma simple si un cuerpo chunked ya termino."""

	offset = 0
	total = len(body)

	while True:
		linea_fin = body.find(b"\r\n", offset)
		if linea_fin == -1:
			return False

		linea = body[offset:linea_fin].split(b";", 1)[0].strip()
		if not linea:
			return False

		try:
			tamano = int(linea, 16)
		except ValueError:
			return False

		offset = linea_fin + 2
		if total < offset + tamano + 2:
			return False

		offset += tamano + 2
		if tamano == 0:
			return total >= offset


def read_http_response(upstream_socket):
	"""Lee la respuesta del servidor destino respetando Content-Length o chunked."""

	data = b""
	upstream_socket.settimeout(5)

	try:
		while HEADER_END not in data:
			chunk = upstream_socket.recv(BUFFER_SIZE)
			if not chunk:
				break
			data += chunk
			if len(data) > 1024 * 1024:
				break

		if not data:
			return b""

		header_end = data.find(HEADER_END)
		if header_end == -1:
			while True:
				try:
					chunk = upstream_socket.recv(BUFFER_SIZE)
				except socket.timeout:
					break
				if not chunk:
					break
				data += chunk
			return data

		headers_text = data[:header_end].decode("iso-8859-1", errors="replace")
		body = data[header_end + len(HEADER_END) :]

		content_length = None
		chunked = False
		for line in headers_text.split("\r\n")[1:]:
			lower = line.lower()
			if lower.startswith("content-length:"):
				value = line.split(":", 1)[1].strip()
				if value.isdigit():
					content_length = int(value)
			elif lower.startswith("transfer-encoding:") and "chunked" in lower:
				chunked = True

		if content_length is not None:
			while len(body) < content_length:
				try:
					chunk = upstream_socket.recv(BUFFER_SIZE)
				except socket.timeout:
					break
				if not chunk:
					break
				body += chunk
			return data[: header_end + len(HEADER_END)] + body[:content_length]

		if chunked:
			while not chunked_complete(body):
				try:
					chunk = upstream_socket.recv(BUFFER_SIZE)
				except socket.timeout:
					break
				if not chunk:
					break
				body += chunk
			return data[: header_end + len(HEADER_END)] + body

		while True:
			try:
				chunk = upstream_socket.recv(BUFFER_SIZE)
			except socket.timeout:
				break
			if not chunk:
				break
			data += chunk

		return data
	except Exception:
		return data


def handle_http(client_socket, host, port, request):
	"""Gestiona GET y POST reenviando la solicitud y la respuesta completa."""

	upstream_socket = None
	bytes_transferred = 0

	try:
		upstream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		upstream_socket.settimeout(5)
		upstream_socket.connect((host, port))
		upstream_socket.sendall(request)

		response = read_http_response(upstream_socket)
		if not response:
			send_error(client_socket, 502, "Bad Gateway")
			return "502", 0

		client_socket.sendall(response)
		bytes_transferred = len(request) + len(response)
		return "200", bytes_transferred
	except Exception:
		send_error(client_socket, 502, "Bad Gateway")
		return "502", bytes_transferred
	finally:
		safe_close(upstream_socket)


def relay(source, destination, stats=None):
	"""Reenvia bytes en una sola direccion durante el tunel HTTPS."""

	try:
		while True:
			data = source.recv(BUFFER_SIZE)
			if not data:
				break
			destination.sendall(data)
			if stats is not None:
				stats["lock"].acquire()
				try:
					stats["bytes"] += len(data)
				finally:
					stats["lock"].release()
	except Exception:
		pass


def extract_sni(data):
	"""Extrae el hostname SNI desde un ClientHello TLS si el paquete lo contiene."""

	try:
		if len(data) < 5:
			return None

		content_type, version, record_length = struct.unpack("!BHH", data[:5])
		if content_type != 22:
			return None

		if len(data) < 5 + record_length:
			return None

		if data[5] != 1:
			return None

		offset = 9
		if len(data) < offset + 34:
			return None

		offset += 34

		if len(data) < offset + 1:
			return None
		session_id_length = data[offset]
		offset += 1 + session_id_length

		if len(data) < offset + 2:
			return None
		cipher_suites_length = struct.unpack("!H", data[offset : offset + 2])[0]
		offset += 2 + cipher_suites_length

		if len(data) < offset + 1:
			return None
		compression_methods_length = data[offset]
		offset += 1 + compression_methods_length

		if len(data) < offset + 2:
			return None
		extensions_length = struct.unpack("!H", data[offset : offset + 2])[0]
		offset += 2
		extensions_end = offset + extensions_length

		while offset + 4 <= len(data) and offset < extensions_end:
			extension_type = struct.unpack("!H", data[offset : offset + 2])[0]
			extension_length = struct.unpack("!H", data[offset + 2 : offset + 4])[0]
			offset += 4

			if offset + extension_length > len(data):
				return None

			extension_data = data[offset : offset + extension_length]
			if extension_type == 0 and len(extension_data) >= 5:
				server_name_list_length = struct.unpack("!H", extension_data[:2])[0]
				list_offset = 2
				list_end = min(len(extension_data), 2 + server_name_list_length)

				while list_offset + 3 <= list_end:
					name_type = extension_data[list_offset]
					name_length = struct.unpack(
						"!H", extension_data[list_offset + 1 : list_offset + 3]
					)[0]
					list_offset += 3

					if list_offset + name_length > list_end:
						return None

					if name_type == 0:
						hostname = extension_data[list_offset : list_offset + name_length]
						try:
							return hostname.decode("ascii")
						except Exception:
							return hostname.decode("utf-8", errors="ignore")

					list_offset += name_length

			offset += extension_length

	except Exception:
		return None

	return None


def handle_https(client_socket, host, port, raw_data):
	"""Gestiona CONNECT creando un tunel TCP sin descifrar TLS."""

	upstream_socket = None
	stats = {"bytes": 0, "lock": threading.Lock()}
	resolved_host = host

	try:
		client_socket.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")

		# El raw_data de CONNECT es la peticion HTTP, no el ClientHello TLS.
		# El primer paquete real del cliente llega despues del 200.
		first_tls_packet = b""
		try:
			client_socket.settimeout(5)
			first_tls_packet = client_socket.recv(BUFFER_SIZE)
		except Exception:
			first_tls_packet = b""

		sni = extract_sni(first_tls_packet)
		if sni:
			resolved_host = sni

		url = f"https://{resolved_host}:{port}/"
		if is_blocked(resolved_host, url):
			send_error(client_socket, 403, "Forbidden")
			return "403", 0

		upstream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		upstream_socket.settimeout(5)
		upstream_socket.connect((resolved_host, port))

		if first_tls_packet:
			upstream_socket.sendall(first_tls_packet)
			stats["bytes"] += len(first_tls_packet)

		cliente_a_servidor = threading.Thread(
			target=relay, args=(client_socket, upstream_socket, stats), daemon=True
		)
		servidor_a_cliente = threading.Thread(
			target=relay, args=(upstream_socket, client_socket, stats), daemon=True
		)

		cliente_a_servidor.start()
		servidor_a_cliente.start()

		cliente_a_servidor.join()
		servidor_a_cliente.join()

		return "200", stats["bytes"]
	except Exception:
		send_error(client_socket, 502, "Bad Gateway")
		return "502", stats["bytes"]
	finally:
		safe_close(upstream_socket)


def handle_client(client_socket, client_address):
	"""Procesa cada conexion en su propio hilo y no deja caer el servidor."""

	method = ""
	host = None
	port = 80
	status = "502"
	bytes_transferred = 0

	try:
		raw_data = receive_request(client_socket)
		if not raw_data:
			return

		method, host, port, request = parse_request(raw_data)
		if not method:
			send_error(client_socket, 502, "Bad Gateway")
			status = "502"
			return

		url = build_url(method, host or "", port, request)

		if host and is_blocked(host, url):
			send_error(client_socket, 403, "Forbidden")
			status = "403"
			print(f"[{method}] {host}:{port} -> {status}")
			log_request(client_address[0], host, method, status, bytes_transferred)
			return

		if method == "CONNECT":
			status, bytes_transferred = handle_https(client_socket, host or "", port, request)
		elif method in ("GET", "POST"):
			if host is None:
				send_error(client_socket, 502, "Bad Gateway")
				status = "502"
			else:
				status, bytes_transferred = handle_http(client_socket, host, port, request)
		else:
			send_error(client_socket, 502, "Bad Gateway")
			status = "502"

		if host:
			print(f"[{method}] {host}:{port} -> {status}")
			log_request(client_address[0], host, method, status, bytes_transferred)
	except Exception:
		try:
			send_error(client_socket, 502, "Bad Gateway")
		except Exception:
			pass
		if method and host:
			print(f"[{method}] {host}:{port} -> 502")
			log_request(client_address[0], host, method, "502", bytes_transferred)
	finally:
		safe_close(client_socket)


def main():
	"""Arranca el servidor proxy principal en el puerto 8080."""

	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

	try:
		server_socket.bind(("0.0.0.0", PUERTO_PROXY))
		server_socket.listen(100)
		print(f"Proxy HTTP escuchando en el puerto {PUERTO_PROXY}")

		while True:
			try:
				client_socket, client_address = server_socket.accept()
			except Exception:
				continue

			hilo = threading.Thread(
				target=handle_client,
				args=(client_socket, client_address),
				daemon=True,
			)
			hilo.start()
	except Exception as error:
		print(f"Error al iniciar el proxy: {error}")
	finally:
		safe_close(server_socket)


if __name__ == "__main__":
	main()
