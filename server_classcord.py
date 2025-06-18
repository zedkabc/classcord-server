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
CLIENTS = {}  # socket: username
USERS = {}    # username: password
LOCK = threading.Lock()

# Logging vers fichier et console (niveau DEBUG pour console)
LOG_FILE = '/var/log/classcord.log'
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# -- Initialisation base SQLite --
def init_database():
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

# -- Mise à jour statut utilisateur --
def update_user_status(username, state):
    logging.debug(f"[DB] update_user_status called: {username} => {state}")
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
        logging.debug(f"[DB] Utilisateurs en ligne : {users}")
        return users

# -- Chargement/sauvegarde utilisateurs depuis fichier .pkl --
def load_users():
    global USERS
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'rb') as f:
            USERS = pickle.load(f)
    logging.info(f"[INIT] Utilisateurs chargés: {list(USERS.keys())}")

def save_users():
    with open(USER_FILE, 'wb') as f:
        pickle.dump(USERS, f)
    logging.info("[SAVE] Utilisateurs sauvegardés.")

# -- Envoi message à tous, y compris émetteur --
def broadcast(message, sender_socket=None):
    to_remove = []
    for client_socket, username in CLIENTS.items():
        try:
            client_socket.sendall((json.dumps(message) + '\n').encode())
            logging.debug(f"[ENVOI] Message envoyé à {username} : {message}")
        except Exception as e:
            logging.error(f"[ERREUR] Échec d'envoi à {username} : {e}")
            to_remove.append(client_socket)
    with LOCK:
        for sock in to_remove:
            CLIENTS.pop(sock, None)
            sock.close()

# -- Traitement client --
def handle_client(client_socket):
    buffer = ''
    username = None
    address = client_socket.getpeername()
    logging.info(f"[CONNEXION] Nouvelle connexion depuis {address}")
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                logging.info(f"[RECU] {address} >> {line}")
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
                            logging.info(f"[LOGIN] {username} connecté")

                            # Envoi liste des connectés au client
                            online_users = list_online_users()
                            client_socket.sendall((json.dumps({
                                'type': 'list_users',
                                'users': online_users
                            }) + '\n').encode())

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
                        logging.info(f"[INFO] Connexion invitée détectée : {username}")

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
                        logging.debug(f"[DB] Message enregistré pour {username}")
                    except Exception as e:
                        logging.error(f"[ERREUR DB] Impossible d'enregistrer le message : {e}")

                    logging.info(f"[MSG] {username} >> {msg['content']}")
                    broadcast(msg)  # Diffuse aussi au client qui envoie

                elif msg['type'] == 'status' and username:
                    update_user_status(username, msg['state'])
                    broadcast({'type': 'status', 'user': username, 'state': msg['state']}, client_socket)
                    logging.info(f"[STATUS] {username} est maintenant {msg['state']}")

    except Exception as e:
        logging.error(f'[ERREUR] Problème avec {address} ({username}): {e}')
    finally:
        if username:
            update_user_status(username, 'offline')
            broadcast({'type': 'status', 'user': username, 'state': 'offline'}, client_socket)
        with LOCK:
            CLIENTS.pop(client_socket, None)
        client_socket.close()
        logging.info(f"[DECONNEXION] {address} déconnecté")

def main():
    init_database()
    load_users()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    logging.info(f"[DEMARRAGE] Serveur en écoute sur {HOST}:{PORT}")
    print(f"[INFO] Serveur en écoute sur {HOST}:{PORT}")
    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == '__main__':
    main()
