import socket
import threading
import json
import os
import logging
import sqlite3
import time
from datetime import datetime

LOG_FILE = '/home/louka/classcord-server/debug.log'
ADMIN_LOG_FILE = '/home/louka/classcord-server/admin_console.log'
DB_FILE = 'classcord.db'

HOST = '0.0.0.0'
PORT = 12345
PORT_ADMIN = 12346

CLIENTS = {}  # socket: {'username': str, 'channel': str, 'connected': bool}
LOCK = threading.Lock()

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# --- CONFIGURATION LOGGING ---
logger = logging.getLogger("classcord")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

admin_handler = logging.FileHandler(ADMIN_LOG_FILE, encoding='utf-8')
admin_handler.setLevel(logging.INFO)
admin_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
logger.addHandler(admin_handler)
# -----------------------------

def init_database():
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                state TEXT,
                last_seen TEXT
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                content TEXT,
                timestamp TEXT,
                channel TEXT
            );
        """)
        conn.commit()

def register_user(username, password):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (username, password, state, last_seen)
                VALUES (?, ?, 'offline', datetime('now'))
            """, (username, password))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def check_user_password(username, password):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return row and row[0] == password

def update_user_status(username, state):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET state = ?, last_seen = datetime('now') WHERE username = ?
        """, (state, username))
        conn.commit()

def list_online_users():
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE state = 'online'")
        return [row[0] for row in cursor.fetchall()]

def broadcast(message, sender_socket=None):
    to_remove = []
    sender_channel = CLIENTS.get(sender_socket, {}).get('channel', 'general')
    for client_socket, info in CLIENTS.items():
        if not info.get('connected'):
            continue
        if sender_socket is None or info.get('channel', 'general') == sender_channel:
            try:
                client_socket.sendall((json.dumps(message) + '\n').encode())
                logger.info(f"[ENVOI #{info.get('channel', 'general')}] -> {info['username']}: {message.get('content', '')}")
            except Exception as e:
                logger.error(f"[ERREUR ENVOI] {info.get('username', '?')}: {e}")
                to_remove.append(client_socket)
    with LOCK:
        for sock in to_remove:
            CLIENTS[sock]['connected'] = False
            try:
                sock.close()
            except:
                pass

def send_system_message(content, channel='general'):
    message = {
        'type': 'system',
        'content': content,
        'timestamp': datetime.now().isoformat(),
        'channel': channel
    }
    logger.info(f"[SYSTEM #{channel}] {content}")
    broadcast(message)

def handle_admin(admin_socket):
    logger.info("Admin connecté")
    buffer = ''
    try:
        while True:
            data = admin_socket.recv(1024).decode()
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                try:
                    command = json.loads(line)
                except json.JSONDecodeError:
                    continue

                action = command.get("action")
                if action == "list_clients":
                    with LOCK:
                        actifs = [info['username'] for sock, info in CLIENTS.items() if info.get('connected')]
                    admin_socket.sendall((json.dumps({'type': 'list', 'clients': actifs}) + '\n').encode())

                elif action == "broadcast":
                    content = command.get("message", "")
                    send_system_message("[ADMIN] " + content)

                elif action == "kick":
                    username = command.get("username")
                    with LOCK:
                        for sock, info in list(CLIENTS.items()):
                            if info.get("username") == username:
                                try:
                                    sock.sendall((json.dumps({'type': 'system', 'content': 'Déconnecté par l\'admin.'}) + '\n').encode())
                                    sock.shutdown(socket.SHUT_RDWR)
                                except:
                                    pass
                                sock.close()
                                info['connected'] = False
                                update_user_status(username, 'offline')
                                break

                elif action == "shutdown":
                    logger.info("Arrêt du serveur demandé par l’admin.")
                    os._exit(0)
    except Exception as e:
        logger.error(f"[ADMIN ERROR] {e}")
    finally:
        admin_socket.close()

def handle_client(client_socket):
    buffer = ''
    username = None
    address = client_socket.getpeername()
    logger.info(f"Nouvelle connexion de {address}")
    try:
        while True:
            try:
                data = client_socket.recv(1024).decode()
                if not data:
                    time.sleep(0.1)
                    continue
            except (ConnectionResetError, ConnectionAbortedError):
                break

            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    client_socket.sendall((json.dumps({'type': 'error', 'message': 'Message JSON malformé.'}) + '\n').encode())
                    continue

                msg_type = msg.get('type')

                if msg_type == 'register':
                    with LOCK:
                        success = register_user(msg.get('username', ''), msg.get('password', ''))
                        response = {'type': 'register', 'status': 'ok'} if success else {'type': 'error', 'message': 'Username already exists.'}
                        client_socket.sendall((json.dumps(response) + '\n').encode())

                elif msg_type == 'login':
                    with LOCK:
                        if check_user_password(msg.get('username', ''), msg.get('password', '')):
                            username = msg['username']
                            CLIENTS[client_socket] = {'username': username, 'channel': 'general', 'connected': True}
                            update_user_status(username, 'online')
                            client_socket.sendall((json.dumps({'type': 'login', 'status': 'ok'}) + '\n').encode())
                            broadcast({'type': 'status', 'user': username, 'state': 'online'}, client_socket)
                            client_socket.sendall((json.dumps({'type': 'list_users', 'users': list_online_users()}) + '\n').encode())
                            send_system_message(f"{username} a rejoint le salon #general.")
                        else:
                            client_socket.sendall((json.dumps({'type': 'error', 'message': 'Login failed.'}) + '\n').encode())

                elif msg_type == 'message' and username:
                    content = msg.get('content')
                    if content:
                        channel = CLIENTS[client_socket]['channel']
                        msg.update({
                            'from': username,
                            'timestamp': datetime.now().isoformat(),
                            'channel': channel
                        })
                        with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO messages (sender, content, timestamp, channel)
                                VALUES (?, ?, ?, ?)
                            """, (username, content, msg['timestamp'], channel))
                            conn.commit()
                        broadcast(msg, sender_socket=client_socket)

                elif msg_type == 'list_users':
                    users = list_online_users()
                    client_socket.sendall((json.dumps({'type': 'list_users', 'users': users}) + '\n').encode())

                elif msg_type == 'join_channel' and username:
                    channel_name = msg.get('channel', 'general')
                    old_channel = CLIENTS[client_socket]['channel']
                    CLIENTS[client_socket]['channel'] = channel_name
                    send_system_message(f"{username} a rejoint #{channel_name}.", channel_name)
    except Exception as e:
        logger.error(f"[ERREUR] {address} ({username}): {e}")
    finally:
        if username:
            update_user_status(username, 'offline')
            broadcast({'type': 'status', 'user': username, 'state': 'offline'}, client_socket)
            send_system_message(f"{username} a quitté le salon.")
        with LOCK:
            if client_socket in CLIENTS:
                CLIENTS[client_socket]['connected'] = False
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            client_socket.close()

def main():
    init_database()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)

    admin_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    admin_socket.bind((HOST, PORT_ADMIN))
    admin_socket.listen(1)

    logger.info(f"Serveur démarré sur {HOST}:{PORT}")
    logger.info(f"Port admin en écoute sur {HOST}:{PORT_ADMIN}")

    threading.Thread(target=lambda: accept_loop(server_socket, handle_client), daemon=True).start()
    threading.Thread(target=lambda: accept_loop(admin_socket, handle_admin), daemon=True).start()

    while True:
        time.sleep(1)

def accept_loop(sock, handler):
    while True:
        client, addr = sock.accept()
        threading.Thread(target=handler, args=(client,), daemon=True).start()

if __name__ == '__main__':
    main()
