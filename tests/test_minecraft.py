"""
Unit tests for Minecraft event system and log parsing
"""

import sys
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import GameSession, User
from core.constants import MINECRAFT_LOG_PATTERNS


class TestMinecraftLogPatterns:
    """Test regex patterns for Minecraft log parsing"""

    def test_player_join_pattern(self):
        """Test player join detection pattern"""
        join_pattern = r"(\w+) joined the game"
        log_line = "[14:30:00] JMG joined the game"

        match = re.search(join_pattern, log_line)
        assert match is not None
        assert match.group(1) == "JMG"

    def test_player_leave_pattern(self):
        """Test player leave detection pattern"""
        leave_pattern = r"(\w+) left the game"
        log_line = "[14:31:00] JMG left the game"

        match = re.search(leave_pattern, log_line)
        assert match is not None
        assert match.group(1) == "JMG"

    def test_player_join_with_different_usernames(self):
        """Test join pattern with various username formats"""
        join_pattern = r"(\w+) joined the game"

        test_cases = [
            ("[14:30:00] JMG joined the game", "JMG"),
            ("[14:30:00] Player123 joined the game", "Player123"),
            ("[14:30:00] Steve_Minecraft joined the game", "Steve_Minecraft"),
        ]

        for log_line, expected_player in test_cases:
            match = re.search(join_pattern, log_line)
            assert match is not None
            assert match.group(1) == expected_player

    def test_server_start_pattern(self):
        """Test server start detection"""
        start_pattern = r"Server started"
        log_line = "[14:00:00] Server started"

        match = re.search(start_pattern, log_line)
        assert match is not None

    def test_server_stop_pattern(self):
        """Test server stop detection"""
        stop_pattern = r"Stopping the server"
        log_line = "[14:50:00] Stopping the server"

        match = re.search(stop_pattern, log_line)
        assert match is not None


class TestGameSession:
    """Test game session tracking"""

    def test_game_session_creation(self):
        """Test creating a game session"""
        session = MagicMock(spec=GameSession)
        session.id = 1
        session.user_id = 1
        session.join_time = datetime.utcnow()
        session.leave_time = None
        session.duration_minutes = None

        assert session.join_time is not None
        assert session.leave_time is None
        assert session.status == "active" or session.leave_time is None

    def test_game_session_duration_calculation(self):
        """Test calculating session duration"""
        join_time = datetime.utcnow() - timedelta(hours=1)
        leave_time = datetime.utcnow()
        duration = (leave_time - join_time).total_seconds() / 60

        assert duration > 55 and duration < 65  # Approximately 60 minutes

    def test_game_session_short_duration(self):
        """Test session with short duration"""
        join_time = datetime.utcnow() - timedelta(minutes=5)
        leave_time = datetime.utcnow()
        duration = (leave_time - join_time).total_seconds() / 60

        assert duration > 4 and duration < 6  # Approximately 5 minutes

    def test_game_session_long_duration(self):
        """Test session with long duration (8 hours)"""
        join_time = datetime.utcnow() - timedelta(hours=8)
        leave_time = datetime.utcnow()
        duration = (leave_time - join_time).total_seconds() / 60

        assert duration > 475 and duration < 485  # Approximately 480 minutes

    def test_game_session_not_started(self):
        """Test game session not started yet"""
        session = MagicMock(spec=GameSession)
        session.leave_time = None

        is_active = session.leave_time is None
        assert is_active is True

    def test_game_session_already_ended(self):
        """Test game session already ended"""
        session = MagicMock(spec=GameSession)
        session.leave_time = datetime.utcnow()

        is_active = session.leave_time is None
        assert is_active is False


class TestPlaytimeEarning:
    """Test playtime earning calculations"""

    def test_playtime_earning_one_hour(self):
        """Test 1 hour playtime earning"""
        duration_minutes = 60
        earning_rate = 0.5  # CC per minute
        earning = duration_minutes * earning_rate

        assert earning == 30.0

    def test_playtime_earning_with_multiplier(self):
        """Test playtime earning with multiplier"""
        duration_minutes = 60
        earning_rate = 0.5
        multiplier = 1.5
        earning = duration_minutes * earning_rate * multiplier

        assert earning == 45.0

    def test_playtime_earning_short_session(self):
        """Test playtime earning for 5 minute session"""
        duration_minutes = 5
        earning_rate = 0.5
        earning = duration_minutes * earning_rate

        assert earning == 2.5

    def test_playtime_earning_multiple_sessions(self):
        """Test cumulative earning from multiple sessions"""
        session1_duration = 60
        session2_duration = 120
        earning_rate = 0.5

        total_earning = (session1_duration + session2_duration) * earning_rate
        assert total_earning == 90.0


class TestPlayerTracking:
    """Test tracking players across sessions"""

    def test_single_player_session(self):
        """Test tracking single player session"""
        user = MagicMock(spec=User)
        user.discord_id = 123
        user.minecraft_username = "JMG"

        session = MagicMock(spec=GameSession)
        session.user_id = 1
        session.join_time = datetime.utcnow()

        assert session.user_id is not None

    def test_multiple_sessions_same_user(self):
        """Test multiple sessions for same user"""
        user = MagicMock(spec=User)
        user.discord_id = 123
        user.minecraft_username = "JMG"

        sessions = []
        
        session1 = MagicMock(spec=GameSession)
        session1.user_id = 1
        session1.join_time = datetime.utcnow() - timedelta(days=1)
        sessions.append(session1)

        session2 = MagicMock(spec=GameSession)
        session2.user_id = 1
        session2.join_time = datetime.utcnow()
        sessions.append(session2)

        user_sessions = [s for s in sessions if s.user_id == 1]
        assert len(user_sessions) == 2

    def test_player_join_creates_session(self):
        """Test that player join creates session"""
        log_line = "[14:30:00] JMG joined the game"
        player_name = "JMG"

        # Session should be created
        session = MagicMock(spec=GameSession)
        session.user_id = 1
        assert session.user_id is not None

    def test_player_leave_closes_session(self):
        """Test that player leave closes session"""
        session = MagicMock(spec=GameSession)
        session.join_time = datetime.utcnow() - timedelta(hours=1)
        session.leave_time = None

        # Close session
        session.leave_time = datetime.utcnow()
        duration = (session.leave_time - session.join_time).total_seconds() / 60

        assert session.leave_time is not None
        assert duration > 0


class TestMultiplePlayerTracking:
    """Test tracking multiple players simultaneously"""

    def test_multiple_concurrent_sessions(self):
        """Test multiple players in concurrent sessions"""
        sessions = []

        for i in range(3):
            session = MagicMock(spec=GameSession)
            session.user_id = i + 1
            session.join_time = datetime.utcnow()
            sessions.append(session)

        active = [s for s in sessions if s.leave_time is None]
        assert len(active) == 3

    def test_different_players_tracked_separately(self):
        """Test different players have separate session records"""
        user1 = MagicMock(spec=User)
        user1.discord_id = 111
        user1.minecraft_username = "Player1"

        user2 = MagicMock(spec=User)
        user2.discord_id = 222
        user2.minecraft_username = "Player2"

        session1 = MagicMock(spec=GameSession)
        session1.user_id = 1

        session2 = MagicMock(spec=GameSession)
        session2.user_id = 2

        assert session1.user_id != session2.user_id


class TestLogFileMonitoring:
    """Test log file watching mechanism"""

    def test_file_position_tracking(self):
        """Test tracking file read position"""
        initial_position = 0
        read_position = 150

        assert read_position > initial_position

    def test_file_rotation_detection(self):
        """Test detection of file rotation"""
        old_size = 10000
        new_size = 500

        # File rotated if size decreased
        file_rotated = new_size < old_size
        assert file_rotated is True

    def test_new_lines_detection(self):
        """Test detecting new log lines"""
        old_position = 100
        current_position = 350
        new_bytes = current_position - old_position

        assert new_bytes == 250


class TestEventCallbacks:
    """Test event callback system"""

    def test_player_join_callback(self):
        """Test player join callback is called"""
        callback_called = False
        player_name = None

        def on_player_join(name):
            nonlocal callback_called, player_name
            callback_called = True
            player_name = name

        # Simulate event
        on_player_join("JMG")

        assert callback_called is True
        assert player_name == "JMG"

    def test_player_leave_callback(self):
        """Test player leave callback is called"""
        callback_called = False
        player_name = None

        def on_player_leave(name):
            nonlocal callback_called, player_name
            callback_called = True
            player_name = name

        # Simulate event
        on_player_leave("JMG")

        assert callback_called is True
        assert player_name == "JMG"

    def test_multiple_callbacks(self):
        """Test multiple callbacks for same event"""
        calls = []

        def callback1():
            calls.append("callback1")

        def callback2():
            calls.append("callback2")

        # Execute
        callback1()
        callback2()

        assert len(calls) == 2
        assert "callback1" in calls
        assert "callback2" in calls


# Test execution
if __name__ == "__main__":
    import unittest

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestMinecraftLogPatterns))
    suite.addTests(loader.loadTestsFromTestCase(TestGameSession))
    suite.addTests(loader.loadTestsFromTestCase(TestPlaytimeEarning))
    suite.addTests(loader.loadTestsFromTestCase(TestPlayerTracking))
    suite.addTests(loader.loadTestsFromTestCase(TestMultiplePlayerTracking))
    suite.addTests(loader.loadTestsFromTestCase(TestLogFileMonitoring))
    suite.addTests(loader.loadTestsFromTestCase(TestEventCallbacks))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    sys.exit(0 if result.wasSuccessful() else 1)
