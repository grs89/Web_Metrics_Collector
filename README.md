# 🌐 Web Geo Profiler (WMC)

[🇧🇷 Português](#web-geo-profiler-wmc-português)

WMC es un sistema centralizado de monitoreo de registros que visualiza el tráfico web geográficamente y por volumen. Consulta servidores remotos Nginx/Apache vía SSH, analiza los registros, los enriquece con datos GeoIP y los almacena en PostgreSQL para su visualización en Grafana.

![Dashboard Screenshot](docs/images/dashboard_screenshot.png)

## ✨ Características
- **Sin Agentes**: Utiliza SSH para leer registros (no requiere instalación en servidores remotos).
- **Enriquecimiento**: Agrega Ciudad/País/Latitud/Longitud a cada petición.
- **Inteligencia de Seguridad**:
  - **Detección de Falsos Googlebot**: Bloqueia IPs que pretenden ser Googlebot.
  - **Fail2Ban Lite**: Bloqueo automático de IPs con actividad maliciosa.
  - **Monitoreo de Amenazas**: Visualiza picos de SQLi, XSS y errores.
- **Redes Avanzadas**:
  - **DNS Inverso**: Resuelve IPs a nombres de host (con caché).
  - **Mapa de Tráfico Animado**: Visualización 3D en vivo del flujo de tráfico.
- **Retención de Datos**: Limpieza automática de registros con más de 1 año.
- **Analítica**: Desglose por Navegador, Sistema Operativo y Dispositivo.
- **Visualización**: Dashboard de Grafana preconfigurado con Mapa Mundial.
- **Soporte**: Nginx (JSON) y Apache (Formato de Registro Combinado).

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

## ➕ Incorporar un Nuevo Servidor

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
  - **Detecção de Falso Googlebot**: Bloqueia IPs fingindo ser o Googlebot.
  - **Fail2Ban Lite**: Banimento automático de IPs envolvidos em atividades maliciosas.
  - **Monitoramento de Ameaças**: Visualiza picos de SQLi, XSS e erros.
- **Redes Avançadas**:
  - **DNS Reverso**: Resolve IPs para nomes de host (com cache).
  - **Mapa de Tráfego Animado**: Visualização 3D ao vivo do fluxo de tráfego.
- **Retenção de Dados**: Limpieza automática de logs com mais de 1 ano.
- **Analytics**: Detalhamento por Navegador, Sistema Operacional e Dispositivo.
- **Visualização**: Dashboard Grafana pré-configurado com Mapa Mundial.
- **Suporte**: Nginx (JSON) e Apache (Formato de Log Combinado).

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

## ➕ Adicionando um Novo Servidor

Para adicionar um novo servidor ao pool de monitoramento:

1. **Acesso SSH**: Garanta que a máquina rodando o WMC tenha acesso via chave pública SSH ao servidor de destino.
2. **Formato de Log**:
   - Se usar **Nginx**, configure-o para gerar logs JSON (recomendado) o use o formato combinado padrão.
   - Se usar **Apache**, garanta o `Combined Log Format`.
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
