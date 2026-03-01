# 🏗️ Web Metrics Collector: Arquitectura del Sistema (V2)

Esta documentación proporciona una visión técnica detallada del **Web Metrics Collector (WMC)**, diseñada para desarrolladores que deseen entender, mantener o extender el sistema tras la expansión de rendimiento y seguridad.

---

## 📋 Tabla de Contenidos
1. [Arquitectura General](#arquitectura)
2. [Interacción de Componentes (Mermaid)](#interaccion)
3. [Flujo de Datos y Tareas de Fondo](#flujo-de-datos)
4. [Estrategia de Almacenamiento Dual](#almacenamiento)
5. [Componentes del Core (.py)](#componentes-del-core)
6. [Observabilidad y Métricas](#observabilidad)
7. [Tech Stack](#tech-stack)

---

## 1. Arquitectura General <a name="arquitectura"></a>

WMC utiliza una arquitectura **basada en eventos y asíncrona** implementada con `asyncio`. El sistema ahora opera en tres planos distintos:
1.  **Ingesta de Logs**: Alta frecuencia, desacoplada mediante colas.
2.  **Monitoreo de Salud (Telemetría)**: Baja frecuencia (60s), extrae vitales del sistema.
3.  **Vigilancia de Seguridad (SSL)**: Muy baja frecuencia (12h), valida certificados.

### Diagrama de Bloques Actualizado
```mermaid
graph TD
    subgraph "Nube / Servidores Externos"
        S1[Web Servers\nNginx, Apache...]
        S2[App Servers\nTraefik, Caddy...]
    end

    subgraph "WMC Container (asyncio)"
        Main[main.py\nEvent Loop]
        
        subgraph "Tareas Ingesta"
            R[SSHLogReader]
            Q[(asyncio.Queue)]
            P[LogProcessor]
        end

        subgraph "Tareas Monitoreo"
            SYS[SystemMetricsCollector]
            SSL[SSLMonitor]
        end

        subgraph "Capa de Persistencia"
            MS[MultiStorage]
            PG_S[PostgresStorage]
            CH_S[ClickHouseStorage]
        end
        
        M[Prometheus\n:8080/metrics]
    end

    subgraph "Infraestructura Local"
        DB_PG[(PostgreSQL 16\nEstado & Alerta)]
        DB_CH[(ClickHouse\nAnalítica Masiva)]
        G[Grafana 12]
    end

    S1 & S2 -- "SSH (Logs & Commands)" --> R
    R --> P --> Q --> MS
    MS --> PG_S & CH_S
    PG_S --> DB_PG
    CH_S --> DB_CH
    SYS -- "SSH Commands" --> R
    SYS & SSL --> M
    G -- "Queries" --> DB_PG & DB_CH
```

---

## 2. Interacción de Componentes <a name="interaccion"></a>

El siguiente diagrama de secuencia describe cómo interactúan los componentes durante un ciclo típico de procesamiento.

```mermaid
sequenceDiagram
    participant Main as main.py
    participant SSH as SSHLogReader
    participant Proc as LogProcessor
    participant Storage as MultiStorage
    participant DBs as PG & ClickHouse

    Main->>Main: Init Event Loop
    par Tareas Paralelas
        Main->>Proc: start_worker()
        Main->>Main: run_system_metrics_task(60s)
        Main->>Main: run_ssl_monitor_task(12h)
    end

    Note over Main, SSH: Ciclo de Logs (cada 10s)
    Main->>SSH: read_updates(path)
    SSH-->>Main: Delta log lines
    Main->>Proc: process_host(data)
    Proc->>Proc: parse & enrich (GeoIP, DNS, UA)
    Proc->>Proc: enqueue(parsed_log)
    
    Note over Proc, DBs: Worker de Fondo (Batch 500)
    Proc->>Storage: save_logs(batch)
    par Parallel Insert
        Storage->>DBs: SQL Insert (Postgres)
        Storage->>DBs: Insert (ClickHouse Connect)
    end
```

---

## 3. Flujo de Datos y Tareas de Fondo <a name="flujo-de-datos"></a>

### Tareas de Fondo (Background Tasks)
1.  **Log Buffer Worker**: Consume la `asyncio.Queue` y realiza inserciones en batch. Aplica **Exponential Backoff** si ambos almacenes fallan.
2.  **System Metrics Task (60s)**: Ejecuta comandos `top`, `free` y `df` vía SSH para recolectar CPU, RAM y ocupación de disco.
3.  **SSL Monitor Task (12h)**: Realiza un handshake SSL contra los dominios configurados para obtener la fecha de expiración.
4.  **Retention Scheduler (24h)**: Ejecuta comandos de limpieza en PostgreSQL (`DELETE`) y ClickHouse (`ALTER TABLE DELETE`).

---

## 4. Estrategia de Almacenamiento Dual <a name="almacenamiento"></a>

WMC utiliza `storage.py` para implementar un patrón de **Multi-almacenamiento**, permitiendo que los datos fluyan a dos bases de datos con propósitos distintos:

### Comparativa de Esquemas y Tipos de Datos

| Campo | Postgres (Relacional) | ClickHouse (Analítico) | Razón |
| :--- | :--- | :--- | :--- |
| `client_ip` | `INET` | `IPv4` | Optimización de red en CH |
| `timestamp` | `TIMESTAMPTZ` | `DateTime64(3)` | Precisión de ms en CH |
| `status_code`| `SMALLINT` | `UInt16` | Ahorro de espacio |
| `is_fake_bot`| `BOOLEAN` | `UInt8` (0/1) | Compatibilidad CH |
| `source_host`| `VARCHAR` | `LowCardinality(String)` | Compresión por diccionario en CH |

**Filosofía**:
- **Postgres**: Actúa como fuente de verdad para el estado actual, IPs bloqueadas y filtros rápidos.
- **ClickHouse**: Actúa como el motor de analítica histórica pesada, optimizado para agregaciones (ej: "hits por país en el último año").

### Implementación del MultiStorage

El wrapper `MultiStorage` en `storage.py` utiliza `asyncio.gather` para realizar las inserciones en PostgreSQL y ClickHouse de forma paralela, maximizando el throughput:

```python
async def save_logs(self, logs):
    tasks = [self.primary.save_logs(logs)]
    if self.secondary:
        tasks.append(self.secondary.save_logs(logs))
    await asyncio.gather(*tasks)
```

### Estrategia de Persistencia y Resiliencia

WMC implementa múltiples capas para asegurar que no se pierdan datos:

1.  **Persistencia de Offsets**: Utiliza un gestor de estado (`state.py`) que guarda la última posición leída de cada archivo en cada host en un archivo `/app/data/state.json`. Esto permite reanudar la lectura tras un reinicio sin duplicar datos.
2.  **Volumen Local**: El archivo de estado se guarda en un volumen persistente de Docker (`wmc-data`), lo que garantiza su supervivencia incluso si el contenedor es recreado.
3.  **Retry en Almacenamiento**: Implementa *Exponential Backoff* al intentar escribir en Postgres o ClickHouse para manejar caídas temporales de la base de datos.
4.  **Segmentación por Categorías**: El sistema ahora soporta diferentes naturalezas de logs, clasificados mediante la columna `log_category` (`access`, `error`, `app`).

### Inicialización de Datos

El archivo `database/clickhouse_init.sql` define el esquema de la tabla `web_access_logs`. Es crucial que este script incluya `USE wmc_db;` para asegurar que las tablas se creen en el esquema correcto durante el primer arranque del contenedor.

### Detección de Anomalías (Z-Score)

En la V3, se ha introducido un motor de detección de anomalías estadísticas en `anomaly_detector.py`. Este componente realiza consultas periódicas a ClickHouse para comparar el tráfico actual contra el histórico.

- **Modelo**: Utiliza el **Z-Score** para medir desviaciones estándar del promedio.
- **Ventana**: Compara los últimos 5 minutos de tráfico contra las mismas ventanas de tiempo en semanas anteriores (estacionalidad).
- **Métricas**: Expone `wmc_traffic_anomaly_score` a Prometheus para alertado en Grafana.

---

## 5. Componentes del Core (.py) <a name="componentes-del-core"></a>

| Archivo | Responsabilidad Técnica |
| :--- | :--- |
| `main.py` | Orquestador central. Gestiona el ciclo de vida de todas las tareas `asyncio`. |
| `processor.py` | Coordina el enriquecimiento. Usa un buffer de 10k entradas para absorber picos. |
| `storage.py` | Implementa `PostgresStorage`, `ClickHouseStorage` y el wrapper `MultiStorage`. |
| `state.py` | Gestor de persistencia de punteros (offsets) JSON. |
| `ssh_client.py` | Abstracción de red. Maneja reconexiones automáticas y ejecución de comandos remotos. |
| `system_metrics.py` | Parser de telemetría. Convierte salidas de shell de Linux en métricas Prometheus. |
| `ssl_monitor.py` | Monitor de seguridad. Realiza conexiones socket SSL para auditar certificados. |
| `parser.py` | Motor de expresiones regulares y JSON para accesos, errores y logs de apps. |
| `geoip.py` | Interfaz asíncrona para la base de datos MaxMind GeoLite2. |
| `ua_enricher.py` | Clasificador de User-Agents (Diferencia bots de humanos). |
| `anomaly_detector.py` | Motor estadístico de detección de anomalías basándose en ClickHouse. |

---

## 6. Observabilidad y Métricas <a name="observabilidad"></a>

WMC expone un endpoint Prometheus en el puerto **8082** con métricas clave:

- **Sistema**: `wmc_host_cpu_usage_percent`, `wmc_host_memory_usage_percent`, `wmc_host_disk_usage_percent`.
- **Inteligencia**: `wmc_traffic_anomaly_score`, `wmc_anomalies_detected_total`.
- **Seguridad**: `wmc_ssl_cert_days_remaining`.
- **Rendimiento**: `wmc_ingestion_latency_seconds` (Histograma).
- **Salud del Buffer**: `wmc_log_buffer_size`.

---

## 7. Tech Stack <a name="tech-stack"></a>

| Categoría | Tecnología |
| :--- | :--- |
| **Lenguaje** | Python 3.12 (Asíncrono) |
| **Bases de Datos** | PostgreSQL 16 & ClickHouse 24 |
| **Networking** | `asyncssh` & `asyncpg` & `clickhouse-connect` |
| **Geolocalización** | MaxMind GeoLite2 |
| **Visualización** | Grafana 12.0 |
| **Observabilidad** | Prometheus Client |
