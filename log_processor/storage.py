import asyncpg
import logging
import json
import clickhouse_connect
import asyncio

class PostgresStorage:
    def __init__(self, db_params):
        self.db_params = db_params
        self.pool = None

    async def connect(self):
        try:
            if not self.pool:
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
            logging.error(f"Failed to connect to Postgres: {e}")
            return False

    async def save_logs(self, logs):
        if not logs: return
        if not self.pool and not await self.connect(): return

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
                log.get('request_time_ms'), log.get('bot_category'),
                log.get('log_category', 'access')
            ) for log in logs
        ]

        sql = """
            INSERT INTO web_access_logs (
                timestamp, source_host, client_ip, hostname, method, uri, 
                status_code, response_size, user_agent, browser, os, device, is_fake_bot, referrer,
                country_code, city, latitude, longitude, 
                server_type, raw_log,
                request_time_ms, bot_category,
                log_category
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23
            )
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.executemany(sql, records)
                logging.info(f"Saved {len(logs)} logs to Postgres")
        except Exception as e:
            logging.error(f"Failed to save batch to Postgres: {e}")

    async def block_ip(self, ip_address, reason):
        if not self.pool and not await self.connect(): return
        sql = "INSERT INTO blocked_ips (ip_address, reason) VALUES ($1, $2) ON CONFLICT (ip_address) DO NOTHING"
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(sql, ip_address, reason)
                logging.info(f"BLOCKED IP (PG): {ip_address} Reason: {reason}")
        except Exception as e:
            logging.error(f"Failed to block IP in PG: {e}")

    async def cleanup_old_logs(self, retention_days=365):
        if not self.pool and not await self.connect(): return
        sql = f"DELETE FROM web_access_logs WHERE timestamp < NOW() - INTERVAL '{retention_days} days'"
        try:
            async with self.pool.acquire() as conn:
                status = await conn.execute(sql)
                logging.info(f"Postgres Data Retention: {status}")
        except Exception as e:
            logging.error(f"Failed to cleanup PG logs: {e}")

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None


class ClickHouseStorage:
    def __init__(self, ch_params):
        self.ch_params = ch_params
        self.client = None

    def connect(self):
        try:
            if not self.client:
                self.client = clickhouse_connect.get_client(
                    host=self.ch_params.get('host'),
                    port=self.ch_params.get('port', 8123),
                    username=self.ch_params.get('user'),
                    password=self.ch_params.get('password'),
                    database=self.ch_params.get('database')
                )
                logging.info("Connected to ClickHouse")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to ClickHouse: {e}")
            return False

    async def save_logs(self, logs):
        if not logs: return
        # ClickHouse client is mostly synchronous but fast, we wrap it
        if not self.client and not self.connect(): return

        data = []
        for log in logs:
            data.append([
                log.get('timestamp'), log.get('source_host'), log.get('client_ip'),
                log.get('hostname') or '', log.get('method') or '', log.get('uri') or '',
                int(log.get('status_code') or 0), int(log.get('response_size') or 0),
                float(log.get('request_time_ms') or 0),
                log.get('country_code') or '', log.get('city') or '',
                float(log.get('latitude') or 0.0), float(log.get('longitude') or 0.0),
                log.get('user_agent') or '', log.get('browser') or '',
                log.get('os') or '', log.get('device') or '', log.get('bot_category') or '',
                1 if log.get('is_fake_bot') else 0, log.get('referrer') or '',
                log.get('server_type') or '', log.get('log_category') or 'access',
                log.get('raw_log') or ''
            ])

        columns = [
            'timestamp', 'source_host', 'client_ip', 'hostname', 'method', 'uri',
            'status_code', 'response_size', 'request_time_ms',
            'country_code', 'city', 'latitude', 'longitude',
            'user_agent', 'browser', 'os', 'device', 'bot_category',
            'is_fake_bot', 'referrer', 'server_type', 'log_category', 'raw_log'
        ]

        try:
            await asyncio.to_thread(self.client.insert, 'web_access_logs', data, column_names=columns)
            logging.info(f"Saved {len(logs)} logs to ClickHouse")
        except Exception as e:
            logging.error(f"Failed to save batch to ClickHouse: {e}")

    async def cleanup_old_logs(self, retention_days=365):
        if not self.client and not self.connect(): return
        sql = f"ALTER TABLE web_access_logs DELETE WHERE timestamp < now() - INTERVAL {retention_days} DAY"
        try:
            await asyncio.to_thread(self.client.command, sql)
            logging.info(f"ClickHouse Data Retention: {retention_days} days clean up command sent.")
        except Exception as e:
            logging.error(f"Failed to cleanup CH logs: {e}")

    async def close(self):
        if self.client:
            await asyncio.to_thread(self.client.close)
            self.client = None


class MultiStorage:
    def __init__(self, primary, secondary=None):
        self.primary = primary
        self.secondary = secondary

    async def connect(self):
        res = await self.primary.connect()
        if self.secondary:
            # Secondary might be sync/async depending on implementation choice
            # but for now we call it
            if hasattr(self.secondary, 'connect'):
                if asyncio.iscoroutinefunction(self.secondary.connect):
                    await self.secondary.connect()
                else:
                    self.secondary.connect()
        return res

    async def save_logs(self, logs):
        tasks = [self.primary.save_logs(logs)]
        if self.secondary:
            tasks.append(self.secondary.save_logs(logs))
        await asyncio.gather(*tasks)

    async def block_ip(self, ip_address, reason):
        await self.primary.block_ip(ip_address, reason)

    async def cleanup_old_logs(self, retention_days=365):
        tasks = [self.primary.cleanup_old_logs(retention_days)]
        if self.secondary:
            tasks.append(self.secondary.cleanup_old_logs(retention_days))
        await asyncio.gather(*tasks)

    async def close(self):
        await self.primary.close()
        if self.secondary:
            await self.secondary.close()

# For backward compatibility and ease of use in main.py
LogStorage = MultiStorage
