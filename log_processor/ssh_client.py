import asyncssh
import logging
import asyncio
from metrics import SSH_CONNECTION_ATTEMPTS_TOTAL

class SSHLogReader:
    def __init__(self, host_config):
        self.host = host_config['host']
        self.port = int(host_config.get('port', 22))
        self.user = host_config['user']
        self.key_path = host_config['key_path']
        self.conn = None
        self.log_offsets = {} # Map file_path -> current_offset

    async def connect(self, retries=5, base_delay=1):
        for attempt in range(retries):
            try:
                if not self.conn:
                    self.conn = await asyncssh.connect(
                        self.host, 
                        port=self.port, 
                        username=self.user, 
                        client_keys=[self.key_path],
                        known_hosts=None
                    )
                    logging.info(f"Connected to {self.host} (asyncssh)")
                    SSH_CONNECTION_ATTEMPTS_TOTAL.labels(host=self.host, result="success").inc()
                return True
            except Exception as e:
                delay = base_delay * (2 ** attempt)
                logging.warning(f"Connection attempt {attempt + 1}/{retries} failed for {self.host}: {e}. Retrying in {delay}s...")
                SSH_CONNECTION_ATTEMPTS_TOTAL.labels(host=self.host, result="failure").inc()
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
                else:
                    logging.error(f"Final connection attempt failed for {self.host}")
                    return False
        return False

    async def read_updates(self, file_path):
        """
        Reads new content from file_path starting from the last known offset.
        Returns the new content and updates the offset.
        """
        if not self.conn and not await self.connect():
            return None

        offset = self.log_offsets.get(file_path, 0)
        
        try:
            # Check file size first to detect truncation (rotation)
            result = await self.conn.run(f"stat -c %s {file_path}", check=True)
            current_size = int(result.stdout.strip())
            
            if current_size < offset:
                logging.info(f"File {file_path} was rotated (size {current_size} < {offset}). Resetting offset.")
                offset = 0
            
            if current_size == offset:
                return "" # No new data

            # Read from offset
            # tail -c +K outputs bytes starting from K
            read_cmd = f"tail -c +{offset + 1} {file_path}"
            result = await self.conn.run(read_cmd, check=True)
            new_data_str = result.stdout
            # asyncssh stdout is already a string by default unless requested bytes
            
            if new_data_str:
                # We need the byte length for the offset update to be precise
                # but asyncssh might handle encoding. Let's ensure we get bytes for length.
                # Actually, asyncssh .run() with stdout encoded usually works fine.
                # For safety and precision with offsets, let's use byte length if possible.
                byte_len = len(new_data_str.encode('utf-8'))
                self.log_offsets[file_path] = offset + byte_len
                return new_data_str
            
            return ""

        except Exception as e:
            logging.error(f"Error reading {file_path} on {self.host}: {e}")
            self.conn = None # Force reconnect next time
            return None

    async def close(self):
        if self.conn:
            self.conn.close()
            await self.conn.wait_closed()
            self.conn = None
