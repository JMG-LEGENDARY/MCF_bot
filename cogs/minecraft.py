"""Cog Minecraft - Événements et suivi du serveur Minecraft"""

import discord
from discord.ext import commands, tasks
import logging
import re
from datetime import datetime
from pathlib import Path

from discord import app_commands
from db import db, get_or_create_user, GameSession, User, add_transaction
from core.constants import MINECRAFT_LOG_PATTERNS, EMOJI
from utils import extract_minecraft_username_from_log, get_logger, calculate_playtime_earning, format_coins
from utils.minecraft_monitor import MinecraftLogMonitor
from config import config

logger = get_logger(__name__)


class MinecraftCog(commands.Cog):
    """Gestion des événements Minecraft"""
    
    def __init__(self, bot):
        self.bot = bot
        self.monitor: MinecraftLogMonitor = None
        self.monitor_task = None

    @commands.Cog.listener()
    async def on_ready(self):
        """Initialise le suivi des logs au démarrage"""
        logger.info("🎮 MinecraftCog prêt")
        
        # Démarrer le monitoring si configuré
        # À activer avec un path vers les logs
        # await self.start_monitoring("/path/to/logs.txt")

    async def start_monitoring(self, log_path: str):
        """Démarre le monitoring des logs Minecraft"""
        if self.monitor is not None:
            logger.warning("Monitoring déjà actif")
            return
        
        self.monitor = MinecraftLogMonitor(log_path)
        self.monitor.register_callback("player_join", self._handle_player_join)
        self.monitor.register_callback("player_leave", self._handle_player_leave)
        
        logger.info(f"📍 Monitoring des logs: {log_path}")

    async def _handle_player_join(self, username: str):
        """Gère l'événement d'un joueur qui rejoint"""
        logger.info(f"🟢 {username} a rejoint le serveur")
        
        try:
            with db.get_session() as session:
                # Créer une session de jeu
                game_session = GameSession(
                    minecraft_username=username,
                    login_time=datetime.utcnow()
                )
                session.add(game_session)
                session.commit()
                
                # Envoyer un message de bienvenue
                channel_id = config.CHANNELS.get("gestion_mc")
                if channel_id:
                    try:
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            # Obtenir le WelcomeCog
                            welcome_cog = self.bot.get_cog("WelcomeCog")
                            if welcome_cog:
                                await welcome_cog.send_welcome_message(channel, username)
                    except Exception as e:
                        logger.error(f"Erreur lors de l'envoi du message de bienvenue: {e}")
        
        except Exception as e:
            logger.error(f"Erreur dans _handle_player_join: {e}", exc_info=True)

    async def _handle_player_leave(self, username: str):
        """Gère l'événement d'un joueur qui quitte"""
        logger.info(f"🔴 {username} a quitté le serveur")
        
        try:
            with db.get_session() as session:
                # Mettre à jour la session de jeu (logout)
                last_session = (
                    session.query(GameSession)
                    .filter(GameSession.minecraft_username == username)
                    .filter(GameSession.logout_time.is_(None))
                    .order_by(GameSession.id.desc())
                    .first()
                )
                
                if last_session:
                    last_session.logout_time = datetime.utcnow()
                    playtime_seconds = (last_session.logout_time - last_session.login_time).total_seconds()
                    playtime_minutes = playtime_seconds / 60
                    last_session.total_playtime_minutes = playtime_minutes
                    
                    # Créditer les gains au joueur
                    user = session.query(User).filter(User.minecraft_username == username).first()
                    if user:
                        earning = calculate_playtime_earning(
                            playtime_minutes,
                            multiplier=user.playtime_multiplier,
                            rate=config.VOICE_EARNING_RATE
                        )
                        
                        if earning > 0:
                            add_transaction(
                                session, user.id, earning, "playtime",
                                f"Temps de jeu: {playtime_minutes:.0f}m",
                                base_amount=playtime_minutes * config.VOICE_EARNING_RATE,
                                multiplier=user.playtime_multiplier
                            )
                        
                        user.total_playtime_minutes += playtime_minutes
                    
                    session.commit()
                
                # Envoyer un message d'au revoir
                channel_id = config.CHANNELS.get("gestion_mc")
                if channel_id:
                    try:
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            # Obtenir le WelcomeCog
                            welcome_cog = self.bot.get_cog("WelcomeCog")
                            if welcome_cog:
                                session_time = playtime_minutes if last_session else 0
                                await welcome_cog.send_goodbye_message(channel, username)
                                await welcome_cog.log_player_stats(username, session_time, "leave")
                    except Exception as e:
                        logger.error(f"Erreur lors de l'envoi du message d'au revoir: {e}")
        
        except Exception as e:
            logger.error(f"Erreur dans _handle_player_leave: {e}", exc_info=True)

    @app_commands.command(name="playtime", description="Affiche votre temps de jeu Minecraft")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def playtime(self, interaction: discord.Interaction):
        """Affiche le temps de jeu total d'un utilisateur"""
        await interaction.response.defer(ephemeral=True)
        
        with db.get_session() as session:
            user = session.query(User).filter(User.discord_id == interaction.user.id).first()
            if not user:
                embed = discord.Embed(
                    title="❌ Utilisateur non trouvé",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Calculer le temps total
            total_seconds = user.total_playtime_minutes * 60
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            
            earning = user.total_playtime_minutes * config.VOICE_EARNING_RATE * user.playtime_multiplier
            
            embed = discord.Embed(
                title="🎮 Temps de jeu Minecraft",
                color=discord.Color.green()
            )
            embed.add_field(name="Temps total", value=f"**{hours}h {minutes}m**", inline=True)
            embed.add_field(name="Multiplicateur", value=f"**{user.playtime_multiplier}x**", inline=True)
            embed.add_field(
                name="Gains totaux",
                value=f"**{format_coins(earning)}**",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    """Fonction requise par discord.py pour charger le cog."""
    await bot.add_cog(MinecraftCog(bot))
    logger.info("✅ MinecraftCog chargé")
