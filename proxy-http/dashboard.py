"""Panel web del proxy HTTP.

Este modulo expone una aplicacion Flask liviana para mostrar y exportar las
metricas del proxy en tiempo real.
"""

import os

try:
	from flask import Flask, jsonify, render_template, request, send_file
except Exception as exc:  # pragma: no cover - fallback defensivo
	Flask = None
	jsonify = None
	render_template = None
	request = None
	send_file = None
	print(f"[AVISO] Flask no esta disponible para el dashboard: {exc}")


try:
	from logger import LOGS_CSV, get_metricas
except Exception as exc:  # pragma: no cover - fallback defensivo
	LOGS_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs.csv")
	_logger_error = str(exc)

	def get_metricas():
		"""Retorna metricas vacias si logger.py no esta disponible."""

		print(f"[AVISO] logger.py no esta disponible para el dashboard: {_logger_error}")
		return _metricas_vacias()


APP_DIR = os.path.dirname(os.path.abspath(__file__))


def _metricas_vacias():
	"""Construye la estructura vacia que espera el template."""

	return {
		"total_solicitudes": 0,
		"total_bytes": 0,
		"solicitudes_bloqueadas": 0,
		"solicitudes_permitidas": 0,
		"dominios": {},
		"clientes": {},
		"top5_dominios": [],
		"total_mb": 0,
		"porcentaje_bloqueadas": 0,
		"porcentaje_permitidas": 0,
		"clientes_activos": [],
	}


def _obtener_metricas_seguras():
	"""Obtiene metricas del logger sin dejar caer el panel si hay errores."""

	try:
		metricas = get_metricas()
		return metricas if isinstance(metricas, dict) else _metricas_vacias()
	except Exception as exc:
		print(f"[AVISO] No se pudieron leer las metricas: {exc}")
		return _metricas_vacias()


def _archivo_csv_existe():
	"""Comprueba si logs.csv existe antes de intentar exportarlo."""

	return os.path.exists(LOGS_CSV)


def _ruta_archivo_texto(nombre_archivo):
	"""Construye la ruta absoluta de un archivo de texto del panel."""

	return os.path.join(os.path.dirname(os.path.abspath(__file__)), nombre_archivo)


def _leer_archivo_texto(nombre_archivo):
	"""Lee un archivo de texto del panel y retorna su contenido o una cadena vacia."""

	path = _ruta_archivo_texto(nombre_archivo)

	if not os.path.exists(path):
		return ""

	try:
		with open(path, "r", encoding="utf-8") as file:
			return file.read()
	except OSError as exc:
		print(f"[AVISO] No se pudo leer {nombre_archivo}: {exc}")
		return ""


def _guardar_archivo_texto(nombre_archivo, contenido):
	"""Sobrescribe un archivo de texto del panel con el contenido recibido."""

	path = _ruta_archivo_texto(nombre_archivo)

	try:
		with open(path, "w", encoding="utf-8") as file:
			file.write(contenido)
	except OSError as exc:
		return False, f"No se pudo guardar {nombre_archivo}: {exc}"

	return True, "Lista actualizada"


if Flask is not None:
	app = Flask(__name__, template_folder=os.path.join(APP_DIR, "templates"))
else:  # pragma: no cover - fallback defensivo
	app = None


if app is not None:

	@app.route("/")
	def inicio():
		"""Renderiza el panel principal con las metricas actuales."""

		metricas = _obtener_metricas_seguras()
		return render_template("dashboard.html", metricas=metricas)


	@app.route("/exportar/csv")
	def exportar_csv():
		"""Descarga logs.csv como archivo adjunto."""

		if not _archivo_csv_existe():
			return "logs.csv no existe en este momento.", 404

		return send_file(
			LOGS_CSV,
			mimetype="text/csv",
			as_attachment=True,
			download_name="logs.csv",
		)


	@app.route("/exportar/json")
	def exportar_json():
		"""Devuelve las metricas actuales en formato JSON."""

		return jsonify(_obtener_metricas_seguras())


	@app.route("/blocked", methods=["GET", "POST"])
	def blocked():
		"""Lee o actualiza blocked.txt desde el panel."""

		if request.method == "GET":
			return jsonify({"contenido": _leer_archivo_texto("blocked.txt")})

		payload = request.get_json(silent=True) or {}
		contenido = payload.get("contenido", "")
		exito, mensaje = _guardar_archivo_texto("blocked.txt", contenido)
		if not exito:
			return jsonify({"ok": False, "mensaje": mensaje}), 500

		return jsonify({"ok": True, "mensaje": mensaje})


	@app.route("/keywords", methods=["GET", "POST"])
	def keywords():
		"""Lee o actualiza keywords.txt desde el panel."""

		if request.method == "GET":
			return jsonify({"contenido": _leer_archivo_texto("keywords.txt")})

		payload = request.get_json(silent=True) or {}
		contenido = payload.get("contenido", "")
		exito, mensaje = _guardar_archivo_texto("keywords.txt", contenido)
		if not exito:
			return jsonify({"ok": False, "mensaje": mensaje}), 500

		return jsonify({"ok": True, "mensaje": mensaje})
else:  # pragma: no cover - fallback defensivo

	def inicio():
		"""Placeholder cuando Flask no esta disponible."""

		return None


	def exportar_csv():
		"""Placeholder cuando Flask no esta disponible."""

		return None


	def exportar_json():
		"""Placeholder cuando Flask no esta disponible."""

		return None


def iniciar_dashboard():
	"""Arranca el servidor Flask del panel en el puerto 8081."""

	if app is None:
		print("[AVISO] No se pudo iniciar el dashboard porque Flask no esta disponible.")
		return

	try:
		app.run(host="0.0.0.0", port=8081, debug=False, use_reloader=False)
	except OSError as exc:
		print(f"[AVISO] No se pudo iniciar el dashboard en el puerto 8081: {exc}")
	except Exception as exc:
		print(f"[AVISO] Error inesperado al iniciar el dashboard: {exc}")
