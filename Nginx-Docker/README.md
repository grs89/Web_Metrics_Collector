# 🐳 WGP - Web Geo Profiler (Docker)

Despliegue con Docker Compose del sistema WGP para monitoreo y análisis de logs de **Nginx** y **Apache** con geolocalización.

## 📋 Requisitos

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM mínimo
- 20GB espacio en disco

## 🚀 Inicio Rápido

```bash
# 1. Configurar variables de entorno
cp env.example .env

# 2. (Opcional) Descargar base de datos GeoIP
MAXMIND_LICENSE_KEY=tu_clave ./scripts/download-geoip.sh

# 3. Iniciar servicios
docker compose up -d

# 4. Verificar estado
docker compose ps
```

## 🖥️ Servidores Soportados

| Servidor | Formatos | Auto-detección |
|----------|----------|----------------|
| **Nginx** | JSON | ✅ |
| **Apache** | JSON, Combined | ✅ |

## 📦 Servicios

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **Grafana** | 3000 | Dashboard de visualización |
| **Logstash** | 5044 | Recibe logs de Filebeat |
| **Logstash** | 5000 | TCP/UDP alternativo |
| **PostgreSQL** | 5432 | Base de datos |

## 📁 Estructura

```
Nginx-Docker/
├── docker-compose.yml        # Orquestación de servicios
├── env.example               # Variables de entorno de ejemplo
├── README.md                 # Este archivo
│
├── filebeat/
│   └── filebeat.yml          # Config para servidor web remoto
│
├── grafana/
│   ├── dashboards/
│   │   └── webserver-overview.json
│   └── provisioning/
│
├── log-processor/
│   ├── Dockerfile
│   ├── main.py               # Procesador Nginx + Apache + GeoIP
│   ├── requirements.txt
│   └── geoip/
│
├── logstash/
│   ├── config/
│   │   └── logstash.yml
│   └── pipeline/
│       └── webserver.conf    # Pipeline para Nginx y Apache
│
├── nginx/                    # Nginx de prueba local
│
├── nginx-server/             # Para servidores Nginx remotos
│   ├── nginx.conf.example
│   └── install-filebeat.sh
│
├── postgres/
│   └── init/
│       ├── 01-schema.sql     # Tabla web_access_logs
│       └── 02-extensions.sql
│
└── scripts/
    ├── download-geoip.sh
    └── generate-test-traffic.sh
```

## ⚙️ Configuración

### Variables de Entorno (`.env`)

```bash
# PostgreSQL
POSTGRES_USER=wgp_user
POSTGRES_PASSWORD=wgp_secure_password_2024
POSTGRES_DB=web_logs

# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin123

# Log Processor
DEFAULT_SERVER_TYPE=nginx  # o 'apache'
```

### GeoIP (Opcional)

```bash
MAXMIND_LICENSE_KEY=tu_clave ./scripts/download-geoip.sh
docker compose restart log-processor
```

## 🛠️ Comandos Útiles

```bash
# Ver logs
docker compose logs -f
docker compose logs -f log-processor

# Reiniciar
docker compose restart

# Detener
docker compose down

# Eliminar datos (⚠️)
docker compose down -v

# PostgreSQL
docker compose exec postgres psql -U wgp_user -d web_logs
```

## 📡 Configurar Servidor Nginx

```nginx
http {
    log_format json_combined escape=json
        '{"timestamp":"$time_iso8601","remote_addr":"$remote_addr",...}';
    access_log /var/log/nginx/access.log json_combined;
}
```

## 📡 Configurar Servidor Apache

```apache
LogFormat "{ \"timestamp\":\"%{%Y-%m-%dT%H:%M:%S%z}t\", ... \"log_type\":\"apache_access\" }" wgp_json
CustomLog /var/log/apache2/access.log wgp_json
```

## 📊 Acceso a Grafana

- URL: `http://localhost:3000`
- Usuario: `admin`
- Password: `admin123` (o el configurado)

## 🔍 Troubleshooting

```bash
# Filebeat
telnet IP_SERVIDOR_WGP 5044
sudo filebeat test output

# Logs
docker compose logs -f logstash
docker compose logs -f log-processor
```

---

📖 Ver [README principal](../README.md) para documentación completa.
