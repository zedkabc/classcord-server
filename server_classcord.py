import socket
import threading
import json
import os
import logging
import sqlite3
import time
from datetime import datetime

DB_FILE = 'classcord.db'
HOST = '0.0.0.0'
PORT = 12345

CLIENTS = {}
LOCK = threading.Lock()

# --- LOGGING CONSOLE UNIQUEMENT ---
logger = logging.getLogger("classcord")
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)
# -----------------------------------

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
        try:
            conn.execute("INSERT INTO users (username, password, state, last_seen) VALUES (?, ?, 'offline', datetime('now'))", (username, password))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def check_user_password(username, password):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        row = conn.execute("SELECT password FROM users WHERE username = ?", (username,)).fetchone()
        return row and row[0] == password

def update_user_status(username, state):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        conn.execute("UPDATE users SET state = ?, last_seen = datetime('now') WHERE username = ?", (state, username))
        conn.commit()

def list_online_users():
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        return [row[0] for row in conn.execute("SELECT username FROM users WHERE state = 'online'")]

def broadcast(message, sender_socket=None):
    to_remove = []
    sender_channel = CLIENTS.get(sender_socket, {}).get('channel', 'general')
    for client_socket, info in CLIENTS.items():
        if not info.get('connected'):
            continue
        if info.get('channel', 'general') == sender_channel:
            try:
                client_socket.sendall((json.dumps(message) + '\n').encode())
                logger.info(f"[#{info.get('channel', 'general')}] {info['username']} -> {message.get('content', '')}")
            except Exception as e:
                logger.warning(f"[ERREUR ENVOI] {info.get('username', '?')} -> {e}")
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

def handle_client(client_socket):
    buffer = ''
    username = None
    address = client_socket.getpeername()
    logger.info(f"[NOUVELLE CONNEXION] {address}")
    try:
        while True:
            try:
                data = client_socket.recv(1024).decode()
                if not data:
                    time.sleep(0.1)
                    continue
            except (ConnectionResetError, ConnectionAbortedError):
                logger.warning(f"[FORCE DÉCONNEXION] {address}")
                break

            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning(f"[JSON MALFORMÉ] {address}: {line}")
                    client_socket.sendall((json.dumps({'type': 'error', 'message': 'Message JSON malformé.'}) + '\n').encode())
                    continue

                msg_type = msg.get('type')

                if msg_type == 'register':
                    with LOCK:
                        success = register_user(msg.get('username', ''), msg.get('password', ''))
                        if success:
                            logger.info(f"[INSCRIPTION] {msg.get('username')}")
                            response = {'type': 'register', 'status': 'ok'}
                        else:
                            response = {'type': 'error', 'message': 'Username already exists.'}
                        client_socket.sendall((json.dumps(response) + '\n').encode())

                elif msg_type == 'login':
                    with LOCK:
                        if check_user_password(msg.get('username', ''), msg.get('password', '')):
                            username = msg['username']
                            CLIENTS[client_socket] = {'username': username, 'channel': 'general', 'connected': True}
                            update_user_status(username, 'online')
                            logger.info(f"[CONNEXION] {username} depuis {address}")
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
                        timestamp = datetime.now().isoformat()
                        msg.update({'from': username, 'timestamp': timestamp, 'channel': channel})
                        with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
                            conn.execute("INSERT INTO messages (sender, content, timestamp, channel) VALUES (?, ?, ?, ?)",
                                         (username, content, timestamp, channel))
                            conn.commit()
                        broadcast(msg, sender_socket=client_socket)

                elif msg_type == 'list_users':
                    client_socket.sendall((json.dumps({'type': 'list_users', 'users': list_online_users()}) + '\n').encode())

                elif msg_type == 'join_channel' and username:
                    new_channel = msg.get('channel', 'general')
                    old_channel = CLIENTS[client_socket]['channel']
                    CLIENTS[client_socket]['channel'] = new_channel
                    send_system_message(f"{username} a rejoint #{new_channel}.", new_channel)

    except Exception as e:
        logger.error(f"[ERREUR] {address} ({username}): {e}")
    finally:
        if username:
            update_user_status(username, 'offline')
            broadcast({'type': 'status', 'user': username, 'state': 'offline'}, client_socket)
            send_system_message(f"{username} a quitté le salon.")
            logger.info(f"[DÉCONNEXION] {username} ({address})")
        with LOCK:
            CLIENTS.pop(client_socket, None)
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
    logger.info(f"🎧 Serveur lancé sur {HOST}:{PORT}")
    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == '__main__':
    main()
