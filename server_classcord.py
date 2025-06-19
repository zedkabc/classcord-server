import socket
import threading
import json
import os
import sqlite3
from datetime import datetime

HOST = '0.0.0.0'
USER_PORT = 12345
ADMIN_PORT = 54321
DB_FILE = 'classcord.db'

CLIENTS = {}  # socket: {'username': str, 'connected': bool}
LOCK = threading.Lock()

# === Base SQLite ===
def init_db():
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                state TEXT,
                last_seen TEXT
            )
        """)
        conn.commit()

def register_user(username, password):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password, state, last_seen) VALUES (?, ?, 'offline', datetime('now'))", (username, password))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def check_user_password(username, password):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username=?", (username,))
        row = c.fetchone()
        return row and row[0] == password

def update_user_status(username, state):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET state=?, last_seen=datetime('now') WHERE username=?", (state, username))
        conn.commit()

def list_online_users():
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE state='online'")
        return [r[0] for r in c.fetchall()]

# === Broadcast ===
def broadcast(message, exclude_socket=None):
    to_remove = []
    with LOCK:
        for sock, info in CLIENTS.items():
            if not info.get('connected', False):
                continue
            if sock != exclude_socket:
                try:
                    sock.sendall((json.dumps(message) + '\n').encode())
                except Exception:
                    to_remove.append(sock)
        for s in to_remove:
            CLIENTS[s]['connected'] = False
            try:
                s.close()
            except:
                pass

# === Gestion clients utilisateurs ===
def handle_user_client(sock):
    addr = sock.getpeername()
    buffer = ''
    username = None
    print(f"[CONNEXION USER] Client connecté: {addr}")
    try:
        while True:
            data = sock.recv(1024).decode()
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    sock.sendall(json.dumps({'type': 'error', 'message': 'JSON invalide'}).encode() + b'\n')
                    continue

                mtype = msg.get('type')

                if mtype == 'register':
                    uname = msg.get('username')
                    pwd = msg.get('password')
                    with LOCK:
                        if register_user(uname, pwd):
                            sock.sendall(json.dumps({'type': 'register', 'status': 'ok'}).encode() + b'\n')
                            print(f"[REGISTER] {uname} enregistré")
                        else:
                            sock.sendall(json.dumps({'type': 'error', 'message': 'Username déjà utilisé'}).encode() + b'\n')

                elif mtype == 'login':
                    uname = msg.get('username')
                    pwd = msg.get('password')
                    with LOCK:
                        if check_user_password(uname, pwd):
                            username = uname
                            CLIENTS[sock] = {'username': username, 'connected': True}
                            update_user_status(username, 'online')
                            sock.sendall(json.dumps({'type': 'login', 'status': 'ok'}).encode() + b'\n')
                            broadcast({'type': 'status', 'user': username, 'state': 'online'}, exclude_socket=sock)
                            print(f"[LOGIN] {username} connecté")
                        else:
                            sock.sendall(json.dumps({'type': 'error', 'message': 'Échec du login'}).encode() + b'\n')

                elif mtype == 'message':
                    if not username:
                        sock.sendall(json.dumps({'type': 'error', 'message': 'Pas connecté'}).encode() + b'\n')
                        continue
                    content = msg.get('content')
                    if content:
                        timestamp = datetime.now().isoformat()
                        message_to_send = {
                            'type': 'message',
                            'from': username,
                            'content': content,
                            'timestamp': timestamp
                        }
                        broadcast(message_to_send, exclude_socket=None)

                else:
                    sock.sendall(json.dumps({'type': 'error', 'message': 'Commande inconnue'}).encode() + b'\n')

    except Exception as e:
        print(f"[ERREUR USER] Client {addr} ({username}): {e}")

    finally:
        if username:
            with LOCK:
                update_user_status(username, 'offline')
                CLIENTS.pop(sock, None)
                broadcast({'type': 'status', 'user': username, 'state': 'offline'}, exclude_socket=sock)
        try:
            sock.close()
        except:
            pass
        print(f"[DECONNEXION USER] Client {addr} déconnecté")

# === Gestion console admin ===
def handle_admin_client(sock):
    addr = sock.getpeername()
    print(f"[CONNEXION ADMIN] Console admin connectée: {addr}")

    def send_menu():
        menu = "\n=== MENU ADMIN ===\n" \
               "1. Lister utilisateurs connectés\n" \
               "2. Kicker un utilisateur\n" \
               "3. Envoyer un message global\n" \
               "4. Éteindre le serveur\n" \
               "0. Quitter\n" \
               "Choix : "
        sock.sendall(menu.encode())

    def list_users():
        users = list_online_users()
        if not users:
            msg = "Aucun utilisateur connecté.\n"
        else:
            msg = "Utilisateurs connectés:\n" + "\n".join(users) + "\n"
        sock.sendall(msg.encode())

    while True:
        try:
            send_menu()
            choice = sock.recv(1024).decode().strip()
            if not choice:
                break
            if choice == '1':
                list_users()
            elif choice == '2':
                sock.sendall(b"Nom d'utilisateur à kicker : ")
                target = sock.recv(1024).decode().strip()
                if not target:
                    continue
                kicked_sock = None
                with LOCK:
                    for s, info in CLIENTS.items():
                        if info.get('username') == target and info.get('connected', False):
                            kicked_sock = s
                            break
                if kicked_sock:
                    try:
                        kicked_sock.sendall(json.dumps({'type': 'kick', 'message': 'Vous avez été expulsé par l’admin.'}).encode() + b'\n')
                        CLIENTS[kicked_sock]['connected'] = False
                        kicked_sock.close()
                        update_user_status(target, 'offline')
                        broadcast({'type': 'system', 'content': f"{target} a été expulsé par l’admin."})
                        sock.sendall(f"Utilisateur {target} expulsé.\n".encode())
                    except Exception:
                        sock.sendall(b"Erreur lors du kick.\n")
                else:
                    sock.sendall(b"Utilisateur non trouvé.\n")

            elif choice == '3':
                sock.sendall(b"Message global à envoyer : ")
                message = sock.recv(4096).decode().strip()
                if message:
                    broadcast({'type': 'system', 'content': f"ADMIN: {message}"})
                    sock.sendall(b"Message envoyé.\n")

            elif choice == '4':
                broadcast({'type': 'system', 'content': 'Le serveur va s’éteindre.'})
                for s in list(CLIENTS.keys()):
                    try:
                        s.sendall(json.dumps({'type': 'shutdown', 'message': 'Serveur arrêté par admin.'}).encode() + b'\n')
                        s.close()
                    except:
                        pass
                sock.sendall(b"Serveur arrêté.\n")
                print("[ARRET] Serveur arrêté par l’admin.")
                os._exit(0)

            elif choice == '0':
                sock.sendall(b"Au revoir.\n")
                break

            else:
                sock.sendall(b"Choix invalide.\n")

        except Exception as e:
            print(f"[ERREUR ADMIN] {addr}: {e}")
            break

    try:
        sock.close()
    except:
        pass
    print(f"[DECONNEXION ADMIN] Console admin déconnectée: {addr}")

# === Main ===
def main():
    init_db()

    user_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    user_server.bind((HOST, USER_PORT))
    user_server.listen()

    admin_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    admin_server.bind((HOST, ADMIN_PORT))
    admin_server.listen()

    print(f"[DEMARRAGE] Serveur utilisateur sur {HOST}:{USER_PORT}")
    print(f"[DEMARRAGE] Console admin sur {HOST}:{ADMIN_PORT}")

    def accept_users():
        while True:
            client_sock, addr = user_server.accept()
            threading.Thread(target=handle_user_client, args=(client_sock,), daemon=True).start()

    def accept_admins():
        while True:
            admin_sock, addr = admin_server.accept()
            threading.Thread(target=handle_admin_client, args=(admin_sock,), daemon=True).start()

    threading.Thread(target=accept_users, daemon=True).start()
    threading.Thread(target=accept_admins, daemon=True).start()

    # Garde le main thread vivant
    while True:
        threading.Event().wait(1)

if __name__ == '__main__':
    main()
