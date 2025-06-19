import socket
import threading
import json
import pickle
import os
from datetime import datetime

HOST = '0.0.0.0'
PORT = 12345
ADMIN_PORT = 54321

USER_FILE = 'users.pkl'
CLIENTS = {}  # socket: username
USERS = {}    # username: password
LOCK = threading.Lock()

def load_users():
    global USERS
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'rb') as f:
            USERS = pickle.load(f)
    print(f"[INIT] Utilisateurs chargés: {list(USERS.keys())}")

def save_users():
    with open(USER_FILE, 'wb') as f:
        pickle.dump(USERS, f)
    print("[SAVE] Utilisateurs sauvegardés.")

def broadcast(message, sender_socket=None):
    with LOCK:
        for client_socket, username in CLIENTS.items():
            if client_socket != sender_socket:
                try:
                    client_socket.sendall((json.dumps(message) + '\n').encode())
                    print(f"[ENVOI] Message envoyé à {username} : {message}")
                except Exception as e:
                    print(f"[ERREUR] Échec d'envoi à {username} : {e}")

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
                print(f"[RECU] {address} >> {line}")
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
                    broadcast({'type': 'status', 'user': username, 'state': msg['state']}, client_socket)
                    print(f"[STATUS] {username} est maintenant {msg['state']}")

    except Exception as e:
        print(f'[ERREUR] Problème avec {address} ({username}):', e)
    finally:
        if username:
            broadcast({'type': 'status', 'user': username, 'state': 'offline'}, client_socket)
        with LOCK:
            CLIENTS.pop(client_socket, None)
        client_socket.close()
        print(f"[DECONNEXION] {address} déconnecté")

def handle_admin(client):
    buffer = ''
    try:
        while True:
            data = client.recv(1024).decode()
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                msg = json.loads(line)

                if msg['type'] == 'kick':
                    target = msg.get('target')
                    with LOCK:
                        for sock, user in list(CLIENTS.items()):
                            if user == target:
                                try:
                                    sock.sendall(json.dumps({'type': 'kick'}).encode() + b'\n')
                                    sock.close()
                                except Exception as e:
                                    print(f"[ERREUR] Impossible de kicker {user} : {e}")
                                finally:
                                    CLIENTS.pop(sock, None)

                elif msg['type'] == 'global_message':
                    content = msg.get('content', '')
                    if content:
                        message = {
                            'type': 'message',
                            'from': '[ADMIN]',
                            'content': content,
                            'timestamp': datetime.now().isoformat()
                        }
                        print(f"[ADMIN] Message global envoyé : {content}")
                        broadcast(message)

                elif msg['type'] == 'shutdown':
                    print("[ADMIN] Demande d'arrêt reçue. Fermeture du serveur.")
                    os._exit(0)
    except Exception as e:
        print("[ERREUR] Console admin :", e)
    finally:
        client.close()

def start_admin_server():
    admin_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    admin_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    admin_socket.bind((HOST, ADMIN_PORT))
    admin_socket.listen()
    print(f"[ADMIN] Serveur admin en écoute sur le port {ADMIN_PORT}")
    while True:
        client, _ = admin_socket.accept()
        threading.Thread(target=handle_admin, args=(client,), daemon=True).start()

def main():
    load_users()
    threading.Thread(target=start_admin_server, daemon=True).start()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"[DEMARRAGE] Serveur en écoute sur {HOST}:{PORT}")
    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == '__main__':
    main()
