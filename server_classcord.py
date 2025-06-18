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

# -- Configuration des logs --
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEBUG_LOG = os.path.join(BASE_DIR, 'debug.log')
AUDIT_LOG = os.path.join(BASE_DIR, 'audit.log')

# Handlers
debug_handler = logging.FileHandler(DEBUG_LOG)
debug_handler.setLevel(logging.DEBUG)

audit_handler = logging.FileHandler(AUDIT_LOG)
audit_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
debug_handler.setFormatter(formatter)
audit_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Apply handlers
logging.basicConfig(level=logging.DEBUG, handlers=[debug_handler, audit_handler, console_handler])

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

# -- Envoi de message système --
def send_system_message(to_socket, content):
    message = {
        'type': 'system',
        'from': 'server',
        'timestamp': datetime.now().isoformat(),
        'content': content
    }
    try:
        to_socket.sendall((json.dumps(message) + '\n').encode())
        logging.debug(f"[SYSTEM] Message système envoyé à {CLIENTS.get(to_socket, 'inconnu')} : {content}")
    except Exception as e:
        logging.error(f"[ERREUR SYSTEM] Impossible d'envoyer un message système : {e}")

# -- Statut utilisateur --
def update_user_status(username, state):
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

def list_online_users():
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE state = 'online'")
        return [row[0] for row in cursor.fetchall()]

# -- Utilisateurs depuis fichier .pkl --
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

# -- Diffusion message à tous --
def broadcast(message, sender_socket=None):
    to_remove = []
    for client_socket, username in CLIENTS.items():
        try:
            client_socket.sendall((json.dumps(message) + '\n').encode())
            logging.info(f"[ENVOI] Message envoyé à {username} : {message}")
        except Exception as e:
            logging.error(f"[ERREUR] Échec d'envoi à {username} : {e}")
            to_remove.append(client_socket)

# -- Traitement par client --
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
                            client_socket.sendall(json.dumps({'type': 'login', 'status': 'ok'}).encode() + b'\n')
                            broadcast({'type': 'status', 'user': username, 'state': 'online'}, client_socket)
                            logging.info(f"[LOGIN] {username} connecté")

                            # Envoi de la liste des connectés
                            send_system_message(client_socket, f"Bienvenue {username} !")
                            client_socket.sendall((json.dumps({
                                'type': 'list_users',
                                'users': list_online_users()
                            }) + '\n').encode())
                        else:
                            client_socket.sendall(json.dumps({
                                'type': 'error',
                                'message': 'Login failed.'
                            }).encode() + b'\n')

                elif msg['type'] == 'list_users':
                    response = {'type': 'list_users', 'users': list_online_users()}
                    client_socket.sendall((json.dumps(response) + '\n').encode())

                elif msg['type'] == 'message':
                    if not username:
                        username = msg.get('from', 'invité')
                        with LOCK:
                            CLIENTS[client_socket] = username

                    msg['from'] = username
                    msg['timestamp'] = datetime.now().isoformat()

                    try:
                        with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
                            conn.execute("INSERT INTO messages (sender, content, timestamp) VALUES (?, ?, ?)",
                                         (username, msg['content'], msg['timestamp']))
                            conn.commit()
                    except Exception as e:
                        logging.error(f"[ERREUR DB] {e}")

                    broadcast(msg)

                elif msg['type'] == 'status' and username:
                    update_user_status(username, msg['state'])
                    broadcast({'type': 'status', 'user': username, 'state': msg['state']}, client_socket)

    except Exception as e:
        logging.error(f"[ERREUR] Client {address} ({username}) : {e}")
    finally:
        if username:
            update_user_status(username, 'offline')
            broadcast({'type': 'status', 'user': username, 'state': 'offline'}, client_socket)
        with LOCK:
            CLIENTS.pop(client_socket, None)
        client_socket.close()
        logging.info(f"[DECONNEXION] {address} déconnecté")

# -- Main --
def main():
    init_database()
    load_users()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    logging.info(f"[DEMARRAGE] Serveur en écoute sur {HOST}:{PORT}")
    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == '__main__':
    main()
