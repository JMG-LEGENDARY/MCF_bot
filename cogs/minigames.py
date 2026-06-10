"""
Mini-games cog: Dice, Coin Flip, Roulette
Implements Discord Slash Games with CraftyCoin betting
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import asyncio
from datetime import datetime, timezone

from db.database import db, get_or_create_user, add_transaction
from db.models import User, Transaction, MiniGameSession
from core.decorators import handle_errors
from utils.logger import get_logger
from utils.formatters import create_embed

log = get_logger("minigames")


class MiniGamesCog(commands.GroupCog, name="games"):
    """Système de mini-jeux avec paris et récompenses CraftyCoin"""

    def __init__(self, bot):
        self.bot = bot
        self.session = db
        self.game_cooldowns = {}
        
        # Casino rules
        self.MIN_BALANCE_TO_PLAY = 100
        self.PER_GAME_LIMIT_CC = 1000
        self.GAME_COOLDOWN_SECONDS = 30
        self.JACKPOT_CHANCE = 0.001  # 0.1%
        self.JACKPOT_PRIZE = 500
        
    async def cog_load(self):
        """Appelé lors du chargement du Cog"""
        log.info(f"✅ MiniGamesCog chargé - Système de paris prêt")

    async def check_game_cooldown(self, user_id: int):
        """Vérifie si le joueur est sous cooldown"""
        if user_id in self.game_cooldowns:
            last_play = self.game_cooldowns[user_id]
            elapsed = (datetime.now(timezone.utc) - last_play).total_seconds()
            if elapsed < self.GAME_COOLDOWN_SECONDS:
                return False, self.GAME_COOLDOWN_SECONDS - int(elapsed)
        return True, 0

    async def check_casino_rules(self, user_id: int, amount: int):
        """Valide la mise selon les règles de la banque"""
        # Utilisation d'un ID temporaire bidon pour le nom si l'user n'existe pas en DB
        user_obj = get_or_create_user(user_id, "Joueur")
        
        if user_obj.craftycoin_balance < self.MIN_BALANCE_TO_PLAY:
            return False, f"Vous devez avoir au moins {self.MIN_BALANCE_TO_PLAY} CC sur votre compte pour jouer."
        
        if amount <= 0:
            return False, "La mise doit être supérieure à 0 CC !"

        if amount > self.PER_GAME_LIMIT_CC:
            return False, f"La mise maximale par partie est de {self.PER_GAME_LIMIT_CC} CC."
        
        if user_obj.craftycoin_balance < amount:
            return False, f"Fonds insuffisants. Vous possédez actuellement : {user_obj.craftycoin_balance:.1f} CC."
        
        return True, "OK"

    @app_commands.command(name="dice", description="Jouer au dé : lancez un dé face au bot !")
    @app_commands.describe(bet="Montant en CraftyCoin à miser", number="Optionnel : Choisissez votre face (1-6)")
    @handle_errors
    async def dice_game(self, interaction: discord.Interaction, bet: int, number: int = None):
        user_id = interaction.user.id
        
        # Cooldown check
        can_play, wait_time = await self.check_game_cooldown(user_id)
        if not can_play:
            embed = create_embed(
                title="⏱️ Cooldown Actif",
                description=f"Merci de patienter {wait_time}s avant de rejouer.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Validation mise
        valid, msg = await self.check_casino_rules(user_id, bet)
        if not valid:
            embed = create_embed(title="❌ Mise Invalide", description=msg, color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Validation numéro
        if number is not None and (number < 1 or number > 6):
            embed = create_embed(title="❌ Numéro Invalide", description="Choisissez un chiffre entre 1 et 6.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if number == None:
            number = random.randint(1, 6)
            
        await interaction.response.defer()
        
        user = get_or_create_user(user_id, interaction.user.name)
        user.craftycoin_balance -= bet
        
        bot_roll = random.randint(1, 6)
        user_roll = number
        
        embed = create_embed(title="🎲 Jeu de Dés", color=discord.Color.gold())
        embed.add_field(name="Votre Mise", value=f"{bet} CC", inline=True)
        embed.add_field(name="Votre Dé", value=f"🎲 {user_roll}", inline=True)
        embed.add_field(name="Dé du Bot", value=f"🎲 {bot_roll}", inline=True)
        
        if user_roll > bot_roll:
            winnings = int(bet * 1.5)
            user.craftycoin_balance += winnings + bet
            result = "win"
            net_change = winnings
            embed.description = f"🎉 **Gagné !** Vous remportez {winnings} CC !"
            embed.color = discord.Color.green()
            
            # Jackpot chance
            if random.random() < self.JACKPOT_CHANCE:
                user.craftycoin_balance += self.JACKPOT_PRIZE
                embed.add_field(name="🎉 JACKPOT !", value=f"Bonus exceptionnel de {self.JACKPOT_PRIZE} CC !", inline=False)
                net_change += self.JACKPOT_PRIZE
        elif user_roll < bot_roll:
            result = "loss"
            net_change = -bet
            embed.description = f"❌ **Perdu !** Vous perdez votre mise de {bet} CC."
            embed.color = discord.Color.red()
        else:
            user.craftycoin_balance += bet
            result = "tie"
            net_change = 0
            embed.description = "🤝 **Égalité !** Votre mise vous est restituée."
            embed.color = discord.Color.blue()
            
        add_transaction(user_id=user.id, amount=float(net_change), transaction_type="game_dice", description=f"Dé : {result.upper()} (Mise {bet} CC)")
        
        session_game = MiniGameSession(user_id=user.id, game_type="dice", bet_amount=float(bet), result=result, created_at=datetime.now(timezone.utc))
        self.session.add(session_game)
        self.session.commit()
        
        self.game_cooldowns[user_id] = datetime.now(timezone.utc)
        embed.set_footer(text=f"Nouveau solde : {user.craftycoin_balance:.1f} CC")
        await interaction.followup.send(embed=embed)


    @app_commands.command(name="coinflip", description="Lancer une pièce : Pile ou Face (Double ou double) !")
    @app_commands.describe(bet="Montant en CraftyCoin à miser", choice="Choisissez : heads (pile) ou tails (face)")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Pile (Heads)", value="heads"),
        app_commands.Choice(name="Face (Tails)", value="tails")
    ])
    @handle_errors
    async def coinflip_game(self, interaction: discord.Interaction, bet: int, choice: str):
        user_id = interaction.user.id
        
        valid, msg = await self.check_casino_rules(user_id, bet)
        if not valid:
            embed = create_embed(title="❌ Mise Invalide", description=msg, color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        await interaction.response.defer()
        
        user = get_or_create_user(user_id, interaction.user.name)
        user.craftycoin_balance -= bet
        
        result_choice = random.choice(["heads", "tails"])
        
        embed = create_embed(title="🪙 Pile ou Face", description="⏳ La pièce tourne dans les airs...", color=discord.Color.gold())
        embed.add_field(name="Votre Mise", value=f"{bet} CC", inline=True)
        embed.add_field(name="Votre Pronostic", value=choice.upper(), inline=True)
        
        followup_msg = await interaction.followup.send(embed=embed)
        await asyncio.sleep(1.5)
        
        if choice == result_choice:
            winnings = bet * 2
            user.craftycoin_balance += winnings
            result = "win"
            net_change = bet
            embed.description = f"✅ **Gagné !** La pièce est tombée sur {result_choice.upper()}. Vous remportez {winnings} CC !"
            embed.color = discord.Color.green()
        else:
            result = "loss"
            net_change = -bet
            embed.description = f"❌ **Perdu !** La pièce est tombée sur {result_choice.upper()}."
            embed.color = discord.Color.red()
            
        add_transaction(user_id=user.id, amount=float(net_change), transaction_type="game_coinflip", description=f"Coinflip : {result.upper()}")
        
        session_game = MiniGameSession(user_id=user.id, game_type="coinflip", bet_amount=float(bet), result=result, created_at=datetime.now(timezone.utc))
        self.session.add(session_game)
        self.session.commit()
        
        embed.set_footer(text=f"Nouveau solde : {user.craftycoin_balance:.1f} CC")
        await followup_msg.edit(embed=embed)


    @app_commands.command(name="roulette", description="Tenter la roulette européenne : misez sur un numéro entre 0 et 36 !")
    @app_commands.describe(bet="Montant à miser", number="Numéro choisi (0-36)")
    @handle_errors
    async def roulette_game(self, interaction: discord.Interaction, bet: int, number: int):
        user_id = interaction.user.id
        
        valid, msg = await self.check_casino_rules(user_id, bet)
        if not valid:
            embed = create_embed(title="❌ Mise Invalide", description=msg, color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        if number < 0 or number > 36:
            embed = create_embed(title="❌ Numéro Invalide", description="Le numéro doit être compris entre 0 et 36.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        await interaction.response.defer()
        
        user = get_or_create_user(user_id, interaction.user.name)
        user.craftycoin_balance -= bet
        
        wheel_result = random.randint(0, 36)
        
        embed = create_embed(title="🎡 Roulette Européenne", color=discord.Color.gold())
        embed.add_field(name="Votre Mise", value=f"{bet} CC", inline=True)
        embed.add_field(name="Votre Numéro", value=f"#{number}", inline=True)
        embed.add_field(name="Résultat de la bille", value=f"#{wheel_result}", inline=True)
        
        if number == wheel_result:
            winnings = bet * 35
            user.craftycoin_balance += winnings + bet
            result = "win"
            net_change = winnings
            embed.description = f"🎉 **INCROYABLE JACKPOT !** La bille s'arrête sur le #{wheel_result} ! Vous gagnez {winnings} CC !"
            embed.color = discord.Color.green()
        else:
            result = "loss"
            net_change = -bet
            embed.description = f"❌ **Perdu !** La bille s'est arrêtée sur le #{wheel_result}."
            embed.color = discord.Color.red()
            
        add_transaction(user_id=user.id, amount=float(net_change), transaction_type="game_roulette", description=f"Roulette : {result.upper()} sur #{number}")
        
        session_game = MiniGameSession(user_id=user.id, game_type="roulette", bet_amount=float(bet), result=result, created_at=datetime.now(timezone.utc))
        self.session.add(session_game)
        self.session.commit()
        
        embed.set_footer(text=f"Nouveau solde : {user.craftycoin_balance:.1f} CC")
        await interaction.followup.send(embed=embed)


    @app_commands.command(name="stats", description="Afficher vos statistiques de jeu ou celles d'un autre utilisateur")
    @app_commands.describe(user="L'utilisateur dont vous voulez voir les stats")
    @handle_errors
    async def minigames_stats(self, interaction: discord.Interaction, user: discord.User = None):
        await interaction.response.defer()
        target = user or interaction.user
        user_obj = get_or_create_user(target.id, target.name)
        
        sessions = self.session.query(MiniGameSession).filter(MiniGameSession.user_id == user_obj.id).all()
        
        if not sessions:
            embed = create_embed(title="📊 Statistiques Casino", description=f"{target.mention} n'a pas encore misé un seul CraftyCoin !", color=discord.Color.blue())
            await interaction.followup.send(embed=embed)
            return
            
        total_games = len(sessions)
        wins = len([s for s in sessions if s.result == "win"])
        losses = len([s for s in sessions if s.result == "loss"])
        ties = len([s for s in sessions if s.result == "tie"])
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        total_bet = sum([s.bet_amount for s in sessions])
        
        game_types = {}
        for session in sessions:
            game_types[session.game_type] = game_types.get(session.game_type, 0) + 1
            
        embed = create_embed(title="📊 Statistiques de Jeu", color=discord.Color.blue())
        embed.add_field(name="Parties Jouées", value=str(total_games), inline=True)
        embed.add_field(name="Victoires", value=f"✅ {wins}", inline=True)
        embed.add_field(name="Défaites", value=f"❌ {losses}", inline=True)
        embed.add_field(name="Égalités", value=f"🤝 {ties}", inline=True)
        embed.add_field(name="Taux de Win", value=f"{win_rate:.1f}%", inline=True)
        embed.add_field(name="Total Misé", value=f"{total_bet:.0f} CC", inline=True)
        
        game_breakdown = "\n".join([f"🔹 **{game.capitalize()}** : {count} partie(s)" for game, count in game_types.items()])
        embed.add_field(name="Répartition par jeu", value=game_breakdown, inline=False)
        
        if target.avatar:
            embed.set_thumbnail(url=target.avatar.url)
            
        await interaction.followup.send(embed=embed)


async def setup(bot):
    """Charge le Cog dans le bot principal"""
    await bot.add_cog(MiniGamesCog(bot))