import socket
import threading
import json
import sqlite3
import os
from datetime import datetime

HOST = '0.0.0.0'
PORT = 12345
DB_FILE = 'classcord.db'
CLIENTS = {}  # socket: username
LOCK = threading.Lock()

# Initialisation de la base SQLite
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                state TEXT DEFAULT 'offline',
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                channel TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

def register_user(username, password):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return False
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True

def check_login(username, password):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        return result and result[0] == password

def update_user_state(username, state):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET state = ?, last_seen = CURRENT_TIMESTAMP WHERE username = ?", (state, username))
        conn.commit()

def save_message(username, channel, content):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (username, channel, content) VALUES (?, ?, ?)", (username, channel, content))
        conn.commit()

def broadcast(message, sender_socket=None):
    for client_socket, username in CLIENTS.items():
        if client_socket != sender_socket:
            try:
                client_socket.sendall((json.dumps(message) + '\n').encode())
            except:
                pass

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
                msg = json.loads(line)

                if msg['type'] == 'register':
                    success = register_user(msg['username'], msg['password'])
                    if success:
                        response = {'type': 'register', 'status': 'ok'}
                    else:
                        response = {'type': 'error', 'message': 'Username already exists.'}
                    client_socket.sendall((json.dumps(response) + '\n').encode())

                elif msg['type'] == 'login':
                    if check_login(msg['username'], msg['password']):
                        username = msg['username']
                        CLIENTS[client_socket] = username
                        update_user_state(username, 'online')
                        response = {'type': 'login', 'status': 'ok'}
                        client_socket.sendall((json.dumps(response) + '\n').encode())
                        broadcast({'type': 'status', 'user': username, 'state': 'online'}, client_socket)
                    else:
                        response = {'type': 'error', 'message': 'Login failed.'}
                        client_socket.sendall((json.dumps(response) + '\n').encode())

                elif msg['type'] == 'message':
                    if not username:
                        continue
                    msg['from'] = username
                    msg['timestamp'] = datetime.now().isoformat()
                    channel = msg.get('channel', '#general')
                    save_message(username, channel, msg['content'])
                    broadcast(msg, client_socket)

                elif msg['type'] == 'status' and username:
                    update_user_state(username, msg['state'])
                    broadcast({'type': 'status', 'user': username, 'state': msg['state']}, client_socket)

    except Exception as e:
        print(f"[ERREUR] {username}: {e}")
    finally:
        if username:
            update_user_state(username, 'offline')
            broadcast({'type': 'status', 'user': username, 'state': 'offline'}, client_socket)
        CLIENTS.pop(client_socket, None)
        client_socket.close()

def main():
    init_db()
    print(f"[DEMARRAGE] Serveur en écoute sur {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        while True:
            client_socket, addr = s.accept()
            threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == '__main__':
    main()
