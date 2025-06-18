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

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# Handler debug.log (tout)
debug_handler = logging.FileHandler('/home/louka/classcord-server/debug.log')
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(logging.Formatter(LOG_FORMAT))

# Handler audit.log (niveau INFO et plus)
audit_handler = logging.FileHandler('audit.log')
audit_handler.setLevel(logging.INFO)
audit_handler.setFormatter(logging.Formatter(LOG_FORMAT))

# Console (optionnel)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

# Application root logger
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[debug_handler, audit_handler, console_handler]
)

def init_database():
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                state TEXT,
                last_seen TEXT
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                content TEXT,
                timestamp TEXT
            );
        """)
        conn.commit()

def update_user_status(username, state):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO users (username, state, last_seen)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(username) DO UPDATE SET
                state = excluded.state,
                last_seen = datetime('now');
        """, (username, state))
        conn.commit()

def list_online_users():
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE state = 'online'")
        return [row[0] for row in c.fetchall()]

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

def broadcast(message, sender_socket=None):
    for sock, user in CLIENTS.items():
        try:
            sock.sendall((json.dumps(message) + '\n').encode())
            logging.debug(f"[BROADCAST] → {user}: {message}")
        except Exception as e:
            logging.error(f"[ERREUR BROADCAST] {user}: {e}")

def send_system_message(to_socket, content):
    try:
        message = {
            'type': 'system',
            'from': 'Serveur',
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        to_socket.sendall((json.dumps(message) + '\n').encode())
        logging.debug(f"[SYSTEM] → {CLIENTS.get(to_socket, '???')}: {content}")
    except Exception as e:
        logging.error(f"[ERREUR SYSTEM MSG] {e}")

def handle_client(sock):
    address = sock.getpeername()
    username = None
    buffer = ''

    logging.info(f"[CONNEXION] {address} connecté.")

    try:
        while True:
            data = sock.recv(1024).decode()
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                logging.debug(f"[RECU] {address} > {line}")
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError as e:
                    logging.error(f"[ERREUR JSON] {address}: {e}")
                    continue

                mtype = msg.get('type', 'inconnu')

                if mtype == 'register':
                    logging.info(f"[REGISTER] Tentative de {msg['username']} depuis {address}")
                    with LOCK:
                        if msg['username'] in USERS:
                            sock.sendall(json.dumps({'type': 'error', 'message': 'Username already exists.'}).encode() + b'\n')
                            logging.warning(f"[REGISTER-ECHEC] {msg['username']} existe déjà.")
                        else:
                            USERS[msg['username']] = msg['password']
                            save_users()
                            sock.sendall(json.dumps({'type': 'register', 'status': 'ok'}).encode() + b'\n')
                            logging.info(f"[REGISTER-OK] {msg['username']} enregistré.")

                elif mtype == 'login':
                    logging.info(f"[LOGIN] Tentative de {msg['username']} depuis {address}")
                    with LOCK:
                        if USERS.get(msg['username']) == msg['password']:
                            username = msg['username']
                            CLIENTS[sock] = username
                            update_user_status(username, 'online')
                            sock.sendall(json.dumps({'type': 'login', 'status': 'ok'}).encode() + b'\n')
                            broadcast({'type': 'status', 'user': username, 'state': 'online'}, sock)
                            send_system_message(sock, f"Bienvenue {username} !")
                            logging.info(f"[LOGIN-OK] {username} connecté depuis {address}")
                        else:
                            sock.sendall(json.dumps({'type': 'error', 'message': 'Login failed.'}).encode() + b'\n')
                            logging.warning(f"[LOGIN-ECHEC] {msg['username']} mauvaise authentification.")

                elif mtype == 'message':
                    if not username:
                        username = msg.get('from', 'invité')
                        with LOCK:
                            CLIENTS[sock] = username

                    msg['from'] = username
                    msg['timestamp'] = datetime.now().isoformat()

                    try:
                        with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
                            c = conn.cursor()
                            c.execute("INSERT INTO messages (sender, content, timestamp) VALUES (?, ?, ?)",
                                      (username, msg['content'], msg['timestamp']))
                            conn.commit()
                    except Exception as e:
                        logging.error(f"[ERREUR DB MESSAGE] {username}: {e}")

                    logging.info(f"[MESSAGE] {username} ({address}) > {msg['content']}")
                    broadcast(msg)

                elif mtype == 'status' and username:
                    update_user_status(username, msg['state'])
                    broadcast({'type': 'status', 'user': username, 'state': msg['state']}, sock)
                    logging.info(f"[STATUS] {username} est maintenant {msg['state']}")

    except Exception as e:
        logging.error(f"[ERREUR] {address} ({username}) : {e}")
    finally:
        if username:
            update_user_status(username, 'offline')
            broadcast({'type': 'status', 'user': username, 'state': 'offline'}, sock)
            logging.info(f"[DECONNEXION] {username} ({address}) déconnecté")
        with LOCK:
            CLIENTS.pop(sock, None)
        sock.close()

def main():
    init_database()
    load_users()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    logging.info(f"[DEMARRAGE] Serveur lancé sur {HOST}:{PORT}")
    while True:
        client, addr = server.accept()
        threading.Thread(target=handle_client, args=(client,), daemon=True).start()

if __name__ == '__main__':
    main()
