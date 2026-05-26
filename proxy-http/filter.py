"""Filtro de dominios y keywords para el proxy HTTP/HTTPS.

El modulo recarga `blocked.txt` en cada llamada para detectar cambios en caliente
y decide si una solicitud debe bloquearse o permitirse.
"""

import os
import re


def _archivo_blocked_path():
	"""Retorna la ruta absoluta del archivo blocked.txt junto a este modulo."""

	return os.path.join(os.path.dirname(os.path.abspath(__file__)), "blocked.txt")


def _archivo_keywords_path():
	"""Retorna la ruta absoluta del archivo keywords.txt junto a este modulo."""

	return os.path.join(os.path.dirname(os.path.abspath(__file__)), "keywords.txt")


def _normalizar_host(host):
	"""Normaliza el host para comparaciones sin distincion de mayusculas."""

	if host is None:
		return ""
	return str(host).strip().lower().rstrip(".")


def load_blocked_domains():
	"""Lee blocked.txt y devuelve un conjunto con los dominios bloqueados."""

	blocked_domains = set()
	path = _archivo_blocked_path()

	if not os.path.exists(path):
		print(f"[AVISO] No se encontro blocked.txt en: {path}. El filtro seguira permitiendo todo.")
		return blocked_domains

	try:
		with open(path, "r", encoding="utf-8") as file:
			for raw_line in file:
				line = raw_line.strip().lower()
				if not line or line.startswith("#"):
					continue
				blocked_domains.add(line)
	except OSError as exc:
		print(f"[AVISO] No se pudo leer blocked.txt: {exc}. El filtro seguira permitiendo todo.")

	return blocked_domains


def load_keywords():
	"""Lee keywords.txt y devuelve una lista con las palabras clave bloqueadas."""

	keywords = []
	path = _archivo_keywords_path()

	if not os.path.exists(path):
		print(f"[AVISO] No se encontro keywords.txt en: {path}. El filtro seguira permitiendo todo.")
		return keywords

	try:
		with open(path, "r", encoding="utf-8") as file:
			for raw_line in file:
				line = raw_line.strip().lower()
				if not line or line.startswith("#"):
					continue
				keywords.append(line)
	except OSError as exc:
		print(f"[AVISO] No se pudo leer keywords.txt: {exc}. El filtro seguira permitiendo todo.")

	return keywords


def is_domain_blocked(host, blocked_domains):
	"""Verifica si el host o cualquiera de sus subdominios esta bloqueado."""

	normalized_host = _normalizar_host(host)
	if not normalized_host:
		return False

	for blocked_domain in blocked_domains:
		if normalized_host == blocked_domain:
			return True
		if normalized_host.endswith("." + blocked_domain):
			return True

	return False


def is_keyword_blocked(url):
	"""Verifica si la URL contiene alguna palabra clave bloqueada."""

	if not url:
		return False

	keywords_bloqueadas = load_keywords()
	url_normalizada = str(url).lower()
	for keyword in keywords_bloqueadas:
		if re.search(re.escape(keyword.lower()), url_normalizada):
			print(f"[BLOQUEADO] motivo: keyword → {keyword} encontrada en URL")
			return True

	return False


def is_blocked(host, url):
	"""Retorna True si el host o la URL cumplen alguna regla de bloqueo."""

	if not host:
		return False

	blocked_domains = load_blocked_domains()
	if is_domain_blocked(host, blocked_domains):
		print(f"[BLOQUEADO] motivo: dominio → {_normalizar_host(host)}")
		return True

	if is_keyword_blocked(url):
		return True

	return False
