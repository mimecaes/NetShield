"""Registro de solicitudes y métricas en memoria para el proxy.

Este modulo guarda cada solicitud en logs.csv y mantiene un resumen seguro para
ser consumido por el panel web.
"""

import csv
import os
import threading
from datetime import datetime


# Archivo de log ubicado en la misma carpeta que este modulo.
LOGS_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs.csv")


# Proteccion para accesos concurrentes desde varios hilos del proxy.
_metricas_lock = threading.Lock()


# Contadores y colecciones en memoria para el panel web.
metricas = {
	"total_solicitudes": 0,
	"total_bytes": 0,
	"solicitudes_bloqueadas": 0,
	"solicitudes_permitidas": 0,
	"dominios": {},
	"clientes": {},
}


def _asegurar_archivo_csv():
	"""Crea logs.csv con encabezados si aun no existe."""

	if os.path.exists(LOGS_CSV):
		return

	try:
		with open(LOGS_CSV, "w", newline="", encoding="utf-8") as archivo:
			escritor = csv.writer(archivo)
			escritor.writerow(["timestamp", "ip_cliente", "dominio", "metodo", "estado", "bytes"])
	except OSError as exc:
		print(f"[AVISO] No se pudo crear logs.csv: {exc}")


def _normalizar_texto(valor):
	"""Convierte valores vacios o nulos en texto util para el log."""

	if valor is None:
		return "desconocido"

	texto = str(valor).strip()
	return texto if texto else "desconocido"


def _normalizar_bytes(bytes_transferred):
	"""Convierte el total de bytes a entero sin romper el proxy."""

	try:
		return int(bytes_transferred)
	except (TypeError, ValueError):
		return 0


def _escribir_csv(timestamp, ip, host, method, estado, bytes_transferred):
	"""Escribe una fila en logs.csv sin detener el proxy ante errores."""

	_asegurar_archivo_csv()

	try:
		with open(LOGS_CSV, "a", newline="", encoding="utf-8") as archivo:
			escritor = csv.writer(archivo)
			escritor.writerow([
				timestamp,
				ip,
				host,
				method,
				estado,
				bytes_transferred,
			])
	except OSError as exc:
		print(f"[AVISO] No se pudo escribir en logs.csv: {exc}")


def _actualizar_metricas(ip, host, estado, bytes_transferred):
	"""Actualiza el resumen en memoria protegiendo el acceso con un lock."""

	_metricas_lock.acquire()
	try:
		metricas["total_solicitudes"] += 1
		metricas["total_bytes"] += bytes_transferred

		if estado == "bloqueado":
			metricas["solicitudes_bloqueadas"] += 1
		else:
			metricas["solicitudes_permitidas"] += 1

		host_clave = _normalizar_texto(host)
		ip_clave = _normalizar_texto(ip)

		metricas["dominios"][host_clave] = metricas["dominios"].get(host_clave, 0) + 1
		metricas["clientes"][ip_clave] = metricas["clientes"].get(ip_clave, 0) + 1
	finally:
		_metricas_lock.release()


def log_request(ip, host, method, status, bytes_transferred):
	"""Registra una solicitud en CSV y actualiza las metricas en memoria."""

	timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	ip_normalizada = _normalizar_texto(ip)
	host_normalizado = _normalizar_texto(host)
	method_normalizado = _normalizar_texto(method).upper()
	bytes_normalizados = _normalizar_bytes(bytes_transferred)
	estado = "bloqueado" if str(status) == "403" else "permitido"
	bytes_csv = bytes_normalizados if estado == "permitido" else 0

	_escribir_csv(
		timestamp,
		ip_normalizada,
		host_normalizado,
		method_normalizado,
		estado,
		bytes_csv,
	)
	_actualizar_metricas(ip_normalizada, host_normalizado, estado, bytes_normalizados if estado == "permitido" else 0)


def get_metricas():
	"""Devuelve una copia segura de las metricas lista para el panel web."""

	_metricas_lock.acquire()
	try:
		contador_total = metricas["total_solicitudes"]
		permitidas = metricas["solicitudes_permitidas"]
		bloqueadas = metricas["solicitudes_bloqueadas"]
		total_bytes = metricas["total_bytes"]

		return {
			"total_solicitudes": contador_total,
			"total_bytes": total_bytes,
			"solicitudes_bloqueadas": bloqueadas,
			"solicitudes_permitidas": permitidas,
			"dominios": dict(metricas["dominios"]),
			"clientes": dict(metricas["clientes"]),
			"top5_dominios": sorted(
				metricas["dominios"].items(),
				key=lambda item: (-item[1], item[0]),
			)[:5],
			"total_mb": round(total_bytes / (1024 * 1024), 2),
			"porcentaje_bloqueadas": round((bloqueadas * 100 / contador_total), 2) if contador_total else 0,
			"porcentaje_permitidas": round((permitidas * 100 / contador_total), 2) if contador_total else 0,
			"clientes_activos": sorted(
				metricas["clientes"].items(),
				key=lambda item: (-item[1], item[0]),
			),
		}
	finally:
		_metricas_lock.release()


# Inicializacion del archivo CSV al cargar el modulo.
_asegurar_archivo_csv()
