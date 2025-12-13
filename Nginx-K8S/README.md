# ☸️ NGP - Nginx Geo Profiler (Kubernetes)

Despliegue en Kubernetes del sistema NGP para monitoreo y análisis de logs de Nginx con geolocalización.

## 📋 Requisitos

- Kubernetes 1.24+
- kubectl configurado
- Cluster con al menos 4GB RAM disponible
- StorageClass configurado (para PVCs)
- (Opcional) Ingress Controller para acceso externo

## 🚀 Inicio Rápido

### Opción 1: Con Kustomize (Recomendado)

```bash
# Desde la carpeta Nginx-K8S
kubectl apply -k .
```

### Opción 2: Manual

```bash
# 1. Crear namespace
kubectl apply -f namespace.yaml

# 2. Crear secrets (⚠️ modificar primero)
kubectl apply -f secrets.yaml

# 3. Crear ConfigMaps
kubectl apply -f configmap.yaml

# 4. Crear PVCs
kubectl apply -f pvc.yaml

# 5. Desplegar servicios (en orden)
kubectl apply -f postgres-deployment.yaml
kubectl apply -f logstash-deployment.yaml
kubectl apply -f log-processor-deployment.yaml
kubectl apply -f grafana-deployment.yaml

# 6. (Opcional) CronJob de retención
kubectl apply -f retention-cronjob.yaml

# 7. (Opcional) Ingress
kubectl apply -f ingress.yaml
```

### Verificar Despliegue

```bash
# Ver pods
kubectl get pods -n ngp

# Ver servicios
kubectl get svc -n ngp

# Ver logs
kubectl logs -f deployment/logstash -n ngp
kubectl logs -f deployment/log-processor -n ngp
```

## 📁 Estructura de Archivos

```
Nginx-K8S/
├── README.md                    # Este archivo
├── kustomization.yaml           # Para despliegue con Kustomize
│
├── namespace.yaml               # Namespace 'ngp'
├── secrets.yaml                 # Credenciales (⚠️ modificar)
├── configmap.yaml               # Configuraciones
├── pvc.yaml                     # Persistent Volume Claims
│
├── postgres-deployment.yaml     # PostgreSQL + Service
├── logstash-deployment.yaml     # Logstash + Service
├── log-processor-deployment.yaml # Log Processor
├── grafana-deployment.yaml      # Grafana + Service
│
├── retention-cronjob.yaml       # Limpieza de datos antiguos
└── ingress.yaml                 # Ingress (opcional)
```

## ⚙️ Configuración

### Secrets

Antes de desplegar, modifica `secrets.yaml`:

```yaml
stringData:
  POSTGRES_USER: "tu_usuario"
  POSTGRES_PASSWORD: "tu_password_seguro"
  POSTGRES_DB: "nginx_logs"
  GRAFANA_USER: "admin"
  GRAFANA_PASSWORD: "tu_password_seguro"
```

> ⚠️ **Producción**: Usa [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets), [External Secrets](https://external-secrets.io/) o [Vault](https://www.vaultproject.io/)

### Storage

Ajusta los PVCs en `pvc.yaml` según tu cluster:

```yaml
spec:
  storageClassName: tu-storage-class  # standard, gp2, etc.
  resources:
    requests:
      storage: 20Gi  # Ajustar según necesidad
```

### Imagen del Log Processor

El log-processor necesita una imagen Docker. Opciones:

**Opción A: Construir y publicar**
```bash
cd ../Nginx-Docker/log-processor
docker build -t tu-registry/ngp-log-processor:latest .
docker push tu-registry/ngp-log-processor:latest
```

**Opción B: Usar imagen local (desarrollo)**
```yaml
# En log-processor-deployment.yaml
image: ngp-log-processor:latest
imagePullPolicy: Never
```

### GeoIP

Para habilitar geolocalización, necesitas el archivo `GeoLite2-City.mmdb`:

1. Descargar de [MaxMind](https://www.maxmind.com/en/geolite2/signup)
2. Crear ConfigMap o Secret con el archivo
3. Montar en el pod del log-processor

```bash
# Crear ConfigMap con el archivo
kubectl create configmap geoip-data \
  --from-file=GeoLite2-City.mmdb=./GeoLite2-City.mmdb \
  -n ngp
```

## 🌐 Acceso a los Servicios

### Grafana

**Con LoadBalancer:**
```bash
kubectl get svc grafana-service -n ngp
# Usar EXTERNAL-IP:3000
```

**Con Port Forward (desarrollo):**
```bash
kubectl port-forward svc/grafana-service 3000:3000 -n ngp
# Acceder a http://localhost:3000
```

**Con Ingress:**
```bash
# Modificar ingress.yaml con tu dominio
kubectl apply -f ingress.yaml
```

### Logstash (para Filebeat)

**Con LoadBalancer:**
```bash
kubectl get svc logstash-service -n ngp
# Usar EXTERNAL-IP:5044 en la config de Filebeat
```

**Con NodePort:**
```yaml
# Modificar logstash-deployment.yaml
spec:
  type: NodePort
  ports:
    - port: 5044
      nodePort: 30044  # Puerto fijo
```

## 🛠️ Comandos Útiles

```bash
# Ver recursos del namespace
kubectl get all -n ngp

# Ver logs de un pod
kubectl logs -f deployment/logstash -n ngp
kubectl logs -f deployment/grafana -n ngp

# Ejecutar shell en un pod
kubectl exec -it deployment/postgres -n ngp -- psql -U ngp_user -d nginx_logs

# Escalar deployments
kubectl scale deployment/log-processor --replicas=2 -n ngp

# Ver eventos
kubectl get events -n ngp --sort-by='.lastTimestamp'

# Eliminar todo
kubectl delete -k .
# o
kubectl delete namespace ngp
```

## 📊 Monitoreo del Cluster

### Métricas de Pods

```bash
# Uso de recursos
kubectl top pods -n ngp

# Descripción detallada
kubectl describe pod -l app=postgres -n ngp
```

### Health Checks

```bash
# Estado de los pods
kubectl get pods -n ngp -o wide

# Verificar readiness
kubectl get pods -n ngp -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}'
```

## 🔄 Actualizaciones

### Rolling Update

```bash
# Actualizar imagen
kubectl set image deployment/grafana grafana=grafana/grafana:10.2.0 -n ngp

# Ver progreso
kubectl rollout status deployment/grafana -n ngp

# Rollback si hay problemas
kubectl rollout undo deployment/grafana -n ngp
```

### Con Kustomize

Modifica la versión en `kustomization.yaml`:

```yaml
images:
  - name: grafana/grafana
    newTag: "10.2.0"
```

```bash
kubectl apply -k .
```

## 🔒 Seguridad

### Network Policies (Opcional)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ngp-network-policy
  namespace: ngp
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ngp
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: ngp
```

### Pod Security

Los deployments incluyen:
- `securityContext` configurado
- Probes de liveness y readiness
- Límites de recursos

## 🔍 Troubleshooting

### Pod en CrashLoopBackOff

```bash
kubectl describe pod <pod-name> -n ngp
kubectl logs <pod-name> -n ngp --previous
```

### PVC Pending

```bash
kubectl describe pvc postgres-pvc -n ngp
# Verificar StorageClass disponible
kubectl get storageclass
```

### Servicios no accesibles

```bash
# Verificar endpoints
kubectl get endpoints -n ngp

# Test de conectividad
kubectl run test --rm -it --image=busybox -n ngp -- /bin/sh
# Dentro del pod:
nc -zv postgres-service 5432
```

### Log Processor no conecta a PostgreSQL

```bash
# Verificar que postgres está listo
kubectl get pods -n ngp -l app=postgres

# Ver logs del init container
kubectl logs deployment/log-processor -c wait-for-postgres -n ngp
```

## 📈 Escalabilidad

### Horizontal Pod Autoscaler (Opcional)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: log-processor-hpa
  namespace: ngp
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: log-processor
  minReplicas: 1
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

---

📖 Ver [README principal](../README.md) para documentación completa.

