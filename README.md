# NetShield — Proxy HTTP con Filtrado y Monitoreo

Proxy HTTP implementado en Python que actúa como intermediario entre un cliente e Internet. Intercepta tráfico HTTP y HTTPS, aplica reglas de filtrado por dominio y palabras clave, genera logs auditables y presenta métricas en tiempo real mediante un panel web.

---

## Requisitos

- Python 3.8 o superior
- Flask

```bash
pip install flask
```

---

## Estructura del proyecto

```
proxy-http/
├── main.py          # Iniciar proxy y panel
├── proxy.py         # Núcleo del proxy HTTP/HTTPS
├── filter.py        # Módulo de filtrado (dominios y palabras clave)
├── logger.py        # Sistema de logs y métricas en memoria
├── dashboard.py     # Panel web
├── blocked.txt      # Lista de dominios bloqueados
├── keywords.txt     # Lista de palabras clave bloqueadas (HTTP)
├── templates/
│   └── dashboard.html
└── static/
    └── css/
        └── dashboard.css
```

---

## Ejecución

```bash
cd proxy-http
python main.py
```

El sistema arranca dos servicios en paralelo:

| Servicio | Dirección |
|---|---|
| Proxy HTTP/HTTPS | `http://localhost:8080` |
| Panel de monitoreo | `http://localhost:8081` |

---

## Configurar el navegador

### Firefox
1. Ajustes → Configuración de red → Configuración manual del proxy
2. Proxy HTTP: `127.0.0.1` — Puerto: `8080`
3. Marcar **"Usar este proxy también para HTTPS"**

### Chrome
Chrome usa el proxy del sistema Windows:

1. Configuración de Windows → Red e Internet → Proxy
2. Activar **"Usar un servidor proxy"**
3. Dirección: `127.0.0.1` — Puerto: `8080`

### Android

1. Wi-Fi -> Configuración de Red Actual
2. Ver más -> Proxy -> Seleccionar Manual
3. Nombre de host del proxy: `127.0.0.1` - Puerto: `8080`

---

## Filtrado

### Bloquear dominios
Editar `blocked.txt`, un dominio por línea:
```
facebook.com
tiktok.com
```
Los cambios se aplican de inmediato sin reiniciar el proxy. También se pueden editar desde el panel web en `http://localhost:8081`.

### Bloquear por palabras clave (solo HTTP)
Editar `keywords.txt`, una palabra clave por línea:
```
gambling

```
Si la palabra aparece en la URL de una petición HTTP, la solicitud es bloqueada.

---

## Panel de monitoreo

Acceder en `http://localhost:8081`. Se actualiza automáticamente cada 10 segundos.

Métricas disponibles:
- Total de solicitudes atendidas
- Volumen de datos transferidos (MB)
- Top 5 dominios más visitados
- Solicitudes bloqueadas vs permitidas (cantidad y porcentaje)
- Clientes activos (IP y número de solicitudes)

---

## Exportar registros

| Formato | URL |
|---|---|
| CSV | `http://localhost:8081/exportar/csv` |
| JSON | `http://localhost:8081/exportar/json` |

---

## Cómo funciona el filtrado HTTPS (SNI)

Para tráfico HTTPS el proxy no descifra el contenido. En su lugar, intercepta el paquete **ClientHello** del handshake TLS y lee el campo **SNI (Server Name Indication)** — que viaja sin cifrar — para obtener el dominio real. Si el dominio está en `blocked.txt`, la conexión se corta antes de establecerse.

---

## Tecnologías

- **Python** — lenguaje principal
- **Flask** — panel web
- **threading** — concurrencia de conexiones
- **socket** — manejo de red a bajo nivel
