"""
API Crafty - Intégration complète avec Crafty Controller

Ce module gère toutes les requêtes asynchrones vers l'API de Crafty Controller
pour administrer et suivre l'état du serveur Minecraft.
"""

import asyncio
import logging
from typing import Any, Dict, List, Union
from urllib.parse import parse_qs, urlparse

import aiohttp

from config import config
from utils import get_logger

# Initialisation du logger
logger = get_logger(__name__)

# --- CONFIGURATION DE L'API ---
CRAFTY_BASE_URL: str = config.CRAFTY_BASE_URL
SERVER_ID: str = config.CRAFTY_SERVER_ID
HEADERS: Dict[str, str] = {
    "Authorization": f"Bearer {config.CRAFTY_API_TOKEN}",
    "Content-Type": "application/json",
}


async def obtenir_stats_crafty() -> Dict[str, Any]:
    """
    Interroge l'API Crafty pour obtenir les statistiques en temps réel du serveur.

    Returns:
        Dict[str, Any]: Un dictionnaire contenant les statistiques du serveur
                        ou un message d'erreur.
    """
    if not SERVER_ID:
        return {"erreur": "ID de serveur manquant dans la configuration"}

    endpoint = f"{CRAFTY_BASE_URL}/api/v2/servers/{SERVER_ID}/stats"
    timeout_val = config.TIMEOUTS.get("crafty_api_timeout", 10)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                endpoint,
                headers=HEADERS,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=timeout_val)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {})
                elif response.status == 401:
                    return {"erreur": "Token Crafty invalide (401)"}
                else:
                    return {"erreur": f"Erreur Crafty ({response.status})"}
                    
    except asyncio.TimeoutError:
        return {"erreur": "Timeout: Crafty ne répond pas"}
    except Exception as e:
        logger.error(f"Erreur lors de l'appel à Crafty: {e}")
        return {"erreur": f"Impossible de joindre Crafty: {e}"}


async def demarrer_serveur() -> Dict[str, Union[bool, str]]:
    """
    Envoie une requête pour démarrer le serveur Minecraft.

    Returns:
        Dict[str, Union[bool, str]]: Résultat de l'action (succès ou erreur).
    """
    endpoint = f"{CRAFTY_BASE_URL}/api/v2/servers/{SERVER_ID}/action/start"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint,
                headers=HEADERS,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status in [200, 204]:
                    logger.info("✅ Serveur démarré")
                    return {"success": True, "message": "Serveur en cours de démarrage..."}
                else:
                    text = await response.text()
                    return {"success": False, "erreur": f"Erreur {response.status}: {text}"}
                    
    except Exception as e:
        logger.error(f"Erreur au démarrage: {e}")
        return {"success": False, "erreur": str(e)}


async def arreter_serveur() -> Dict[str, Union[bool, str]]:
    """
    Envoie une requête pour arrêter proprement le serveur Minecraft.

    Returns:
        Dict[str, Union[bool, str]]: Résultat de l'action (succès ou erreur).
    """
    endpoint = f"{CRAFTY_BASE_URL}/api/v2/servers/{SERVER_ID}/action/stop"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint,
                headers=HEADERS,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status in [200, 204]:
                    logger.info("✅ Serveur arrêté")
                    return {"success": True, "message": "Serveur arrêt en cours..."}
                else:
                    text = await response.text()
                    return {"success": False, "erreur": f"Erreur {response.status}: {text}"}
                    
    except Exception as e:
        logger.error(f"Erreur à l'arrêt: {e}")
        return {"success": False, "erreur": str(e)}


async def redemarrer_serveur() -> Dict[str, Union[bool, str]]:
    """
    Envoie une requête pour redémarrer le serveur Minecraft.

    Returns:
        Dict[str, Union[bool, str]]: Résultat de l'action (succès ou erreur).
    """
    endpoint = f"{CRAFTY_BASE_URL}/api/v2/servers/{SERVER_ID}/action/restart"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint,
                headers=HEADERS,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status in [200, 204]:
                    logger.info("✅ Serveur redémarré")
                    return {"success": True, "message": "Serveur en cours de redémarrage..."}
                else:
                    text = await response.text()
                    return {"success": False, "erreur": f"Erreur {response.status}: {text}"}
                    
    except Exception as e:
        logger.error(f"Erreur au redémarrage: {e}")
        return {"success": False, "erreur": str(e)}


async def envoyer_commande(commande: str) -> Dict[str, Union[bool, str]]:
 
    endpoint = f"{CRAFTY_BASE_URL}/api/v2/servers/{SERVER_ID}/stdin"
    print(endpoint)
    
    # Payload d'origine conservé pour compatibilité
    payload = {
        "command": commande
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint,
                data=commande,
                headers=HEADERS,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status in [200, 204]:
                    logger.info(f"✅ Commande envoyée: {commande}")
                    return {"success": True, "message": "Commande envoyée"}
                else:
                    text = await response.text()
                    return {"success": False, "erreur": f"Erreur {response.status}: {text}"}
                    
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de commande: {e}")
        return {"success": False, "erreur": str(e)}


async def obtenir_logs() -> List[Dict[str, Any]]:
    """
    Récupère l'historique des derniers logs de la console du serveur.

    Returns:
        List[Dict[str, Any]]: Liste des lignes de logs renvoyées par l'API.
    """
    endpoint = f"{CRAFTY_BASE_URL}/api/v2/servers/{SERVER_ID}/logs"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                endpoint,
                headers=HEADERS,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                else:
                    return []
                    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des logs: {e}")
        return []