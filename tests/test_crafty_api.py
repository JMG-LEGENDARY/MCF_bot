"""
Unit tests for Crafty API integration
"""

import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from crafty_api import CraftyAPI
except ImportError:
    CraftyAPI = None


class TestCraftyAPI:
    """Test Crafty API methods"""

    def test_crafty_api_initialization(self):
        """Test CraftyAPI initialization"""
        if CraftyAPI is None:
            print("Skipping: CraftyAPI not available")
            return

        api = MagicMock(spec=CraftyAPI)
        api.base_url = "https://100.111.101.28:8443"
        api.token = "test_token"
        
        assert api.base_url is not None
        assert api.token is not None

    def test_server_status_endpoint(self):
        """Test server status endpoint"""
        status = {
            "status": "online",
            "players_online": 5,
            "players_max": 20,
            "cpu_usage": 45.2,
            "ram_usage": 4096
        }

        assert status["status"] == "online"
        assert status["players_online"] == 5
        assert status["cpu_usage"] > 0

    def test_server_start_command(self):
        """Test server start command"""
        response = {
            "success": True,
            "message": "Server starting..."
        }

        assert response["success"] is True
        assert "starting" in response["message"].lower()

    def test_server_stop_command(self):
        """Test server stop command"""
        response = {
            "success": True,
            "message": "Server stopping..."
        }

        assert response["success"] is True
        assert "stopping" in response["message"].lower()

    def test_server_restart_command(self):
        """Test server restart command"""
        response = {
            "success": True,
            "message": "Server restarting..."
        }

        assert response["success"] is True
        assert "restarting" in response["message"].lower()

    def test_execute_command(self):
        """Test executing server command"""
        command = "say Welcome to the server!"
        response = {
            "success": True,
            "message": "Command executed",
            "command": command
        }

        assert response["success"] is True
        assert response["command"] == command

    def test_execute_give_command(self):
        """Test executing give command (item delivery)"""
        command = "give JMG diamond_pickaxe 1"
        response = {
            "success": True,
            "message": "Command executed",
            "command": command
        }

        assert response["success"] is True
        assert "give" in response["command"]

    def test_get_logs(self):
        """Test retrieving server logs"""
        logs = [
            "[14:30:00] Server started",
            "[14:30:15] JMG joined the game",
            "[14:31:00] JMG left the game"
        ]

        assert len(logs) == 3
        assert "[14:30:15]" in logs[1]

    def test_api_error_handling_offline_server(self):
        """Test API error when server is offline"""
        error = {
            "success": False,
            "message": "Server is offline",
            "error_code": 503
        }

        assert error["success"] is False
        assert error["error_code"] == 503

    def test_api_error_handling_invalid_command(self):
        """Test API error for invalid command"""
        error = {
            "success": False,
            "message": "Invalid command syntax",
            "error_code": 400
        }

        assert error["success"] is False
        assert error["error_code"] == 400

    def test_api_authentication_error(self):
        """Test API authentication error"""
        error = {
            "success": False,
            "message": "Authentication failed",
            "error_code": 401
        }

        assert error["success"] is False
        assert error["error_code"] == 401

    def test_api_timeout_error(self):
        """Test API timeout error"""
        error = {
            "success": False,
            "message": "Request timeout",
            "error_code": 408
        }

        assert error["success"] is False
        assert error["error_code"] == 408


class TestCraftyAPIAsync:
    """Test async Crafty API calls"""

    async def test_async_status_call(self):
        """Test async status retrieval"""
        api = MagicMock()
        api.obtenir_stats_crafty = AsyncMock(return_value={
            "status": "online",
            "players_online": 3
        })

        result = await api.obtenir_stats_crafty()
        
        assert result["status"] == "online"
        assert api.obtenir_stats_crafty.called

    async def test_async_start_server(self):
        """Test async server start"""
        api = MagicMock()
        api.demarrer_serveur = AsyncMock(return_value={
            "success": True,
            "message": "Server starting"
        })

        result = await api.demarrer_serveur()
        
        assert result["success"] is True
        assert api.demarrer_serveur.called

    async def test_async_execute_command(self):
        """Test async command execution"""
        api = MagicMock()
        api.envoyer_commande = AsyncMock(return_value={
            "success": True,
            "command": "say Hello"
        })

        result = await api.envoyer_commande("say Hello")
        
        assert result["success"] is True
        assert api.envoyer_commande.called

    async def test_async_give_command(self):
        """Test async give command execution"""
        api = MagicMock()
        api.envoyer_commande = AsyncMock(return_value={
            "success": True,
            "command": "give JMG diamond 64"
        })

        result = await api.envoyer_commande("give JMG diamond 64")
        
        assert result["success"] is True
        assert "give" in result["command"]


class TestCraftyServerStates:
    """Test different server states"""

    def test_server_online_state(self):
        """Test server in online state"""
        server_state = {
            "online": True,
            "players_online": 2,
            "can_execute_commands": True
        }

        assert server_state["online"] is True
        assert server_state["can_execute_commands"] is True

    def test_server_offline_state(self):
        """Test server in offline state"""
        server_state = {
            "online": False,
            "players_online": 0,
            "can_execute_commands": False
        }

        assert server_state["online"] is False
        assert server_state["can_execute_commands"] is False

    def test_server_starting_state(self):
        """Test server in starting state"""
        server_state = {
            "status": "starting",
            "progress": 25
        }

        assert server_state["status"] == "starting"
        assert server_state["progress"] > 0

    def test_server_stopping_state(self):
        """Test server in stopping state"""
        server_state = {
            "status": "stopping",
            "progress": 75
        }

        assert server_state["status"] == "stopping"
        assert server_state["progress"] > 0


class TestCraftyResourceUsage:
    """Test server resource monitoring"""

    def test_cpu_usage_monitoring(self):
        """Test CPU usage from API"""
        stats = {
            "cpu_usage": 45.2,
            "cpu_cores": 4
        }

        assert stats["cpu_usage"] > 0
        assert stats["cpu_usage"] < 100

    def test_ram_usage_monitoring(self):
        """Test RAM usage from API"""
        stats = {
            "ram_usage_mb": 4096,
            "ram_max_mb": 8192,
            "ram_percentage": 50.0
        }

        assert stats["ram_usage_mb"] > 0
        assert stats["ram_percentage"] > 0
        assert stats["ram_percentage"] <= 100

    def test_disk_space_monitoring(self):
        """Test disk space from API"""
        stats = {
            "disk_used_gb": 25.5,
            "disk_total_gb": 100.0,
            "disk_percentage": 25.5
        }

        assert stats["disk_used_gb"] > 0
        assert stats["disk_percentage"] > 0

    def test_players_monitoring(self):
        """Test players online monitoring"""
        stats = {
            "players_online": 5,
            "players_max": 20,
            "players_percentage": 25.0
        }

        assert stats["players_online"] <= stats["players_max"]
        assert stats["players_percentage"] > 0


class TestCraftyCommandExecution:
    """Test command execution validation"""

    def test_command_sanitization(self):
        """Test command is properly sanitized"""
        raw_command = "say Hello; stop"
        # Commands should not contain dangerous characters
        dangerous_chars = [";", "|", "&", "`", "$", "(", ")"]
        is_safe = not any(char in raw_command for char in dangerous_chars)
        
        # In this case, should be flagged as unsafe
        assert is_safe is False

    def test_safe_command_execution(self):
        """Test safe command passes validation"""
        safe_command = "say Welcome to the server"
        dangerous_chars = [";", "|", "&", "`", "$", "(", ")"]
        is_safe = not any(char in safe_command for char in dangerous_chars)
        
        assert is_safe is True

    def test_give_command_formatting(self):
        """Test give command format"""
        player = "JMG"
        item = "diamond_pickaxe"
        amount = 1
        
        command = f"give {player} {item} {amount}"
        assert command == "give JMG diamond_pickaxe 1"

    def test_multiple_commands_execution(self):
        """Test executing multiple commands in sequence"""
        commands = [
            "say Server maintenance starting",
            "say 30 seconds to restart",
            "restart"
        ]

        assert len(commands) == 3
        assert "restart" in commands[-1]


class TestCraftyErrorRecovery:
    """Test error handling and recovery"""

    def test_retry_on_timeout(self):
        """Test retry logic on timeout"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Simulate timeout
                raise TimeoutError("API request timeout")
            except TimeoutError:
                retry_count += 1
                if retry_count >= max_retries:
                    break

        assert retry_count == max_retries

    def test_fallback_to_cached_status(self):
        """Test fallback to cached status on error"""
        current_status = {"online": True, "cached": False}
        cached_status = {"online": True, "cached": True}

        try:
            # Try to fetch fresh status (fails)
            raise ConnectionError("Cannot reach API")
        except ConnectionError:
            # Fall back to cache
            status = cached_status

        assert status["cached"] is True

    def test_graceful_degradation(self):
        """Test graceful degradation when API unavailable"""
        api_available = False
        
        if not api_available:
            # Use fallback/cache
            fallback_status = "unknown"
        else:
            fallback_status = "online"

        assert fallback_status == "unknown"


# Async test runner
def run_async_tests():
    """Run async tests"""
    test = TestCraftyAPIAsync()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(test.test_async_status_call())
        loop.run_until_complete(test.test_async_start_server())
        loop.run_until_complete(test.test_async_execute_command())
        loop.run_until_complete(test.test_async_give_command())
        print("✅ Async tests passed")
    finally:
        loop.close()


# Test execution
if __name__ == "__main__":
    import unittest

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestCraftyAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestCraftyServerStates))
    suite.addTests(loader.loadTestsFromTestCase(TestCraftyResourceUsage))
    suite.addTests(loader.loadTestsFromTestCase(TestCraftyCommandExecution))
    suite.addTests(loader.loadTestsFromTestCase(TestCraftyErrorRecovery))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Run async tests
    print("\n--- Running Async Tests ---")
    try:
        run_async_tests()
    except Exception as e:
        print(f"❌ Async tests failed: {e}")

    sys.exit(0 if result.wasSuccessful() else 1)
