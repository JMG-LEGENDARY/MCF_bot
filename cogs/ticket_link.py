"""
Ticket System Cog - Gestion autonome des tickets (Aide & Liaison Minecraft)
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from datetime import datetime

from db.database import db
from db.models import User
from utils.logger import get_logger
from utils.formatters import create_embed
from config import config
import crafty_api

log = get_logger("tickets")

# Configuration des IDs (Conversion forcée en int pour parer les formats strings de la config)
try:
    TICKET_CHANNEL_ID = int(config.CHANNELS.get("ticket_channel"))
except (TypeError, ValueError):
    TICKET_CHANNEL_ID = None
    log.error("❌ L'ID 'ticket_channel' dans config est manquant ou invalide !")

CATEGORY_TICKETS_ID = None  # 💡 Mets l'ID d'une catégorie ici si tu veux les ranger

# Rôles Staff autorisés (Conversion forcée en int également)
STAFF_ROLES = []
for role_key in ["manager_minecraft", "manager_discord", "manager_crafty"]:
    role_val = config.ROLES.get(role_key)
    if role_val:
        try:
            STAFF_ROLES.append(int(role_val))
        except ValueError:
            log.error(f"❌ L'ID du rôle {role_key} dans la config n'est pas un entier valide : {role_val}")


class TicketButtonsView(discord.ui.View):
    """Vue persistante contenant les boutons de création de ticket"""
    def __init__(self):
        # timeout=None rend la vue persistante (survit aux reboots du bot)
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Demander de l'aide", 
        style=discord.ButtonStyle.secondary, 
        custom_id="ticket_help",
        emoji="❓"
    )
    async def ticket_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self.create_ticket_channel(interaction, ticket_type="aide")

    @discord.ui.button(
        label="Se connecter à Minecraft", 
        style=discord.ButtonStyle.success, 
        custom_id="ticket_minecraft",
        emoji="🎮"
    )
    async def ticket_minecraft(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self.create_ticket_channel(interaction, ticket_type="minecraft")

    async def create_ticket_channel(self, interaction: discord.Interaction, ticket_type: str):
        guild = interaction.guild
        user = interaction.user
        
        # Base des permissions : Personne ne voit le salon sauf...
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }
        
        # ...les rôles de Staff configurés
        for role_id in STAFF_ROLES:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        # Récupération de la catégorie optionnelle
        category = guild.get_channel(CATEGORY_TICKETS_ID) if CATEGORY_TICKETS_ID else None
        
        # Création du salon textuel personnalisé
        channel_name = f"{ticket_type}-{user.name}"
        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"Ticket {ticket_type} créé par {user.name}"
        )
        
        await interaction.followup.send(f"✅ Ton ticket a été créé ici : {ticket_channel.mention}", ephemeral=True)
        
        # Redirection du comportement selon le bouton cliqué
        if ticket_type == "aide":
            await self.handle_help_ticket(ticket_channel, user)
        elif ticket_type == "minecraft":
            await self.handle_minecraft_ticket(ticket_channel, user, interaction.client)

    async def handle_help_ticket(self, channel: discord.TextChannel, user: discord.User):
        embed = create_embed(
            title="❓ Ticket d'Assistance",
            description=f"Bonjour {user.mention},\n\nUn membre de l'équipe de management va t'installer et répondre à ta demande sous peu. Laisse un message décrivant ton problème.",
            color=discord.Color.blue()
        )
        await channel.send(embed=embed)

    async def handle_minecraft_ticket(self, channel: discord.TextChannel, user: discord.User, bot: commands.Bot):
        embed = create_embed(
            title="🔗 Liaison de compte Minecraft",
            description=(
                f"Bienvenue dans ton ticket {user.mention} !\n\n"
                "Pour rejoindre notre serveur et lier ton compte Discord à la boutique, "
                "veuillez répondre ci-dessous avec votre **pseudo Minecraft exact uniquement**.\n\n"
                "⚠️ *Pas d'espace, pas d'emojis ni de caractères spéciaux.*"
            ),
            color=discord.Color.green()
        )
        await channel.send(embed=embed)

        def check(message):
            return message.author.id == user.id and message.channel.id == channel.id

        try:
            # Attente de la réponse du joueur (Timeout 5 minutes)
            msg = await bot.wait_for("message", check=check, timeout=300.0)
            minecraft_pseudo = msg.content.strip()

            # Sécurité syntaxe pseudo Minecraft
            if len(minecraft_pseudo) > 16 or " " in minecraft_pseudo:
                embed_error = create_embed(
                    title="❌ Pseudo invalide",
                    description="Un pseudo Minecraft valide fait 16 caractères maximum et ne contient pas d'espace. Ferme ce ticket et réessaie.",
                    color=discord.Color.red()
                )
                await channel.send(embed=embed_error)
                return

            # Synchronisation ORM Base de données
            with db.get_session() as session:
                # 🔍 1. Vérification si le pseudo est déjà utilisé par un AUTRE utilisateur
                existing_user = session.query(User).filter(
                    User.minecraft_username == minecraft_pseudo
                ).first()

                if existing_user and existing_user.id != str(user.id):
                    embed_taken = create_embed(
                        title="❌ Pseudo déjà utilisé",
                        description=(
                            f"Le pseudo Minecraft **{minecraft_pseudo}** est déjà lié à un autre compte Discord.\n\n"
                            "Si tu penses qu'il s'agit d'une erreur ou de ton ancien compte, contacte un administrateur."
                        ),
                        color=discord.Color.red()
                    )
                    await channel.send(embed=embed_taken)
                    return

                # 🔍 2. Recherche ou création du profil de l'utilisateur actuel
                with db.get_session() as session:
                    user_data = session.query(User).filter(
                        User.discord_id == user.id
                    ).first()
            
                if not user_data:
                    user_data = User(id=str(user.id), craftycoin_balance=0)
                    session.add(user_data)
            
                # Enregistrement du pseudo Minecraft
                user_data.minecraft_username = minecraft_pseudo
                session.commit()

            # 🎮 3. Ajout automatique sur la Whitelist Minecraft via RCON
            whitelist_status = "Enregistré en base de données."
            
            if crafty_api.SERVER_ID:  # Vérifie que l'API Crafty est configurée avant de tenter l'ajout
                try:
                    # Envoi de la commande de whitelist en jeu
                    command = f"/whitelist add {minecraft_pseudo}"
                    await crafty_api.envoyer_commande(command)
                    print(f"Commande envoyée : {command}")
                    whitelist_status = "L'accès au serveur Minecraft a été validé et tu as été ajouté à la **Whitelist** en jeu !"
                except Exception as rcon_err:
                    log.error(f"❌ Erreur RCON lors de l'ajout à la whitelist de {minecraft_pseudo} : {rcon_err}")
                    whitelist_status = "Liaison DB validée, mais l'ajout automatique en jeu a échoué (serveur Minecraft injoignable)."

            embed_success = create_embed(
                title="✅ Whitelist & Liaison OK",
                description=(
                    f"Ton compte Discord est lié au joueur : **{minecraft_pseudo}**.\n\n"
                    f"{whitelist_status}\n\n"
                    "Tu peux dès à présent utiliser la boutique !"
                ),
                color=discord.Color.green()
            )
            await channel.send(embed=embed_success)
            log.info(f"🔗 Liaison réussie via bouton : {user.name} ↔ {minecraft_pseudo}")

        except asyncio.TimeoutError:
            await channel.send("⏳ Temps écoulé ! Le processus s'est arrêté. Tu peux fermer ce salon.")
        except Exception as e:
            log.error(f"Erreur lors de la liaison automatique : {e}", exc_info=True)


class TicketsCog(commands.Cog):
    """Cog principal pour gérer l'initialisation du système de tickets"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Enregistre la vue pour qu'elle intercepte les clics même après un reboot du bot
        self.bot.add_view(TicketButtonsView())
        log.info("🔒 Vue persistante des tickets enregistrée")

    @app_commands.command(name="setup-tickets", description="Déploie le panel de boutons de tickets (Admin only)")
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, interaction: discord.Interaction):
        """Commande permettant d'injecter l'embed et les boutons dans le bon salon"""
        if not TICKET_CHANNEL_ID:
            await interaction.response.send_message(
                "❌ Impossible de déployer : l'ID du salon est mal configuré.", 
                ephemeral=True
            )
            return

        target_channel = interaction.guild.get_channel(TICKET_CHANNEL_ID)
        
        if not target_channel:
            await interaction.response.send_message(
                f"❌ Le salon configuré (ID: {TICKET_CHANNEL_ID}) est introuvable sur ce serveur.", 
                ephemeral=True
            )
            return

        embed = create_embed(
            title="🎫 Support & Connexion Serveur",
            description=(
                "Bienvenue sur l'interface d'accès de notre communauté !\n\n"
                "**❓ Demander de l'aide** : Ouvre un ticket d'assistance pour toute question ou problème.\n"
                "**🎮 Se connecter à Minecraft** : Lance le processus de Whitelist et lie ton compte pour utiliser la boutique Discord."
            ),
            color=discord.Color.purple()
        )
        
        # Envoi de l'interface avec les boutons dans le salon configuré
        await target_channel.send(embed=embed, view=TicketButtonsView())
        await interaction.response.send_message("✅ Panel de tickets déployé avec succès !", ephemeral=True)


async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
    log.info("✅ TicketsCog chargé")