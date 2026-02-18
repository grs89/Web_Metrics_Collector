import pytest
import asyncio
from storage import LogStorage
from dns_enricher import DNSEnricher
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
class TestAsyncComponents:
    
    async def test_dns_enricher_async(self):
        enricher = DNSEnricher()
        # Mock asyncio get_running_loop().getnameinfo
        with patch('asyncio.get_running_loop') as mock_loop:
            mock_loop_instance = mock_loop.return_value
            mock_loop_instance.getnameinfo = AsyncMock(return_value=('googlebot.com', 'http'))
            
            hostname = await enricher.enrich("8.8.8.8")
            assert hostname == "googlebot.com"
            mock_loop_instance.getnameinfo.assert_called_once_with(("8.8.8.8", 0))

    async def test_log_storage_pool_logic(self):
        # We can't easily test the DB without a container, but we can test the pool initialization logic
        db_params = {'user': 'test', 'password': 'test', 'database': 'test', 'host': 'localhost'}
        storage = LogStorage(db_params)
        
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_pool:
            result = await storage.connect()
            assert result is True
            assert storage.pool is not None
            mock_pool.assert_called_once()
            
            await storage.close()
            assert storage.pool is None

    @pytest.mark.asyncio
    async def test_ssh_reader_connect_mock(self):
        host_cfg = {'host': 'localhost', 'user': 'test', 'key_path': '/tmp/key', 'name': 'test'}
        from ssh_client import SSHLogReader
        reader = SSHLogReader(host_cfg)
        
        with patch('asyncssh.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn
            
            connected = await reader.connect()
            assert connected is True
            assert reader.conn == mock_conn
            mock_connect.assert_called_once()
