import socket
import threading
import json
import pickle
import os
from datetime import datetime
import sqlite3
import sys
import time

HOST = '0.0.0.0'
PORT = 12345         # port chat principal
ADMIN_PORT = 54321   # port console admin

USER_FILE = 'users.pkl'
DB_FILE = 'classcord.db'

CLIENTS = {}  # socket: username
LOCK = threading.Lock()
SERVER_RUNNING = True

# --- Gestion base SQLite utilisateurs ---

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT,
                state TEXT,
                last_seen TEXT
            )
        ''')
        conn.commit()

def save_user_db(username, password, state='offline'):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute('''
            INSERT OR REPLACE INTO users (username, password, state, last_seen)
            VALUES (?, ?, ?, ?)
        ''', (username, password, state, now))
        conn.commit()

def update_user_state(username, state):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute('''
            UPDATE users SET state=?, last_seen=? WHERE username=?
        ''', (state, now, username))
        conn.commit()

def get_user_password(username):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('SELECT password FROM users WHERE username=?', (username,))
        res = c.fetchone()
        return res[0] if res else None

def list_online_users():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('SELECT username FROM users WHERE state="online" ORDER BY last_seen DESC')
        return [row[0] for row in c.fetchall()]

def get_users_info(usernames):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        users_info = []
        for u in usernames:
            c.execute("SELECT state, last_seen FROM users WHERE username=?", (u,))
            r = c.fetchone()
            if r:
                users_info.append({'username': u, 'state': r[0], 'last_seen': r[1]})
        return users_info

# --- Broadcast messages to all clients except sender ---
def broadcast(message, sender_socket=None):
    with LOCK:
        for client_socket in list(CLIENTS.keys()):
            if client_socket != sender_socket:
                try:
                    client_socket.sendall((json.dumps(message) + '\n').encode())
                except Exception as e:
                    print(f"[ERREUR] Envoi à {CLIENTS[client_socket]} impossible : {e}")
                    # On ferme la connexion si erreur
                    client_socket.close()
                    CLIENTS.pop(client_socket, None)

def disconnect_user(username, reason="Kicked by admin"):
    with LOCK:
        to_kick = None
        for sock, user in CLIENTS.items():
            if user == username:
                to_kick = sock
                break
        if to_kick:
            try:
                to_kick.sendall((json.dumps({'type':'kick', 'reason': reason})+'\n').encode())
            except:
                pass
            to_kick.close()
            CLIENTS.pop(to_kick, None)
            update_user_state(username, 'offline')
            broadcast({'type': 'status', 'user': username, 'state': 'offline'})
            print(f"[ADMIN] Utilisateur {username} déconnecté.")

def handle_client(client_socket):
    buffer = ''
    username = None
    address = client_socket.getpeername()
    print(f"[CONNEXION] Nouvelle connexion depuis {address}")
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if not line.strip():
                    continue
                msg = json.loads(line)

                if msg['type'] == 'register':
                    uname = msg['username']
                    pwd = msg['password']
                    # check user exists
                    if get_user_password(uname) is not None:
                        response = {'type': 'error', 'message': 'Username already exists.'}
                    else:
                        save_user_db(uname, pwd, 'offline')
                        response = {'type': 'register', 'status': 'ok'}
                    client_socket.sendall((json.dumps(response) + '\n').encode())

                elif msg['type'] == 'login':
                    uname = msg['username']
                    pwd = msg['password']
                    stored_pwd = get_user_password(uname)
                    if stored_pwd == pwd:
                        username = uname
                        with LOCK:
                            CLIENTS[client_socket] = username
                        update_user_state(username, 'online')
                        response = {'type': 'login', 'status': 'ok'}
                        client_socket.sendall((json.dumps(response) + '\n').encode())
                        broadcast({'type': 'status', 'user': username, 'state': 'online'}, client_socket)
                        print(f"[LOGIN] {username} connecté")
                    else:
                        response = {'type': 'error', 'message': 'Login failed.'}
                        client_socket.sendall((json.dumps(response) + '\n').encode())

                elif msg['type'] == 'message':
                    if not username:
                        username = msg.get('from', 'invité')
                        with LOCK:
                            CLIENTS[client_socket] = username
                        print(f"[INFO] Connexion invitée détectée : {username}")
                    msg['from'] = username
                    msg['timestamp'] = datetime.now().isoformat()
                    print(f"[MSG] {username} >> {msg['content']}")
                    broadcast(msg, client_socket)

                elif msg['type'] == 'status' and username:
                    update_user_state(username, msg['state'])
                    broadcast({'type': 'status', 'user': username, 'state': msg['state']}, client_socket)
                    print(f"[STATUS] {username} est maintenant {msg['state']}")

    except Exception as e:
        print(f'[ERREUR] Problème avec {address} ({username}):', e)
    finally:
        if username:
            update_user_state(username, 'offline')
            broadcast({'type': 'status', 'user': username, 'state': 'offline'}, client_socket)
        with LOCK:
            CLIENTS.pop(client_socket, None)
        client_socket.close()
        print(f"[DECONNEXION] {address} déconnecté")

# --- Admin server handler ---

def handle_admin_client(sock, addr):
    global SERVER_RUNNING
    buffer = ''
    try:
        while True:
            data = sock.recv(1024).decode()
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if not line.strip():
                    continue
                try:
                    cmd = json.loads(line)
                except Exception:
                    sock.sendall(b'{"error":"JSON invalide"}\n')
                    continue

                ctype = cmd.get('type')

                if ctype == 'list_users':
                    users = list_online_users()
                    users_info = get_users_info(users)
                    resp = json.dumps({'users': users_info}) + '\n'
                    sock.sendall(resp.encode())

                elif ctype == 'kick':
                    target = cmd.get('target')
                    if target:
                        disconnect_user(target)
                        sock.sendall(json.dumps({'result': f'Utilisateur {target} kické.'}).encode() + b'\n')
                    else:
                        sock.sendall(json.dumps({'error': 'Paramètre target manquant'}).encode() + b'\n')

                elif ctype == 'broadcast':
                    content = cmd.get('content')
                    if content:
                        broadcast({'type': 'message', 'from': 'ADMIN', 'content': content, 'timestamp': datetime.now().isoformat()})
                        sock.sendall(json.dumps({'result': 'Message global envoyé.'}).encode() + b'\n')
                    else:
                        sock.sendall(json.dumps({'error': 'Paramètre content manquant'}).encode() + b'\n')

                elif ctype == 'shutdown':
                    sock.sendall(json.dumps({'result': 'Arrêt du serveur en cours.'}).encode() + b'\n')
                    print("[ADMIN] Arrêt du serveur demandé.")
                    SERVER_RUNNING = False
                    # On ferme la socket admin client pour libérer la boucle
                    sock.close()
                    return

                else:
                    sock.sendall(json.dumps({'error': 'Commande inconnue'}).encode() + b'\n')

    except Exception as e:
        print(f"[ADMIN] Erreur avec client admin {addr}: {e}")
    finally:
        sock.close()

def admin_server():
    global SERVER_RUNNING
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, ADMIN_PORT))
    server.listen()
    print(f"[ADMIN] Serveur admin en écoute sur {HOST}:{ADMIN_PORT}")
    while SERVER_RUNNING:
        try:
            sock, addr = server.accept()
            threading.Thread(target=handle_admin_client, args=(sock, addr), daemon=True).start()
        except Exception as e:
            print("[ADMIN] Erreur accept:", e)
    server.close()
    print("[ADMIN] Serveur admin arrêté.")

def main():
    global SERVER_RUNNING
    init_db()
    print("[INIT] Base de données initialisée.")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"[DEMARRAGE] Serveur en écoute sur {HOST}:{PORT}")

    threading.Thread(target=admin_server, daemon=True).start()

    try:
        while SERVER_RUNNING:
            server_socket.settimeout(1.0)
            try:
                client_socket, addr = server_socket.accept()
                threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        print("\n[STOP] Arrêt demandé via clavier.")
    finally:
        SERVER_RUNNING = False
        server_socket.close()
        print("[STOP] Serveur arrêté.")

if __name__ == '__main__':
    main()
