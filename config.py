"""Configuration centralisée avec support .env"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables depuis .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


class Config:
    """Configuration de base du bot"""
    
    # --- DISCORD BOT ---
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    MC_JOIN_TOKEN: str = os.getenv("MC_JOIN_TOKEN", "")
    MINECRAFT_LOG_PATH: str = os.getenv("MINECRAFT_LOG_PATH", "")

    # --- BOT Minecraft ---
    MC_JOIN_ID = int(os.getenv("MC_JOIN_ID", "0"))
    
    # --- CRAFTY API ---
    CRAFTY_BASE_URL: str = os.getenv("CRAFTY_BASE_URL", "https://100.111.101.28:8443")
    CRAFTY_API_TOKEN: str = os.getenv("CRAFTY_API_TOKEN", "")
    CRAFTY_SERVER_ID: str = os.getenv("CRAFTY_SERVER_ID", "")
    
    # --- DISCORD SERVER ---
    MCF_GUILD_ID: int = int(os.getenv("MCF_GUILD_ID", "0"))
    
    # --- CHANNELS ---
    CHANNELS = {
        "gestion_mc": int(os.getenv("GESTION_MC_CHANNEL", "0")),
        "gestion_console": int(os.getenv("GESTION_CONSOLE_CHANNEL", "0")),
        "gestion_debian": int(os.getenv("GESTION_DEBIAN_CHANNEL", "0")),
        "logs": int(os.getenv("LOGS_CHANNEL", "0")),
        "commands": int(os.getenv("COMMANDS_CHANNEL", "0")),
        "boutique": int(os.getenv("BOUTIQUE_CHANNEL", "0")),
        "economie": int(os.getenv("ECONOMIE_CHANNEL", "0")),
        "quetes": int(os.getenv("QUETES_CHANNEL", "0")),
        "info": int(os.getenv("INFO_CHANNEL", "0")),
        "info_serveur": int(os.getenv("INFO_SERVEUR_CHANNEL", "0")),
        "signalement": int(os.getenv("SIGNALEMENT_CHANNEL", "0")),
        "modo_only": int(os.getenv("MODO_ONLY_CHANNEL", "0")),
        "ticket_channel": int(os.getenv("TICKET_CHANNEL_ID", "0"))
    }
    
    # --- ROLES ---
    ROLES = {
        "manager_ultim": int(os.getenv("MANAGER_ULTIM_ROLE", "0")),
        "next_ban": int(os.getenv("NEXT_BAN_ROLE", "0")),
        "manager_minecraft": int(os.getenv("MANAGER_MINECRAFT_ROLE", "0")),
        "manager_discord": int(os.getenv("MANAGER_DISCORD_ROLE", "0")),
        "manager_crafty": int(os.getenv("MANAGER_CRAFTY_ROLE", "0")),
        "createurs": int(os.getenv("CREATEURS_ROLE", "0")),
        "membres_serveur": int(os.getenv("MEMBRES_SERVEUR_ROLE", "0")),
    }
    
    # --- DATABASE ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./jmg_bot.db")
    
    # --- ECONOMY SETTINGS ---
    MESSAGE_CHARACTER_RATE: float = float(os.getenv("MESSAGE_CHARACTER_RATE", "0.1"))
    VOICE_EARNING_RATE: float = float(os.getenv("VOICE_EARNING_RATE", "0.5"))
    DAILY_REWARD_BASE: int = int(os.getenv("DAILY_REWARD_BASE", "10"))
    DAILY_REWARD_MULTIPLIER: float = float(os.getenv("DAILY_REWARD_MULTIPLIER", "1.5"))
    SPAM_PREVENTION_TIME: int = int(os.getenv("SPAM_PREVENTION_TIME", "5"))
    ANTI_COPYPASTE_THRESHOLD: float = float(os.getenv("ANTI_COPYPASTE_THRESHOLD", "0.85"))
    
    # --- ENVIRONMENT ---
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    TIMEOUTS = {
        "crafty_api": int(os.getenv("CRAFTY_API_TIMEOUT", "10"))
    }


def validate_config():
    """Valide que les tokens essentiels sont présents"""
    required = ["BOT_TOKEN", "CRAFTY_API_TOKEN", "CRAFTY_SERVER_ID"]
    missing = [var for var in required if not getattr(Config, var)]
    if missing:
        raise ValueError(f"Variables d'environnement manquantes: {', '.join(missing)}")
    return True


# Export pour usage facile
config = Config()

"""# === Discord Bot ===
BOT_TOKEN=
MC_JOIN_TOKEN=
#MC_JOIN_ID=1297710596505997425 de base
MC_JOIN_ID=1523385975189930118 #avec modification du nom

# === Crafty Server ===
CRAFTY_BASE_URL=https://100.82.172.73:8443
CRAFTY_API_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJpYXQiOjE3ODE5NTEwOTAsInRva2VuX2lkIjoxfQ.f545XqZ9BRxodPeQ9oM3QbLpBt-jqrylqur4xmLktqI
CRAFTY_SERVER_ID=6fd40185-e660-4620-b6a8-7f9654770b68

# === Discord Server & Channels ===
MCF_GUILD_ID=993457171759120424
GESTION_MC_CHANNEL=1302323091002626170
GESTION_CONSOLE_CHANNEL=1512030104690102412
GESTION_DEBIAN_CHANNEL=1512030347586441226
LOGS_CHANNEL=1324057375845646408
COMMANDS_CHANNEL=1315286059189534771
BOUTIQUE_CHANNEL=1325807725422317618
ECONOMIE_CHANNEL=1325416392379334727
QUETES_CHANNEL=1303751988630257674
INFO_CHANNEL=1258468979433934969
INFO_SERVEUR_CHANNEL=1318524054231187466
SIGNALEMENT_CHANNEL=1308826785563152414
MODO_ONLY_CHANNEL=1258297452763680799
TICKET_CHANNEL_ID = 1258491800310648864

# === Discord Roles ===
MANAGER_ULTIM_ROLE=1258299049942188032
NEXT_BAN_ROLE=1303310386778341457
MANAGER_MINECRAFT_ROLE=1258298144316456990
MANAGER_DISCORD_ROLE=1258299897396854875
MANAGER_CRAFTY_ROLE=1294371187006378115
CREATEURS_ROLE=1306304501199671386
MEMBRES_SERVEUR_ROLE=1306304501199671386

# === Database ===
DATABASE_URL=sqlite:///./jmg_bot.db

# === Economy Settings ===
MESSAGE_CHARACTER_RATE=0.1
VOICE_EARNING_RATE=0.5
DAILY_REWARD_BASE=10
DAILY_REWARD_MULTIPLIER=1.5
SPAM_PREVENTION_TIME=5
ANTI_COPYPASTE_THRESHOLD=0.85

# === Environment ===
DEBUG=False
LOG_LEVEL=INFO

crafty_api_timeout=10"""
