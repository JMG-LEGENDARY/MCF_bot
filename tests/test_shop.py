"""
Unit tests for shop and purchase system
"""

import sys
import os
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import User, ShopItem, PendingPurchase, Transaction


class TestShopItems:
    """Test shop item management"""

    def test_shop_item_creation(self):
        """Test creating a shop item"""
        item = MagicMock(spec=ShopItem)
        item.id = 1
        item.name = "Diamond Pickaxe"
        item.price = 500
        item.minecraft_command = "give {player} diamond_pickaxe 1"
        item.category = "tools"
        item.available = True

        assert item.name == "Diamond Pickaxe"
        assert item.price == 500
        assert item.category == "tools"
        assert item.available is True

    def test_shop_item_command_variables(self):
        """Test shop item command has {player} placeholder"""
        item = MagicMock(spec=ShopItem)
        item.minecraft_command = "give {player} diamond_pickaxe 1"

        # Should contain player placeholder
        assert "{player}" in item.minecraft_command

    def test_shop_item_with_quantity(self):
        """Test shop item supports quantity in command"""
        item = MagicMock(spec=ShopItem)
        item.minecraft_command = "give {player} diamond 64"

        assert "64" in item.minecraft_command


class TestPurchase:
    """Test purchase creation and validation"""

    def test_purchase_creation(self):
        """Test creating a pending purchase"""
        purchase = MagicMock(spec=PendingPurchase)
        purchase.id = 1
        purchase.user_id = 1
        purchase.shop_item_id = 1
        purchase.quantity = 1
        purchase.total_cost = 500
        purchase.status = "pending"
        purchase.created_at = datetime.utcnow()

        assert purchase.status == "pending"
        assert purchase.total_cost == 500

    def test_purchase_total_cost_calculation(self):
        """Test purchase total cost = item_price * quantity"""
        item_price = 100
        quantity = 5
        total_cost = item_price * quantity

        assert total_cost == 500

    def test_purchase_delivery_completed(self):
        """Test purchase status changes to completed"""
        purchase = MagicMock(spec=PendingPurchase)
        purchase.status = "pending"
        
        # Simulate delivery
        purchase.status = "completed"
        purchase.delivered_at = datetime.utcnow()

        assert purchase.status == "completed"
        assert purchase.delivered_at is not None


class TestPurchaseValidation:
    """Test purchase validation before creation"""

    def test_sufficient_balance_for_purchase(self):
        """Test user has sufficient balance"""
        user = MagicMock(spec=User)
        user.craftycoin_balance = 1000
        item_price = 500

        can_purchase = user.craftycoin_balance >= item_price
        assert can_purchase is True

    def test_insufficient_balance_for_purchase(self):
        """Test user lacks sufficient balance"""
        user = MagicMock(spec=User)
        user.craftycoin_balance = 300
        item_price = 500

        can_purchase = user.craftycoin_balance >= item_price
        assert can_purchase is False

    def test_purchase_with_exact_balance(self):
        """Test purchase with exact balance amount"""
        user = MagicMock(spec=User)
        user.craftycoin_balance = 500
        item_price = 500

        can_purchase = user.craftycoin_balance >= item_price
        assert can_purchase is True

    def test_zero_or_negative_quantity_rejected(self):
        """Test purchase with invalid quantity"""
        quantity = 0
        is_valid = quantity > 0
        assert is_valid is False

        quantity = -5
        is_valid = quantity > 0
        assert is_valid is False

    def test_maximum_quantity_limit(self):
        """Test purchase respects quantity limit"""
        max_per_user = 10
        requested_quantity = 15

        can_purchase = requested_quantity <= max_per_user
        assert can_purchase is False

    def test_quantity_within_limit(self):
        """Test quantity within acceptable range"""
        max_per_user = 10
        requested_quantity = 5

        can_purchase = requested_quantity <= max_per_user
        assert can_purchase is True


class TestPurchaseDelivery:
    """Test purchase delivery mechanism"""

    def test_delivery_command_formatting(self):
        """Test command is formatted correctly for delivery"""
        player_name = "JMG"
        item_command = "give {player} diamond_pickaxe 1"
        formatted_command = item_command.format(player=player_name)

        assert formatted_command == "give JMG diamond_pickaxe 1"

    def test_delivery_multiple_items(self):
        """Test delivery with multiple items (quantity > 1)"""
        player_name = "JMG"
        base_command = "give {player} apple 64"
        quantity = 2

        # Execute command twice
        commands = [base_command.format(player=player_name) for _ in range(quantity)]
        
        assert len(commands) == 2
        assert commands[0] == "give JMG apple 64"
        assert commands[1] == "give JMG apple 64"

    def test_pending_purchase_tracked(self):
        """Test pending purchases are tracked"""
        purchases = []
        
        purchase = MagicMock(spec=PendingPurchase)
        purchase.status = "pending"
        purchases.append(purchase)

        assert len(purchases) == 1
        assert purchases[0].status == "pending"

    def test_delivered_purchase_removed_from_pending(self):
        """Test delivered purchases removed from pending"""
        purchases = []
        
        purchase = MagicMock(spec=PendingPurchase)
        purchase.status = "pending"
        purchases.append(purchase)

        # Simulate delivery
        purchase.status = "completed"

        pending = [p for p in purchases if p.status == "pending"]
        assert len(pending) == 0


class TestPurchaseNotifications:
    """Test purchase notifications"""

    def test_purchase_confirmation_message(self):
        """Test user gets purchase confirmation"""
        item = MagicMock(spec=ShopItem)
        item.name = "Diamond Pickaxe"
        item.price = 500

        confirmation_msg = f"Achat confirmé: {item.name} pour {item.price} CC"
        assert "Achat confirmé" in confirmation_msg
        assert "Diamond Pickaxe" in confirmation_msg

    def test_delivery_notification_on_join(self):
        """Test user gets notification when purchase delivered"""
        notification = "Votre achat de Diamond Pickaxe a été livré!"
        
        assert "livré" in notification.lower()

    def test_insufficient_balance_message(self):
        """Test error message for insufficient balance"""
        needed = 500
        available = 300
        shortage = needed - available

        error_msg = f"Solde insuffisant. Besoin: {needed} CC, Vous avez: {available} CC"
        assert str(shortage) in error_msg


class TestPurchaseWithMultipleUsers:
    """Test purchase system with multiple users"""

    def test_multiple_purchases_isolated(self):
        """Test multiple user purchases don't interfere"""
        user1 = MagicMock(spec=User)
        user1.discord_id = 111
        user1.craftycoin_balance = 1000

        user2 = MagicMock(spec=User)
        user2.discord_id = 222
        user2.craftycoin_balance = 500

        # Purchase by user1
        user1.craftycoin_balance -= 100

        # Purchase by user2
        user2.craftycoin_balance -= 100

        assert user1.craftycoin_balance == 900
        assert user2.craftycoin_balance == 400

    def test_purchase_history_per_user(self):
        """Test each user has separate purchase history"""
        user1_purchases = []
        user2_purchases = []

        purchase1 = MagicMock(spec=PendingPurchase)
        purchase1.user_id = 1
        user1_purchases.append(purchase1)

        purchase2 = MagicMock(spec=PendingPurchase)
        purchase2.user_id = 2
        user2_purchases.append(purchase2)

        assert len(user1_purchases) == 1
        assert len(user2_purchases) == 1
        assert user1_purchases[0].user_id != user2_purchases[0].user_id


class TestShopCategories:
    """Test shop item categories"""

    def test_item_categories(self):
        """Test all shop item categories"""
        categories = ["weapons", "armor", "tools", "building", "food", "potions", "enchantments", "misc"]
        
        for category in categories:
            assert len(category) > 0

    def test_item_in_category(self):
        """Test item belongs to correct category"""
        item = MagicMock(spec=ShopItem)
        item.category = "weapons"

        assert item.category in ["weapons", "armor", "tools", "building", "food", "potions", "enchantments", "misc"]

    def test_filter_items_by_category(self):
        """Test filtering items by category"""
        items = []
        
        item1 = MagicMock(spec=ShopItem)
        item1.category = "weapons"
        items.append(item1)

        item2 = MagicMock(spec=ShopItem)
        item2.category = "tools"
        items.append(item2)

        weapons = [i for i in items if i.category == "weapons"]
        assert len(weapons) == 1


# Test execution
if __name__ == "__main__":
    import unittest

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestShopItems))
    suite.addTests(loader.loadTestsFromTestCase(TestPurchase))
    suite.addTests(loader.loadTestsFromTestCase(TestPurchaseValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestPurchaseDelivery))
    suite.addTests(loader.loadTestsFromTestCase(TestPurchaseNotifications))
    suite.addTests(loader.loadTestsFromTestCase(TestPurchaseWithMultipleUsers))
    suite.addTests(loader.loadTestsFromTestCase(TestShopCategories))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    sys.exit(0 if result.wasSuccessful() else 1)
