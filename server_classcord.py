import socket
import threading
import json
import sqlite3
import os
import logging
from datetime import datetime

HOST = '0.0.0.0'
PORT = 12345

DB_FILE = 'users.db'
CLIENTS = {}  # socket: username
LOCK = threading.Lock()

# Logging
LOG_PATH = "/var/log/classcord.log"
logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format='%(asctime)s - %(message)s')

# Init DB
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            state TEXT DEFAULT 'offline'
        )
    ''')
    conn.commit()
    conn.close()

def user_exists(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE username = ?", (username,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def get_password(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def create_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    conn.commit()
    conn.close()

def set_user_state(username, state):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor
