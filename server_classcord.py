import socket
import threading
import json
import os
import sqlite3
import time
from datetime import datetime

DB_FILE = 'classcord.db'

HOST = '0.0.0.0'
PORT = 12345

CLIENTS = {}  # socket: {'username': str, 'channel': str, 'connected': bool}
LOCK = threading.Lock()

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
            except Exception:
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
    broadcast(message)

def handle_client(client_socket):
    buffer = ''
    username = None
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    client_socket.sendall(json.dumps({'type': 'error', 'message': 'JSON malformé'}).encode() + b'\n')
                    continue

                msg_type = msg.get('type')

                if msg_type == 'register':
                    with LOCK:
                        success = register_user(msg.get('username', ''), msg.get('password', ''))
                    if success:
                        client_socket.sendall(json.dumps({'type': 'register', 'status': 'ok'}).encode() + b'\n')
                    else:
                        client_socket.sendall(json.dumps({'type': 'error', 'message': 'Username exists'}).encode() + b'\n')

                elif msg_type == 'login':
                    with LOCK:
                        if check_user_password(msg.get('username', ''), msg.get('password', '')):
                            username = msg['username']
                            CLIENTS[client_socket] = {'username': username, 'channel': 'general', 'connected': True}
                            update_user_status(username, 'online')
                            client_socket.sendall(json.dumps({'type': 'login', 'status': 'ok'}).encode() + b'\n')

                            broadcast({'type': 'status', 'user': username, 'state': 'online'}, client_socket)

                            online_users = list_online_users()
                            client_socket.sendall(json.dumps({'type': 'list_users', 'users': online_users}).encode() + b'\n')

                            send_system_message(f"{username} a rejoint le salon #general.")
                        else:
                            client_socket.sendall(json.dumps({'type': 'error', 'message': 'Login failed'}).encode() + b'\n')

                elif msg_type == 'message' and username:
                    content = msg.get('content')
                    if content:
                        channel = CLIENTS[client_socket]['channel']
                        timestamp = datetime.now().isoformat()
                        with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO messages (sender, content, timestamp, channel)
                                VALUES (?, ?, ?, ?)
                            """, (username, content, timestamp, channel))
                            conn.commit()
                        message_to_send = {
                            'type': 'message',
                            'from': username,
                            'content': content,
                            'timestamp': timestamp,
                            'channel': channel
                        }
                        broadcast(message_to_send, sender_socket=client_socket)

                elif msg_type == 'list_users':
                    users = list_online_users()
                    client_socket.sendall(json.dumps({'type': 'list_users', 'users': users}).encode() + b'\n')

                elif msg_type == 'kick_user' and username:
                    # Vérifier si client admin (optionnel)
                    kicked_user = msg.get('username')
                    kicked_socket = None
                    for sock, info in CLIENTS.items():
                        if info['username'] == kicked_user:
                            kicked_socket = sock
                            break
                    if kicked_socket:
                        kicked_socket.sendall(json.dumps({'type': 'kick', 'message': 'Vous avez été expulsé par l’admin.'}).encode() + b'\n')
                        CLIENTS[kicked_socket]['connected'] = False
                        kicked_socket.close()
                        update_user_status(kicked_user, 'offline')
                        send_system_message(f"{kicked_user} a été expulsé par l’admin.")
                    else:
                        client_socket.sendall(json.dumps({'type': 'error', 'message': 'Utilisateur non trouvé'}).encode() + b'\n')

                elif msg_type == 'global_message' and username:
                    content = msg.get('content')
                    if content:
                        send_system_message(f"ADMIN: {content}")

                elif msg_type == 'shutdown' and username:
                    send_system_message("Le serveur va s’éteindre.")
                    # Fermer proprement toutes les connexions
                    for sock in list(CLIENTS.keys()):
                        try:
                            sock.sendall(json.dumps({'type': 'shutdown', 'message': 'Serveur arrêté par admin.'}).encode() + b'\n')
                            sock.close()
                        except:
                            pass
                    os._exit(0)

                elif msg_type == 'join_channel' and username:
                    channel_name = msg.get('channel', 'general')
                    CLIENTS[client_socket]['channel'] = channel_name
                    send_system_message(f"{username} a rejoint #{channel_name}.", channel_name)

    except Exception:
        pass
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
    print(f"Serveur démarré sur {HOST}:{PORT}")

    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == '__main__':
    main()
