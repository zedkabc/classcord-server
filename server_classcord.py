import socket
import threading
import json
import pickle
import os
import logging
import sqlite3
from datetime import datetime

log_dir = os.path.dirname('/home/louka/classcord-server/debug.log')
os.makedirs(log_dir, exist_ok=True)

HOST = '0.0.0.0'
PORT = 12345

USER_FILE = 'users.pkl'
DB_FILE = 'classcord.db'
LOG_FILE = '/home/louka/classcord-server/debug.log'

CLIENTS = {}  # socket: {'username': str, 'channel': str}
USERS = {}    # username: password
LOCK = threading.Lock()

# Logger configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# Init DB
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
                timestamp TEXT,
                channel TEXT
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
    logger.info(f"[INIT] Utilisateurs chargés: {list(USERS.keys())}")

def save_users():
    with open(USER_FILE, 'wb') as f:
        pickle.dump(USERS, f)
    logger.info("[SAVE] Utilisateurs sauvegardés.")

def broadcast(message, sender_socket=None):
    to_remove = []
    sender_channel = CLIENTS.get(sender_socket, {}).get('channel', 'general')
    for client_socket, info in CLIENTS.items():
        if info.get('channel', 'general') == sender_channel:
            try:
                client_socket.sendall((json.dumps(message) + '\n').encode())
                logger.info(f"[ENVOI #{sender_channel}] -> {info['username']}: {message['content']}")
            except Exception as e:
                logger.error(f"[ERREUR ENVOI] {info['username']}: {e}")
                to_remove.append(client_socket)
    with LOCK:
        for sock in to_remove:
            CLIENTS.pop(sock, None)
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
                            CLIENTS[client_socket] = {'username': username, 'channel': 'general'}
                            update_user_status(username, 'online')
                            client_socket.sendall((json.dumps({'type': 'login', 'status': 'ok'}) + '\n').encode())
                            broadcast({'type': 'status', 'user': username, 'state': 'online'}, client_socket)

                            online_users = list_online_users()
                            client_socket.sendall((json.dumps({
                                'type': 'list_users',
                                'users': online_users
                            }) + '\n').encode())

                            send_system_message(f"{username} a rejoint le salon #general.", 'general')
                        else:
                            client_socket.sendall((json.dumps({'type': 'error', 'message': 'Login failed.'}) + '\n').encode())

                elif msg['type'] == 'join_channel':
                    if client_socket in CLIENTS:
                        CLIENTS[client_socket]['channel'] = msg['channel']
                        send_system_message(f"{CLIENTS[client_socket]['username']} a rejoint #{msg['channel']}.", msg['channel'])

                elif msg['type'] == 'message':
                    if not username:
                        username = msg.get('from', 'invité')
                        CLIENTS[client_socket] = {'username': username, 'channel': 'general'}
                    channel = CLIENTS[client_socket]['channel']
                    msg['from'] = username
                    msg['timestamp'] = datetime.now().isoformat()
                    msg['channel'] = channel

                    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO messages (sender, content, timestamp, channel)
                            VALUES (?, ?, ?, ?)
                        """, (username, msg['content'], msg['timestamp'], channel))
                        conn.commit()

                    broadcast(msg, sender_socket=client_socket)

                elif msg['type'] == 'list_users':
                    online_users = list_online_users()
                    client_socket.sendall((json.dumps({'type': 'list_users', 'users': online_users}) + '\n').encode())

                elif msg['type'] == 'status' and username:
                    update_user_status(username, msg['state'])
                    broadcast({'type': 'status', 'user': username, 'state': msg['state']}, client_socket)

    except Exception as e:
        logger.error(f"[ERREUR] {address} ({username}): {e}")
    finally:
        if username:
            update_user_status(username, 'offline')
            broadcast({'type': 'status', 'user': username, 'state': 'offline'}, client_socket)
            send_system_message(f"{username} a quitté le salon.")
        with LOCK:
            CLIENTS.pop(client_socket, None)
        client_socket.close()

def admin_interface():
    print("[ADMIN] Interface admin démarrée")
    while True:
        print("\n--- MENU ADMIN ---")
        print("1. Afficher clients actifs")
        print("2. Envoyer une alerte globale")
        print("3. Déconnecter un client")
        print("4. Quitter le serveur")
        choice = input("Choix: ").strip()

        if choice == '1':
            print("Clients actifs :")
            with LOCK:
                for sock, info in CLIENTS.items():
                    print(f" - {info['username']} (#{info['channel']})")
        elif choice == '2':
            alert = input("Alerte à envoyer : ").strip()
            if alert:
                send_system_message("[ALERTE ADMIN] " + alert)
        elif choice == '3':
            user = input("Nom du client à déconnecter : ").strip()
            found = False
            with LOCK:
                for sock, info in list(CLIENTS.items()):
                    if info['username'] == user:
                        try:
                            sock.shutdown(socket.SHUT_RDWR)
                            sock.close()
                        except Exception as e:
                            print(f"Erreur socket : {e}")
                        CLIENTS.pop(sock, None)
                        update_user_status(user, 'offline')
                        broadcast({'type': 'status', 'user': user, 'state': 'offline'})
                        print(f"{user} déconnecté.")
                        found = True
                        break
            if not found:
                print(f"Client '{user}' non trouvé.")
        elif choice == '4':
            print("Arrêt du serveur...")
            os._exit(0)
        else:
            print("Choix invalide.")

def main():
    init_database()
    load_users()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    logger.info(f"[DEMARRAGE] Serveur en écoute sur {HOST}:{PORT}")
    threading.Thread(target=admin_interface, daemon=True).start()
    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == '__main__':
    main()
