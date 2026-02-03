# 🌐 WGP - Web Geo Profiler

Sistema de monitoreo y análisis de logs de servidores web con geolocalización, métricas en tiempo real y visualización en Grafana. Soporta **Nginx** y **Apache** con recolección centralizada via **SSH**.

![Grafana Dashboard](https://img.shields.io/badge/Grafana-Dashboard-orange?style=for-the-badge&logo=grafana)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?style=for-the-badge&logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?style=for-the-badge&logo=docker)
![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-326CE5?style=for-the-badge&logo=kubernetes)
![Nginx](https://img.shields.io/badge/Nginx-Supported-009639?style=for-the-badge&logo=nginx)
![Apache](https://img.shields.io/badge/Apache-Supported-D22128?style=for-the-badge&logo=apache)

## ✨ Características

- 📊 **Métricas en tiempo real** - Requests/segundo, tiempos de respuesta, códigos de estado
- 🌍 **Geomap interactivo** - Visualiza el origen geográfico de las visitas
- 🗄️ **PostgreSQL** - Almacenamiento robusto con retención de 1 año
- 📈 **Dashboards Grafana** - Paneles preconfigurados multi-host
- 🔍 **Análisis detallado** - Top IPs, URIs, países, user agents
- 🐳 **Docker Compose** - Despliegue simple
- ☸️ **Kubernetes** - Despliegue escalable para producción
- 🔧 **Multi-servidor** - Soporta **Nginx** y **Apache** simultáneamente
- 🖥️ **Multi-host** - Filtra y visualiza por servidor origen
- 🚀 **Arquitectura PULL** - Sin agentes, recolección via SSH

## 🏗️ Arquitectura

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
│Server 1│  │Server 2│   │        │
└────────┘  └────────┘   └────────┘
```

### Ventajas de Arquitectura PULL

| Característica | Beneficio |
|----------------|-----------|
| 🚀 **Sin Logstash** | ~1GB menos de RAM |
| 📦 **Sin agentes** | No necesita instalar Filebeat |
| 🔒 **Sin puertos abiertos** | Servidores no exponen servicios |
| 🎛️ **Control centralizado** | Gestión desde un solo punto |

## 🖥️ Servidores Web Soportados

| Servidor | Formatos de Log | Auto-detección |
|----------|-----------------|----------------|
| **Nginx** | JSON | ✅ Sí |
| **Apache** | JSON, Combined Log Format | ✅ Sí |

## 📦 Opciones de Despliegue

| Método | Caso de Uso | Documentación |
|--------|-------------|---------------|
| 🐳 **Docker Compose** | Desarrollo, servidores individuales | [Web_Metric_Collector_Docker/](./Web_Metric_Collector_Docker/) |
| ☸️ **Kubernetes** | Producción, alta disponibilidad | [Web_Metric_Collector_K8S/](./Web_Metric_Collector_K8S/) |

## 🚀 Inicio Rápido

### Docker Compose

```bash
cd Web_Metric_Collector_Docker

# 1. Configurar
cp env.example .env

# 2. Generar SSH key
ssh-keygen -t rsa -b 4096 -f ./ssh/id_rsa -N ""

# 3. Copiar a servidores web
ssh-copy-id -i ./ssh/id_rsa.pub wgp@TU_SERVIDOR

# 4. Configurar hosts
nano config/hosts.yml

# 5. (Opcional) GeoIP
MAXMIND_LICENSE_KEY=tu_clave ./scripts/download-geoip.sh

# 6. Iniciar
docker compose up -d
```

### Kubernetes

```bash
cd Web_Metric_Collector_K8S

# Modificar secrets.yaml con tus credenciales
# Crear secret con SSH key
kubectl create secret generic wgp-ssh-key \
  --from-file=id_rsa=./ssh/id_rsa -n wgp

# Desplegar
kubectl apply -k .
```

## 📁 Estructura del Proyecto

```
WGP/
├── README.md                          # Este archivo
│
├── Web_Metric_Collector_Docker/       # 🐳 Docker Compose
│   ├── docker-compose.yml
│   ├── config/
│   │   └── hosts.yml                  # Configuración de hosts
│   ├── ssh/                           # SSH keys
│   ├── grafana/
│   ├── log-processor/                 # PULL via SSH
│   └── postgres/
│
└── Web_Metric_Collector_K8S/          # ☸️ Kubernetes
    ├── kustomization.yaml
    └── ...
```

## ⚙️ Configuración de Hosts

Edita `config/hosts.yml`:

```yaml
global:
  pull_interval: 30
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

## 📌 Agregar un Nuevo Host (Paso a Paso)

### Paso 1: Generar SSH Key (solo la primera vez)

```bash
cd Web_Metric_Collector_Docker
ssh-keygen -t rsa -b 4096 -f ./ssh/id_rsa -N ""
```

### Paso 2: Preparar el Servidor Remoto

Ejecuta estos comandos **en el servidor web que quieres monitorear**:

```bash
# Crear usuario wgp
sudo useradd -m -s /bin/bash wgp

# Dar permisos para leer logs
sudo usermod -aG adm wgp          # Debian/Ubuntu
# sudo usermod -aG nginx wgp      # RHEL/CentOS (Nginx)
# sudo usermod -aG apache wgp     # RHEL/CentOS (Apache)
```

### Paso 3: Copiar SSH Key al Servidor

Ejecuta esto **desde el servidor WGP**:

```bash
ssh-copy-id -i ./ssh/id_rsa.pub wgp@IP_DEL_SERVIDOR
```

### Paso 4: Probar Conexión

```bash
# Probar que puedes leer logs
ssh -i ./ssh/id_rsa wgp@IP_DEL_SERVIDOR "tail -1 /var/log/nginx/access.log"
```

### Paso 5: Agregar Host a config/hosts.yml

```yaml
hosts:
  - name: mi-servidor           # Nombre descriptivo
    enabled: true               # Activar monitoreo
    host: 192.168.1.10          # IP del servidor
    server_type: nginx          # nginx o apache
    log_paths:
      - /var/log/nginx/access.log
```

### Paso 6: Reiniciar y Verificar

```bash
# Reiniciar log-processor
docker compose restart log-processor

# Ver logs para confirmar conexión
docker compose logs -f log-processor
```

### Paso 7: Verificar en Grafana

1. Abre http://localhost:3001
2. Usuario: `admin` / Password: `admin123`
3. En el dashboard, selecciona tu host en el filtro "Host"

> 💡 **Tip**: Los logs se recolectan cada 30 segundos. Espera un minuto para ver datos.

## 🌐 URLs y Puertos

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **Grafana** | 3001 | Dashboard de visualización |
| **PostgreSQL** | 5432 | Base de datos |

## 📊 Dashboard de Grafana

El dashboard incluye:

### Filtros Multi-Host
- 🖥️ **Filtro por Host** - Selecciona servidor específico
- 🔧 **Filtro por Tipo** - Nginx o Apache

### Visualizaciones
- 📊 **Host Summary** - Tabla resumen por servidor
- 📈 **Requests Over Time** - Por host
- 🗺️ **Geomap** - Mapa mundial
- 📋 **Top Tables** - IPs, países, URIs

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

## 📡 Formato de Logs (Apache JSON)

```apache
LogFormat "{ \"timestamp\":\"%{%Y-%m-%dT%H:%M:%S%z}t\", \"remote_addr\":\"%a\", \"request_method\":\"%m\", \"request_uri\":\"%U%q\", \"status\":%>s, \"body_bytes_sent\":%B }" wgp_json
CustomLog /var/log/apache2/access.log wgp_json
```

## 🌍 GeoIP (Opcional)

```bash
# Registrarse en MaxMind (gratis)
# https://www.maxmind.com/en/geolite2/signup

cd Web_Metric_Collector_Docker
MAXMIND_LICENSE_KEY=tu_clave ./scripts/download-geoip.sh
docker compose restart log-processor
```

## 🔍 Consultas SQL Útiles

```sql
-- Resumen por host
SELECT * FROM v_host_summary;

-- Requests por servidor (últimas 24h)
SELECT source_host, server_type, COUNT(*) as requests
FROM web_access_logs
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY source_host, server_type;

-- IPs con más errores
SELECT source_host, remote_addr, COUNT(*) as errors
FROM web_access_logs
WHERE status >= 400
GROUP BY source_host, remote_addr
ORDER BY errors DESC LIMIT 20;
```

## 📝 Troubleshooting

### Conexión SSH falla
```bash
# Verificar desde container
docker compose exec log-processor ssh -i /app/ssh/id_rsa wgp@IP "echo OK"
```

### No aparecen datos
```bash
# Ver logs del collector
docker compose logs -f log-processor

# Verificar posiciones
cat log-processor-data/positions.json
```

## 🔒 Seguridad en Producción

1. **Restringir SSH key** - Solo comando tail
2. **Firewall** - Solo SSH desde WGP server
3. **VPN** - Si es posible, usar red privada
4. **Kubernetes** - Usar Sealed Secrets o Vault

## 📄 Licencia

MIT License

---

<p align="center">
  Hecho con ❤️ para monitorear tus servidores Nginx y Apache
</p>
