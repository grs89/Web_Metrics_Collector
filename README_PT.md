# Web Geo Profiler (WMC)

[Leer en Español](README.md)

O WMC é um sistema centralizado de monitoramento de logs que visualiza o tráfego da web geograficamente e por volume. Ele consulta servidores remotos Nginx/Apache via SSH, analisa os logs, enriquece-os com dados GeoIP e os armazena no PostgreSQL para visualização no Grafana.

![Dashboard Screenshot](docs/images/dashboard_screenshot.png)

## Funcionalidades
- **Sem Agentes**: Usa SSH para ler logs (sem instalação necessária em servidores remotos).
- **Enriquecimento**: Adiciona Cidade/País/Lat/Lon a cada requisição.
- **Inteligência de Segurança**:
  - **Detecção de Falso Googlebot**: Bloqueia IPs fingindo ser o Googlebot.
  - **Fail2Ban Lite**: Banimento automático de IPs envolvidos em atividades maliciosas.
  - **Monitoramento de Ameaças**: Visualiza picos de SQLi, XSS e erros.
- **Redes Avançadas**:
  - **DNS Reverso**: Resolve IPs para nomes de host (com cache).
  - **Mapa de Tráfego Animado**: Visualização 3D ao vivo do fluxo de tráfego.
- **Retenção de Dados**: Limpeza automática de logs com mais de 1 ano.
- **Analytics**: Detalhamento por Navegador, Sistema Operacional e Dispositivo.
- **Visualização**: Dashboard Grafana pré-configurado com Mapa Mundial.
- **Suporte**: Nginx (JSON) e Apache (Formato de Log Combinado).

## Início Rápido (Docker Compose Local)

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
5. **Executar**:
   ```bash
   docker-compose up -d --build
   ```
6. **Acessar o Grafana**: Abra `http://localhost:3000` (Usuário: `admin` / Senha: `admin`). O dashboard "WMC Dashboard" está pré-carregado.

## Adicionando um Novo Servidor

Para adicionar um novo servidor ao pool de monitoramento:

1. **Acesso SSH**: Garanta que a máquina rodando o WMC tenha acesso via chave pública SSH ao servidor de destino.
2. **Formato de Log**:
   - Se usar **Nginx**, configure-o para gerar logs JSON (recomendado) ou use o formato combinado padrão.
   - Se usar **Apache**, garanta o `Combined Log Format`.
3. **Atualizar Configuração**: Adicione a entrada ao `hosts.yml` como mostrado acima.
4. **Reiniciar**: Reinicie o container do processador de logs para aplicar as alterações.
   ```bash
   docker-compose restart log-processor
   ```

## Implantação em Produção (Kubernetes)
Os manifestos estão localizados em `k8s/`.
1. Atualize `k8s/configmap.yaml` (gerado via Kustomize) com seu `hosts.yml` real.
2. Crie offsets/segredos para as chaves SSH.
3. Aplique:
   ```bash
   kubectl apply -k k8s/
   ```
