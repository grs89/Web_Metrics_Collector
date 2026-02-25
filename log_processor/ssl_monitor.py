import ssl
import socket
import logging
import asyncio
from datetime import datetime
from prometheus_client import Gauge

# Metric definition
SSL_CERT_DAYS_REMAINING = Gauge(
    "wmc_ssl_cert_days_remaining",
    "Number of days until the SSL certificate expires",
    ["domain"]
)

class SSLMonitor:
    def __init__(self, hosts_cfg):
        self.hosts_cfg = hosts_cfg

    async def check_all(self):
        """Checks SSL status for all unique domains found in vHosts or hostnames."""
        domains = set()
        for host in self.hosts_cfg:
            # We assume the user might have domains in different places
            # For now, let's look at host names or if they have a 'domains' list
            if 'domains' in host:
                domains.update(host['domains'])
            elif '.' in host['host'] and not host['host'].replace('.', '').isdigit():
                domains.add(host['host'])
        
        if not domains:
            logging.info("No domains found for SSL monitoring.")
            return

        logging.info(f"Checking SSL for domains: {domains}")
        tasks = [self._check_domain(d) for d in domains]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_domain(self, domain):
        try:
            # Running SSL check in a thread to avoid blocking loop
            expiry_date = await asyncio.to_thread(self._get_expiry_date, domain)
            if expiry_date:
                remaining = (expiry_date - datetime.now()).days
                SSL_CERT_DAYS_REMAINING.labels(domain=domain).set(remaining)
                logging.info(f"SSL for {domain}: {remaining} days remaining")
        except Exception as e:
            logging.error(f"Error checking SSL for {domain}: {e}")

    def _get_expiry_date(self, domain):
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                # cert['notAfter'] is like 'Feb 15 12:00:00 2025 GMT'
                expiry_str = cert['notAfter']
                return datetime.strptime(expiry_str, '%b %d %H:%M:%S %Y %Z')
