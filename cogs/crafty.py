"""Cog Crafty - Commandes regroupées sous la racine /gestion"""

import discord
from discord.ext import commands
from discord import app_commands
import crafty_api
from utils import (
    format_server_status_embed, format_error_embed, format_success_embed,
    get_logger
)
from core.decorators import (
    log_command, defer_interaction, require_manager_minecraft,
    require_manager_crafty, handle_errors
)

logger = get_logger(__name__)


class CraftyCog(commands.Cog):
    """Commandes pour la gestion centralisée du panel et serveur Minecraft"""
    
    def __init__(self, bot):
        self.bot = bot

    # 1. Déclaration de la commande racine parente
    gestion = app_commands.Group(
        name="gestion", 
        description="Commande principale de gestion globale du serveur et de Crafty"
    )

    # 2. Déclaration du sous-groupe : /gestion server [...]
    server_group = app_commands.Group(
        name="server", 
        description="Commandes liées au contrôle du serveur Minecraft", 
        parent=gestion
    )

    # 3. Déclaration du sous-groupe : /gestion users [...]
    users_group = app_commands.Group(
        name="users", 
        description="Commandes liées aux utilisateurs de l'infrastructure Crafty", 
        parent=gestion
    )

    # 4. Déclaration du sous-groupe : /gestion backup [...]
    backup_group = app_commands.Group(
        name="backup", 
        description="Commandes liées aux sauvegardes du serveur", 
        parent=gestion
    )

    # --- SUBCOMMANDS: /gestion server ... ---

    @server_group.command(name="status", description="Affiche le statut en temps réel du serveur")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    @defer_interaction(ephemeral=True)
    @log_command
    @handle_errors
    async def status(self, interaction: discord.Interaction):
        data = await crafty_api.obtenir_stats_crafty()
        
        if "erreur" in data:
            embed = format_error_embed("Erreur", data["erreur"])
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        is_online = data.get("running", False)
        players = data.get("online_players", 0)
        max_players = data.get("max_players", 20)
        cpu = data.get("cpu", None)
        memory = data.get("memory", None)
        server_name = data.get("name", "Serveur Minecraft")
        
        embed = format_server_status_embed(
            is_online=is_online, players=players, max_players=max_players, cpu=cpu, memory=memory
        )
        embed.title = f"Statut - {server_name}"
        embed.set_footer(text="Mis à jour en direct")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @server_group.command(name="demarrer", description="Démarre le serveur Minecraft")
    @require_manager_minecraft()
    @defer_interaction(ephemeral=False)
    @log_command
    @handle_errors
    async def demarrer(self, interaction: discord.Interaction):
        result = await crafty_api.demarrer_serveur()
        
        if result.get("success"):
            embed = format_success_embed("Serveur en démarrage", "L'ordre de démarrage a été transmis à Crafty.")
            await interaction.followup.send(embed=embed)
        else:
            embed = format_error_embed("Erreur", result.get("erreur", "Erreur inconnue"))
            await interaction.followup.send(embed=embed, ephemeral=True)

    @server_group.command(name="arreter", description="Arrête proprement le serveur Minecraft")
    @require_manager_minecraft()
    @defer_interaction(ephemeral=False)
    @log_command
    @handle_errors
    async def arreter(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚠️ Confirmation requise",
            description="Êtes-vous sûr de vouloir arrêter le serveur Minecraft ?",
            color=discord.Color.orange()
        )
        
        yes_button = discord.ui.Button(label="Oui, éteindre", style=discord.ButtonStyle.danger)
        no_button = discord.ui.Button(label="Annuler", style=discord.ButtonStyle.secondary)
        
        async def yes_callback(btn_interaction: discord.Interaction):
            await btn_interaction.response.defer()
            result = await crafty_api.arreter_serveur()
            if result.get("success"):
                embed_success = format_success_embed("Serveur en cours d'arrêt", "L'extinction programmée est initiée.")
                await btn_interaction.followup.send(embed=embed_success)
            else:
                embed_err = format_error_embed("Erreur", result.get("erreur", "Erreur inconnue"))
                await btn_interaction.followup.send(embed=embed_err, ephemeral=True)
        
        async def no_callback(btn_interaction: discord.Interaction):
            await btn_interaction.response.defer()
            await btn_interaction.followup.send("Action d'arrêt annulée.", ephemeral=True)
        
        yes_button.callback = yes_callback
        no_button.callback = no_callback
        
        view = discord.ui.View()
        view.add_item(yes_button)
        view.add_item(no_button)
        await interaction.followup.send(embed=embed, view=view)

    @server_group.command(name="redemarrer", description="Redémarre le serveur Minecraft")
    @require_manager_minecraft()
    @defer_interaction(ephemeral=False)
    @log_command
    @handle_errors
    async def redemarrer(self, interaction: discord.Interaction):
        result = await crafty_api.redemarrer_serveur()
        
        if result.get("success"):
            embed = format_success_embed("Redémarrage en cours", "Le serveur redémarre.")
            await interaction.followup.send(embed=embed)
        else:
            embed = format_error_embed("Erreur", result.get("erreur", "Erreur inconnue"))
            await interaction.followup.send(embed=embed, ephemeral=True)

    @server_group.command(name="cmd", description="Envoie une commande brute à la console")
    @app_commands.describe(commande="Commande Minecraft (ex: say Hello, op Pseudo...)")
    @require_manager_crafty()
    @defer_interaction(ephemeral=False)
    @log_command
    @handle_errors
    async def cmd(self, interaction: discord.Interaction, commande: str):
        if commande.startswith("/"):
            commande = commande[1:]  # Crafty n'a pas besoin du slash initial en console
        
        result = await crafty_api.envoyer_commande(commande)
        
        if result.get("success"):
            embed = format_success_embed("Commande exécutée", f"```\n> {commande}\n```")
            await interaction.followup.send(embed=embed)
        else:
            embed = format_error_embed("Erreur", result.get("erreur", "Erreur de transmission"))
            await interaction.followup.send(embed=embed, ephemeral=True)

    @server_group.command(name="logs", description="Affiche les dernières lignes de la console")
    @require_manager_crafty()
    @defer_interaction(ephemeral=True)
    @log_command
    @handle_errors
    async def logs(self, interaction: discord.Interaction):
        logs_data = await crafty_api.obtenir_logs()
        if not logs_data:
            await interaction.followup.send("Impossible de récupérer les logs ou aucun log trouvé.", ephemeral=True)
            return
            
        # On vérifie si l'API renvoie des dictionnaires ou des chaînes brutes pour éviter tout crash
        lignes_logs = []
        for log in logs_data[-15:]:
            if isinstance(log, dict):
                lignes_logs.append(log.get("line", ""))
            else:
                lignes_logs.append(str(log))
                
        texte_logs = "\n".join(lignes_logs)
        
        embed = discord.Embed(title="Logs du serveur",
            description=f"```text\n{texte_logs}\n```",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Affichage des 15 dernières lignes")
        await interaction.followup.send(embed=embed, ephemeral=True)


    # --- SUBCOMMANDS: /gestion users ... ---

    @users_group.command(name="list", description="Liste les utilisateurs configurés sur le panel Crafty")
    @require_manager_crafty()
    @defer_interaction(ephemeral=True)
    @log_command
    @handle_errors
    async def list_users(self, interaction: discord.Interaction):
        result = await crafty_api.obtenir_utilisateurs()
        if not result:
            await interaction.followup.send("Impossible de récupérer les utilisateurs ou aucun utilisateur trouvé.", ephemeral=True)
            return
        users = []
        for user in result:
            if isinstance(user, dict):
                users.append(user)
            else:
                users.append({"username": str(user), "role": {"name": "Aucun rôle"}})
        if not users:
            await interaction.followup.send("Aucun utilisateur trouvé sur le panel Crafty.", ephemeral=True)
            return
            
        texte_users = ""
        print(users)
        for u in users:
            try :
                username = u.get("username", "Inconnu")
                if u.get("superuser") == True:
                    role = "Administrateur (Superuser)"
                else:
                    role = "Utilisateur"
                created_at = u.get("created", "Date inconnue")

                if u.get("enabled") == True:
                    activ = "Actif"
                else:
                    activ = "Inactif"

                texte_users += f"• **{username}** — Rôle : `{role}` — Compte créé le {created_at} — Compte {activ} \n"
            except Exception as e:
                logger.error(f"Erreur en traitant un utilisateur Crafty: {e}")
                texte_users += f"• **{str(u)}** — Impossible de récupérer les détails\n"
                embed = format_error_embed("Erreur")
                await interaction.followup.send(embed=embed, ephemeral=True)
                continue
            
            embed = discord.Embed(
                title="Utilisateurs Crafty",
                description=texte_users,
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            


    # --- SUBCOMMANDS: /gestion backup ... ---

    
    @backup_group.command(name="creer", description="Déclenche la création d'une nouvelle sauvegarde")
    @require_manager_minecraft()
    @defer_interaction(ephemeral=False)
    @log_command
    @handle_errors
    async def creer_backup(self, interaction: discord.Interaction):
        result = await crafty_api.creer_sauvegarde()
        
        if result.get("success"):
            embed = format_success_embed(
                "Sauvegarde lancée", 
                "La création d'une nouvelle sauvegarde a été demandée avec succès."
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = format_error_embed("Erreur", result.get("erreur", "Échec du lancement de la sauvegarde."))
            await interaction.followup.send(embed=embed, ephemeral=True)


# --- FONCTION D'ENTRÉE POUR DISCORD.PY ---
async def setup(bot):
    """Permet au bot d'enregistrer et de charger ce Cog"""
    await bot.add_cog(CraftyCog(bot))
