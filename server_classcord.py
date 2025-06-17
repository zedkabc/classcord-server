import socket
import threading
import json
import os
import logging

HOST = "0.0.0.0"
PORT = 12345
DATA_FILE = "users.json"
LOCK = threading.Lock()
clients = []  # 🆕 Liste des connexions client

# Configuration du log
LOG_PATH = "/var/log/classcord/classcord.log"
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Chargement ou création de la base utilisateurs
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        USERS = json.load(f)
else:
    USERS = {}

logging.info(f"Utilisateurs chargés: {list(USERS.keys())}")

def save_users():
    with LOCK:
        with open(DATA_FILE, "w") as f:
            json.dump(USERS, f)
        logging.info("Utilisateurs sauvegardés.")

def broadcast(message, sender_conn=None):
    """Envoie un message à tous les clients connectés sauf l'émetteur"""
    data = json.dumps({"type": "message", "content": message}).encode()
    with LOCK:
        for client in clients:
            if client != sender_conn:
                try:
                    client.sendall(data)
                except Exception as e:
                    logging.error(f"Erreur d'envoi à un client : {e}")

def handle_client(conn, address):
    global clients
    logging.info(f"Connexion depuis {address}")
    username = None
    with LOCK:
        clients.append(conn)
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            try:
                msg = json.loads(data.decode())
            except json.JSONDecodeError:
                continue

            if msg["type"] == "login":
                username = msg["username"]
                with LOCK:
                    USERS[username] = {"state": "online", "address": address[0]}
                logging.info(f"{username} connecté")
                broadcast(f"{username} a rejoint le chat.", conn)
                save_users()
            elif msg["type"] == "message":
                logging.info(f"{username} >> {msg['content']}")
                broadcast(f"{username}: {msg['content']}", conn)
            elif msg["type"] == "status":
                with LOCK:
                    USERS[username]["state"] = msg["state"]
                logging.info(f"{username} est maintenant {msg['state']}")
                save_users()
    except Exception as e:
        logging.error(f"Problème avec {address} ({username}): {e}")
    finally:
        with LOCK:
            if username and username in USERS:
                USERS[username]["state"] = "offline"
            if conn in clients:
                clients.remove(conn)
            save_users()
        logging.info(f"{address} déconnecté")
        broadcast(f"{username} s'est déconnecté.", conn)
        conn.close()

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        logging.info(f"Serveur démarré sur {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.daemon = True
            client_thread.start()

if __name__ == "__main__":
    main()
