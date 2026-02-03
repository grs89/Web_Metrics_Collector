# Web Geo Profiler (WMC)

WMC is a centralized log monitoring system that visualizes web traffic geographically and by volume. It polls remote Nginx/Apache servers via SSH, parses logs, enriches them with GeoIP data, and stores them in PostgreSQL for visualization in Grafana.

## Features
- **Agentless**: Uses SSH to read logs (no install required on remote servers).
- **Enrichment**: Adds City/Country/Lat/Lon to every request.
- **Security Intelligence**:
  - **Fake Googlebot Detection**: Blocks IPs pretending to be Googlebot.
  - **Fail2Ban Lite**: Auto-bans IPs engaging in malicious activity.
  - **Threat Monitoring**: Visualizes SQLi, XSS, and error spikes.
- **Advanced Networking**:
  - **Reverse DNS**: Resolves IPs to Hostnames (cached).
  - **Animated Traffic Map**: Live 3D visualization of traffic flow.
- **Data Retention**: Auto-cleanup of logs older than 1 year.
- **Analytics**: Browser, OS, and Device breakdown.
- **Visualization**: Pre-configured Grafana Dashboard with Worldmap.
- **Support**: Nginx (JSON) and Apache (Combined Log Format).

## Quick Start (Local Docker Compose)

1. **Prerequisites**: Docker & Docker Compose.
2. **Setup SSH Keys**: Ensure you have SSH keys that can access your target servers. Mount them in `docker-compose.yml` or place in a folder.
3. **Configure Hosts**: Edit `hosts.yml` to define your servers.
   ```yaml
   hosts:
     - name: "my-web-server"
       host: "1.2.3.4"
       user: "root"
       key_path: "/ssh_keys/id_rsa" # Path inside the container
       log_files:
         - path: "/var/log/nginx/access.log"
           type: "nginx-json"
   ```
4. **GeoIP Database**: Place `GeoLite2-City.mmdb` in `log_processor/` (optional, but needed for maps).
5. **Run**:
   ```bash
   docker-compose up -d --build
   ```
6. **Access Grafana**: Open `http://localhost:3000` (User: `admin` / Password: `admin`). The dashboard "WMC Dashboard" is pre-loaded.

## Onboarding a New Server

To add a new server to the monitoring pool:

1. **SSH Access**: Ensure the machine running WMC has SSH public key access to the target server.
2. **Log Format**: 
   - If using **Nginx**, configure it to output JSON logs (recommended) or use standard combined.
   - If using **Apache**, ensure `Combined Log Format`.
3. **Update Config**: Add the entry to `hosts.yml` as shown above.
4. **Restart**: Restart the log processor container to pick up changes.
   ```bash
   docker-compose restart log-processor
   ```

## Production Deployment (Kubernetes)
Manifests are located in `k8s/`.
1. Update `k8s/configmap.yaml` (generated via Kustomize) with your real `hosts.yml`.
2. Create offsets/secrets for SSH keys.
3. Apply:
   ```bash
   kubectl apply -k k8s/
   ```
