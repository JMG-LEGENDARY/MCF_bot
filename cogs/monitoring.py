"""
Monitoring Cog - Health checks and bot status monitoring
Commands: /bot-status (staff only), error webhooks
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import psutil
import os

from requests import session

from db.database import db, get_leaderboard
from db.models import Transaction, User
from utils.logger import get_logger
from utils.formatters import create_embed

log = get_logger("monitoring")


class MonitoringCog(commands.Cog):
    """Bot monitoring and health checks"""

    def __init__(self, bot):
        self.bot = bot
        self.session = db  # 🛠️ CORRECTION 1 : db n'est pas "callable", on enlève les parenthèses
        self.start_time = datetime.utcnow()
        self.error_log = []
        self.max_errors = 100

    @app_commands.command(name="bot-status", description="Affiche le statut système du bot")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def status_bot(self, interaction: discord.Interaction):
        """
        Show bot status and health metrics (Staff only)
        
        Usage: /bot-status
        """
        
        # Calculate uptime
        uptime = datetime.utcnow() - self.start_time
        uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds // 60) % 60}m"
        
        # Get user count
        user_count = self.session.query(User).count()
        
        # Get transaction stats (last 24h)
        yesterday = datetime.utcnow() - timedelta(days=1)
        txn_24h = self.session.query(Transaction).filter(
            Transaction.created_at >= yesterday
        ).count()
        
        total_coins = self.session.query(User).with_entities(
            db.func.sum(User.craftycoin_balance)
        ).scalar() or 0
        
        # Get resource usage
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        cpu_usage = process.cpu_percent(interval=1)
        
        embed = create_embed(
            title="🤖 Bot Status & Health",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        embed.add_field(name="Latency", value=f"{self.bot.latency * 1000:.0f}ms", inline=True)
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=True)
        
        embed.add_field(name="Users (DB)", value=str(user_count), inline=True)
        embed.add_field(name="Total CraftyCoin", value=f"{total_coins:.0f} CC", inline=True)
        embed.add_field(name="Transactions (24h)", value=str(txn_24h), inline=True)
        
        embed.add_field(name="Memory Usage", value=f"{memory_usage:.1f} MB", inline=True)
        embed.add_field(name="CPU Usage", value=f"{cpu_usage:.1f}%", inline=True)
        embed.add_field(name="Python Version", value=discord.__version__, inline=True)
        
        if self.error_log:
            embed.add_field(name="Recent Errors", value=str(len(self.error_log)), inline=True)
        
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.send_message(embed=embed)
        log.info(f"📊 {interaction.user} checked bot status")

    @app_commands.command(name="bot-errors", description="Affiche les erreurs récentes du bot")
    @app_commands.checks.has_permissions(administrator=True)
    async def status_errors(self, interaction: discord.Interaction, limit: int = 10):
        """
        View recent errors (Admin only)
        
        Usage: /bot-errors [limit]
        """
        # 🛠️ CORRECTION 2 : Changement du nom de la méthode de 'bot_errors' en 'status_errors'
        # pour respecter la restriction sur les préfixes 'bot_' et 'cog_' dans discord.py
        
        if not self.error_log:
            embed = create_embed(
                title="✅ No Recent Errors",
                description="Bot is running smoothly!",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            return
        
        embed = create_embed(
            title="⚠️  Recent Errors",
            description=f"Last {min(limit, len(self.error_log))} errors",
            color=discord.Color.gold()
        )
        
        for error in self.error_log[-limit:]:
            embed.add_field(
                name=error["command"],
                value=(
                    f"**Time:** {error['timestamp']}\n"
                    f"**User:** {error['user']}\n"
                    f"```{error['error'][:200]}```"
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def log_error(
        self,
        command_name: str,
        user: str,
        error: Exception
    ):
        """
        Store error in memory for monitoring
        """

        self.error_log.append({
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "command": command_name,
            "user": user,
            "error": str(error)
        })

        # Keep only last N errors
        if len(self.error_log) > self.max_errors:
            self.error_log.pop(0)

        log.error(
            f"Command Error | {command_name} | "
            f"User: {user} | Error: {error}"
        )

    @tasks.loop(minutes=10)
    async def health_check(self):
        """
        Periodic health monitoring
        """

        try:
            process = psutil.Process(os.getpid())

            memory_usage = process.memory_info().rss / 1024 / 1024
            cpu_usage = process.cpu_percent()

            # Alert thresholds
            if memory_usage > 1000:
                log.warning(
                    f"⚠️ High memory usage detected: "
                    f"{memory_usage:.1f} MB"
                )

            if cpu_usage > 80:
                log.warning(
                    f"⚠️ High CPU usage detected: "
                    f"{cpu_usage:.1f}%"
                )

            # Database test
            with db.get_session() as session:
                session.query(User).first()

            log.debug(
                f"Health Check | "
                f"RAM={memory_usage:.1f}MB | "
                f"CPU={cpu_usage:.1f}%"
            )

        except Exception as e:
            log.error(f"Health check failed: {e}")

    @health_check.before_loop
    async def before_health_check(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ):
        """
        Global slash command error handler
        """

        await self.log_error(
            command_name=getattr(
                interaction.command,
                "name",
                "Unknown"
            ),
            user=str(interaction.user),
            error=error
        )

        if app_commands.errors.MissingPermissions:
            embed = create_embed(
                title="❌ Permission refusée",
                description="Vous n'avez pas les permissions nécessaires.",
                color=discord.Color.red()
            )

        else:
            embed = create_embed(
                title="⚠️ Erreur",
                description=(
                    "Une erreur inattendue est survenue.\n"
                    "L'équipe technique a été notifiée."
                ),
                color=discord.Color.orange()
            )

        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=embed,
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True
                )
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Startup logging
        """

        log.info(
            f"✅ MonitoringCog loaded | "
            f"{len(self.bot.guilds)} guilds"
        )

        if not self.health_check.is_running():
            self.health_check.start()


async def setup(bot):
    """
    Load cog
    """

    await bot.add_cog(MonitoringCog(bot))