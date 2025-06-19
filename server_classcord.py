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
    msg_str = json.dumps(message) + '\n'
    for client_socket, username in list(CLIENTS.items()):
        if client_socket != sender_socket:
            try:
                client_socket.sendall(msg_str.encode())
                print(f"[ENVOI] à {username} : {message}")
            except:
                with LOCK:
                    print(f"[ERREUR] Échec d'envoi à {username}. Déconnexion.")
                    CLIENTS.pop(client_socket, None)
                    client_socket.close()

def handle_client(client_socket):
    buffer = ''
    username = None
    address = client_socket.getpeername()
    print(f"[CONNEXION] {address}")
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                msg = json.loads(line)
                print(f"[RECU] {address} : {msg}")

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
                            print(f"[LOGIN] {username} connecté.")
                        else:
                            response = {'type': 'error', 'message': 'Login failed.'}
                            client_socket.sendall((json.dumps(response) + '\n').encode())

                elif msg['type'] == 'message':
                    if not username:
                        username = msg.get('from', 'invité')
                        with LOCK:
                            CLIENTS[client_socket] = username
                    msg['from'] = username
                    msg['timestamp'] = datetime.now().isoformat()
                    print(f"[MSG] {username} >> {msg['content']}")
                    broadcast(msg, client_socket)

                elif msg['type'] == 'status' and username:
                    broadcast({'type': 'status', 'user': username, 'state': msg['state']}, client_socket)
                    print(f"[STATUS] {username} est {msg['state']}")

    except Exception as e:
        print(f"[ERREUR] Client {address} ({username}) : {e}")
    finally:
        if username:
            broadcast({'type': 'status', 'user': username, 'state': 'offline'}, client_socket)
        with LOCK:
            CLIENTS.pop(client_socket, None)
        client_socket.close()
        print(f"[DECONNEXION] {address} / {username}")

def handle_admin():
    admin_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    admin_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    admin_sock.bind((HOST, ADMIN_PORT))
    admin_sock.listen()
    print(f"[ADMIN] Console admin en écoute sur {HOST}:{ADMIN_PORT}")
    while True:
        client, _ = admin_sock.accept()
        threading.Thread(target=handle_admin_connection, args=(client,), daemon=True).start()

def handle_admin_connection(client):
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
                print(f"[ADMIN CMD] {msg}")

                if msg['type'] == 'kick':
                    target = msg.get('target')
                    with LOCK:
                        for sock, user in list(CLIENTS.items()):
                            if user == target:
                                try:
                                    sock.sendall(json.dumps({'type': 'kick'}).encode())
                                    sock.close()
                                    CLIENTS.pop(sock)
                                    print(f"[KICK] {target} expulsé.")
                                except:
                                    print(f"[KICK-FAIL] Impossible d’expulser {target}")
                                break

                elif msg['type'] == 'global_message':
                    content = msg.get('content', '')
                    if content:
                        global_msg = {
                            'type': 'message',
                            'from': 'ADMIN',
                            'content': content,
                            'timestamp': datetime.now().isoformat()
                        }
                        broadcast(global_msg)

                elif msg['type'] == 'shutdown':
                    print("[ARRET] Arrêt demandé par l'admin.")
                    os._exit(0)

                elif msg['type'] == 'get_users':
                    with LOCK:
                        users = list(CLIENTS.values())
                    client.sendall((json.dumps({'users': users}) + '\n').encode())

    except Exception as e:
        print(f"[ADMIN ERR] {e}")
    finally:
        client.close()

def main():
    load_users()
    threading.Thread(target=handle_admin, daemon=True).start()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"[SERVEUR] En écoute sur {HOST}:{PORT}")
    while True:
        client_socket, _ = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == '__main__':
    main()
