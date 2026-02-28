import logging
import asyncio
import statistics
from datetime import datetime
from metrics import TRAFFIC_ANOMALY_SCORE, ANOMALIES_DETECTED_TOTAL

class AnomalyDetector:
    def __init__(self, storage):
        """
        storage: MultiStorage instance (specifically we need the ClickHouse part)
        """
        self.storage = storage
        self.ch_client = None
        
    def _ensure_ch_client(self):
        if not self.ch_client and self.storage.secondary:
            # ClickHouseStorage is usually the secondary
            if hasattr(self.storage.secondary, 'client'):
                self.ch_client = self.storage.secondary.client
            elif hasattr(self.storage.primary, 'client'):
                self.ch_client = self.storage.primary.client
        return self.ch_client

    async def check_anomalies(self, host_name):
        """
        Calculates the Z-Score for the current traffic compared to 
        the last 4 weeks at the same day/time.
        """
        if not self._ensure_ch_client():
            return

        try:
            # 1. Get current traffic (last 5 minutes)
            current_hits = await self._get_current_hits(host_name)
            
            # 2. Get historical line (same day of week, same hour window, last 4 weeks)
            history = await self._get_historical_hits(host_name)
            
            if len(history) < 2:
                logging.debug(f"[{host_name}] Not enough historical data for anomaly detection yet.")
                return

            avg = statistics.mean(history)
            std = statistics.stdev(history) if len(history) > 1 else 1
            
            # Avoid division by zero
            if std == 0: std = 1 
            
            z_score = (current_hits - avg) / std
            
            # Update Prometheus
            TRAFFIC_ANOMALY_SCORE.labels(host=host_name).set(z_score)
            
            if z_score > 3.0: # Serious anomaly (3 sigmas)
                logging.warning(f"🚨 ANOMALY DETECTED for {host_name}: Z-Score={z_score:.2f} (Current: {current_hits}, Avg: {avg:.2f})")
                ANOMALIES_DETECTED_TOTAL.labels(host=host_name).inc()
            elif z_score < -3.0:
                logging.warning(f"⚠️ LOW TRAFFIC ANOMALY for {host_name}: Z-Score={z_score:.2f} (Current: {current_hits}, Avg: {avg:.2f})")
                
        except Exception as e:
            logging.error(f"Error in anomaly detection for {host_name}: {e}")

    async def _get_current_hits(self, host_name):
        query = f"""
            SELECT count() 
            FROM web_access_logs 
            WHERE source_host = '{host_name}' 
            AND timestamp >= now() - INTERVAL 5 MINUTE
        """
        result = await asyncio.to_thread(self.ch_client.command, query)
        return int(result) if result else 0

    async def _get_historical_hits(self, host_name):
        """
        Gets hits for the same 5-minute window in previous weeks.
        """
        query = f"""
            SELECT count() as hits
            FROM web_access_logs
            WHERE source_host = '{host_name}'
            AND toDayOfWeek(timestamp) = toDayOfWeek(now())
            AND toHour(timestamp) = toHour(now())
            AND toMinute(timestamp) BETWEEN toMinute(now()) - 5 AND toMinute(now()) + 5
            AND timestamp < now() - INTERVAL 1 HOUR
            GROUP BY toStartOfInterval(timestamp, INTERVAL 5 MINUTE)
        """
        # Note: This query is a simplification. In a real prod env, 
        # we'd want exactly the same time window over the last 4 weeks.
        result = await asyncio.to_thread(self.ch_client.query, query)
        return [row[0] for row in result.result_rows] if result.result_rows else []
