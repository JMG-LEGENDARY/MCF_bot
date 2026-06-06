import json
import time
import threading
import requests
import websocket

# --- CONFIGURATION ---
CRAFTY_URL = "http://localhost:8000"  # Remplace par l'IP/Port de ton Crafty
CRAFTY_WS_URL = "ws://localhost:8000/ws"  # URL WebSocket (souvent /ws ou /api/v2/ws selon la version)

API_TOKEN = "TON_API_TOKEN_ICI"
SERVER_ID = "TON_SERVER_ID_ICI"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# --- 1. FONCTIONS API REST (Interactions) ---

def send_command(command):
    """Envoie une commande à la console du serveur Minecraft"""
    url = f"{CRAFTY_URL}/api/v2/servers/{SERVER_ID}/command"
    payload = {"command": command}
    
    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        if response.status_code == 200:
            print(f"[Bot] Commande envoyée avec succès : {command}")
            return response.json()
        else:
            print(f"[Erreur API] {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[Erreur Connexion] {e}")

def get_server_stats():
    """Récupère l'état du serveur (joueurs en ligne, RAM, etc.)"""
    url = f"{CRAFTY_URL}/api/v2/servers/{SERVER_ID}/stats"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        # Exemple pour extraire les joueurs (la structure exacte dépend de la version de Crafty)
        print(f"[Stats] Joueurs connectés : {data.get('data', {}).get('online_players', 0)}")
        return data
    return None


# --- 2. WEBSOCKET (Lecture des Logs en Temps Réel) ---

def on_message(ws, message):
    """Gère les messages reçus du WebSocket de Crafty"""
    data = json.loads(message)
    
    # Crafty envoie beaucoup de données (stats, logs, etc.)
    # On filtre pour ne garder que ce qui nous intéresse
    msg_type = data.get("type")
    
    # Si c'est un log de console
    if msg_type == "console":
        log_line = data.get("data", {}).get("line", "")
        print(f"[Console MC] {log_line.strip()}")
        
        # Exemple d'interaction automatique : si un joueur se connecte
        if "joined the game" in log_line:
            player_name = log_line.split(" ")[0]
            print(f"[Bot Détection] {player_name} vient de se connecter !")
            # On peut saluer le joueur en jeu
            send_command(f"say Bienvenue {player_name} !")

def on_error(ws, error):
    print(f"[WS Erreur] {error}")

def on_close(ws, close_status_code, close_msg):
    print("[WS Connexion fermée]")

def on_open(ws):
    print("[WS Connexion établie] Écoute des logs...")
    # Certaines versions de Crafty demandent une authentification 
    # ou un abonnement spécifique après l'ouverture du WS
    auth_payload = {
        "action": "auth",
        "token": API_TOKEN
    }
    ws.send(json.dumps(auth_payload))

def start_websocket():
    """Lance le client WebSocket dans un thread séparé"""
    ws = websocket.WebSocketApp(
        CRAFTY_WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()

# --- Lancement du Bot ---
if __name__ == "__main__":
    # 1. On lance l'écoute des logs en arrière-plan
    ws_thread = threading.Thread(target=start_websocket)
    ws_thread.daemon = True
    ws_thread.start()
    
    # Attente que le WS se connecte
    time.sleep(2)
    
    # 2. Exemple d'interaction de test
    get_server_stats()
    send_command("list")
    
    # Boucle principale pour maintenir le script en vie
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Bot arrêté.")