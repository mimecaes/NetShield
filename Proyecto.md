# Universidad Nacional Sede Regional Brunca

Campus Pérez Zeledón / Campus Coto

## Comunicación y redes de computadores

# Proyecto - I ciclo 2026

**Prof:** M.C. Gabriel Núñez M.
**Valor:** 15 % de la nota final
**Grupos:** 2 a 3 personas
**Fecha de entrega y demostración:** 9 u 11 de junio de 2026

# Objetivo General

Diseñar e implementar un servidor proxy HTTP con capacidad de filtrado de tráfico y monitoreo de red, que actúe como intermediario entre un cliente e Internet, registrando y analizando las comunicaciones en tiempo real.

# Objetivos Específicos

1. Implementar un proxy HTTP funcional que intercepte, reenvíe y registre las solicitudes de los clientes.
2. Incorporar filtrado de dominios en tráfico HTTP y HTTPS (mediante inspección SNI).
3. Desarrollar un sistema de monitoreo que muestre métricas clave del tráfico en tiempo real.
4. Aplicar al menos una funcionalidad adicional que enriquezca el sistema más allá de los requisitos mínimos.

# Descripción del Proyecto

Cada grupo desarrollará de forma independiente un sistema de proxy HTTP que se ubica entre un cliente e Internet. El sistema debe ser capaz de interceptar el tráfico, aplicar reglas de filtrado, generar logs auditables y presentar métricas de uso.

El proyecto se divide en tres componentes principales: el núcleo del proxy, el módulo de filtrado y el sistema de monitoreo. Adicionalmente, cada grupo debe proponer e implementar una funcionalidad extra de su elección.

# Requisitos Técnicos

## 1. Proxy HTTP

* Interceptar y reenviar solicitudes HTTP (métodos GET, POST como mínimo).
* Responder correctamente a los clientes con el contenido obtenido del servidor destino.
* Manejar múltiples conexiones concurrentes (mediante hilos).

## 2. Filtrado

* Mantener una lista configurable de dominios bloqueados (archivo de texto).
* Para tráfico HTTP: bloquear por dominio completo o por palabras clave en la URL.
* Para tráfico HTTPS: filtrar por dominio inspeccionando el campo SNI (Server Name Indication) en el saludo TLS. No se requiere descifrar el contenido.
* Retornar una respuesta de bloqueo clara al cliente cuando un dominio esté restringido.

## 3. Monitoreo y Logs

Registrar cada solicitud en un archivo de log con:

* IP del cliente
* Dominio/URL
* Método HTTP (GET, POST, etc.)
* Estado (permitido/bloqueado)
* Tamaño de la respuesta (bytes transferidos al cliente)
* Marca de tiempo (timestamp)

Mostrar al menos las siguientes métricas en un panel web (puerto separado):

* Total de solicitudes atendidas
* Volumen de datos transferidos (megabytes enviados desde el proxy al cliente)
* Top 5 de dominios más visitados
* Solicitudes bloqueadas vs permitidas (cantidad y porcentaje)
* Clientes activos (direcciones IP y número de solicitudes por cliente)

El panel web puede actualizarse mediante recarga manual o automática.

## 4. Funcionalidad Adicional (elección del grupo)

Cada grupo debe implementar al menos una de las siguientes funcionalidades o proponer una propia:

* Caché de respuestas HTTP (en disco o memoria)
* Sistema de alertas ante volumen inusual de solicitudes desde un cliente
* Exportación de reportes (CSV o JSON)
* Otra funcionalidad propuesta por el grupo (requiere aprobación previa)

# Tecnologías

No existe restricción de lenguaje de programación ni de sistema operativo. Algunas opciones sugeridas:

* Lenguajes: Python, Java, C++, Node.js, Go
* Sistema operativo: Linux, Windows o Mac

Independientemente de la tecnología elegida, el sistema debe ser completamente funcional y demostrable el día de la entrega.

# Entrega y Demostración

* Código fuente: Un archivo .zip con todo el código y un archivo README.txt con instrucciones de ejecución.

* Demostración en vivo: El día de la entrega, el grupo debe mostrar el funcionamiento del proxy con al menos un cliente (puede ser el mismo equipo o uno diferente). Se evaluará:

  * El navegador navega correctamente a través del proxy
  * Los dominios bloqueados no se pueden acceder
  * El panel web muestra las estadísticas correctamente
  * La funcionalidad extra implementada

* Defensa individual: Cada integrante debe explicar una parte del proyecto. Si un integrante no demuestra conocimiento, su nota se penaliza.

# Criterios de Evaluación

| Componente                                               | Porcentaje |
| -------------------------------------------------------- | ---------- |
| Proxy HTTP funcional (intercepta, reenvía, concurrencia) | 35 %       |
| Filtrado de dominios (HTTP y HTTPS por SNI)              | 25 %       |
| Monitoreo y logs (panel web con métricas)                | 20 %       |
| Funcionalidad adicional                                  | 10 %       |
| Demostración y defensa oral                              | 10 %       |
| **Total**                                                | **100 %**  |

**Nota importante:** Un proyecto que no sea demostrable en la fecha de entrega no podrá optar al puntaje de los componentes no mostrados.

# Notas técnicas

* El proxy funciona con HTTP. Para HTTPS, solo se puede filtrar por dominio (a través del SNI), no se puede ver el contenido.
* Investigue cómo configurar su navegador para usar un proxy.
* Pruebe con páginas HTTP (ej. http://example.com) para verificar el filtrado por palabra clave.
* No se requiere documentación escrita. La defensa oral y la demostración son suficientes.

# Fin del enunciado
