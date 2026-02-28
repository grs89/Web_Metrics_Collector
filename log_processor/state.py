import json
import os
import logging
import asyncio

class StateManager:
    def __init__(self, state_file="/app/data/state.json"):
        self.state_file = state_file
        self.offsets = {} # host -> { file_path -> offset }
        self._lock = asyncio.Lock()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        logging.info(f"StateManager initialized with file: {self.state_file}")

    def load(self):
        """Loads offsets from the JSON file."""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        logging.info(f"Checking for state file at: {self.state_file}")
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    self.offsets = json.load(f)
                logging.info(f"Loaded offsets from {self.state_file}")
            except Exception as e:
                logging.error(f"Failed to load state file: {e}")
                self.offsets = {}
        else:
            logging.info("No state file found. Starting fresh.")
            self.offsets = {}
        return self.offsets

    async def save(self, current_offsets):
        """
        Atomically saves the current offsets to the JSON file.
        current_offsets: { host_name: { file_path: offset } }
        """
        async with self._lock:
            try:
                # Write to a temporary file first to avoid corruption
                temp_file = f"{self.state_file}.tmp"
                with open(temp_file, 'w') as f:
                    json.dump(current_offsets, f, indent=2)
                
                os.replace(temp_file, self.state_file)
                logging.info(f"Successfully saved {len(current_offsets)} host offsets to {self.state_file}")
            except Exception as e:
                logging.error(f"Failed to save state file: {e}")

    def get_host_offsets(self, host_name):
        """Returns the offsets for a specific host."""
        return self.offsets.get(host_name, {})
