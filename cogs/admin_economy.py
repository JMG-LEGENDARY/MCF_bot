"""
Admin Economy Cog - Gestion de l'économie par les administrateurs
Commandes: /admin-give, /admin-set, /admin-reset, item management, multipliers
"""

import discord
from discord.ext import commands
from datetime import datetime

from db.database import db, get_or_create_user, add_transaction, get_leaderboard
from core.decorators import require_role, is_creator, handle_errors
from db.models import User, Transaction, ShopItem
from utils.logger import get_logger
from utils.formatters import create_embed

log = get_logger("admin_economy")


class AdminEconomyCog(commands.Cog):
    """Administrative commands for economy management"""

    def __init__(self, bot):
        self.bot = bot
        self.session = db

    @commands.command(name="admin-give")
    @commands.has_permissions(administrator=True)
    async def admin_give(self, ctx, user: discord.User, amount: int):
        """
        Give CraftyCoin to a user (Admin only)
        
        Usage: /admin-give @user <amount>
        """
        
        if amount <= 0:
            embed = create_embed(
                title="❌ Invalid Amount",
                description="Amount must be positive",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        user_obj = get_or_create_user(user.id, user.name)
        old_balance = user_obj.craftycoin_balance
        user_obj.craftycoin_balance += amount
        
        # Create transaction
        add_transaction(
            user_id=user_obj.id,
            amount=amount,
            transaction_type="admin_give",
            description=f"Admin gave {amount} CC (admin: {ctx.author.name})"
        )
        
        self.session.commit()
        
        embed = create_embed(
            title="✅ CraftyCoin Distributed",
            color=discord.Color.green()
        )
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Amount", value=f"+{amount} CC", inline=True)
        embed.add_field(name="Old Balance", value=f"{old_balance} CC", inline=True)
        embed.add_field(name="New Balance", value=f"{user_obj.craftycoin_balance} CC", inline=True)
        embed.add_field(name="Admin", value=ctx.author.mention, inline=True)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
        log.info(f"🎁 Admin {ctx.author} gave {amount} CC to {user} (balance: {old_balance} → {user_obj.craftycoin_balance})")

    @commands.command(name="admin-set")
    @commands.has_permissions(administrator=True)
    async def admin_set(self, ctx, user: discord.User, amount: int):
        """
        Set CraftyCoin balance for a user (Admin only)
        
        Usage: /admin-set @user <amount>
        """
        
        if amount < 0:
            embed = create_embed(
                title="❌ Invalid Amount",
                description="Amount cannot be negative",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        user_obj = get_or_create_user(user.id, user.name)
        old_balance = user_obj.craftycoin_balance
        diff = amount - old_balance
        user_obj.craftycoin_balance = amount
        
        # Create transaction
        add_transaction(
            user_id=user_obj.id,
            amount=diff,
            transaction_type="admin_set",
            description=f"Admin set balance to {amount} CC (was {old_balance} CC, admin: {ctx.author.name})"
        )
        
        self.session.commit()
        
        embed = create_embed(
            title="✅ Balance Set",
            color=discord.Color.green()
        )
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Old Balance", value=f"{old_balance} CC", inline=True)
        embed.add_field(name="New Balance", value=f"{amount} CC", inline=True)
        embed.add_field(name="Difference", value=f"{diff:+.0f} CC", inline=True)
        embed.add_field(name="Admin", value=ctx.author.mention, inline=True)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
        log.info(f"⚙️  Admin {ctx.author} set {user}'s balance to {amount} CC (was {old_balance} CC)")

    @commands.command(name="admin-reset")
    @commands.has_permissions(administrator=True)
    async def admin_reset(self, ctx, user: discord.User):
        """
        Reset CraftyCoin balance to 0 (Admin only)
        
        Usage: /admin-reset @user
        Requires confirmation
        """
        
        user_obj = get_or_create_user(user.id, user.name)
        old_balance = user_obj.craftycoin_balance
        
        # Confirmation
        embed = create_embed(
            title="⚠️  Confirm Reset",
            description=f"Reset {user.mention}'s balance from {old_balance} CC to 0?\nThis cannot be undone!",
            color=discord.Color.gold()
        )
        
        msg = await ctx.send(embed=embed, components=[
            discord.ui.Button(label="Confirm", style=discord.ButtonStyle.danger),
            discord.ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)
        ])
        
        # Wait for button click
        try:
            interaction = await self.bot.wait_for(
                "button_click",
                check=lambda i: i.user == ctx.author and i.message == msg,
                timeout=30
            )
            
            if interaction.data["custom_id"] == 0:  # Confirm button
                user_obj.craftycoin_balance = 0
                
                add_transaction(
                    user_id=user_obj.id,
                    amount=-old_balance,
                    transaction_type="admin_reset",
                    description=f"Admin reset balance from {old_balance} CC to 0 (admin: {ctx.author.name})"
                )
                
                self.session.commit()
                
                embed = create_embed(
                    title="✅ Balance Reset",
                    color=discord.Color.green()
                )
                embed.add_field(name="User", value=user.mention, inline=True)
                embed.add_field(name="Old Balance", value=f"{old_balance} CC", inline=True)
                embed.add_field(name="New Balance", value="0 CC", inline=True)
                embed.add_field(name="Admin", value=ctx.author.mention, inline=True)
                embed.timestamp = datetime.utcnow()
                
                await interaction.response.send_message(embed=embed)
                log.info(f"🔄 Admin {ctx.author} reset {user}'s balance from {old_balance} CC to 0")
            else:
                embed = create_embed(
                    title="❌ Cancelled",
                    description="Reset cancelled",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
        
        except TimeoutError:
            embed = create_embed(
                title="⏱️ Timeout",
                description="Reset confirmation timed out",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command(name="admin-item-add")
    @commands.has_permissions(administrator=True)
    async def admin_item_add(self, ctx, name: str, price: int, command: str, category: str = "misc"):
        """
        Add item to shop (Admin only)
        
        Usage: /admin-item-add <name> <price> <minecraft_command> [category]
        """
        
        if price <= 0:
            embed = create_embed(
                title="❌ Invalid Price",
                description="Price must be positive",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Validate command
        if "{player}" not in command:
            embed = create_embed(
                title="❌ Invalid Command",
                description="Command must contain {player} placeholder",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Create item
        item = ShopItem(
            name=name,
            price=price,
            minecraft_command=command,
            category=category,
            available=True
        )
        
        self.session.add(item)
        self.session.commit()
        
        embed = create_embed(
            title="✅ Item Added",
            color=discord.Color.green()
        )
        embed.add_field(name="Name", value=name, inline=True)
        embed.add_field(name="Price", value=f"{price} CC", inline=True)
        embed.add_field(name="Category", value=category, inline=True)
        embed.add_field(name="Command", value=f"`{command}`", inline=False)
        embed.add_field(name="Admin", value=ctx.author.mention, inline=True)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
        log.info(f"🛒 Admin {ctx.author} added item: {name} (${price} CC)")

    @commands.command(name="admin-multiplier")
    @commands.has_permissions(administrator=True)
    async def admin_multiplier(self, ctx, user: discord.User, mult_type: str, value: float):
        """
        Set multiplier for user (Admin only)
        
        Usage: /admin-multiplier @user <message|playtime|response> <multiplier>
        Example: /admin-multiplier @user message 1.5
        """
        
        if mult_type.lower() not in ["message", "playtime", "response"]:
            embed = create_embed(
                title="❌ Invalid Type",
                description="Use: message, playtime, or response",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        if value < 0:
            embed = create_embed(
                title="❌ Invalid Multiplier",
                description="Multiplier cannot be negative",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        user_obj = get_or_create_user(user.id, user.name)
        mult_type = mult_type.lower() + "_multiplier"
        old_value = getattr(user_obj, mult_type)
        setattr(user_obj, mult_type, value)
        
        self.session.commit()
        
        embed = create_embed(
            title="✅ Multiplier Updated",
            color=discord.Color.green()
        )
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Type", value=mult_type.replace("_", " ").title(), inline=True)
        embed.add_field(name="Old Value", value=f"{old_value}x", inline=True)
        embed.add_field(name="New Value", value=f"{value}x", inline=True)
        embed.add_field(name="Admin", value=ctx.author.mention, inline=True)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
        log.info(f"📊 Admin {ctx.author} set {user}'s {mult_type} to {value}x")

    @commands.command(name="admin-transactions")
    @commands.has_permissions(administrator=True)
    async def admin_transactions(self, ctx, user: discord.User, limit: int = 20):
        """
        View user's transaction history (Admin only)
        
        Usage: /admin-transactions @user [limit]
        """
        
        user_obj = get_or_create_user(user.id, user.name)
        
        # Query transactions
        transactions = self.session.query(Transaction).filter(
            Transaction.user_id == user_obj.id
        ).order_by(Transaction.created_at.desc()).limit(limit).all()
        
        if not transactions:
            embed = create_embed(
                title="📊 Transaction History",
                description=f"No transactions for {user.mention}",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        embed = create_embed(
            title="📊 Transaction History",
            description=f"Last {len(transactions)} transactions",
            color=discord.Color.blue()
        )
        
        for txn in transactions[:10]:  # Show first 10 to fit embed
            sign = "+" if txn.amount > 0 else "-"
            emoji = "📈" if txn.amount > 0 else "📉"
            
            embed.add_field(
                name=f"{emoji} {txn.transaction_type.upper()}",
                value=f"{sign}{abs(txn.amount)} CC · {txn.created_at.strftime('%Y-%m-%d %H:%M')}",
                inline=False
            )
        
        embed.set_footer(text=f"Showing {min(10, len(transactions))} of {len(transactions)} transactions")
        await ctx.send(embed=embed)
        log.info(f"📊 Admin {ctx.author} viewed {user}'s transactions")


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(AdminEconomyCog(bot))
    log.info("✅ AdminEconomyCog loaded")
