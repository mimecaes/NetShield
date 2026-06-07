import threading
import time
from proxy import main as iniciar_proxy
from dashboard import iniciar_dashboard


def main():
    print("========================================")
    print("Proxy HTTP - NetShield")
    print("Proxy:  localhost:8080")
    print("Panel:  http://localhost:8081")
    print("Ctrl+C para detener")
    print("========================================")

    t1 = threading.Thread(target=iniciar_proxy, daemon=True)
    t2 = threading.Thread(target=iniciar_dashboard, daemon=True)
    t1.start()
    t2.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Proxy detenido.")


if __name__ == "__main__":
    main()
