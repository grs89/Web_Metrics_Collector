# ☸️ WGP - Web Geo Profiler (Kubernetes)

Despliegue en Kubernetes del sistema WGP para monitoreo de logs de **Nginx** y **Apache** con geolocalización.

## 🏗️ Arquitectura PULL

```
┌─────────────────────────────────────────────────────────────────┐
│                      Kubernetes Cluster                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                     Namespace: wgp                           ││
│  │  ┌─────────────┐   ┌───────────┐   ┌──────────┐             ││
│  │  │Log Processor│──▶│ PostgreSQL│──▶│  Grafana │──▶ Ingress  ││
│  │  │   (PULL)    │   └───────────┘   └──────────┘             ││
│  │  └──────┬──────┘                                            ││
│  └─────────┼───────────────────────────────────────────────────┘│
└────────────┼────────────────────────────────────────────────────┘
             │ SSH (cada 30s)
       ┌─────┴─────┬─────────────┐
       ▼           ▼             ▼
   ┌────────┐  ┌────────┐   ┌────────┐
   │ Nginx  │  │ Apache │   │Server N│
   └────────┘  └────────┘   └────────┘
```

> **Sin Logstash** - El log-processor se conecta directamente via SSH.

## 📋 Requisitos

- Kubernetes 1.24+
- kubectl configurado
- Acceso SSH a servidores web remotos

## 🚀 Despliegue

### 1. Crear SSH Key

```bash
# Generar key
ssh-keygen -t rsa -b 4096 -f ./id_rsa -N ""

# Copiar a cada servidor web
ssh-copy-id -i ./id_rsa.pub wgp@TU_SERVIDOR_IP

# Crear secret en K8S
kubectl create namespace wgp
kubectl create secret generic wgp-ssh-key \
  --from-file=id_rsa=./id_rsa \
  -n wgp
```

### 2. Configurar Hosts

Editar `configmap.yaml` → sección `wgp-hosts-config`:

```yaml
hosts:
  - name: nginx-server-1
    enabled: true
    host: 192.168.1.10
    server_type: nginx
    log_paths:
      - /var/log/nginx/access.log
```

### 3. Personalizar Secrets

```bash
# Editar secrets.yaml con tus credenciales
nano secrets.yaml
```

### 4. Desplegar

```bash
kubectl apply -k .
```

### 5. Verificar

```bash
kubectl get pods -n wgp
kubectl logs -f deployment/log-processor -n wgp
```

## 📦 Componentes

| Componente | Replicas | Descripción |
|------------|----------|-------------|
| **log-processor** | 1 | Recolecta logs via SSH |
| **postgres** | 1 | Base de datos |
| **grafana** | 1 | Dashboard |
| **retention-cronjob** | CronJob | Limpieza anual |

## 🔧 Preparar Servidor Remoto

```bash
# En cada servidor web
sudo useradd -m -s /bin/bash wgp
sudo usermod -aG adm wgp

# Desde máquina con kubectl
ssh-copy-id -i ./id_rsa.pub wgp@SERVIDOR_IP
```

## 📊 Acceso a Grafana

### Con Port-Forward

```bash
kubectl port-forward svc/grafana-service 3001:3000 -n wgp
# Abrir http://localhost:3001
```

### Con Ingress

Descomentar en `kustomization.yaml`:
```yaml
resources:
  - ingress.yaml
```

## 🛠️ Comandos Útiles

```bash
# Ver logs
kubectl logs -f deployment/log-processor -n wgp

# Reiniciar después de cambiar config
kubectl rollout restart deployment/log-processor -n wgp

# Acceder a PostgreSQL
kubectl exec -it deployment/postgres -n wgp -- psql -U wgp_user -d web_logs

# Ver posiciones guardadas
kubectl exec deployment/log-processor -n wgp -- cat /app/data/positions.json
```

## 📁 Estructura

```
Web_Metric_Collector_K8S/
├── kustomization.yaml          # Orquestación
├── namespace.yaml              # Namespace wgp
├── secrets.yaml                # Credenciales
├── configmap.yaml              # Hosts config + Grafana
├── pvc.yaml                    # Persistent volumes
├── postgres-deployment.yaml    # PostgreSQL
├── log-processor-deployment.yaml # PULL via SSH
├── grafana-deployment.yaml     # Grafana
├── retention-cronjob.yaml      # Limpieza
└── ingress.yaml                # (Opcional)
```

## 🔒 Seguridad

Para producción:
- Usar **Sealed Secrets** o **Vault** para credenciales
- Restringir SSH key con `command=` en authorized_keys
- Network Policies para aislar pods

---

📖 Ver [README principal](../README.md) para más información.
