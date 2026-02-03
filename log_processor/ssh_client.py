import paramiko
import time
import logging

class SSHLogReader:
    def __init__(self, host_config):
        self.host = host_config['host']
        self.port = int(host_config.get('port', 22))
        self.user = host_config['user']
        self.key_path = host_config['key_path']
        self.client = None
        self.log_offsets = {} # Map file_path -> current_offset

    def connect(self):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            key = paramiko.RSAKey.from_private_key_file(self.key_path)
            self.client.connect(self.host, port=self.port, username=self.user, pkey=key, timeout=10)
            logging.info(f"Connected to {self.host}")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to {self.host}: {e}")
            return False

    def read_updates(self, file_path):
        """
        Reads new content from file_path starting from the last known offset.
        Returns the new content and updates the offset.
        """
        if not self.client and not self.connect():
            return None

        offset = self.log_offsets.get(file_path, 0)
        
        # Command to get current file size and content from offset
        # Using stat to get size, then tail if size > offset
        # Or simpler: just try to read from offset using dd or tail
        # tail -c +N outputs bytes starting from N (1-based index). 
        # So if offset is 0, we need +1. If offset is 100, we need +101.
        
        try:
            # Check file size first to detect truncation (rotation)
            check_cmd = f"stat -c %s {file_path}"
            _, stdout, _ = self.client.exec_command(check_cmd)
            current_size = int(stdout.read().decode().strip())
            
            if current_size < offset:
                logging.info(f"File {file_path} was rotated (size {current_size} < {offset}). Resetting offset.")
                offset = 0
            
            if current_size == offset:
                return "" # No new data

            # Read from offset
            # tail -c +K outputs bytes starting from K
            read_cmd = f"tail -c +{offset + 1} {file_path}"
            _, stdout, _ = self.client.exec_command(read_cmd)
            new_data = stdout.read() # Read binary to be safe, then decode
            
            if new_data:
                self.log_offsets[file_path] = offset + len(new_data)
                return new_data.decode('utf-8', errors='replace')
            
            return ""

        except Exception as e:
            logging.error(f"Error reading {file_path} on {self.host}: {e}")
            self.client = None # Force reconnect
            return None
