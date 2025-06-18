import socket
import threading
import json
import pickle
import os
import logging
import sqlite3
from datetime import datetime

HOST = '0.0.0.0'
PORT = 12345

USER_FILE = 'users.pkl'
DB_FILE = 'classcord.db'
LOG_FILE = '/home/louka/classcord-server/debug.log'

CLIENTS = {}  # socket: username
USERS = {}    # username: password
LOCK = threading.Lock()

# Configuration du logger pour écrire dans debug.log et console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

logger.info("=== Serveur ClassCord démarrage ===")

# -- Initialisation base SQLite --
def init_database():
    logger.debug("Initialisation de la base SQLite")
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                state TEXT,
                last_seen TEXT
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                content TEXT,
                timestamp TEXT
            );
        """)
        conn.commit()
    logger.debug("Base SQLite initialisée")

# -- Mise à jour statut utilisateur --
def update_user_status(username, state):
    logger.debug(f"[DB] update_user_status appelé : {username} => {state}")
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, state, last_seen)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(username) DO UPDATE SET
                state = excluded.state,
                last_seen = datetime('now');
        """, (username, state))
        conn.commit()

# -- Récupération liste des connectés --
def list_online_users():
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE state = 'online'")
        rows = cursor.fetchall()
        users = [row[0] for row in rows]
        logger.debug(f"[DB] Utilisateurs en ligne : {users}")
        return users

# -- Chargement/sauvegarde utilisateurs depuis fichier .pkl --
def load_users():
    global USERS
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'rb') as f:
            USERS = pickle.load(f)
    logger.info(f"[INIT] Utilisateurs chargés: {list(USERS.keys())}")

def save_users():
    with open(USER_FILE, 'wb') as f:
        pickle.dump(USERS, f)
    logger.info("[SAVE] Utilisateurs sauvegardés.")

# -- Envoi message à tous, y compris émetteur --
def broadcast(message, sender_socket=None):
    to_remove = []
    for client_socket, username in CLIENTS.items():
        try:
            client_socket.sendall((json.dumps(message) + '\n').encode())
            logger.info(f"[ENVOI] Message envoyé à {username} : {message}")
        except Exception as e:
            logger.error(f"[ERREUR] Échec d'envoi à {username} : {e}")
            to_remove.append(client_socket)
    # Nettoyage des sockets défaillants
    with LOCK:
        for sock in to_remove:
            CLIENTS.pop(sock, None)
            try:
                sock.close()
            except:
                pass

# -- Envoi message système (nouveaux arrivants, alertes, départs) --
def send_system_message(content):
    message = {
        'type': 'system',
        'content': content,
        'timestamp': datetime.now().isoformat()
    }
    logger.info(f"[SYSTEM MESSAGE] {content}")
    broadcast(message)

# -- Traitement client --
def handle_client(client_socket):
    buffer = ''
    username = None
    address = client_socket.getpeername()
    logger.info(f"[CONNEXION] Nouvelle connexion depuis {address}")
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                logger.info(f"[RECU] {address} >> {line}")
                msg = json.loads(line)

                if msg['type'] == 'register':
                    with LOCK:
                        if msg['username'] in USERS:
                            response = {'type': 'error', 'message': 'Username already exists.'}
                        else:
                            USERS[msg['username']] = msg['password']
                            save_users()
                            response = {'type': 'register', 'status': 'ok'}
                        client_socket.sendall((json.dumps(response) + '\n').encode())

                elif msg['type'] == 'login':
                    with LOCK:
                        if USERS.get(msg['username']) == msg['password']:
                            username = msg['username']
                            CLIENTS[client_socket] = username
                            update_user_status(username, 'online')
                            response = {'type': 'login', 'status': 'ok'}
                            client_socket.sendall((json.dumps(response) + '\n').encode())
                            broadcast({'type': 'status', 'user': username, 'state': 'online'}, client_socket)
                            logger.info(f"[LOGIN] {username} connecté")

                            # Envoi liste des connectés au client
                            online_users = list_online_users()
                            client_socket.sendall((json.dumps({
                                'type': 'list_users',
                                'users': online_users
                            }) + '\n').encode())

                            # Message système de bienvenue
                            send_system_message(f"{username} vient de rejoindre le chat.")

                        else:
                            response = {'type': 'error', 'message': 'Login failed.'}
                            client_socket.sendall((json.dumps(response) + '\n').encode())

                elif msg['type'] == 'list_users':
                    online_users = list_online_users()
                    response = {'type': 'list_users', 'users': online_users}
                    client_socket.sendall((json.dumps(response) + '\n').encode())

                elif msg['type'] == 'message':
                    if not username:
                        username = msg.get('from', 'invité')
                        with LOCK:
                            CLIENTS[client_socket] = username
                        logger.info(f"[INFO] Connexion invitée détectée : {username}")

                    msg['from'] = username
                    msg['timestamp'] = datetime.now().isoformat()

                    try:
                        with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO messages (sender, content, timestamp)
                                VALUES (?, ?, ?)
                            """, (username, msg['content'], msg['timestamp']))
                            conn.commit()
                        logger.debug(f"[DB] Message enregistré pour {username}")
                    except Exception as e:
                        logger.error(f"[ERREUR DB] Impossible d'enregistrer le message : {e}")

                    logger.info(f"[MSG] {username} >> {msg['content']}")
                    broadcast(msg)  # Diffuse aussi au client qui envoie

                elif msg['type'] == 'status' and username:
                    update_user_status(username, msg['state'])
                    broadcast({'type': 'status', 'user': username, 'state': msg['state']}, client_socket)
                    logger.info(f"[STATUS] {username} est maintenant {msg['state']}")

    except Exception as e:
        logger.error(f'[ERREUR] Problème avec {address} ({username}): {e}')
    finally:
        if username:
            update_user_status(username, 'offline')
            broadcast({'type': 'status', 'user': username, 'state': 'offline'}, client_socket)
            send_system_message(f"{username} a quitté le chat.")
        with LOCK:
            CLIENTS.pop(client_socket, None)
        client_socket.close()
        logger.info(f"[DECONNEXION] {address} déconnecté")

def main():
    init_database()
    load_users()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    logger.info(f"[DEMARRAGE] Serveur en écoute sur {HOST}:{PORT}")
    print(f"[INFO] Serveur en écoute sur {HOST}:{PORT}")
    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == '__main__':
    main()

import time

def admin_interface():
    """
    Interface texte d'administration côté serveur
    """
    print("[ADMIN] Interface admin démarrée")
    while True:
        print("\n--- MENU ADMIN CLASSCORD ---")
        print("1. Afficher clients actifs")
        print("2. Envoyer une alerte globale")
        print("3. Stopper un client")
        print("4. Quitter serveur")
        choice = input("Choix: ").strip()

        if choice == '1':
            print("Clients actifs :")
            with LOCK:
                for sock, user in CLIENTS.items():
                    try:
                        addr = sock.getpeername()
                    except Exception:
                        addr = "Inconnu"
                    print(f" - {user} @ {addr}")
        elif choice == '2':
            alert = input("Texte de l'alerte : ").strip()
            if alert:
                msg = {
                    'type': 'system',
                    'content': alert,
                    'timestamp': datetime.now().isoformat()
                }
                broadcast(msg)
                print("Alerte envoyée à tous les clients.")
        elif choice == '3':
            user_to_kick = input("Nom du client à stopper : ").strip()
            found = False
            with LOCK:
                for sock, user in list(CLIENTS.items()):
                    if user == user_to_kick:
                        print(f"Déconnexion de {user}...")
                        try:
                            sock.shutdown(socket.SHUT_RDWR)
                            sock.close()
                        except Exception as e:
                            print(f"Erreur en fermant la socket : {e}")
                        CLIENTS.pop(sock, None)
                        found = True
                        update_user_status(user, 'offline')
                        broadcast({'type': 'status', 'user': user, 'state': 'offline'})
                        break
            if not found:
                print(f"Aucun client nommé '{user_to_kick}' trouvé.")
        elif choice == '4':
            print("Arrêt du serveur demandé.")
            os._exit(0)  # Quitte immédiatement
        else:
            print("Choix invalide. Réessayez.")

def main():
    init_database()
    load_users()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    logging.info(f"[DEMARRAGE] Serveur en écoute sur {HOST}:{PORT}")
    print(f"[INFO] Serveur en écoute sur {HOST}:{PORT}")

    # Thread admin
    threading.Thread(target=admin_interface, daemon=True).start()

    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

