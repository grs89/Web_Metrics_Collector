import asyncpg
import logging
import json

class LogStorage:
    def __init__(self, db_params):
        self.db_params = db_params
        self.pool = None

    async def connect(self):
        try:
            if not self.pool:
                # asyncpg uses slightly different param names or a DSN
                # Convert psycopg2 params to asyncpg compatible
                self.pool = await asyncpg.create_pool(
                    user=self.db_params.get('user'),
                    password=self.db_params.get('password'),
                    database=self.db_params.get('database'),
                    host=self.db_params.get('host'),
                    port=self.db_params.get('port', 5432),
                    min_size=5,
                    max_size=20
                )
                logging.info("Connected to PostgreSQL (asyncpg pool initialized)")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to DB: {e}")
            return False

    async def save_logs(self, logs):
        if not logs:
            return

        if not self.pool and not await self.connect():
            return

        # Prepare records for asyncpg executemany
        # asyncpg is much faster with executemany and positional arguments
        records = [
            (
                log.get('timestamp'), log.get('source_host'), log.get('client_ip'), 
                log.get('hostname'), log.get('method'), log.get('uri'), 
                log.get('status_code'), log.get('response_size'), log.get('user_agent'), 
                log.get('browser'), log.get('os'), log.get('device'), 
                log.get('is_fake_bot'), log.get('referrer'),
                log.get('country_code'), log.get('city'), 
                log.get('latitude'), log.get('longitude'), 
                log.get('server_type'), log.get('raw_log'),
                log.get('request_time_ms'), log.get('bot_category')
            ) for log in logs
        ]

        sql = """
            INSERT INTO web_access_logs (
                timestamp, source_host, client_ip, hostname, method, uri, 
                status_code, response_size, user_agent, browser, os, device, is_fake_bot, referrer,
                country_code, city, latitude, longitude, 
                server_type, raw_log,
                request_time_ms, bot_category
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22
            )
        """
        
        try:
            async with self.pool.acquire() as conn:
                await conn.executemany(sql, records)
                logging.info(f"Saved {len(logs)} logs")
        except Exception as e:
            logging.error(f"Failed to save batch: {e}")

    async def block_ip(self, ip_address, reason):
        if not self.pool and not await self.connect():
            return

        sql = """
            INSERT INTO blocked_ips (ip_address, reason)
            VALUES ($1, $2)
            ON CONFLICT (ip_address) DO NOTHING
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(sql, ip_address, reason)
                logging.info(f"BLOCKED IP: {ip_address} Reason: {reason}")
        except Exception as e:
            logging.error(f"Failed to block IP {ip_address}: {e}")

    async def cleanup_old_logs(self, retention_days=365):
        if not self.pool and not await self.connect():
            return

        # Use interval string safely with asyncpg
        sql = f"DELETE FROM web_access_logs WHERE timestamp < NOW() - INTERVAL '{retention_days} days'"
        
        try:
            async with self.pool.acquire() as conn:
                status = await conn.execute(sql)
                # status is something like "DELETE 10"
                logging.info(f"Data Retention: {status}")
        except Exception as e:
            logging.error(f"Failed to cleanup old logs: {e}")

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None
