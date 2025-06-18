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

LOG_FILE = '/var/log/classcord.log'
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

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

def send_system_message(to_socket, content):
    message = {
        'type': 'system',
        'from': 'server',
        'content': content,
        'timestamp': datetime.now().isoformat()
    }
    try:
        with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (sender, content, timestamp)
                VALUES (?, ?, ?)
            """, ('server', content, message['timestamp']))
            conn.commit()

        to_socket.sendall((json.dumps(message) + '\n').encode())
        logging.info(f"[SYSTÈME] Envoyé : {content}")
    except Exception as e:
        logging.error(f"[ERREUR SYSTÈME] : {e}")

def broadcast_system_message(content):
    message = {
        'type': 'system',
        'from': 'server',
        'content': content,
        'timestamp': datetime.now().isoformat()
    }
    try:
        with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (sender, content, timestamp)
                VALUES (?, ?, ?)
            """, ('server', content, message['timestamp']))
            conn.commit()
    except Exception as e:
        logging.error(f"[ERREUR DB] Système : {e}")

    for client_socket in CLIENTS:
        try:
            client_socket.sendall((json.dumps(message) + '\n').encode())
        except Exception as e:
            logging.error(f"[ERREUR BROADCAST] : {e}")

def broadcast(message, sender_socket=None):
    for client_socket, username in CLIENTS.items():
        try:
            client_socket.sendall((json.dumps(message) + '\n').encode())
        except Exception as e:
            logging.error(f"[ERREUR ENVOI {username}] : {e}")

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

                            response = {'type': 'login', 'status': 'ok'}
                            client_socket.sendall((json.dumps(response) + '\n').encode())

                            broadcast({'type': 'status', 'user': username, 'state': 'online'}, client_socket)
                            broadcast_system_message(f"{username} est connecté.")
                            logging.info(f"[LOGIN] {username} connecté")

                            client_socket.sendall((json.dumps({
                                'type': 'list_users',
                                'users': list_online_users()
                            }) + '\n').encode())
                        else:
                            response = {'type': 'error', 'message': 'Login failed.'}
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
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO messages (sender, content, timestamp)
                                VALUES (?, ?, ?)
                            """, (username, msg['content'], msg['timestamp']))
                            conn.commit()
                    except Exception as e:
                        logging.error(f"[ERREUR DB MSG] : {e}")
                    broadcast(msg)

                elif msg['type'] == 'status' and username:
                    update_user_status(username, msg['state'])
                    broadcast({'type': 'status', 'user': username, 'state': msg['state']}, client_socket)

    except Exception as e:
        logging.error(f"[ERREUR CLIENT {username}] : {e}")
    finally:
        if username:
            update_user_status(username, 'offline')
            broadcast({'type': 'status', 'user': username, 'state': 'offline'}, client_socket)
            broadcast_system_message(f"{username} s'est déconnecté.")
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
    logging.info(f"[SERVEUR] En écoute sur {HOST}:{PORT}")
    while True:
        client_socket, _ = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == '__main__':
    main()
