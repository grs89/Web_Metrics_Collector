# 🌐 Web Metrics Collector (WMC)

[🇧🇷 Português](#web-metrics-collector-wmc-português)

WMC es un sistema centralizado de monitoreo de logs que visualiza el tráfico web geográficamente y por volumen. Se conecta a servidores remotos vía SSH, analiza los registros, los enriquece con datos GeoIP y los almacena en PostgreSQL y ClickHouse para su visualización en Grafana.

[![Build Scan Push - DockerHub](https://github.com/grs89/Web_Metrics_Collector/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/grs89/Web_Metrics_Collector/actions/workflows/docker-publish.yml)
[![Docker Hub](https://img.shields.io/docker/v/gersonofstone/web_metrics_collector?label=Docker%20Hub&logo=docker)](https://hub.docker.com/r/gersonofstone/web_metrics_collector)
[![Docker Pulls](https://img.shields.io/docker/pulls/gersonofstone/web_metrics_collector?logo=docker)](https://hub.docker.com/r/gersonofstone/web_metrics_collector)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

![Dashboard Screenshot](docs/images/dashboard_screenshot.png)

---

## 📋 Tabla de Contenidos

- [✨ Características](#-características)
- [🚀 Inicio Rápido (Docker Compose)](#-inicio-rápido-docker-compose-local)
- [➕ Formatos de Log Soportados](#-formatos-de-log-soportados)
- [➕ Incorporar un Nuevo Servidor](#-incorporar-un-nuevo-servidor)
- [🔁 CI/CD y Publicación de Imagen](#-cicd-y-publicación-de-imagen)
- [☁️ Despliegue en Producción (Kubernetes)](#️-despliegue-en-producción-kubernetes)
- [🏗️ Arquitectura](#️-arquitectura)

---

## ✨ Características

### 📡 Recolección Multi-Servidor
- **Sin Agentes**: Usa SSH para leer logs (no requiere instalación en servidores remotos).
- **Formatos Soportados**: Nginx (JSON/CLF), Apache (Combined), IIS (W3C), **Traefik (JSON)**, **Caddy (JSON)**, **HAProxy**.
- **Multisoporte de Logs**: Soporte para `access.log`, `error.log` (Nginx) y logs de aplicaciones (`Python`, `Node.js`, `PHP`).

### 🛡️ Inteligencia de Seguridad
- **Detección de Hosts Sospechosos**: Identifica clones (Phishing), scanners y configuraciones DNS erróneas.
- **Detección de Falsos Googlebot**: Bloquea IPs que pretenden ser Googlebot mediante Reverse DNS.
- **Fail2Ban Lite**: Bloqueo automático de IPs con actividad maliciosa.
- **Clasificación de Bots**: Visualiza "Good Bots" (Google, Bing) vs "Bad Bots" (MJ12, Petal).
- **Monitor SSL**: Audita la fecha de expiración de certificados cada 12 horas.

### 🔁 Resiliencia y Persistencia
- **Persistencia de Offsets**: Guarda la posición de lectura en `data/state.json` para no perder ni duplicar datos tras un reinicio.
- **Buffer en Memoria**: Cola interna `asyncio.Queue` (10.000 entradas) desacopla la ingesta del almacenamiento.
- **Exponential Backoff (SSH y DB)**: Reintentos inteligentes para conexiones SSH y escrituras en base de datos (1s → 2s → 4s → 8s → 16s).

### 📉 Inteligencia de Datos
- **Detección de Anomalías (Z-Score)**: Compara el tráfico en tiempo real contra el promedio histórico por semana para identificar picos o caídas inusuales.
- **Categorización de Logs**: Columna `log_category` que distingue entre `access`, `error` y `app`.
- **Almacenamiento Dual**: Los logs se guardan simultáneamente en **PostgreSQL** (estado y filtros rápidos) y **ClickHouse** (analítica de millones de registros).

### 📊 Observabilidad
- **Métricas Prometheus**: Endpoint en `:8082/metrics` con telemetría completa del sistema.
- **System Metrics (60s)**: Recolecta CPU, RAM y disco de cada servidor remoto vía SSH.
- **ClickHouse Analytics**: Motor optimizado para consultas agregadas históricas.
- **Docker Health Check**: Monitoreo automático del event loop. Si se bloquea, Docker puede reiniciar el contenedor.

### 📈 Analítica y Visualización (Grafana 12)
- **Dos dashboards preconfigurados**:
  - **WMC Dashboard**: Mapa mundial, latencia, fuentes de tráfico, bots, desglose por navegador/OS/dispositivo.
  - **🛡️ WMC Security Center**: Mapa de ataques, Top 10 IPs amenaza, ancho de banda bots vs usuarios reales.
- **Mapa de Tráfico Animado**: Visualización 3D en vivo del flujo de tráfico (plugin `volkovlabs-echarts-panel`).
- **DNS Inverso**: Resuelve IPs a nombres de host (con caché).
- **Retención de Datos**: Limpieza automática de registros con más de 1 año.

---

## 🚀 Inicio Rápido (Docker Compose Local)

### Prerrequisitos
- Docker y Docker Compose instalados.
- Una cuenta gratuita en [MaxMind](https://www.maxmind.com/en/geolite2/signup) para obtener la base de datos GeoIP (se descarga automáticamente).

### Pasos

1. **Clona el repositorio**:
   ```bash
   git clone https://github.com/grs89/Web_Metrics_Collector.git
   cd Web_Metrics_Collector
   ```

2. **Configura el entorno**: Copia `.env.example` a `.env` y añade tu clave MaxMind:
   ```bash
   cp .env.example .env
   # Edita .env y rellena GEOIP_LICENSE_KEY=TU_CLAVE_AQUI
   ```

3. **Configura las llaves SSH**: Coloca tus llaves SSH privadas en la carpeta `keys/`.

4. **Configura los hosts**: Edita `hosts.yml` para definir tus servidores:
   ```yaml
   hosts:
     - name: "mi-servidor-web"
       host: "1.2.3.4"
       user: "root"
       key_path: "/ssh_keys/id_rsa"
       log_files:
         - path: "/var/log/nginx/access.log"
           type: "nginx-json"
         - path: "/var/log/nginx/error.log"
           type: "nginx-error"
         # Otros tipos: nginx-combined, apache-combined, iis, traefik, caddy, haproxy
   ```

5. **Levanta los servicios**:
   ```bash
   docker compose up -d --build
   ```

6. **Accede a Grafana**: Abre `http://localhost:3000` (Usuario: `admin` / Contraseña: `admin`).
   - **WMC Dashboard**: Analítica general de tráfico.
   - **🛡️ WMC Security Center**: Centro de mando de seguridad.

7. **Métricas internas (Prometheus)**: `http://localhost:8082/metrics`.

### ⚙️ Configuración del Dashboard
Para que la detección de **Hosts Sospechosos** funcione:
1. En el dashboard, busca la caja de texto **"Trusted Domain"** en la parte superior.
2. Escribe tu dominio principal (ej: `misitio.com`).
3. El panel "🚨 Suspicious Hosts" mostrará solo el tráfico que **NO** coincide con tu dominio.

---

## ➕ Formatos de Log Soportados

| Tipo (`hosts.yml`) | Servidor | Formato |
| :--- | :--- | :--- |
| `nginx-json` | Nginx | JSON estructurado (recomendado, incluye latencia) |
| `nginx-combined` | Nginx | Combined Log Format estándar |
| `nginx-error` | Nginx | Log de errores de Nginx |
| `apache-combined` | Apache | Combined Log Format estándar |
| `iis` | Microsoft IIS | W3C Extended Log Format |
| `traefik` | Traefik | JSON estructurado |
| `caddy` | Caddy | JSON estructurado |
| `haproxy` | HAProxy | HTTP Log Format estándar |
| `app` | Python/Node.js/PHP | Log de aplicación genérico |

---

## ➕ Incorporar un Nuevo Servidor

1. **Acceso SSH**: Asegúrate de tener acceso mediante llave pública SSH al servidor objetivo.
2. **Elige el formato** de la tabla de arriba y usa el `type` correspondiente en `hosts.yml`.
3. **Actualizar Configuración**: Agrega la entrada a `hosts.yml`.
4. **Reiniciar**:
   ```bash
   docker compose restart log-processor
   ```

---

## 🔁 CI/CD y Publicación de Imagen

El pipeline de CI/CD está implementado con **GitHub Actions** y publica la imagen automáticamente en **Docker Hub**.

### Flujo de trabajo (`docker-publish.yml`)

| Disparador | Acción |
| :--- | :--- |
| `push` de un tag `v*.*.*` | Build, Scan (Trivy) y Push a Docker Hub |
| `workflow_dispatch` | Ejecución manual desde GitHub |

El workflow reutiliza la plantilla `grs89/github-template/.github/workflows/docker-build_push_auto.yml@v2`.

### Secretos requeridos en el repositorio GitHub

| Secreto | Descripción |
| :--- | :--- |
| `DOCKERHUB_TOKEN` | Token de acceso de Docker Hub |
| `DOCKERHUB_USERNAME` | Usuario de Docker Hub |
| `DOCKERHUB_REPO` | Nombre del repositorio en Docker Hub |

### Publicar una nueva versión

```bash
git tag v1.0.3 && git push origin v1.0.3
```

---

## ☁️ Despliegue en Producción (Kubernetes)

Los manifiestos se encuentran en `k8s/` y se gestionan con **Kustomize**.

| Archivo | Descripción |
| :--- | :--- |
| `kustomization.yaml` | Punto de entrada de Kustomize |
| `log_processor.yaml` | Deployment del procesador de logs |
| `postgres.yaml` | StatefulSet de PostgreSQL |
| `grafana.yaml` | Deployment de Grafana |
| `coredns.yaml` | ConfigMap para resolución DNS interna |
| `ingress.yaml` | Ingress para exponer Grafana |
| `secrets-example.yaml` | Plantilla de secretos (SSH keys, credenciales) |

### Pasos de despliegue

1. Actualiza `k8s/kustomization.yaml` y `k8s/log_processor.yaml` con tu configuración de hosts.
2. Crea los secretos para las llaves SSH y credenciales de base de datos:
   ```bash
   # Copia y adapta el ejemplo
   cp k8s/secrets-example.yaml k8s/secrets.yaml
   ```
3. Aplica con Kustomize:
   ```bash
   kubectl apply -k k8s/
   ```

---

## 🏗️ Arquitectura

Para una visión técnica detallada de los componentes, flujo de datos, estrategia de almacenamiento dual y observabilidad, consulta [ARCHITECTURE.MD](ARCHITECTURE.MD).

### Stack Tecnológico

| Categoría | Tecnología |
| :--- | :--- |
| **Lenguaje** | Python 3.12 (Asíncrono, `asyncio`) |
| **Bases de Datos** | PostgreSQL 16 & ClickHouse |
| **Networking** | `asyncssh` & `asyncpg` & `clickhouse-connect` |
| **Geolocalización** | MaxMind GeoLite2 (descarga automática) |
| **Visualización** | Grafana 12.0 |
| **Observabilidad** | Prometheus Client |
| **Contenedores** | Docker (multi-stage build, non-root user) |
| **Orquestación** | Kubernetes + Kustomize |
| **CI/CD** | GitHub Actions → Docker Hub |

---

# 🌐 Web Metrics Collector (WMC) - Português

[🇪🇸 Español](#web-metrics-collector-wmc)

O WMC é um sistema centralizado de monitoramento de logs que visualiza o tráfego da web geograficamente e por volume. Conecta-se a servidores remotos via SSH, analisa os logs, enriquece-os com dados GeoIP e os armazena no PostgreSQL e ClickHouse para visualização no Grafana.

![Dashboard Screenshot](docs/images/dashboard_screenshot.png)

---

## 📋 Tabela de Conteúdos

- [✨ Funcionalidades](#-funcionalidades)
- [🚀 Início Rápido (Docker Compose)](#-início-rápido-docker-compose-local)
- [➕ Formatos de Log Suportados](#-formatos-de-log-suportados)
- [➕ Adicionando um Novo Servidor](#-adicionando-um-novo-servidor)
- [🔁 CI/CD e Publicação da Imagem](#-cicd-e-publicação-da-imagem)
- [☁️ Implantação em Produção (Kubernetes)](#️-implantação-em-produção-kubernetes)

---

## ✨ Funcionalidades

### 📡 Coleta Multi-Servidor
- **Sem Agentes**: Usa SSH para ler logs (sem instalação necessária em servidores remotos).
- **Formatos Suportados**: Nginx (JSON/CLF), Apache (Combined), IIS (W3C), **Traefik (JSON)**, **Caddy (JSON)**, **HAProxy**.
- **Multisuporte de Logs**: Suporte para `access.log`, `error.log` (Nginx) e logs de aplicações (`Python`, `Node.js`, `PHP`).

### 🛡️ Inteligência de Segurança
- **Detecção de Hosts Suspeitos**: Identifica clones (Phishing), scanners e configurações de DNS incorretas.
- **Detecção de Falso Googlebot**: Bloqueia IPs fingindo ser o Googlebot via Reverse DNS.
- **Fail2Ban Lite**: Banimento automático de IPs com atividade maliciosa.
- **Classificação de Bots**: Visualiza "Good Bots" (Google, Bing) vs "Bad Bots" (MJ12, Petal).
- **Monitor SSL**: Audita a data de expiração dos certificados a cada 12 horas.

### 🔁 Resiliência e Persistência
- **Persistência de Offsets**: Salva a posição de leitura em `data/state.json` para evitar perda ou duplicação de dados após reinicialização.
- **Buffer em Memória**: Fila interna `asyncio.Queue` (10.000 entradas) desacopla a ingestão do armazenamento.
- **Exponential Backoff (SSH e DB)**: Tentativas automáticas para conexões SSH e escritas no banco (1s → 2s → 4s → 8s → 16s).

### 📉 Inteligência de Dados
- **Detecção de Anomalias (Z-Score)**: Compara o tráfego em tempo real com a média histórica semanal para identificar picos ou quedas incomuns.
- **Categorização de Logs**: Coluna `log_category` diferenciando `access`, `error` e `app`.
- **Armazenamento Dual**: Os logs são salvos simultaneamente no **PostgreSQL** (estado e filtros rápidos) e **ClickHouse** (análise de milhões de registros).

### 📊 Observabilidade
- **Métricas Prometheus**: Endpoint em `:8082/metrics` com telemetria completa do sistema.
- **System Metrics (60s)**: Coleta CPU, RAM e disco de cada servidor remoto via SSH.
- **ClickHouse Analytics**: Motor otimizado para consultas agregadas históricas.
- **Docker Health Check**: Monitoramento automático do event loop. Se travar, o Docker pode reiniciar o container.

### 📈 Análise e Visualização (Grafana 12)
- **Dois dashboards pré-configurados**:
  - **WMC Dashboard**: Mapa mundial, latência, fontes de tráfego, bots, detalhamento por navegador/OS/dispositivo.
  - **🛡️ WMC Security Center**: Mapa de ataques, Top 10 IPs ameaça, largura de banda bots vs usuários reais.
- **Mapa de Tráfego Animado**: Visualização 3D ao vivo do fluxo de tráfego.
- **DNS Reverso**: Resolve IPs para nomes de host (com cache).
- **Retenção de Dados**: Limpeza automática de logs com mais de 1 ano.

---

## 🚀 Início Rápido (Docker Compose Local)

### Pré-requisitos
- Docker e Docker Compose instalados.
- Uma conta gratuita no [MaxMind](https://www.maxmind.com/en/geolite2/signup) para obter a base de dados GeoIP (baixada automaticamente).

### Passos

1. **Clone o repositório**:
   ```bash
   git clone https://github.com/grs89/Web_Metrics_Collector.git
   cd Web_Metrics_Collector
   ```

2. **Configure o ambiente**: Copie `.env.example` para `.env` e adicione sua chave MaxMind:
   ```bash
   cp .env.example .env
   # Edite .env e preencha GEOIP_LICENSE_KEY=SUA_CHAVE_AQUI
   ```

3. **Configure as chaves SSH**: Coloque suas chaves SSH privadas na pasta `keys/`.

4. **Configure os hosts**: Edite `hosts.yml` para definir seus servidores:
   ```yaml
   hosts:
     - name: "meu-servidor-web"
       host: "1.2.3.4"
       user: "root"
       key_path: "/ssh_keys/id_rsa"
       log_files:
         - path: "/var/log/nginx/access.log"
           type: "nginx-json"
   ```

5. **Suba os serviços**:
   ```bash
   docker compose up -d --build
   ```

6. **Acesse o Grafana**: Abra `http://localhost:3000` (Usuário: `admin` / Senha: `admin`).
   - **WMC Dashboard**: Análise geral de tráfego.
   - **🛡️ WMC Security Center**: Centro de comando de segurança.

7. **Métricas internas (Prometheus)**: `http://localhost:8082/metrics`.

### ⚙️ Configuração do Dashboard
Para que a detecção de **Hosts Suspeitos** funcione:
1. No dashboard, encontre a caixa de texto **"Trusted Domain"** no topo.
2. Digite seu domínio principal (ex: `meusite.com`).
3. O painel "🚨 Suspicious Hosts" mostrará apenas o tráfego que **NÃO** coincide com seu domínio.

---

## ➕ Formatos de Log Suportados

| Tipo (`hosts.yml`) | Servidor | Formato |
| :--- | :--- | :--- |
| `nginx-json` | Nginx | JSON estruturado (recomendado, inclui latência) |
| `nginx-combined` | Nginx | Combined Log Format padrão |
| `nginx-error` | Nginx | Log de erros do Nginx |
| `apache-combined` | Apache | Combined Log Format padrão |
| `iis` | Microsoft IIS | W3C Extended Log Format |
| `traefik` | Traefik | JSON estruturado |
| `caddy` | Caddy | JSON estruturado |
| `haproxy` | HAProxy | HTTP Log Format padrão |
| `app` | Python/Node.js/PHP | Log de aplicação genérico |

---

## ➕ Adicionando um Novo Servidor

1. **Acesso SSH**: Garanta acesso via chave pública SSH ao servidor de destino.
2. **Escolha o formato** da tabela de formatos e use o `type` correspondente no `hosts.yml`.
3. **Atualizar Configuração**: Adicione a entrada ao `hosts.yml`.
4. **Reiniciar**:
   ```bash
   docker compose restart log-processor
   ```

---

## 🔁 CI/CD e Publicação da Imagem

O pipeline de CI/CD é implementado com **GitHub Actions** e publica a imagem automaticamente no **Docker Hub**.

| Gatilho | Ação |
| :--- | :--- |
| `push` de uma tag `v*.*.*` | Build, Scan (Trivy) e Push para o Docker Hub |
| `workflow_dispatch` | Execução manual pelo GitHub |

### Publicar uma nova versão

```bash
git tag v1.0.3 && git push origin v1.0.3
```

---

## ☁️ Implantação em Produção (Kubernetes)

Os manifestos estão em `k8s/` e são gerenciados com **Kustomize**.

1. Atualize `k8s/kustomization.yaml` com sua configuração de hosts.
2. Crie os segredos para as chaves SSH e credenciais de banco de dados.
3. Aplique:
   ```bash
   kubectl apply -k k8s/
   ```
