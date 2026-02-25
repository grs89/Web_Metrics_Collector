import logging
import asyncio
from metrics import (
    HOST_CPU_USAGE, 
    HOST_MEMORY_USAGE, 
    HOST_DISK_USAGE, 
    HOST_LOAD_AVG
)

class SystemMetricsCollector:
    def __init__(self, host_cfg, reader):
        self.host_cfg = host_cfg
        self.reader = reader
        self.host_name = host_cfg['name']

    async def collect(self):
        """Collects all system metrics from the host."""
        logging.info(f"[{self.host_name}] Collecting system metrics...")
        
        # We run these concurrently for efficiency
        tasks = [
            self._collect_cpu_load(),
            self._collect_memory(),
            self._collect_disk()
        ]
        await asyncio.gather(*tasks)

    async def _collect_cpu_load(self):
        # Using /proc/loadavg for load and top for CPU usage
        # This is a bit complex to parse top, let's use a simpler way if possible
        # For CPU, we can use: grep 'cpu ' /proc/stat
        # But for now, let's keep it simple with loadavg
        load_out = await self.reader.run_command("cat /proc/loadavg")
        if load_out:
            try:
                load_1min = float(load_out.split()[0])
                HOST_LOAD_AVG.labels(host=self.host_name).set(load_1min)
            except (IndexError, ValueError):
                pass

        # CPU Usage (approximate via top)
        cpu_out = await self.reader.run_command("top -bn1 | grep 'Cpu(s)'")
        if cpu_out:
            try:
                # Example: %Cpu(s):  5.0 us,  2.5 sy,  0.0 ni, 92.5 id...
                idle = float(cpu_out.split('id')[0].split(',')[-1].strip())
                usage = 100.0 - idle
                HOST_CPU_USAGE.labels(host=self.host_name).set(usage)
            except (IndexError, ValueError):
                pass

    async def _collect_memory(self):
        mem_out = await self.reader.run_command("free | grep Mem")
        if mem_out:
            try:
                # Mem:          total        used        free      shared  buff/cache   available
                parts = mem_out.split()
                total = int(parts[1])
                available = int(parts[6])
                usage_pct = ((total - available) / total) * 100.0
                HOST_MEMORY_USAGE.labels(host=self.host_name).set(usage_pct)
            except (IndexError, ValueError, ZeroDivisionError):
                pass

    async def _collect_disk(self):
        disk_out = await self.reader.run_command("df -h / --output=pcent,target | tail -n 1")
        if disk_out:
            try:
                # 15% /
                parts = disk_out.split()
                pct = float(parts[0].replace('%', ''))
                mount = parts[1]
                HOST_DISK_USAGE.labels(host=self.host_name, mountpoint=mount).set(pct)
            except (IndexError, ValueError):
                pass
