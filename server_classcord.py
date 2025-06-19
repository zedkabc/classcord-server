import socket
import threading
import json
import os
import logging
import sqlite3
import time
from datetime import datetime

LOG_FILE = '/home/louka/classcord-server/debug.log'
DB_FILE = 'classcord.db'

HOST = '0.0.0.0'
PORT = 12345

CLIENTS = {}
LOCK = threading.Lock()
ADMIN_INPUT_LOCK = threading.Lock()

# --- Logging setup ---
logger = logging.getLogger("classcord-server")
logger.setLevel(logging.DEBUG)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# --- Database functions ---

def init_database():
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            status TEXT
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            content TEXT,
            timestamp TEXT,
            channel TEXT
        )
        """)
        conn.commit()
    logger.info("Base de données initialisée.")

def register_user(username, password):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return False
        cursor.execute("INSERT INTO users (username, password, status) VALUES (?, ?, ?)", (username, password, 'offline'))
        conn.commit()
        return True

def check_user_password(username, password):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return row is not None and row[0] == password

def update_user_status(username, status):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = ? WHERE username = ?", (status, username))
        conn.commit()

def list_online_users():
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE status = 'online'")
        rows = cursor.fetchall()
        return [r[0] for r in rows]

# --- Communication helpers ---

def broadcast(message, sender_socket=None):
    to_remove = []
    sender_channel = CLIENTS.get(sender_socket, {}).get('channel', 'general')
    for client_socket, info in CLIENTS.items():
        if not info.get('connected'):
            continue
        # envoi uniquement aux clients dans le même channel que l'émetteur (ou à tous si sender_socket None)
        if sender_socket is None or info.get('channel', 'general') == sender_channel:
            try:
                client_socket.sendall((json.dumps(message) + '\n').encode())
                with ADMIN_INPUT_LOCK:
                    logger.info(f"[ENVOI #{info.get('channel', 'general')}] -> {info['username']}: {message.get('content', '')}")
            except Exception as e:
                with ADMIN_INPUT_LOCK:
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
    with ADMIN_INPUT_LOCK:
        logger.info(f"[SYSTEM #{channel}] {content}")
    broadcast(message)

# --- Client handler ---

def handle_client(client_socket):
    buffer = ''
    username = None
    address = client_socket.getpeername()
    with ADMIN_INPUT_LOCK:
        logger.info(f"Nouvelle connexion de {address}")
    try:
        while True:
            try:
                data = client_socket.recv(1024).decode()
                if not data:
                    # Client a fermé proprement la connexion
                    break
            except (ConnectionResetError, ConnectionAbortedError):
                with ADMIN_INPUT_LOCK:
                    logger.error(f"[DÉCONNEXION FORCÉE] {address}")
                break

            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    with ADMIN_INPUT_LOCK:
                        logger.warning(f"[JSON MALFORMÉ] de {address} : {line}")
                    client_socket.sendall((json.dumps({'type': 'error', 'message': 'Message JSON malformé.'}) + '\n').encode())
                    continue

                msg_type = msg.get('type')

                if msg_type == 'register':
                    with LOCK:
                        success = register_user(msg.get('username', ''), msg.get('password', ''))
                    if success:
                        with ADMIN_INPUT_LOCK:
                            logger.info(f"Nouvel utilisateur inscrit : {msg.get('username', '')}")
                        response = {'type': 'register', 'status': 'ok'}
                    else:
                        response = {'type': 'register', 'status': 'fail', 'message': 'Username already exists.'}
                    client_socket.sendall((json.dumps(response) + '\n').encode())

                elif msg_type == 'login':
                    with LOCK:
                        if check_user_password(msg.get('username', ''), msg.get('password', '')):
                            username = msg['username']
                            CLIENTS[client_socket] = {'username': username, 'channel': 'general', 'connected': True}
                            update_user_status(username, 'online')
                            with ADMIN_INPUT_LOCK:
                                logger.info(f"Utilisateur connecté : {username} depuis {address}")
                            client_socket.sendall((json.dumps({'type': 'login', 'status': 'ok'}) + '\n').encode())
                            broadcast({'type': 'status', 'user': username, 'state': 'online'}, client_socket)

                            online_users = list_online_users()
                            client_socket.sendall((json.dumps({
                                'type': 'list_users',
                                'users': online_users
                            }) + '\n').encode())

                            send_system_message(f"{username} a rejoint le salon #general.")
                        else:
                            client_socket.sendall((json.dumps({'type': 'login', 'status': 'fail', 'message': 'Login failed.'}) + '\n').encode())

                elif msg_type == 'message' and username:
                    content = msg.get('content')
                    if content:
                        channel = CLIENTS[client_socket]['channel']
                        msg['from'] = username
                        msg['timestamp'] = datetime.now().isoformat()
                        msg['channel'] = channel

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
        with ADMIN_INPUT_LOCK:
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

# --- Admin interface ---

def admin_interface():
    with ADMIN_INPUT_LOCK:
        print("[ADMIN] Interface admin démarrée")
    while True:
        with ADMIN_INPUT_LOCK:
            print("\n--- MENU ADMIN ---")
            print("1. Afficher clients actifs")
            print("2. Envoyer une alerte globale")
            print("3. Déconnecter un client")
            print("4. Quitter le serveur")
            choice = input("Choix: ").strip()

        if choice == '1':
            with LOCK, ADMIN_INPUT_LOCK:
                actifs = [(sock, info) for sock, info in CLIENTS.items() if info.get('connected')]
                if actifs:
                    for sock, info in actifs:
                        print(f" - {info['username']} (#{info['channel']})")
                else:
                    print("Aucun client actif.")

        elif choice == '2':
            with ADMIN_INPUT_LOCK:
                alert = input("Alerte à envoyer : ").strip()
            if alert:
                send_system_message("[ALERTE ADMIN] " + alert)

        elif choice == '3':
            with LOCK:
                actifs = [(sock, info) for sock, info in CLIENTS.items() if info.get('connected')]
            if not actifs:
                with ADMIN_INPUT_LOCK:
                    print("Aucun client connecté.")
                continue
            with ADMIN_INPUT_LOCK:
                for i, (sock, info) in enumerate(actifs):
                    print(f"{i+1}. {info['username']} (#{info['channel']})")
                try:
                    sel = int(input("Numéro client à déconnecter: "))
                    if 1 <= sel <= len(actifs):
                        sock_to_kick = actifs[sel - 1][0]
                        username = CLIENTS[sock_to_kick]['username']
                        try:
                            sock_to_kick.sendall((json.dumps({'type': 'system', 'content': 'Déconnecté par l\'admin.'}) + '\n').encode())
                        except:
                            pass
                        try:
                            sock_to_kick.shutdown(socket.SHUT_RDWR)
                        except:
                            pass
                        sock_to_kick.close()
                        CLIENTS[sock_to_kick]['connected'] = False
                        update_user_status(username, 'offline')
                        print(f"Client {username} déconnecté.")
                except ValueError:
                    print("Entrée invalide.")

        elif choice == '4':
            with ADMIN_INPUT_LOCK:
                print("Fermeture du serveur...")
            os._exit(0)
        else:
            with ADMIN_INPUT_LOCK:
                print("Choix invalide.")

# --- Main server loop ---

def main():
    init_database()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    with ADMIN_INPUT_LOCK:
        logger.info(f"Serveur démarré sur {HOST}:{PORT}")
    threading.Thread(target=admin_interface, daemon=True).start()

    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == '__main__':
    main()
