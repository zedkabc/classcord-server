import socket
import threading
import json
import os
import logging
import sqlite3
from datetime import datetime

LOG_FILE = '/home/louka/classcord-server/debug.log'
DB_FILE = 'classcord.db'

HOST = '0.0.0.0'
PORT = 12345

CLIENTS = {}  # socket: {'username': str, 'channel': str}
LOCK = threading.Lock()

# Création du dossier logs si besoin
log_dir = os.path.dirname(LOG_FILE)
os.makedirs(log_dir, exist_ok=True)

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
        if row and row[0] == password:
            return True
        return False

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
        # broadcast to clients in same channel or all if sender_socket is None
        if sender_socket is None or info.get('channel', 'general') == sender_channel:
            try:
                client_socket.sendall((json.dumps(message) + '\n').encode())
                logger.info(f"[ENVOI #{info.get('channel', 'general')}] -> {info['username']}: {message.get('content', '')}")
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
    logger.info(f"Nouvelle connexion de {address}")
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                logger.info(f"Connexion fermée par le client {address} ({username})")
                break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning(f"Message JSON malformé reçu de {address} : {line}")
                    error_msg = {'type': 'error', 'message': 'Message JSON malformé.'}
                    try:
                        client_socket.sendall((json.dumps(error_msg) + '\n').encode())
                    except:
                        pass
                    continue

                msg_type = msg.get('type')
                if not msg_type:
                    logger.warning(f"Message sans type reçu de {address}")
                    continue

                if msg_type == 'register':
                    with LOCK:
                        success = register_user(msg.get('username', ''), msg.get('password', ''))
                        if success:
                            logger.info(f"Nouvel utilisateur inscrit : {msg.get('username', '')}")
                            response = {'type': 'register', 'status': 'ok'}
                        else:
                            logger.info(f"Inscription échouée, utilisateur existant : {msg.get('username', '')}")
                            response = {'type': 'error', 'message': 'Username already exists.'}
                        client_socket.sendall((json.dumps(response) + '\n').encode())

                elif msg_type == 'login':
                    with LOCK:
                        if check_user_password(msg.get('username', ''), msg.get('password', '')):
                            username = msg['username']
                            CLIENTS[client_socket] = {'username': username, 'channel': 'general'}
                            update_user_status(username, 'online')
                            logger.info(f"Utilisateur connecté : {username} depuis {address}")
                            client_socket.sendall((json.dumps({'type': 'login', 'status': 'ok'}) + '\n').encode())
                            broadcast({'type': 'status', 'user': username, 'state': 'online'}, client_socket)

                            online_users = list_online_users()
                            client_socket.sendall((json.dumps({
                                'type': 'list_users',
                                'users': online_users
                            }) + '\n').encode())

                            send_system_message(f"{username} a rejoint le salon #general.", 'general')
                        else:
                            logger.info(f"Échec connexion utilisateur : {msg.get('username', '')} depuis {address}")
                            client_socket.sendall((json.dumps({'type': 'error', 'message': 'Login failed.'}) + '\n').encode())

                elif msg_type == 'join_channel':
                    if client_socket in CLIENTS:
                        channel_name = msg.get('channel', 'general')
                        old_channel = CLIENTS[client_socket]['channel']
                        CLIENTS[client_socket]['channel'] = channel_name
                        logger.info(f"{CLIENTS[client_socket]['username']} a quitté #{old_channel} pour rejoindre #{channel_name}")
                        send_system_message(f"{CLIENTS[client_socket]['username']} a rejoint #{channel_name}.", channel_name)

                elif msg_type == 'message':
                    if not username:
                        logger.warning(f"Message reçu d'un client non identifié {address}")
                        continue
                    content = msg.get('content')
                    if not content:
                        logger.warning(f"Message vide reçu de {username}")
                        continue
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

                    logger.info(f"Message de {username} dans #{channel} : {content}")
                    broadcast(msg, sender_socket=client_socket)

                elif msg_type == 'list_users':
                    online_users = list_online_users()
                    client_socket.sendall((json.dumps({'type': 'list_users', 'users': online_users}) + '\n').encode())

                elif msg_type == 'status' and username:
                    state = msg.get('state')
                    if state:
                        update_user_status(username, state)
                        logger.info(f"Changement d'état utilisateur {username} -> {state}")
                        broadcast({'type': 'status', 'user': username, 'state': state}, client_socket)

    except Exception as e:
        logger.error(f"[ERREUR] {address} ({username}): {e}")
    finally:
        if username:
            update_user_status(username, 'offline')
            broadcast({'type': 'status', 'user': username, 'state': 'offline'}, client_socket)
            send_system_message(f"{username} a quitté le salon.")
            logger.info(f"Utilisateur déconnecté : {username} ({address})")
        else:
            logger.info(f"Connexion fermée sans login depuis {address}")
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
            with LOCK:
                print(f"DEBUG: CLIENTS = {CLIENTS}")
                if CLIENTS:
                    print("Clients actifs :")
                    for sock, info in CLIENTS.items():
                        print(f" - {info['username']} (#{info['channel']})")
                else:
                    print("Aucun client actif.")
        elif choice == '2':
            alert = input("Alerte à envoyer : ").strip()
            if alert:
                send_system_message("[ALERTE ADMIN] " + alert)
        elif choice == '3':
            with LOCK:
                if not CLIENTS:
                    print("Aucun client connecté.")
                    continue
                print("Clients connectés :")
                for i, (sock, info) in enumerate(CLIENTS.items()):
                    print(f"{i+1}. {info['username']} (#{info['channel']})")
                try:
                    sel = int(input("Numéro client à déconnecter: "))
                    if 1 <= sel <= len(CLIENTS):
                        sock_to_kick = list(CLIENTS.keys())[sel - 1]
                        username = CLIENTS[sock_to_kick]['username']
                        try:
                            # Envoi message de déconnexion
                            sock_to_kick.sendall((json.dumps({'type': 'system', 'content': 'Vous avez été déconnecté par l\'admin.'}) + '\n').encode())
                        except:
                            pass
                        try:
                            sock_to_kick.shutdown(socket.SHUT_RDWR)
                        except:
                            pass
                        sock_to_kick.close()
                        CLIENTS.pop(sock_to_kick, None)
                        update_user_status(username, 'offline')
                        print(f"Client {username} déconnecté.")
                        logger.info(f"Client déconnecté par admin : {username}")
                    else:
                        print("Numéro invalide.")
                except ValueError:
                    print("Entrée invalide.")
        elif choice == '4':
            print("Fermeture du serveur...")
            os._exit(0)
        else:
            print("Choix invalide.")

def main():
    init_database()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    logger.info(f"Serveur démarré sur {HOST}:{PORT}")

    threading.Thread(target=admin_interface, daemon=True).start()

    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == '__main__':
    main()
