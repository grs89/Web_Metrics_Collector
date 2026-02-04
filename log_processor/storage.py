import psycopg2
from psycopg2.extras import execute_batch
import logging
import time

class LogStorage:
    def __init__(self, db_params):
        self.db_params = db_params
        self.conn = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(**self.db_params)
            logging.info("Connected to PostgreSQL")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to DB: {e}")
            return False

    def save_logs(self, logs):
        if not logs:
            return

        if not self.conn or self.conn.closed:
            if not self.connect():
                return

        sql = """
            INSERT INTO web_access_logs (
                timestamp, source_host, client_ip, hostname, method, uri, 
                status_code, response_size, user_agent, browser, os, device, is_fake_bot, referrer,
                country_code, city, latitude, longitude, 
                server_type, raw_log,
                request_time_ms, bot_category
            ) VALUES (
                %(timestamp)s, %(source_host)s, %(client_ip)s, %(hostname)s, %(method)s, %(uri)s,
                %(status_code)s, %(response_size)s, %(user_agent)s, %(browser)s, %(os)s, %(device)s, %(is_fake_bot)s, %(referrer)s,
                %(country_code)s, %(city)s, %(latitude)s, %(longitude)s,
                %(server_type)s, %(raw_log)s,
                %(request_time_ms)s, %(bot_category)s
            )
        """
        
        try:
            with self.conn.cursor() as cur:
                execute_batch(cur, sql, logs)
                self.conn.commit()
                logging.info(f"Saved {len(logs)} logs")
        except Exception as e:
            logging.error(f"Failed to save batch: {e}")
            self.conn.rollback()

    def block_ip(self, ip_address, reason):
        if not self.conn or self.conn.closed:
            if not self.connect():
                return

        sql = """
            INSERT INTO blocked_ips (ip_address, reason)
            VALUES (%s, %s)
            ON CONFLICT (ip_address) DO NOTHING
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, (ip_address, reason))
                self.conn.commit()
                logging.info(f"BLOCKED IP: {ip_address} Reason: {reason}")
        except Exception as e:
            logging.error(f"Failed to block IP {ip_address}: {e}")
            self.conn.rollback()

    def cleanup_old_logs(self, retention_days=365):
        if not self.conn or self.conn.closed:
            if not self.connect():
                return

        sql = "DELETE FROM web_access_logs WHERE timestamp < NOW() - INTERVAL '%s days'"
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, (retention_days,))
                deleted_count = cur.rowcount
                self.conn.commit()
                if deleted_count > 0:
                    logging.info(f"Data Retention: Cleaned up {deleted_count} logs older than {retention_days} days.")
                else:
                    logging.info(f"Data Retention: No logs older than {retention_days} days found.")
        except Exception as e:
            logging.error(f"Failed to cleanup old logs: {e}")
            self.conn.rollback()
