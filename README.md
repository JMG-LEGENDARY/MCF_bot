# JMG Bot v2 🤖

Bot Discord pour gestion d'un serveur Minecraft avec système d'économie CraftyCoin.

## 📋 Fonctionnalités

- **Serveur Minecraft (Crafty)**: Gestion du serveur avec démarrage/arrêt/statut
- **Économie CraftyCoin**: Système de récompense basé sur l'activité Discord et Minecraft
- **Shop**: Boutique pour acheter des items Minecraft avec CraftyCoins
- **Anti-spam**: Détection de copier-coller et AFK en vocal
- **Événements Minecraft**: Détection des joueurs qui rejoignent/quittent
- **Messages personnalisés**: Messages de bienvenue/au revoir randomisés

## 🏗️ Structure du Projet

```
JMG_BOT v2/
├── main.py                 # Point d'entrée du bot
├── config.py              # Configuration centralisée (.env)
├── crafty_api.py          # Intégration API Crafty
├── requirements.txt       # Dépendances Python
│
├── cogs/                  # Modules fonctionnalités
│   ├── commands.py        # Commandes générales
│   ├── admin.py          # Commandes administrateur
│   ├── crafty.py         # Gestion serveur Minecraft
│   ├── economy.py        # Système CraftyCoin (TODO)
│   ├── minecraft.py      # Événements Minecraft (TODO)
│   └── config.py         # Configuration Discord (TODO)
│
├── core/                 # Modules noyau
│   ├── decorators.py     # Décorateurs (checks, logging)
│   └── constants.py      # Constantes globales
│
├── db/                   # Gestion base de données
│   ├── database.py       # Connexion et helpers SQLAlchemy
│   └── models.py         # Modèles SQLAlchemy
│
├── utils/                # Utilitaires
│   ├── logger.py         # Configuration logging
│   ├── formatters.py     # Formateurs Discord embeds
│   └── helpers.py        # Fonctions utilitaires
│
└── logs/                 # Fichiers de log
```

## 🚀 Installation

### 1. Prérequis
- Python 3.10+
- pip

### 2. Configuration de l'environnement

```bash
# Créer un venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate      # Windows

# Installer les dépendances
pip install -r requirements.txt

# Copier le fichier de configuration
cp .env.example .env
```

### 3. Remplir le fichier `.env`

```env
# Bot Discord
BOT_TOKEN=votre_token_ici
MC_JOIN_TOKEN=token_du_bot_minecraft

# Crafty
CRAFTY_BASE_URL=https://votre_ip:8443
CRAFTY_API_TOKEN=votre_token_crafty
CRAFTY_SERVER_ID=id_du_serveur

# Discord
MCF_GUILD_ID=id_du_serveur_discord
# ... (voir .env.example pour tous les IDs)

# Économie
MESSAGE_CHARACTER_RATE=0.1
VOICE_EARNING_RATE=0.5
```

### 4. Démarrer le bot

```bash
python main.py
```

## 💰 Système d'Économie

### Comment gagner des CraftyCoins

| Activité | Revenu de base | Multiplicateur |
|----------|---|---|
| Message Discord | 0.1 × caractères | 1.0x |
| Réponse aux gens | Même que message | 1.5x |
| Aide apportée | Même que message | 2.0x |
| Temps vocal | 0.5 par minute | 1.0x |
| Playtime Minecraft | Basé sur durée | 1.0x |
| Récompense quotidienne | 10 CC | +1.5x par jour |

### Anti-spam

- Détection de copier-coller : les messages similaires à >85% sont flaggés
- Détection AFK vocal : timeout après 10 minutes d'inactivité
- Limite de messages : délai de spam prevention (5s)

### Shop

1. Joueur achète un item (débité de CraftyCoins)
2. Achat enregistré dans "pending_purchases"
3. Quand le joueur rejoint Minecraft → `/give` automatique
4. Statut = "completed"

## 🔧 Configuration

Tous les IDs Discord, rôles, et canaux sont configurables via `.env`.

### Rôles importants

- `manager_minecraft`: Peut arrêter/démarrer le serveur
- `manager_discord`: Gestion Discord
- `manager_crafty`: Gestion Crafty
- `createurs`: Accès aux commandes de créateur

## 📝 Commandes (TODO)

## 🗄️ Base de Données

Utilise SQLAlchemy + SQLite pour stockage persistant:
- Users (Discord + Minecraft data)
- ShopItems & PendingPurchases
- Transactions (historique CraftyCoin)
- GameSessions (playtime tracking)
- AntiSpamRecords (détection copier-coller)
- VoiceActivity (AFK detection)

## 📊 Logging

- Console + Fichiers (logs/)
- Rotation automatique des logs
- Erreurs séparées (errors.log)
- Niveau configurable via `.env`

## ⚠️ Sécurité

- **Jamais commiter le fichier `.env`** (tokens sensibles)
- `.env` est ignoré par `.gitignore`
- Utiliser `.env.example` pour la documentation

## 🛠️ Développement

### Ajouter un nouveau cog

```python
# cogs/my_feature.py
import discord
from discord.ext import commands
from core.decorators import log_command

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="mycommand")
    @log_command
    async def my_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello!")

async def setup(bot):
    await bot.add_cog(MyCog(bot))
```

### Ajouter une transaction

```python
from db import db, add_transaction

with db.get_session() as session:
    add_transaction(
        session=session,
        user_id=user.id,
        amount=10.0,
        transaction_type="message",
        description="Message envoyé",
        multiplier=1.5
    )
```

## 📞 Support

Questions ? Contactez les Managers ou consultez les logs.

---

**Dernière mise à jour**: Juin 2026 | **Version**: 2.0.0
