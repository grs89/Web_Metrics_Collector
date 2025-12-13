# 🌍 NGP - Nginx Geo Profiler

Sistema completo de monitoreo y análisis de logs de acceso de Nginx con geolocalización, métricas en tiempo real y visualización en Grafana. Diseñado para recibir logs de servidores Nginx remotos mediante **Filebeat**.

![Grafana Dashboard](https://img.shields.io/badge/Grafana-Dashboard-orange?style=for-the-badge&logo=grafana)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?style=for-the-badge&logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?style=for-the-badge&logo=docker)
![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-326CE5?style=for-the-badge&logo=kubernetes)
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
- 📡 **Filebeat** - Recibe logs de servidores Nginx remotos

## 📦 Opciones de Despliegue

| Método | Caso de Uso | Documentación |
|--------|-------------|---------------|
| 🐳 **Docker Compose** | Desarrollo, servidores individuales | [Nginx-Docker/](./Nginx-Docker/) |
| ☸️ **Kubernetes** | Producción, alta disponibilidad | [Nginx-K8S/](./Nginx-K8S/) |

## 🏗️ Arquitectura

```
┌─────────────────────────────┐         ┌─────────────────────────────────────────┐
│   SERVIDOR NGINX REMOTO     │         │           SERVIDOR NGP                  │
│                             │         │       (Docker / Kubernetes)             │
│  Nginx ──▶ Filebeat ────────────────▶ Logstash ──▶ Log Processor ──▶ PostgreSQL│
│         (logs JSON)         │  :5044  │                  + GeoIP        │       │
└─────────────────────────────┘         │                                 ▼       │
                                        │                             Grafana     │
                                        │                              :3000      │
                                        └─────────────────────────────────────────┘
```

## 🚀 Inicio Rápido

### Docker Compose

```bash
cd Nginx-Docker

# Configurar
cp env.example .env

# (Opcional) GeoIP
MAXMIND_LICENSE_KEY=tu_clave ./scripts/download-geoip.sh

# Iniciar
docker compose up -d
```

### Kubernetes

```bash
cd Nginx-K8S

# Modificar secrets.yaml con tus credenciales
# Luego desplegar con Kustomize
kubectl apply -k .
```

## 📁 Estructura del Proyecto

```
NGP/
├── README.md                 # Este archivo
├── .gitignore                # Archivos ignorados por Git
│
├── Nginx-Docker/             # 🐳 Despliegue con Docker Compose
│   ├── docker-compose.yml
│   ├── env.example
│   ├── README.md
│   ├── filebeat/
│   ├── grafana/
│   ├── log-processor/
│   ├── logstash/
│   ├── nginx/
│   ├── nginx-server/
│   ├── postgres/
│   └── scripts/
│
└── Nginx-K8S/                # ☸️ Despliegue en Kubernetes
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
- Total de requests (24h)
- IPs únicas
- Países de origen
- Tiempo de respuesta promedio

### Visualizaciones
- 📈 **Requests Over Time** - Gráfico temporal de requests
- 🥧 **Status Codes** - Distribución de códigos HTTP
- 🗺️ **Geomap** - Mapa mundial con ubicaciones de visitantes
- 📋 **Top Tables** - IPs, países, URIs más frecuentes
- ⏱️ **Response Time** - Percentiles P95/P99

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

### 2. Instalar Filebeat

**Script automático:**

```bash
# Copiar script al servidor Nginx
scp Nginx-Docker/nginx-server/install-filebeat.sh usuario@servidor:/tmp/

# Ejecutar en el servidor
sudo /tmp/install-filebeat.sh IP_SERVIDOR_NGP
```

**Manual:**

```bash
# Debian/Ubuntu
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo gpg --dearmor -o /usr/share/keyrings/elastic-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/elastic-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list
sudo apt update && sudo apt install filebeat
```

Configurar `/etc/filebeat/filebeat.yml`:

```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/nginx/access.log
    json.keys_under_root: true
    json.add_error_key: true
    fields:
      log_type: nginx_access
    fields_under_root: true

output.logstash:
  hosts: ["IP_SERVIDOR_NGP:5044"]
```

```bash
sudo systemctl enable filebeat
sudo systemctl start filebeat
```

## 🌍 GeoIP (Opcional)

Para obtener datos de geolocalización:

1. Regístrate en [MaxMind GeoLite2](https://www.maxmind.com/en/geolite2/signup) (gratis)
2. Genera una license key
3. Ejecuta:

**Docker:**
```bash
cd Nginx-Docker
MAXMIND_LICENSE_KEY=tu_clave ./scripts/download-geoip.sh
docker compose restart log-processor
```

**Kubernetes:**
```bash
# Descargar y crear ConfigMap
kubectl create configmap geoip-data \
  --from-file=GeoLite2-City.mmdb=./GeoLite2-City.mmdb \
  -n ngp
```

## 🔒 Seguridad en Producción

1. **Cambiar contraseñas** en `.env` o `secrets.yaml`
2. **Usar SSL/TLS** entre Filebeat y Logstash
3. **Firewall**: Solo abrir puertos necesarios
4. **VPN/Red privada**: Si es posible, usar red interna
5. **Kubernetes**: Usar Sealed Secrets o Vault para secretos

## 🔍 Consultas SQL Útiles

```sql
-- Ver últimos logs
SELECT * FROM nginx_access_logs 
ORDER BY timestamp DESC LIMIT 100;

-- Requests por país (últimas 24h)
SELECT country_name, COUNT(*) as requests
FROM nginx_access_logs
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY country_name
ORDER BY requests DESC;

-- IPs con más errores
SELECT remote_addr, COUNT(*) as errors
FROM nginx_access_logs
WHERE status >= 400
GROUP BY remote_addr
ORDER BY errors DESC LIMIT 20;

-- Ejecutar limpieza manual
SELECT cleanup_old_logs(365);
```

## 📝 Troubleshooting

### Filebeat no envía logs

```bash
# Verificar conectividad
telnet IP_SERVIDOR_NGP 5044

# Ver logs de Filebeat
sudo tail -f /var/log/filebeat/filebeat

# Testear output
sudo filebeat test output
```

### No aparecen datos en Grafana

1. Verificar Logstash: `docker compose logs -f logstash` o `kubectl logs -f deployment/logstash -n ngp`
2. Verificar log-processor: `docker compose logs -f log-processor` o `kubectl logs -f deployment/log-processor -n ngp`
3. Verificar formato JSON en Nginx

### GeoIP no funciona

```bash
# Docker
ls -la Nginx-Docker/log-processor/geoip/
docker compose restart log-processor

# Kubernetes
kubectl describe configmap geoip-data -n ngp
kubectl rollout restart deployment/log-processor -n ngp
```

## 🛠️ Desarrollo

### Generar tráfico de prueba

```bash
cd Nginx-Docker
./scripts/generate-test-traffic.sh
```

### Construir imagen del log-processor

```bash
cd Nginx-Docker/log-processor
docker build -t ngp-log-processor:latest .
```

## 📄 Licencia

MIT License - Usar libremente para proyectos personales y comerciales.

---

<p align="center">
  Hecho con ❤️ para monitorear tus servidores Nginx
</p>

