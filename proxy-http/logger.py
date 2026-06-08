import csv
import os
import threading
from datetime import datetime

LOGS_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs.csv")

_lock = threading.Lock()

_metricas = {
    "total": 0,
    "bytes": 0,
    "bloqueadas": 0,
    "permitidas": 0,
    "dominios": {},
    "clientes": {},
}

if not os.path.exists(LOGS_CSV):
    with open(LOGS_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["timestamp", "ip_cliente", "url", "metodo", "estado", "bytes"])


def log_request(ip, host, url, metodo, estado, bytes_transferidos):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bloqueado = estado == "403"
    estado_texto = "bloqueado" if bloqueado else "permitido"
    bytes_val = 0 if bloqueado else int(bytes_transferidos)

    with _lock:
        try:
            with open(LOGS_CSV, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([timestamp, ip, url or host, metodo, estado_texto, bytes_val])
        except:
            pass

        _metricas["total"] += 1
        _metricas["bytes"] += bytes_val
        if bloqueado:
            _metricas["bloqueadas"] += 1
        else:
            _metricas["permitidas"] += 1
        _metricas["dominios"][host] = _metricas["dominios"].get(host, 0) + 1
        _metricas["clientes"][ip] = _metricas["clientes"].get(ip, 0) + 1


def get_metricas():
    with _lock:
        total = _metricas["total"]
        bloqueadas = _metricas["bloqueadas"]
        permitidas = _metricas["permitidas"]
        total_bytes = _metricas["bytes"]

        return {
            "total_solicitudes": total,
            "total_mb": round(total_bytes / (1024 * 1024), 2),
            "solicitudes_bloqueadas": bloqueadas,
            "solicitudes_permitidas": permitidas,
            "porcentaje_bloqueadas": round(bloqueadas * 100 / total, 2) if total else 0,
            "porcentaje_permitidas": round(permitidas * 100 / total, 2) if total else 0,
            "top5_dominios": sorted(_metricas["dominios"].items(), key=lambda x: x[1], reverse=True)[:5],
            "clientes_activos": sorted(_metricas["clientes"].items(), key=lambda x: x[1], reverse=True),
        }
