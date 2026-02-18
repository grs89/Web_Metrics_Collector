import asyncio
import socket
from functools import lru_cache
import logging

class DNSEnricher:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # Keep the cache but we'll need a way to check it manually or use a wrapper
    @lru_cache(maxsize=10000)
    def _check_cache(self, ip_address):
        # This is a synchronous check for the cache
        # We can't easily wait for an async function in a sync cache
        # so we use this as a simple lookup
        return None

    async def enrich(self, ip_address):
        """
        Resolves IP to hostname using asyncio.
        """
        if not ip_address:
            return None

        # Simple mental cache check (lru_cache doesn't natively support async easily)
        # For now, we'll just do the async lookup as it's non-blocking
        try:
            loop = asyncio.get_running_loop()
            # getnameinfo is the async-friendly version of gethostbyaddr
            result = await loop.getnameinfo((ip_address, 0))
            # result is (hostname, service)
            return result[0]
        except Exception:
            return None
