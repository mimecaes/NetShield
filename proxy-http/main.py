"""Punto de entrada del proyecto.

Arranca el proxy y el panel web en hilos separados y mantiene el proceso vivo.
"""

import sys
import threading
import time


try:
	from proxy import main as proxy_main
except Exception:
	print("[ERROR] No se pudo importar proxy.py")
	sys.exit(1)


try:
	from dashboard import iniciar_dashboard
except Exception:
	print("[ERROR] No se pudo importar dashboard.py")
	sys.exit(1)


def main():
	"""Arranca ambos servicios en segundo plano y espera interrupcion."""

	print("========================================")
	print("Proxy HTTP arrancando...")
	print("Proxy:    http://localhost:8080")
	print("Panel:    http://localhost:8081")
	print("========================================")

	proxy_thread = threading.Thread(target=proxy_main, name="proxy", daemon=True)
	dashboard_thread = threading.Thread(target=iniciar_dashboard, name="dashboard", daemon=True)

	proxy_thread.start()
	dashboard_thread.start()

	print("Ambos servicios corriendo. Presiona Ctrl+C para detener.")

	try:
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		print("Proxy detenido.")


if __name__ == "__main__":
	main()
