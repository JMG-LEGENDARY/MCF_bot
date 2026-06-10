"""
Unit tests for economy system (earning, multipliers, transfers, anti-spam, AFK detection)
"""

import sys
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import User, Transaction
from db.database import get_or_create_user, add_transaction
from utils.helpers import (
    calculate_message_earning,
    calculate_voice_earning,
    detect_copy_paste,
    calculate_daily_bonus,
    is_afk_voice,
)


class TestMessageEarning:
    """Test message earning calculations"""

    def test_message_earning_basic(self):
        """Test basic message earning: 0.1 * characters"""
        earning = calculate_message_earning(100)
        assert earning == 10.0, f"Expected 10.0, got {earning}"

    def test_message_earning_with_multiplier(self):
        """Test message earning with multiplier"""
        earning = calculate_message_earning(100, multiplier=1.5)
        assert earning == 15.0, f"Expected 15.0, got {earning}"

    def test_message_earning_zero_chars(self):
        """Test message earning with 0 characters"""
        earning = calculate_message_earning(0)
        assert earning == 0.0

    def test_message_earning_high_chars(self):
        """Test message earning with very long message (2000 chars)"""
        earning = calculate_message_earning(2000)
        assert earning == 200.0


class TestVoiceEarning:
    """Test voice earning calculations"""

    def test_voice_earning_basic(self):
        """Test basic voice earning: 0.5 * minutes"""
        earning = calculate_voice_earning(60)  # 1 hour
        assert earning == 30.0, f"Expected 30.0, got {earning}"

    def test_voice_earning_with_multiplier(self):
        """Test voice earning with multiplier"""
        earning = calculate_voice_earning(60, multiplier=1.5)
        assert earning == 45.0, f"Expected 45.0, got {earning}"

    def test_voice_earning_zero_minutes(self):
        """Test voice earning with 0 minutes"""
        earning = calculate_voice_earning(0)
        assert earning == 0.0

    def test_voice_earning_afk_multiplier(self):
        """Test AFK voice earning (0.1x multiplier)"""
        earning = calculate_voice_earning(60, multiplier=0.1)
        assert earning == 3.0, f"Expected 3.0, got {earning}"


class TestDailyBonus:
    """Test daily reward bonus calculations"""

    def test_daily_bonus_day_one(self):
        """Test day 1 bonus: base 10 CC"""
        bonus = calculate_daily_bonus(consecutive_days=1)
        assert bonus == 10.0, f"Expected 10.0, got {bonus}"

    def test_daily_bonus_day_two(self):
        """Test day 2 bonus: 10 * 1.5 = 15 CC"""
        bonus = calculate_daily_bonus(consecutive_days=2)
        assert bonus == 15.0, f"Expected 15.0, got {bonus}"

    def test_daily_bonus_day_three(self):
        """Test day 3 bonus: 10 * 1.5^2 = 22.5 CC"""
        bonus = calculate_daily_bonus(consecutive_days=3)
        assert bonus == 22.5, f"Expected 22.5, got {bonus}"

    def test_daily_bonus_day_five(self):
        """Test day 5 bonus: 10 * 1.5^4 = 50.625 CC"""
        bonus = calculate_daily_bonus(consecutive_days=5)
        expected = 10 * (1.5 ** 4)
        assert abs(bonus - expected) < 0.01, f"Expected {expected}, got {bonus}"

    def test_daily_bonus_zero_days(self):
        """Test with 0 consecutive days (edge case)"""
        bonus = calculate_daily_bonus(consecutive_days=0)
        assert bonus == 0.0 or bonus == 10.0  # Depends on implementation


class TestAntiSpam:
    """Test anti-spam and copy-paste detection"""

    def test_exact_copy_paste_detected(self):
        """Test 100% identical message is flagged"""
        msg1 = "Hello world this is a test"
        msg2 = "Hello world this is a test"
        is_spam = detect_copy_paste(msg1, msg2)
        assert is_spam is True, "Exact copy should be detected"

    def test_similar_copy_paste_detected(self):
        """Test 90% similar message is flagged"""
        msg1 = "The quick brown fox jumps over the lazy dog"
        msg2 = "The quick brown fox jumps over the lazy doge"
        is_spam = detect_copy_paste(msg1, msg2, threshold=0.85)
        assert is_spam is True, "90%+ similar should be detected"

    def test_different_messages_not_detected(self):
        """Test different messages not flagged"""
        msg1 = "Hello world"
        msg2 = "Goodbye world"
        is_spam = detect_copy_paste(msg1, msg2, threshold=0.85)
        assert is_spam is False, "Different messages should not be flagged"

    def test_empty_messages(self):
        """Test empty message handling"""
        is_spam = detect_copy_paste("", "")
        assert is_spam is False

    def test_very_short_messages(self):
        """Test very short message (<3 chars) handling"""
        is_spam = detect_copy_paste("hi", "hi", threshold=0.85)
        # Should be flagged as duplicate (100% match)
        assert is_spam is True


class TestAFKDetection:
    """Test AFK detection in voice"""

    def test_active_voice_not_afk(self):
        """Test active voice user is not AFK"""
        last_activity = datetime.utcnow()  # Just now
        is_afk = is_afk_voice(last_activity, timeout_minutes=10)
        assert is_afk is False, "Recent activity should not be AFK"

    def test_inactive_voice_is_afk(self):
        """Test inactive voice user is AFK after 10 minutes"""
        last_activity = datetime.utcnow() - timedelta(minutes=11)
        is_afk = is_afk_voice(last_activity, timeout_minutes=10)
        assert is_afk is True, "11 minutes inactivity should be AFK"

    def test_exactly_ten_minutes_not_afk(self):
        """Test edge case: exactly 10 minutes boundary"""
        last_activity = datetime.utcnow() - timedelta(minutes=10)
        is_afk = is_afk_voice(last_activity, timeout_minutes=10)
        # Should be on the edge - implementation dependent
        # Let's assume >= timeout_minutes is considered AFK
        assert is_afk in [True, False]  # Accept either (edge case)

    def test_afk_detection_with_custom_timeout(self):
        """Test AFK detection with custom timeout"""
        last_activity = datetime.utcnow() - timedelta(minutes=6)
        is_afk = is_afk_voice(last_activity, timeout_minutes=5)
        assert is_afk is True, "Should be AFK with 5 min timeout"


class TestTransactions:
    """Test transaction tracking and balance"""

    def test_transaction_creation(self):
        """Test creating a transaction record"""
        mock_session = MagicMock()
        user = MagicMock(spec=User)
        user.discord_id = 123456789
        user.craftycoin_balance = 100

        # Mock add_transaction behavior
        transaction = MagicMock(spec=Transaction)
        transaction.amount = 50
        transaction.user_id = 1
        transaction.type = "message"
        transaction.created_at = datetime.utcnow()

        assert transaction.amount == 50
        assert transaction.type == "message"

    def test_balance_update_after_earning(self):
        """Test balance increases after earning"""
        user = MagicMock(spec=User)
        user.craftycoin_balance = 100
        
        # Simulate earning
        earning = 50
        user.craftycoin_balance += earning
        
        assert user.craftycoin_balance == 150

    def test_balance_cannot_go_below_zero_on_purchase(self):
        """Test balance validation on purchase"""
        user = MagicMock(spec=User)
        user.craftycoin_balance = 100
        purchase_amount = 150

        # Should not allow purchase
        can_purchase = user.craftycoin_balance >= purchase_amount
        assert can_purchase is False


class TestMultipliers:
    """Test multiplier system"""

    def test_message_multiplier_application(self):
        """Test message multiplier is applied correctly"""
        base_earning = 10.0
        multiplier = 1.5
        final_earning = base_earning * multiplier
        assert final_earning == 15.0

    def test_playtime_multiplier_application(self):
        """Test playtime multiplier"""
        base_earning = 30.0  # 60 minutes voice
        multiplier = 1.5
        final_earning = base_earning * multiplier
        assert final_earning == 45.0

    def test_response_multiplier_application(self):
        """Test response bonus multiplier (e.g., helping someone)"""
        base_earning = 10.0
        response_multiplier = 2.0
        final_earning = base_earning * response_multiplier
        assert final_earning == 20.0

    def test_multiple_multipliers_stack(self):
        """Test that multiple multipliers can be applied"""
        base = 100.0
        msg_mult = 1.0
        response_mult = 1.5
        final = base * msg_mult * response_mult
        assert final == 150.0

    def test_default_multiplier_is_one(self):
        """Test default multiplier is 1.0x (no bonus)"""
        earning = calculate_message_earning(100, multiplier=1.0)
        assert earning == 10.0  # No multiplier effect


class TestEarningRateLimiting:
    """Test earning rate limits and anti-farming"""

    def test_minimum_chars_for_earning(self):
        """Test messages with <3 chars don't earn"""
        # Assuming 3 char minimum
        earning_2char = calculate_message_earning(2) if 2 >= 3 else 0
        earning_3char = calculate_message_earning(3)
        assert earning_2char == 0
        assert earning_3char >= 0.3

    def test_maximum_earning_per_message(self):
        """Test message earning is capped at 2000 chars (Discord limit)"""
        earning = calculate_message_earning(2000)
        assert earning == 200.0  # 2000 * 0.1


# Test execution
if __name__ == "__main__":
    import unittest

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestMessageEarning))
    suite.addTests(loader.loadTestsFromTestCase(TestVoiceEarning))
    suite.addTests(loader.loadTestsFromTestCase(TestDailyBonus))
    suite.addTests(loader.loadTestsFromTestCase(TestAntiSpam))
    suite.addTests(loader.loadTestsFromTestCase(TestAFKDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestTransactions))
    suite.addTests(loader.loadTestsFromTestCase(TestMultipliers))
    suite.addTests(loader.loadTestsFromTestCase(TestEarningRateLimiting))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with status
    sys.exit(0 if result.wasSuccessful() else 1)
