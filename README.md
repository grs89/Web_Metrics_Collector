# 🌐 WGP - Web Geo Profiler

Sistema completo de monitoreo y análisis de logs de acceso de servidores web con geolocalización, métricas en tiempo real y visualización en Grafana. Diseñado para recibir logs de **Nginx** y **Apache** remotos mediante **Filebeat**.

![Grafana Dashboard](https://img.shields.io/badge/Grafana-Dashboard-orange?style=for-the-badge&logo=grafana)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?style=for-the-badge&logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?style=for-the-badge&logo=docker)
![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-326CE5?style=for-the-badge&logo=kubernetes)
![Nginx](https://img.shields.io/badge/Nginx-Supported-009639?style=for-the-badge&logo=nginx)
![Apache](https://img.shields.io/badge/Apache-Supported-D22128?style=for-the-badge&logo=apache)
![Filebeat](https://img.shields.io/badge/Filebeat-8.x-yellow?style=for-the-badge&logo=elastic)

## ✨ Características

- 📊 **Métricas en tiempo real** - Requests/segundo, tiempos de respuesta, códigos de estado
- 🌍 **Geomap interactivo** - Visualiza el origen geográfico de las visitas
- 🗄️ **PostgreSQL** - Almacenamiento robusto con retención de 1 año
- 📈 **Dashboards Grafana** - Paneles preconfigurados y listos para usar
- 🔍 **Análisis detallado** - Top IPs, URIs, países, user agents
- ⏱️ **Percentiles de latencia** - P95, P99 para monitoreo de rendimiento
- 🐳 **Docker Compose** - Despliegue simple para desarrollo y servidores individuales
- ☸️ **Kubernetes** - Despliegue escalable para producción
- 📡 **Filebeat** - Recibe logs de servidores web remotos
- 🔧 **Multi-servidor** - Soporta **Nginx** y **Apache** simultáneamente

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

## 🏗️ Arquitectura

```
┌─────────────────────────────┐         ┌─────────────────────────────────────────┐
│   SERVIDOR WEB REMOTO       │         │           SERVIDOR WGP                  │
│   (Nginx / Apache)          │         │       (Docker / Kubernetes)             │
│                             │         │                                         │
│  WebServer ──▶ Filebeat ────────────▶ Logstash ──▶ Log Processor ──▶ PostgreSQL│
│           (logs JSON)       │  :5044  │                  + GeoIP        │       │
└─────────────────────────────┘         │                                 ▼       │
                                        │                             Grafana     │
                                        │                              :3000      │
                                        └─────────────────────────────────────────┘
```

## 🚀 Inicio Rápido

### Docker Compose

```bash
cd Web_Metric_Collector_Docker

# Configurar
cp env.example .env

# (Opcional) GeoIP
MAXMIND_LICENSE_KEY=tu_clave ./scripts/download-geoip.sh

# Iniciar
docker compose up -d
```

### Kubernetes

```bash
cd Web_Metric_Collector_K8S

# Modificar secrets.yaml con tus credenciales
# Luego desplegar con Kustomize
kubectl apply -k .
```

## 📁 Estructura del Proyecto

```
WGP/
├── README.md                          # Este archivo
├── .gitignore                         # Archivos ignorados por Git
│
├── Web_Metric_Collector_Docker/       # 🐳 Despliegue con Docker Compose
│   ├── docker-compose.yml
│   ├── env.example
│   ├── README.md
│   ├── filebeat/
│   ├── grafana/
│   ├── log-processor/                 # Soporta Nginx + Apache
│   ├── logstash/
│   ├── nginx/
│   ├── nginx-server/
│   ├── postgres/
│   └── scripts/
│
└── Web_Metric_Collector_K8S/          # ☸️ Despliegue en Kubernetes
    ├── README.md
    ├── kustomization.yaml
    ├── namespace.yaml
    ├── secrets.yaml
    ├── configmap.yaml
    ├── pvc.yaml
    ├── postgres-deployment.yaml
    ├── logstash-deployment.yaml
    ├── log-processor-deployment.yaml
    ├── grafana-deployment.yaml
    ├── retention-cronjob.yaml
    └── ingress.yaml
```

## 🌐 URLs y Puertos

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **Grafana** | 3000 | Dashboard de visualización |
| **Logstash** | 5044 | Recibe logs de Filebeat |
| **Logstash** | 5000 | TCP/UDP alternativo |
| **PostgreSQL** | 5432 | Base de datos |

## 📊 Dashboard de Grafana

El dashboard incluye:

### Métricas Principales
- Total de requests (24h) - Nginx y Apache
- IPs únicas
- Países de origen
- Tiempo de respuesta promedio
- **Filtro por tipo de servidor** (Nginx/Apache)

### Visualizaciones
- 📈 **Requests Over Time** - Gráfico temporal de requests
- 🥧 **Status Codes** - Distribución de códigos HTTP
- 🗺️ **Geomap** - Mapa mundial con ubicaciones de visitantes
- 📋 **Top Tables** - IPs, países, URIs más frecuentes
- ⏱️ **Response Time** - Percentiles P95/P99
- 🖥️ **Server Summary** - Comparación entre Nginx y Apache

## 📡 Configurar Servidor Nginx Remoto

### 1. Configurar formato de logs JSON en Nginx

Edita tu `/etc/nginx/nginx.conf`:

```nginx
http {
    log_format json_combined escape=json
        '{'
            '"timestamp":"$time_iso8601",'
            '"remote_addr":"$remote_addr",'
            '"remote_user":"$remote_user",'
            '"request_method":"$request_method",'
            '"request_uri":"$request_uri",'
            '"request":"$request",'
            '"status":$status,'
            '"body_bytes_sent":$body_bytes_sent,'
            '"request_time":$request_time,'
            '"http_referer":"$http_referer",'
            '"http_user_agent":"$http_user_agent",'
            '"http_x_forwarded_for":"$http_x_forwarded_for",'
            '"host":"$host",'
            '"server_name":"$server_name"'
        '}';

    access_log /var/log/nginx/access.log json_combined;
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### 2. Instalar Filebeat para Nginx

```bash
# Copiar script al servidor Nginx
scp Web_Metric_Collector_Docker/nginx-server/install-filebeat.sh usuario@servidor:/tmp/

# Ejecutar en el servidor
sudo /tmp/install-filebeat.sh IP_SERVIDOR_WGP
```

## 📡 Configurar Servidor Apache Remoto

### 1. Configurar formato de logs JSON en Apache

Edita tu `/etc/apache2/apache2.conf` o `/etc/httpd/conf/httpd.conf`:

```apache
# Habilitar mod_log_config si no está habilitado
LoadModule log_config_module modules/mod_log_config.so

# Formato JSON para WGP
LogFormat "{ \"timestamp\":\"%{%Y-%m-%dT%H:%M:%S%z}t\", \"remote_addr\":\"%a\", \"remote_user\":\"%u\", \"request_method\":\"%m\", \"request_uri\":\"%U%q\", \"request\":\"%r\", \"status\":%>s, \"body_bytes_sent\":%B, \"request_time\":%D, \"http_referer\":\"%{Referer}i\", \"http_user_agent\":\"%{User-Agent}i\", \"http_x_forwarded_for\":\"%{X-Forwarded-For}i\", \"host\":\"%v\", \"log_type\":\"apache_access\" }" wgp_json

CustomLog /var/log/apache2/access.log wgp_json
```

```bash
# Debian/Ubuntu
sudo apache2ctl configtest && sudo systemctl reload apache2

# RHEL/CentOS
sudo apachectl configtest && sudo systemctl reload httpd
```

### 2. Instalar Filebeat para Apache

Configurar `/etc/filebeat/filebeat.yml`:

```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/apache2/access.log    # Debian/Ubuntu
      # - /var/log/httpd/access_log    # RHEL/CentOS
    json.keys_under_root: true
    json.add_error_key: true
    fields:
      log_type: apache_access
    fields_under_root: true

output.logstash:
  hosts: ["IP_SERVIDOR_WGP:5044"]
```

```bash
sudo systemctl enable filebeat
sudo systemctl start filebeat
```

### Formato Combined Log (alternativo)

Si prefieres el formato tradicional de Apache, WGP también lo soporta:

```apache
LogFormat "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"" combined
CustomLog /var/log/apache2/access.log combined
```

Configurar Filebeat sin JSON parsing:

```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/apache2/access.log
    fields:
      log_type: apache_access
    fields_under_root: true

output.logstash:
  hosts: ["IP_SERVIDOR_WGP:5044"]
```

## 🌍 GeoIP (Opcional)

Para obtener datos de geolocalización:

1. Regístrate en [MaxMind GeoLite2](https://www.maxmind.com/en/geolite2/signup) (gratis)
2. Genera una license key
3. Ejecuta:

**Docker:**
```bash
cd Web_Metric_Collector_Docker
MAXMIND_LICENSE_KEY=tu_clave ./scripts/download-geoip.sh
docker compose restart log-processor
```

**Kubernetes:**
```bash
# Descargar y crear ConfigMap
kubectl create configmap geoip-data \
  --from-file=GeoLite2-City.mmdb=./GeoLite2-City.mmdb \
  -n wgp
```

## 🔒 Seguridad en Producción

1. **Cambiar contraseñas** en `.env` o `secrets.yaml`
2. **Usar SSL/TLS** entre Filebeat y Logstash
3. **Firewall**: Solo abrir puertos necesarios
4. **VPN/Red privada**: Si es posible, usar red interna
5. **Kubernetes**: Usar Sealed Secrets o Vault para secretos

## 🔍 Consultas SQL Útiles

```sql
-- Ver últimos logs (ambos servidores)
SELECT server_type, * FROM web_access_logs 
ORDER BY timestamp DESC LIMIT 100;

-- Requests por servidor web (últimas 24h)
SELECT server_type, COUNT(*) as requests
FROM web_access_logs
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY server_type;

-- Requests por país y servidor (últimas 24h)
SELECT server_type, country_name, COUNT(*) as requests
FROM web_access_logs
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY server_type, country_name
ORDER BY requests DESC;

-- IPs con más errores por servidor
SELECT server_type, remote_addr, COUNT(*) as errors
FROM web_access_logs
WHERE status >= 400
GROUP BY server_type, remote_addr
ORDER BY errors DESC LIMIT 20;

-- Comparación de tiempos de respuesta
SELECT server_type, 
       AVG(request_time) as avg_time,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY request_time) as p95,
       PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY request_time) as p99
FROM web_access_logs
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY server_type;

-- Ejecutar limpieza manual
SELECT cleanup_old_logs(365);
```

## 📝 Troubleshooting

### Filebeat no envía logs

```bash
# Verificar conectividad
telnet IP_SERVIDOR_WGP 5044

# Ver logs de Filebeat
sudo tail -f /var/log/filebeat/filebeat

# Testear output
sudo filebeat test output
```

### No aparecen datos en Grafana

1. Verificar Logstash: `docker compose logs -f logstash` o `kubectl logs -f deployment/logstash -n wgp`
2. Verificar log-processor: `docker compose logs -f log-processor` o `kubectl logs -f deployment/log-processor -n wgp`
3. Verificar formato JSON en servidor web

### GeoIP no funciona

```bash
# Docker
ls -la Web_Metric_Collector_Docker/log-processor/geoip/
docker compose restart log-processor

# Kubernetes
kubectl describe configmap geoip-data -n wgp
kubectl rollout restart deployment/log-processor -n wgp
```

### Logs de Apache no se procesan

```bash
# Verificar formato de log
tail -1 /var/log/apache2/access.log

# Si es JSON, debe empezar con {
# Si es Combined, debe verse como: 192.168.1.1 - - [02/Feb/2024:10:30:00 +0000] "GET / HTTP/1.1" 200 1234
```

## 🛠️ Desarrollo

### Generar tráfico de prueba

```bash
cd Web_Metric_Collector_Docker
./scripts/generate-test-traffic.sh
```

### Construir imagen del log-processor

```bash
cd Web_Metric_Collector_Docker/log-processor
docker build -t wgp-log-processor:latest .
```

## 📄 Licencia

MIT License - Usar libremente para proyectos personales y comerciales.

---

<p align="center">
  Hecho con ❤️ para monitorear tus servidores Nginx y Apache
</p>
