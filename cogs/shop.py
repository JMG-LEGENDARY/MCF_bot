"""Cog Shop - Système de boutique et achats"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime

from db import db, get_or_create_user, ShopItem, PendingPurchase
from utils import (
    format_shop_item_embed, format_error_embed, format_success_embed,
    format_coins, get_logger
)
from core.decorators import log_command, defer_interaction, handle_errors
from config import config

logger = get_logger(__name__)


class ShopCog(commands.Cog):
    """Gestion de la boutique et des achats"""
    
    def __init__(self, bot):
        self.bot = bot
        self.check_pending_purchases.start()

    @tasks.loop(seconds=30)
    async def check_pending_purchases(self):
        """Vérifie régulièrement les achats en attente quand les joueurs rejoignent"""
        try:
            pass  # À implémenter avec event on_member_join
        except Exception as e:
            logger.error(f"Erreur dans check_pending_purchases: {e}")

    @check_pending_purchases.before_loop
    async def before_check_pending(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="shop", description="Affiche la boutique")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    @defer_interaction(ephemeral=True)
    @log_command
    @handle_errors
    async def shop(self, interaction: discord.Interaction):
        """Affiche tous les items de la boutique"""
        with db.get_session() as session:
            items = session.query(ShopItem).filter(ShopItem.is_available == True).all()
            
            if not items:
                embed = format_error_embed("Boutique", "Aucun item disponible pour le moment")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Créer un embed par catégorie
            categories = {}
            for item in items:
                cat = item.category or "misc"
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item)
            
            # Créer les embeds
            embeds = []
            for cat, cat_items in categories.items():
                embed = discord.Embed(
                    title=f"🛒 Boutique - {cat.title()}",
                    color=discord.Color.blurple()
                )
                
                for item in cat_items:
                    embed.add_field(
                        name=f"`/{item.id}` - {item.name}",
                        value=f"💎 {format_coins(item.price)}\n{item.description or 'N/A'}",
                        inline=False
                    )
                
                embeds.append(embed)
            
            # Si trop d'embeds, créer une vue avec navigation
            if len(embeds) > 1:
                view = discord.ui.View()
                
                async def prev_callback(button_interaction: discord.Interaction):
                    # Logique de navigation
                    pass
                
                prev_btn = discord.ui.Button(label="⬅ Précédent", style=discord.ButtonStyle.secondary)
                next_btn = discord.ui.Button(label="Suivant ➡", style=discord.ButtonStyle.secondary)
                prev_btn.callback = prev_callback
                view.add_item(prev_btn)
                view.add_item(next_btn)
                
                await interaction.followup.send(embed=embeds[0], view=view, ephemeral=True)
            else:
                await interaction.followup.send(embed=embeds[0] if embeds else format_error_embed("Boutique", "Aucun item"), ephemeral=True)

    @app_commands.command(name="buy", description="Acheter un item de la boutique")
    @app_commands.describe(item_id="ID de l'item", quantity="Quantité (défaut: 1)")
    @app_commands.checks.cooldown(1, 3, key=lambda i: i.user.id)
    @defer_interaction(ephemeral=True)
    @log_command
    @handle_errors
    async def buy(self, interaction: discord.Interaction, item_id: int, quantity: int = 1):
        """Achète un item de la boutique"""
        
        # Validations
        if quantity < 1:
            embed = format_error_embed("Erreur", "La quantité doit être ≥ 1")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        with db.get_session() as session:
            # Vérifier l'item
            item = session.query(ShopItem).filter(ShopItem.id == item_id).first()
            if not item or not item.is_available:
                embed = format_error_embed("Erreur", "Item non trouvé ou indisponible")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Vérifier la limite d'achat
            if item.max_purchase_per_user:
                user_purchases = session.query(PendingPurchase).filter(
                    PendingPurchase.user_id == get_or_create_user(session, interaction.user.id).id,
                    PendingPurchase.item_id == item.id,
                    PendingPurchase.status == "pending"
                ).count()
                
                if user_purchases + quantity > item.max_purchase_per_user:
                    embed = format_error_embed(
                        "Limite d'achat",
                        f"Vous ne pouvez acheter max **{item.max_purchase_per_user}** de cet item"
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            
            # Vérifier le solde
            user = get_or_create_user(session, interaction.user.id)
            total_cost = item.price * quantity
            
            if user.craftycoin_balance < total_cost:
                embed = format_error_embed(
                    "Solde insuffisant",
                    f"Vous avez **{format_coins(user.craftycoin_balance)}** mais l'item coûte **{format_coins(total_cost)}**"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Débiter l'utilisateur
            user.craftycoin_balance -= total_cost
            
            # Créer l'achat en attente
            purchase = PendingPurchase(
                user_id=user.id,
                item_id=item.id,
                quantity=quantity,
                status="pending"
            )
            session.add(purchase)
            session.commit()
            
            # Confirmation
            embed = discord.Embed(
                title="✅ Achat en attente",
                description=f"L'item sera livré quand vous rejoindrez Minecraft",
                color=discord.Color.green()
            )
            embed.add_field(name="Item", value=item.name, inline=True)
            embed.add_field(name="Quantité", value=str(quantity), inline=True)
            embed.add_field(name="Coût", value=f"**-{format_coins(total_cost)}**", inline=True)
            embed.add_field(
                name="Nouveau solde",
                value=f"**{format_coins(user.craftycoin_balance)}**",
                inline=False
            )
            embed.set_footer(text="Connectez-vous à Minecraft pour recevoir votre achat!")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Achat: {interaction.user} → {item.name} x{quantity} ({total_cost} CC)")

    @app_commands.command(name="inventory", description="Affiche votre inventaire d'achats en attente")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    @defer_interaction(ephemeral=True)
    @log_command
    @handle_errors
    async def inventory(self, interaction: discord.Interaction):
        """Affiche les achats en attente de livraison"""
        with db.get_session() as session:
            user = get_or_create_user(session, interaction.user.id)
            pending = session.query(PendingPurchase).filter(
                PendingPurchase.user_id == user.id,
                PendingPurchase.status.in_(["pending", "completed"])
            ).all()
            
            if not pending:
                embed = format_error_embed("Inventaire", "Vous n'avez pas d'achats en attente")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📦 Achats en attente",
                color=discord.Color.blurple()
            )
            
            for purchase in pending:
                item = purchase.item
                status_emoji = "⏳" if purchase.status == "pending" else "✅"
                embed.add_field(
                    name=f"{status_emoji} {item.name}",
                    value=f"Quantité: {purchase.quantity} | Statut: {purchase.status}",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    """Fonction requise par discord.py pour charger le cog."""
    await bot.add_cog(ShopCog(bot))
    logger.info("✅ ShopCog chargé")
