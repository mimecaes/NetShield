NetShield — Proxy HTTP con Filtrado y Monitoreo

Proxy HTTP implementado en Python que actúa como intermediario entre un cliente e Internet.
Intercepta tráfico HTTP y HTTPS, aplica reglas de filtrado por dominio y palabras clave,
genera logs auditables y presenta métricas en tiempo real mediante un panel web.

---------------------------------------------------------------------------

Requisitos

  - Python 3.8 o superior
  - Flask

  Instalar dependencias:
    pip install flask

---------------------------------------------------------------------------

Estructura del proyecto

  proxy-http/
  |-- main.py          Iniciar proxy y panel
  |-- proxy.py         Nucleo del proxy HTTP/HTTPS
  |-- filter.py        Modulo de filtrado (dominios y palabras clave)
  |-- logger.py        Sistema de logs y metricas en memoria
  |-- dashboard.py     Panel web
  |-- blocked.txt      Lista de dominios bloqueados
  |-- keywords.txt     Lista de palabras clave bloqueadas (HTTP)
  |-- templates/
  |   |-- dashboard.html
  |-- static/
      |-- css/
          |-- dashboard.css

---------------------------------------------------------------------------

Ejecucion

  cd proxy-http
  python main.py

  El sistema arranca dos servicios en paralelo:

  Proxy HTTP/HTTPS     ->  http://localhost:8080
  Panel de monitoreo   ->  http://localhost:8081

---------------------------------------------------------------------------

Configurar el navegador

  Firefox:
    1. Ajustes -> Configuracion de red -> Configuracion manual del proxy
    2. Proxy HTTP: 127.0.0.1  |  Puerto: 8080
    3. Marcar "Usar este proxy tambien para HTTPS"

  Chrome:
    Chrome usa el proxy del sistema Windows:
    1. Configuracion de Windows -> Red e Internet -> Proxy
    2. Activar "Usar un servidor proxy"
    3. Direccion: 127.0.0.1  |  Puerto: 8080

  Android:
    1. Wi-Fi -> Configuracion de Red Actual
    2. Ver mas -> Proxy -> Seleccionar Manual
    3. Nombre de host del proxy: 127.0.0.1  |  Puerto: 8080

---------------------------------------------------------------------------

Filtrado

  Bloquear dominios:
    Editar blocked.txt, un dominio por linea:
      facebook.com
      tiktok.com
    Los cambios se aplican de inmediato sin reiniciar el proxy.
    Tambien se pueden editar desde el panel web en http://localhost:8081.

  Bloquear por palabras clave (solo HTTP):
    Editar keywords.txt, una palabra clave por linea:
      gambling
    Si la palabra aparece en la URL de una peticion HTTP, la solicitud es bloqueada.

---------------------------------------------------------------------------

Panel de monitoreo

  Acceder en http://localhost:8081. Se actualiza automaticamente cada 10 segundos.

  Metricas disponibles:
    - Total de solicitudes atendidas
    - Volumen de datos transferidos (MB)
    - Top 5 dominios mas visitados
    - Solicitudes bloqueadas vs permitidas (cantidad y porcentaje)
    - Clientes activos (IP y numero de solicitudes)

---------------------------------------------------------------------------

Exportar registros

  CSV   ->  http://localhost:8081/exportar/csv
  JSON  ->  http://localhost:8081/exportar/json

---------------------------------------------------------------------------

Como funciona el filtrado HTTPS (SNI)

  Para trafico HTTPS el proxy no descifra el contenido. En su lugar, intercepta
  el paquete ClientHello del handshake TLS y lee el campo SNI (Server Name
  Indication) — que viaja sin cifrar — para obtener el dominio real. Si el dominio
  esta en blocked.txt, la conexion se corta antes de establecerse.

---------------------------------------------------------------------------