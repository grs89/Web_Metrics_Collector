# 🐳 NGP - Nginx Geo Profiler (Docker)

Despliegue con Docker Compose del sistema NGP para monitoreo y análisis de logs de Nginx con geolocalización.

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
│   └── filebeat.yml          # Config para servidor Nginx remoto
│
├── grafana/
│   ├── dashboards/
│   │   └── nginx-overview.json
│   └── provisioning/
│       ├── dashboards/
│       └── datasources/
│
├── log-processor/
│   ├── Dockerfile
│   ├── main.py               # Procesador + GeoIP
│   ├── requirements.txt
│   └── geoip/                # Base de datos GeoIP
│
├── logstash/
│   ├── config/
│   │   └── logstash.yml
│   └── pipeline/
│       └── nginx.conf
│
├── nginx/                    # Nginx de prueba local
│   ├── nginx.conf
│   ├── conf.d/
│   └── html/
│
├── nginx-server/             # Para servidores remotos
│   ├── nginx.conf.example
│   └── install-filebeat.sh
│
├── postgres/
│   └── init/
│       ├── 01-schema.sql
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
POSTGRES_USER=ngp_user
POSTGRES_PASSWORD=ngp_secure_password_2024
POSTGRES_DB=nginx_logs

# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin123
GRAFANA_ROOT_URL=http://localhost:3000

# Retención
RETENTION_DAYS=365
```

### GeoIP (Opcional)

1. Regístrate en [MaxMind](https://www.maxmind.com/en/geolite2/signup)
2. Genera una license key
3. Ejecuta:
   ```bash
   MAXMIND_LICENSE_KEY=tu_clave ./scripts/download-geoip.sh
   docker compose restart log-processor
   ```

## 🛠️ Comandos Útiles

```bash
# Ver logs
docker compose logs -f
docker compose logs -f logstash
docker compose logs -f log-processor

# Reiniciar servicios
docker compose restart

# Detener
docker compose down

# Detener y eliminar datos (⚠️)
docker compose down -v

# Entrar a PostgreSQL
docker compose exec postgres psql -U ngp_user -d nginx_logs
```

## 📡 Configurar Servidor Nginx Remoto

### 1. Configurar logs JSON en Nginx

```nginx
http {
    log_format json_combined escape=json
        '{'
            '"timestamp":"$time_iso8601",'
            '"remote_addr":"$remote_addr",'
            '"request_method":"$request_method",'
            '"request_uri":"$request_uri",'
            '"status":$status,'
            '"body_bytes_sent":$body_bytes_sent,'
            '"request_time":$request_time,'
            '"http_referer":"$http_referer",'
            '"http_user_agent":"$http_user_agent"'
        '}';

    access_log /var/log/nginx/access.log json_combined;
}
```

### 2. Instalar Filebeat

```bash
# Usar script automático
sudo /tmp/install-filebeat.sh IP_SERVIDOR_NGP

# O manual: ver README principal
```

## 🔒 Seguridad en Producción

1. **Cambiar contraseñas** en `.env`
2. **Firewall**: Solo abrir puertos necesarios
3. **SSL/TLS**: Configurar entre Filebeat y Logstash
4. **Red privada**: Usar VPN si es posible

## 📊 Acceso a Grafana

- URL: `http://localhost:3000`
- Usuario: `admin` (o el configurado en `.env`)
- Password: `admin123` (o el configurado en `.env`)

## 🔍 Troubleshooting

### Filebeat no envía logs
```bash
telnet IP_SERVIDOR_NGP 5044
sudo filebeat test output
```

### No aparecen datos en Grafana
```bash
docker compose logs -f logstash
docker compose logs -f log-processor
```

### GeoIP no funciona
```bash
ls -la log-processor/geoip/
docker compose restart log-processor
```

---

📖 Ver [README principal](../README.md) para documentación completa.
