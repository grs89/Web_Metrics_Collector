import socket
from functools import lru_cache
import logging

class DNSEnricher:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @lru_cache(maxsize=10000)
    def enrich(self, ip_address):
        """
        Resolves IP to hostname.
        Uses lru_cache to cache results in memory.
        """
        if not ip_address:
            return None

        try:
            # socket.gethostbyaddr returns (hostname, aliaslist, ipaddrlist)
            # We only want the hostname
            hostname, _, _ = socket.gethostbyaddr(ip_address)
            return hostname
        except socket.herror:
            # Host not found (NXDOMAIN) or other DNS error
            return None
        except Exception as e:
            # Network errors, timeouts, etc.
            # self.logger.debug(f"DNS resolution failed for {ip_address}: {e}")
            return None
