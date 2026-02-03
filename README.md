# Web Geo Profiler (WMC)

[Ler em Português](README_PT.md)

WMC es un sistema centralizado de monitoreo de registros que visualiza el tráfico web geográficamente y por volumen. Consulta servidores remotos Nginx/Apache vía SSH, analiza los registros, los enriquece con datos GeoIP y los almacena en PostgreSQL para su visualización en Grafana.

![Dashboard Screenshot](docs/images/dashboard_screenshot.png)

## Características
- **Sin Agentes**: Utiliza SSH para leer registros (no requiere instalación en servidores remotos).
- **Enriquecimiento**: Agrega Ciudad/País/Latitud/Longitud a cada petición.
- **Inteligencia de Seguridad**:
  - **Detección de Falsos Googlebot**: Bloquea IPs que pretenden ser Googlebot.
  - **Fail2Ban Lite**: Bloqueo automático de IPs con actividad maliciosa.
  - **Monitoreo de Amenazas**: Visualiza picos de SQLi, XSS y errores.
- **Redes Avanzadas**:
  - **DNS Inverso**: Resuelve IPs a nombres de host (con caché).
  - **Mapa de Tráfico Animado**: Visualización 3D en vivo del flujo de tráfico.
- **Retención de Datos**: Limpieza automática de registros con más de 1 año.
- **Analítica**: Desglose por Navegador, Sistema Operativo y Dispositivo.
- **Visualización**: Dashboard de Grafana preconfigurado con Mapa Mundial.
- **Soporte**: Nginx (JSON) y Apache (Formato de Registro Combinado).

## Inicio Rápido (Docker Compose Local)

1. **Prerrequisitos**: Docker y Docker Compose.
2. **Configurar Llaves SSH**: Asegúrate de tener llaves SSH que puedan acceder a tus servidores objetivo. Móntalas en `docker-compose.yml` o colócalas en una carpeta.
3. **Configurar Hosts**: Edita `hosts.yml` para definir tus servidores.
   ```yaml
   hosts:
     - name: "mi-servidor-web"
       host: "1.2.3.4"
       user: "root"
       key_path: "/ssh_keys/id_rsa" # Ruta dentro del contenedor
       log_files:
         - path: "/var/log/nginx/access.log"
           type: "nginx-json"
   ```
4. **Base de Datos GeoIP**: Coloca `GeoLite2-City.mmdb` en `log_processor/` (opcional, pero necesario para los mapas).
5. **Ejecutar**:
   ```bash
   docker-compose up -d --build
   ```
6. **Acceder a Grafana**: Abre `http://localhost:3000` (Usuario: `admin` / Contraseña: `admin`). El dashboard "WMC Dashboard" está precargado.

## Incorporar un Nuevo Servidor

Para agregar un nuevo servidor al pool de monitoreo:

1. **Acceso SSH**: Asegúrate de que la máquina que ejecuta WMC tenga acceso mediante llave pública SSH al servidor objetivo.
2. **Formato de Registro**:
   - Si usas **Nginx**, configúralo para generar registros JSON (recomendado) o usa el formato combinado estándar.
   - Si usas **Apache**, asegúrate de usar el `Combined Log Format`.
3. **Actualizar Configuración**: Agrega la entrada a `hosts.yml` como se muestra arriba.
4. **Reiniciar**: Reinicia el contenedor del procesador de registros para aplicar los cambios.
   ```bash
   docker-compose restart log-processor
   ```

## Despliegue en Producción (Kubernetes)
Los manifiestos se encuentran en `k8s/`.
1. Actualiza `k8s/configmap.yaml` (generado vía Kustomize) con tu `hosts.yml` real.
2. Crea offsets/secretos para las llaves SSH.
3. Aplica:
   ```bash
   kubectl apply -k k8s/
   ```
