import sqlite3
import random
import string
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
DATABASE_PATH = "marketplace.db"

def generate_id(prefix):
    """Génère un ID aléatoire avec un préfixe (ex: C-7K9P, WRK-001)"""
    if prefix == "C":
        return f"C-{random.choice(string.ascii_uppercase)}{random.randint(1,9)}{random.choice(string.ascii_uppercase)}{random.randint(1,9)}"
    elif prefix == "WRK":
        return f"WRK-{random.randint(100, 999)}"
    elif prefix == "CMD":
        return f"CMD-{random.randint(100, 999)}"
    elif prefix == "TSK":
        return f"TSK-{random.randint(1000, 9999)}"
    return f"{prefix}-{random.randint(1000, 9999)}"

def init_database():
    """Initialise la base de données avec toutes les tables nécessaires"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Table Clients (entreprises qui commandent)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT UNIQUE NOT NULL,
            telegram_id INTEGER UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Migration: Vérifier si la table tasks existe déjà et ajouter les colonnes manquantes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
    tasks_table_exists = cursor.fetchone() is not None
    
    if tasks_table_exists:
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'platform' not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN platform TEXT DEFAULT 'Google Reviews'")
            logger.info("✅ Migration: Colonne 'platform' ajoutée à la table tasks")
        
        cursor.execute("UPDATE tasks SET reward = 3.5 WHERE reward = 5.0")
        logger.info("✅ Migration: Récompenses ajustées à 3.5 USDT")
    
    # Table Workers (microworkers)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id TEXT UNIQUE NOT NULL,
            telegram_id INTEGER UNIQUE NOT NULL,
            level TEXT DEFAULT 'Bronze',
            rating REAL DEFAULT 0.0,
            balance REAL DEFAULT 0.0,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table Commandes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE NOT NULL,
            client_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            target_link TEXT,
            brief TEXT,
            status TEXT DEFAULT 'pending',
            price REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(client_id)
        )
    ''')
    
    # Table Avis (contenu des avis à distribuer)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            content TEXT NOT NULL,
            rating REAL DEFAULT 5.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
    ''')
    
    # Table Tâches (affectées aux workers)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            order_id TEXT NOT NULL,
            worker_id TEXT,
            review_content TEXT NOT NULL,
            rating REAL DEFAULT 5.0,
            target_link TEXT NOT NULL,
            platform TEXT DEFAULT 'Google Reviews',
            reward REAL DEFAULT 3.5,
            status TEXT DEFAULT 'available',
            proof_screenshot TEXT,
            proof_link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            accepted_at TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (worker_id) REFERENCES workers(worker_id)
        )
    ''')
    
    # Table Messages Support
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            message TEXT NOT NULL,
            sender_type TEXT NOT NULL,
            telegram_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(client_id)
        )
    ''')
    
    # Migrations pour colonnes manquantes
    cursor.execute("PRAGMA table_info(orders)")
    orders_columns = [col[1] for col in cursor.fetchall()]
    
    if 'payment_proof' not in orders_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN payment_proof TEXT")
        logger.info("✅ Migration: Colonne 'payment_proof' ajoutée à la table orders")
    
    if 'order_type' not in orders_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN order_type TEXT DEFAULT 'reviews'")
        logger.info("✅ Migration: Colonne 'order_type' ajoutée à la table orders")
    
    cursor.execute("PRAGMA table_info(clients)")
    clients_columns = [col[1] for col in cursor.fetchall()]
    
    if 'telegram_username' not in clients_columns:
        cursor.execute("ALTER TABLE clients ADD COLUMN telegram_username TEXT")
        logger.info("✅ Migration: Colonne 'telegram_username' ajoutée à la table clients")
    
    conn.commit()
    conn.close()

def get_db():
    """Retourne une connexion à la base de données"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_or_create_client(telegram_id):
    """Récupère ou crée un client par son telegram_id"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM clients WHERE telegram_id = ?", (telegram_id,))
    client = cursor.fetchone()
    
    if not client:
        client_id = generate_id("C")
        cursor.execute(
            "INSERT INTO clients (client_id, telegram_id) VALUES (?, ?)",
            (client_id, telegram_id)
        )
        conn.commit()
        cursor.execute("SELECT * FROM clients WHERE telegram_id = ?", (telegram_id,))
        client = cursor.fetchone()
    
    conn.close()
    return dict(client)

def get_or_create_worker(telegram_id):
    """Récupère ou crée un worker par son telegram_id"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM workers WHERE telegram_id = ?", (telegram_id,))
    worker = cursor.fetchone()
    
    if not worker:
        worker_id = generate_id("WRK")
        cursor.execute(
            "INSERT INTO workers (worker_id, telegram_id) VALUES (?, ?)",
            (worker_id, telegram_id)
        )
        conn.commit()
        cursor.execute("SELECT * FROM workers WHERE telegram_id = ?", (telegram_id,))
        worker = cursor.fetchone()
    
    conn.close()
    return dict(worker)

def create_order(client_id, platform, quantity, target_link, brief, order_type='reviews'):
    """Crée une nouvelle commande"""
    conn = get_db()
    cursor = conn.cursor()
    
    order_id = generate_id("CMD")
    price = quantity * 5.0
    
    cursor.execute('''
        INSERT INTO orders (order_id, client_id, platform, quantity, target_link, brief, price, order_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (order_id, client_id, platform, quantity, target_link, brief, price, order_type))
    
    conn.commit()
    conn.close()
    return order_id

def get_client_orders(client_id):
    """Récupère toutes les commandes d'un client"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM orders WHERE client_id = ? ORDER BY created_at DESC
    ''', (client_id,))
    
    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return orders

def get_all_orders():
    """Récupère toutes les commandes (pour l'admin)"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM orders ORDER BY created_at DESC')
    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return orders

def get_order_by_id(order_id):
    """Récupère une commande par son ID"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,))
    order = cursor.fetchone()
    conn.close()
    return dict(order) if order else None

def add_review_to_order(order_id, content, rating=5.0):
    """Ajoute un avis à une commande"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO reviews (order_id, content, rating)
        VALUES (?, ?, ?)
    ''', (order_id, content, rating))
    
    conn.commit()
    conn.close()

def get_order_reviews(order_id):
    """Récupère tous les avis d'une commande"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM reviews WHERE order_id = ?', (order_id,))
    reviews = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return reviews

def delete_review(review_id):
    """Supprime un avis"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM reviews WHERE id = ?', (review_id,))
    conn.commit()
    conn.close()

def distribute_tasks(order_id):
    """Distribue les avis d'une commande en tâches pour les workers"""
    conn = get_db()
    cursor = conn.cursor()
    
    order = get_order_by_id(order_id)
    if not order:
        conn.close()
        return []
    
    reviews = get_order_reviews(order_id)
    task_ids = []
    
    for review in reviews:
        task_id = generate_id("TSK")
        cursor.execute('''
            INSERT INTO tasks (task_id, order_id, review_content, rating, target_link, reward, platform)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (task_id, order_id, review['content'], review['rating'], order['target_link'], 3.5, order['platform']))
        task_ids.append(task_id)
    
    cursor.execute('UPDATE orders SET status = ? WHERE order_id = ?', ('distributed', order_id))
    
    conn.commit()
    conn.close()
    return task_ids

def get_available_tasks():
    """Récupère toutes les tâches disponibles"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC', ('available',))
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks

def get_task_by_id(task_id):
    """Récupère une tâche par son ID"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
    task = cursor.fetchone()
    conn.close()
    return dict(task) if task else None

def accept_task(task_id, worker_id):
    """Un worker accepte une tâche"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE tasks SET status = ?, worker_id = ?, accepted_at = ?
        WHERE task_id = ? AND status = ?
    ''', ('in_progress', worker_id, datetime.now(), task_id, 'available'))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def submit_proof(task_id, screenshot_path, proof_link):
    """Worker soumet une preuve pour une tâche"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE tasks SET status = ?, proof_screenshot = ?, proof_link = ?
        WHERE task_id = ?
    ''', ('pending_validation', screenshot_path, proof_link, task_id))
    
    conn.commit()
    conn.close()

def get_worker_tasks(worker_id):
    """Récupère toutes les tâches d'un worker"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM tasks WHERE worker_id = ? ORDER BY created_at DESC
    ''', (worker_id,))
    
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks

def get_tasks_pending_validation():
    """Récupère toutes les tâches en attente de validation"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC', ('pending_validation',))
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks

def validate_task(task_id):
    """Valide une tâche et ajoute la récompense au worker"""
    conn = get_db()
    cursor = conn.cursor()
    
    task = get_task_by_id(task_id)
    if not task or task['status'] != 'pending_validation':
        conn.close()
        return False
    
    cursor.execute('''
        UPDATE tasks SET status = ?, completed_at = ?
        WHERE task_id = ?
    ''', ('validated', datetime.now(), task_id))
    
    cursor.execute('''
        UPDATE workers SET balance = balance + ?
        WHERE worker_id = ?
    ''', (task['reward'], task['worker_id']))
    
    conn.commit()
    conn.close()
    return True

def reject_task(task_id):
    """Rejette une tâche"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE tasks SET status = ?, worker_id = NULL, proof_screenshot = NULL, proof_link = NULL
        WHERE task_id = ?
    ''', ('available', task_id))
    
    conn.commit()
    conn.close()

def get_all_workers():
    """Récupère tous les workers (pour l'admin)"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM workers ORDER BY created_at DESC')
    workers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return workers

def update_worker_status(worker_id, status):
    """Met à jour le statut d'un worker"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE workers SET status = ? WHERE worker_id = ?', (status, worker_id))
    conn.commit()
    conn.close()

def get_stats():
    """Récupère les statistiques pour le dashboard admin"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as count FROM orders WHERE status IN (?, ?)', ('paid', 'distributed'))
    active_orders = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM workers WHERE status = ?', ('active',))
    active_workers = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM tasks WHERE status = ?', ('pending_validation',))
    pending_tasks = cursor.fetchone()['count']
    
    conn.close()
    
    return {
        'active_orders': active_orders,
        'active_workers': active_workers,
        'pending_tasks': pending_tasks
    }

def delete_order(order_id):
    """Supprime une commande et tous ses avis associés"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM reviews WHERE order_id = ?', (order_id,))
    cursor.execute('DELETE FROM orders WHERE order_id = ?', (order_id,))
    
    conn.commit()
    conn.close()

def get_worker_by_telegram_id(telegram_id):
    """Récupère un worker par son telegram_id"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM workers WHERE telegram_id = ?', (telegram_id,))
    worker = cursor.fetchone()
    conn.close()
    return dict(worker) if worker else None

def get_client_by_telegram_id(telegram_id):
    """Récupère un client par son telegram_id"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM clients WHERE telegram_id = ?', (telegram_id,))
    client = cursor.fetchone()
    conn.close()
    return dict(client) if client else None

def get_worker_by_id(worker_id):
    """Récupère un worker par son worker_id"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM workers WHERE worker_id = ?', (worker_id,))
    worker = cursor.fetchone()
    conn.close()
    return dict(worker) if worker else None

def save_support_message(client_id, message, sender_type, telegram_username=None):
    """Sauvegarde un message de support"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Créer la table si elle n'existe pas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            message TEXT NOT NULL,
            sender_type TEXT NOT NULL,
            telegram_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(client_id)
        )
    ''')
    
    cursor.execute('''
        INSERT INTO support_messages (client_id, message, sender_type, telegram_username)
        VALUES (?, ?, ?, ?)
    ''', (client_id, message, sender_type, telegram_username))
    
    conn.commit()
    conn.close()

def get_support_messages(client_id=None):
    """Récupère les messages de support"""
    conn = get_db()
    cursor = conn.cursor()
    
    if client_id:
        cursor.execute('''
            SELECT * FROM support_messages 
            WHERE client_id = ? 
            ORDER BY created_at ASC
        ''', (client_id,))
    else:
        cursor.execute('''
            SELECT * FROM support_messages 
            ORDER BY created_at DESC 
            LIMIT 100
        ''')
    
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return messages

def save_payment_proof(order_id, file_path):
    """Sauvegarde la preuve de paiement pour une commande"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Ajouter la colonne si elle n'existe pas
    cursor.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'payment_proof' not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN payment_proof TEXT")
        logger.info("✅ Migration: Colonne 'payment_proof' ajoutée à la table orders")
    
    cursor.execute('''
        UPDATE orders SET payment_proof = ? WHERE order_id = ?
    ''', (file_path, order_id))
    
    conn.commit()
    conn.close()

def update_client_username(telegram_id, username):
    """Met à jour le username Telegram d'un client"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Ajouter la colonne si elle n'existe pas
    cursor.execute("PRAGMA table_info(clients)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'telegram_username' not in columns:
        cursor.execute("ALTER TABLE clients ADD COLUMN telegram_username TEXT")
        logger.info("✅ Migration: Colonne 'telegram_username' ajoutée à la table clients")
    
    cursor.execute('''
        UPDATE clients SET telegram_username = ? WHERE telegram_id = ?
    ''', (username, telegram_id))
    
    conn.commit()
    conn.close()
