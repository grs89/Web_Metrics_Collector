# ☸️ WGP - Web Geo Profiler (Kubernetes)

Despliegue en Kubernetes del sistema WGP para monitoreo y análisis de logs de **Nginx** y **Apache** con geolocalización.

## 📋 Requisitos

- Kubernetes 1.24+
- kubectl configurado
- Cluster con al menos 4GB RAM disponible
- StorageClass configurado (para PVCs)
- (Opcional) Ingress Controller para acceso externo

## 🖥️ Servidores Soportados

| Servidor | Formatos | Auto-detección |
|----------|----------|----------------|
| **Nginx** | JSON | ✅ |
| **Apache** | JSON, Combined | ✅ |

## 🚀 Inicio Rápido

### Con Kustomize (Recomendado)

```bash
kubectl apply -k .
```

### Manual

```bash
kubectl apply -f namespace.yaml
kubectl apply -f secrets.yaml      # ⚠️ Modificar primero
kubectl apply -f configmap.yaml
kubectl apply -f pvc.yaml
kubectl apply -f postgres-deployment.yaml
kubectl apply -f logstash-deployment.yaml
kubectl apply -f log-processor-deployment.yaml
kubectl apply -f grafana-deployment.yaml
kubectl apply -f retention-cronjob.yaml
```

### Verificar Despliegue

```bash
kubectl get pods -n wgp
kubectl get svc -n wgp
kubectl logs -f deployment/log-processor -n wgp
```

## 📁 Estructura de Archivos

```
Nginx-K8S/
├── kustomization.yaml           # Despliegue con Kustomize
├── namespace.yaml               # Namespace 'wgp'
├── secrets.yaml                 # Credenciales (⚠️ modificar)
├── configmap.yaml               # Configuraciones
├── pvc.yaml                     # Persistent Volume Claims
├── postgres-deployment.yaml
├── logstash-deployment.yaml
├── log-processor-deployment.yaml
├── grafana-deployment.yaml
├── retention-cronjob.yaml
└── ingress.yaml                 # (Opcional)
```

## ⚙️ Configuración

### Secrets

Modifica `secrets.yaml`:

```yaml
stringData:
  POSTGRES_USER: "wgp_user"
  POSTGRES_PASSWORD: "tu_password_seguro"
  POSTGRES_DB: "web_logs"
  GRAFANA_USER: "admin"
  GRAFANA_PASSWORD: "tu_password_seguro"
  DEFAULT_SERVER_TYPE: "nginx"  # o 'apache'
```

> ⚠️ **Producción**: Usa Sealed Secrets, External Secrets o Vault

### GeoIP

```bash
kubectl create configmap geoip-data \
  --from-file=GeoLite2-City.mmdb=./GeoLite2-City.mmdb \
  -n wgp
```

## 🌐 Acceso a los Servicios

### Grafana

```bash
# Port Forward
kubectl port-forward svc/grafana-service 3000:3000 -n wgp

# LoadBalancer
kubectl get svc grafana-service -n wgp
```

### Logstash (para Filebeat)

```bash
kubectl get svc logstash-service -n wgp
# Usar EXTERNAL-IP:5044 en Filebeat
```

## 🛠️ Comandos Útiles

```bash
# Ver recursos
kubectl get all -n wgp

# Logs
kubectl logs -f deployment/logstash -n wgp

# PostgreSQL
kubectl exec -it deployment/postgres -n wgp -- psql -U wgp_user -d web_logs

# Escalar
kubectl scale deployment/log-processor --replicas=2 -n wgp

# Eliminar todo
kubectl delete -k .
```

## 🔍 Troubleshooting

### Pod en CrashLoopBackOff
```bash
kubectl describe pod <pod-name> -n wgp
kubectl logs <pod-name> -n wgp --previous
```

### PVC Pending
```bash
kubectl describe pvc postgres-pvc -n wgp
kubectl get storageclass
```

### Servicios no accesibles
```bash
kubectl get endpoints -n wgp
kubectl run test --rm -it --image=busybox -n wgp -- nc -zv postgres-service 5432
```

---

📖 Ver [README principal](../README.md) para documentación completa.
