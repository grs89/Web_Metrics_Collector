# 🌐 Web Geo Profiler (WMC)

[🇧🇷 Português](#web-geo-profiler-wmc-português)

WMC es un sistema centralizado de monitoreo de registros que visualiza el tráfico web geográficamente y por volumen. Consulta servidores remotos Nginx/Apache vía SSH, analiza los registros, los enriquece con datos GeoIP y los almacena en PostgreSQL para su visualización en Grafana.

[![Docker Build (GitHub)](https://github.com/grs89/Web_Metrics_Collector/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/grs89/Web_Metrics_Collector/actions/workflows/docker-publish.yml)
[![Docker Hub](https://img.shields.io/docker/v/gersonofstone/web_metrics_collector?label=Docker%20Hub&logo=docker)](https://hub.docker.com/r/gersonofstone/web_metrics_collector)
[![Docker Pulls](https://img.shields.io/docker/pulls/gersonofstone/web_metrics_collector?logo=docker)](https://hub.docker.com/r/gersonofstone/web_metrics_collector)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

![Dashboard Screenshot](docs/images/dashboard_screenshot.png)

## ✨ Características
- **Sin Agentes**: Utiliza SSH para leer registros (no requiere instalación en servidores remotos).
- **Enriquecimiento**: Agrega Ciudad/País/Latitud/Longitud a cada petición.
- **Inteligencia de Seguridad**:
  - **🛡️ Detección de Hosts Sospechosos**: Identifica clones (Phishing), scanners y configuraciones DNS erróneas.
  - **Detección de Falsos Googlebot**: Bloqueia IPs que pretenden ser Googlebot.
  - **Fail2Ban Lite**: Bloqueo automático de IPs con actividad maliciosa.
  - **Monitoreo de Amenazas**: Visualiza picos de SQLi, XSS y errores.
  - **Clasificación de Bots**: Visualiza "Good Bots" (Google, Bing) vs "Bad Bots" (MJ12, Petal).
- **Rendimiento**:
  - **⏱️ Monitoreo de Latencia**: Tiempos de respuesta promedio por minuto.
- **Redes Avanzadas**:
  - **DNS Inverso**: Resuelve IPs a nombres de host (con caché).
  - **Mapa de Tráfico Animado**: Visualización 3D en vivo del flujo de tráfico.
- **Retención de Datos**: Limpieza automática de registros con más de 1 año.
- **Analítica de Tráfico**:
  - **Fuentes de Tráfico**: Desglose por referidos (Google, Directo, Redes Sociales).
  - **Usuarios Activos**: Conteo en tiempo real por sitio (vHost).
  - **Desglose Técnico**: Navegador, Sistema Operativo y Dispositivo.
- **Visualización**: Dashboard de Grafana preconfigurado con Mapa Mundial.
- **Soporte**: Nginx (JSON), Apache (Formato de Registro Combinado) y **Microsoft IIS** (W3C).

## 🚀 Inicio Rápido (Docker Compose Local)

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

### ⚙️ Configuración del Dashboard
Para que la detección de **Hosts Sospechosos** funcione correctamente:
1. En el dashboard, busca la caja de texto **"Trusted Domain"** en la parte superior.
2. Escribe tu dominio principal (ej: `misitio.com` o `google.com`).
3. El panel "🚨 Suspicious Hosts" se actualizará para mostrar solo el tráfico que **NO** coincide con tu dominio (posibles clones o ataques).


## ➕ Incorporar un Nuevo Servidor

Para agregar un nuevo servidor al pool de monitoreo:

1. **Acceso SSH**: Asegúrate de que la máquina que ejecuta WMC tenga acceso mediante llave pública SSH al servidor objetivo.
2. **Formato de Registro**:
   - Si usas **Nginx**, configúralo para generar registros JSON (recomendado, requerido para métricas de latencia) o usa el formato combinado estándar.
     > **Nota**: Para ver métricas de latencia, tu formato JSON necesita incluir `"request_time": "$request_time"`.
   - Si usas **Apache**, asegúrate de usar el `Combined Log Format`.
   - Si usas **IIS**:
     - Habilita **OpenSSH Server** en Windows.
     - Usa `type: "iis"` en `hosts.yml`.
     - El formato debe ser **W3C Standards** (por defecto en IIS).
3. **Actualizar Configuración**: Agrega la entrada a `hosts.yml` como se muestra arriba.
4. **Reiniciar**: Reinicia el contenedor del procesador de registros para aplicar los cambios.
   ```bash
   docker-compose restart log-processor
   ```

## ☁️ Despliegue en Producción (Kubernetes)
Los manifiestos se encuentran en `k8s/`.
1. Actualiza `k8s/configmap.yaml` (generado vía Kustomize) con tu `hosts.yml` real.
2. Crea offsets/secretos para las llaves SSH.
3. Aplica:
   ```bash
   kubectl apply -k k8s/
   ```

---

# 🌐 Web Geo Profiler (WMC) - Português

[🇪🇸 Español](#web-geo-profiler-wmc)

O WMC é um sistema centralizado de monitoramento de logs que visualiza o tráfego da web geograficamente e por volume. Ele consulta servidores remotos Nginx/Apache via SSH, analisa os logs, enriquece-os com dados GeoIP e os armazena no PostgreSQL para visualização no Grafana.

![Dashboard Screenshot](docs/images/dashboard_screenshot.png)

## ✨ Funcionalidades
- **Sem Agentes**: Usa SSH para ler logs (sem instalação necessária em servidores remotos).
- **Enriquecimento**: Adiciona Cidade/País/Lat/Lon a cada requisição.
- **Inteligência de Segurança**:
  - **🛡️ Detecção de Hosts Suspeitos**: Identifica clones (Phishing), scanners e configurações de DNS incorretas.
  - **Detecção de Falso Googlebot**: Bloqueia IPs fingindo ser o Googlebot.
  - **Fail2Ban Lite**: Banimento automático de IPs envolvidos em atividades maliciosas.
  - **Monitoramento de Ameaças**: Visualiza picos de SQLi, XSS e erros.
  - **Classificação de Bots**: Visualiza "Good Bots" (Google, Bing) vs "Bad Bots" (MJ12, Petal).
- **Desempenho**:
  - **⏱️ Monitoramento de Latência**: Tempos de resposta médios por minuto.
- **Redes Avançadas**:
  - **DNS Reverso**: Resolve IPs para nomes de host (com cache).
  - **Mapa de Tráfego Animado**: Visualização 3D ao vivo do fluxo de tráfego.
- **Retenção de Dados**: Limpeza automática de logs com mais de 1 ano.
- **Análise de Tráfego**:
  - **Fontes de Tráfego**: Detalhamento por referências (Google, Direto, Redes Sociais).
  - **Usuários Ativos**: Contagem em tempo real por site (vHost).
  - **Detalhamento Técnico**: Navegador, Sistema Operacional e Dispositivo.
- **Visualização**: Dashboard Grafana pré-configurado com Mapa Mundial.
- **Suporte**: Nginx (JSON), Apache (Formato de Log Combinado) e **Microsoft IIS** (W3C).

## 🚀 Início Rápido (Docker Compose Local)

1. **Pré-requisitos**: Docker e Docker Compose.
2. **Configurar Chaves SSH**: Garanta que você tenha chaves SSH que possam acessar seus servidores de destino. Monte-as no `docker-compose.yml` ou coloque-as em uma pasta.
3. **Configurar Hosts**: Edite `hosts.yml` para definir seus servidores.
   ```yaml
   hosts:
     - name: "meu-servidor-web"
       host: "1.2.3.4"
       user: "root"
       key_path: "/ssh_keys/id_rsa" # Caminho dentro do container
       log_files:
         - path: "/var/log/nginx/access.log"
           type: "nginx-json"
   ```
4. **Banco de Dados GeoIP**: Coloque `GeoLite2-City.mmdb` em `log_processor/` (opcional, mas necessário para mapas).
5. **Ejecutar**:
   ```bash
   docker-compose up -d --build
   ```
6. **Acessar o Grafana**: Abra `http://localhost:3000` (Usuário: `admin` / Senha: `admin`). O dashboard "WMC Dashboard" está pré-carregado.

### ⚙️ Configuração do Dashboard
Para que a detecção de **Hosts Suspeitos** funcione corretamente:
1. No dashboard, encontre a caixa de texto **"Trusted Domain"** no topo.
2. Digite seu domínio principal (ex: `meusite.com`).
3. O painel "🚨 Suspicious Hosts" será atualizado para mostrar apenas o tráfego que **NÃO** coincide com seu domínio (possíveis clones ou ataques).


## ➕ Adicionando um Novo Servidor

Para adicionar um novo servidor ao pool de monitoramento:

1. **Acesso SSH**: Garanta que a máquina rodando o WMC tenha acesso via chave pública SSH ao servidor de destino.
2. **Formato de Log**:
   - Se usar **Nginx**, configure-o para gerar logs JSON (recomendado, necessário para métricas de latência) o use o formato combinado padrão.
     > **Nota**: Para métricas de latência, seu formato JSON deve incluir `"request_time": "$request_time"`.
   - Se usar **Apache**, garanta o `Combined Log Format`.
   - Se usar **IIS**:
     - Habilite **OpenSSH Server** no Windows.
     - Use `type: "iis"` no `hosts.yml`.
     - O formato deve ser **W3C Standards** (padrão do IIS).
3. **Atualizar Configuração**: Adicione a entrada ao `hosts.yml` como mostrado acima.
4. **Reiniciar**: Reinicie o container do processador de logs para aplicar as alterações.
   ```bash
   docker-compose restart log-processor
   ```

## ☁️ Implantação em Produção (Kubernetes)
Os manifestos estão localizados em `k8s/`.
1. Atualize `k8s/configmap.yaml` (gerado via Kustomize) com seu `hosts.yml` real.
2. Crie offsets/segredos para as chaves SSH.
3. Aplique:
   ```bash
   kubectl apply -k k8s/
   ```
