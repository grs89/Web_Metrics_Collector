# GitHub Actions - Docker Hub Setup

Este proyecto utiliza GitHub Actions para construir y publicar automáticamente imágenes Docker en Docker Hub.

## 📋 Configuración Requerida

### 1. Crear Secrets en GitHub

Ve a tu repositorio en GitHub: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Crea los siguientes secrets:

| Secret Name | Descripción | Ejemplo |
|------------|-------------|---------|
| `DOCKERHUB_USERNAME` | Tu nombre de usuario de Docker Hub | `tuusuario` |
| `DOCKERHUB_TOKEN` | Token de acceso de Docker Hub | `dckr_pat_xxxxx...` |
| `DOCKERHUB_REPO` | Nombre del repositorio en Docker Hub | `web_metrics_collector` |

### 2. Crear Access Token en Docker Hub

1. Ve a [Docker Hub](https://hub.docker.com/)
2. Inicia sesión con tu cuenta
3. Ve a **Account Settings** → **Security** → **New Access Token**
4. Dale un nombre descriptivo (ej: `github-actions-wmc`)
5. Selecciona permisos: **Read, Write, Delete**
6. Copia el token generado (solo se muestra una vez)
7. Pégalo en el secret `DOCKERHUB_TOKEN` de GitHub

## 🚀 Uso del Workflow

El workflow se ejecuta automáticamente **solo cuando creas un tag de versión**:

### Crear y Publicar una Release

```bash
# 1. Asegúrate de que todos los cambios estén commiteados
git add .
git commit -m "Release v1.0.0"

# 2. Crea el tag con versión semántica
git tag v1.0.0

# 3. Sube el tag a GitHub (esto dispara el workflow)
git push origin v1.0.0

# Resultado: Se construye y publica automáticamente en Docker Hub
# Genera tags: v1.0.0, v1.0, v1, latest
```

### Ejecución Manual (Opcional)

También puedes ejecutar el workflow manualmente sin crear un tag:

1. Ve a **Actions** → **Build Scan Push - DockerHub** → **Run workflow**
2. Selecciona la rama
3. Click en **Run workflow**

> [!IMPORTANT]
> El workflow **NO** se ejecuta en push a ramas ni en pull requests.
> Solo se dispara al crear tags con formato `v*.*.*` (ej: `v1.0.0`, `v2.1.3`)


## 🏷️ Tags Generados

El workflow genera automáticamente los siguientes tags cuando creas una release:

| Tag Creado | Tags de Docker Generados | Ejemplo |
|------------|-------------------------|---------|
| `v1.2.3` | `v1.2.3`, `v1.2`, `v1`, `latest` | `tuusuario/web_metrics_collector:v1.2.3` |
| `v2.0.0` | `v2.0.0`, `v2.0`, `v2`, `latest` | `tuusuario/web_metrics_collector:v2.0.0` |
| `v1.5.2` | `v1.5.2`, `v1.5`, `v1`, `latest` | `tuusuario/web_metrics_collector:v1.5.2` |

> [!NOTE]
> El tag `latest` siempre apunta a la última versión publicada.
> Los tags de versión mayor (`v1`, `v2`) permiten actualizaciones automáticas dentro de la misma versión mayor.


## 🏗️ Arquitecturas Soportadas

El workflow construye imágenes multi-arquitectura:

- ✅ `linux/amd64` (Intel/AMD x86_64)
- ✅ `linux/arm64` (ARM 64-bit, Apple Silicon, Raspberry Pi 4+)

## 📦 Usar la Imagen Publicada

### Seguridad (Non-Root User)
La imagen se ejecuta por defecto como un usuario no root (`appuser`, UID `1000`).
Si montas volúmenes desde el host (como llaves SSH), debes asegurarte de que el usuario `1000` tenga permisos de lectura.

### Docker Compose
```yaml
services:
  app:
    image: tuusuario/web_metrics_collector:latest
    user: "1000:1000" # Opcional, ya es el default
    volumes:
       - ./ssh_keys:/ssh_keys:ro # Asegúrate de que UID 1000 pueda leer esto
    # ... resto de la configuración
```

### Docker Run
```bash
docker pull tuusuario/web_metrics_collector:latest
docker run -d tuusuario/web_metrics_collector:latest
```

### Especificar Versión
```bash
docker pull tuusuario/web_metrics_collector:v1.0.0
```

## 🔍 Verificar el Workflow

1. Ve a la pestaña **Actions** en tu repositorio
2. Selecciona el workflow **Build Scan Push - DockerHub**
3. Verifica que el build sea exitoso (✅)
4. Revisa los logs para ver las imágenes publicadas

## 🐛 Troubleshooting

### Error: "denied: requested access to the resource is denied"
- Verifica que `DOCKERHUB_USERNAME` sea correcto en los secrets.
- Verifica que `DOCKERHUB_REPO` sea correcto (nombre del repositorio en Hub).
- Verifica que `DOCKERHUB_TOKEN` tenga permisos de escritura.

### Error: "buildx failed with: ERROR: failed to solve"
- Revisa el `Dockerfile` para errores de sintaxis
- Verifica que todas las dependencias estén disponibles

### La imagen no aparece en Docker Hub
- Verifica que el workflow haya completado exitosamente
- Asegúrate de que no sea un Pull Request (PR no publica imágenes)
- Revisa los logs del step "Build and push Docker image"

## 📝 Notas

- Este workflow utiliza un **workflow reusable** desde `grs89/github-template`
- El workflow usa **caché de Docker** para acelerar builds subsecuentes
- Las imágenes se construyen para **múltiples arquitecturas** en paralelo
- Incluye **escaneo de seguridad con Trivy** antes de publicar

---

© 2026 Web Metrics Collector Contributors
