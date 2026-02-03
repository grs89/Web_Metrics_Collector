# 🐳 WGP - Web Geo Profiler (Docker)

Despliegue con Docker Compose del sistema WGP para monitoreo y análisis de logs de **Nginx** y **Apache** con geolocalización.

## 🏗️ Arquitectura PULL

```
┌─────────────────────────────────────────────────┐
│                 WGP Server                       │
│  ┌─────────────┐   ┌───────────┐   ┌──────────┐ │
│  │Log Processor│──▶│ PostgreSQL│──▶│  Grafana │ │
│  │   (PULL)    │   └───────────┘   └──────────┘ │
│  └──────┬──────┘                                │
└─────────┼───────────────────────────────────────┘
          │ SSH (cada 30s)
    ┌─────┴─────┬─────────────┐
    ▼           ▼             ▼
┌────────┐  ┌────────┐   ┌────────┐
│ Nginx  │  │ Apache │   │Server N│
└────────┘  └────────┘   └────────┘
```

> **Sin Logstash ni Filebeat** - El log-processor se conecta directamente a los servidores via SSH.

## 📋 Requisitos

- Docker 20.10+
- Docker Compose 2.0+
- 2GB RAM mínimo (sin Logstash)
- Acceso SSH a servidores web remotos

## 🚀 Inicio Rápido

```bash
# 1. Configurar variables de entorno
cp env.example .env

# 2. Generar SSH key para conectar a servidores
ssh-keygen -t rsa -b 4096 -f ./ssh/id_rsa -N ""

# 3. Copiar key a cada servidor web
ssh-copy-id -i ./ssh/id_rsa.pub wgp@TU_SERVIDOR_IP

# 4. Configurar hosts remotos
nano config/hosts.yml

# 5. (Opcional) Descargar base de datos GeoIP
MAXMIND_LICENSE_KEY=tu_clave ./scripts/download-geoip.sh

# 6. Iniciar servicios
docker compose up -d
```

## 🖥️ Servidores Soportados

| Servidor | Formatos | Auto-detección |
|----------|----------|----------------|
| **Nginx** | JSON | ✅ |
| **Apache** | JSON, Combined | ✅ |

## 📦 Servicios

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **Grafana** | 3001 | Dashboard de visualización |
| **PostgreSQL** | 5432 | Base de datos |
| **Log-Processor** | - | Recolecta logs via SSH |

## 📁 Estructura

```
Web_Metric_Collector_Docker/
├── docker-compose.yml        # Orquestación de servicios
├── env.example               # Variables de entorno
│
├── config/
│   └── hosts.yml             # Configuración de hosts remotos
│
├── ssh/                      # SSH keys para conexión
│   └── id_rsa                # (generada por ti)
│
├── grafana/
│   ├── dashboards/
│   │   └── wgp-overview.json # Dashboard multi-host
│   └── provisioning/
│
├── log-processor/
│   ├── Dockerfile
│   ├── main.py               # PULL via SSH + GeoIP
│   ├── requirements.txt
│   └── geoip/
│
└── postgres/
    └── init/
        └── 01-schema.sql     # Tabla web_access_logs
```

## ⚙️ Configuración de Hosts

Edita `config/hosts.yml`:

```yaml
global:
  pull_interval: 30    # Segundos entre cada recolección
  ssh_user: wgp
  ssh_key_path: /app/ssh/id_rsa

hosts:
  - name: nginx-server-1
    enabled: true
    host: 192.168.1.10
    server_type: nginx
    log_paths:
      - /var/log/nginx/access.log

  - name: apache-server-1
    enabled: true
    host: 192.168.1.11
    server_type: apache
    log_paths:
      - /var/log/apache2/access.log
```

## 🔧 Preparar Servidor Remoto

```bash
# 1. Crear usuario wgp
sudo useradd -m -s /bin/bash wgp

# 2. Dar permisos de lectura a logs
sudo usermod -aG adm wgp      # Debian/Ubuntu
sudo usermod -aG nginx wgp    # RHEL (Nginx)
sudo usermod -aG apache wgp   # RHEL (Apache)

# 3. Desde WGP server, copiar SSH key
ssh-copy-id -i ./ssh/id_rsa.pub wgp@SERVIDOR_IP

# 4. Probar conexión
ssh -i ./ssh/id_rsa wgp@SERVIDOR_IP "tail -1 /var/log/nginx/access.log"
```

## 📡 Formato de Logs (Nginx JSON)

```nginx
http {
    log_format json_combined escape=json
        '{"timestamp":"$time_iso8601","remote_addr":"$remote_addr",'
        '"request_method":"$request_method","request_uri":"$request_uri",'
        '"status":$status,"body_bytes_sent":$body_bytes_sent,'
        '"request_time":$request_time,"http_user_agent":"$http_user_agent"}';

    access_log /var/log/nginx/access.log json_combined;
}
```

## 📊 Acceso a Grafana

- URL: `http://localhost:3001`
- Usuario: `admin`
- Password: `admin123`

### Dashboard Multi-Host

El dashboard incluye:
- 🖥️ **Filtro por Host** - Selecciona servidor específico
- 🔧 **Filtro por Tipo** - Nginx o Apache
- 📊 **Host Summary** - Tabla resumen por servidor

## 🛠️ Comandos Útiles

```bash
# Ver logs del collector
docker compose logs -f log-processor

# Reiniciar después de cambiar hosts.yml
docker compose restart log-processor

# PostgreSQL
docker compose exec postgres psql -U wgp_user -d web_logs
```

## 🔍 Troubleshooting

```bash
# Verificar conexión SSH
docker compose exec log-processor ssh -i /app/ssh/id_rsa wgp@SERVIDOR_IP "echo OK"

# Ver posiciones guardadas
cat log-processor-data/positions.json
```

---

📖 Ver [README principal](../README.md) para documentación completa.
