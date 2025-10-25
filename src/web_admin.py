import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from src.database import (
    get_all_orders, get_order_by_id, get_order_reviews, add_review_to_order,
    delete_review, distribute_tasks, get_all_workers, update_worker_status,
    get_tasks_pending_validation, validate_task, reject_task, get_stats,
    delete_order, get_task_by_id, get_worker_by_telegram_id
)

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def login_required(f):
    """Décorateur pour protéger les routes admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion admin"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'admin' and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('Connexion réussie !', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Identifiants incorrects', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Déconnexion admin"""
    session.pop('logged_in', None)
    flash('Vous êtes déconnecté', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    """Dashboard principal admin"""
    stats = get_stats()
    orders = get_all_orders()
    workers = get_all_workers()
    pending_tasks = get_tasks_pending_validation()
    
    return render_template('dashboard.html', 
                         stats=stats,
                         orders=orders,
                         workers=workers,
                         pending_tasks=pending_tasks)

@app.route('/order/<order_id>')
@login_required
def order_details(order_id):
    """Page de détails d'une commande"""
    order = get_order_by_id(order_id)
    if not order:
        flash('Commande non trouvée', 'error')
        return redirect(url_for('dashboard'))
    
    reviews = get_order_reviews(order_id)
    
    return render_template('order_details.html', order=order, reviews=reviews)

@app.route('/order/<order_id>/add_review', methods=['POST'])
@login_required
def add_review(order_id):
    """Ajoute un avis manuellement à une commande"""
    content = request.form.get('content')
    rating = float(request.form.get('rating', 5.0))
    
    if content:
        add_review_to_order(order_id, content, rating)
        flash('Avis ajouté avec succès', 'success')
    else:
        flash('Le contenu de l\'avis est requis', 'error')
    
    return redirect(url_for('order_details', order_id=order_id))

@app.route('/order/<order_id>/import_reviews', methods=['POST'])
@login_required
def import_reviews(order_id):
    """Importe des avis depuis un fichier .txt"""
    if 'file' not in request.files:
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('order_details', order_id=order_id))
    
    file = request.files['file']
    if file.filename == '':
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('order_details', order_id=order_id))
    
    if file and file.filename.endswith('.txt'):
        content = file.read().decode('utf-8')
        reviews = [r.strip() for r in content.split('\n\n') if r.strip()]
        
        default_rating = float(request.form.get('default_rating', 5.0))
        
        for review in reviews:
            if review:
                add_review_to_order(order_id, review, default_rating)
        
        flash(f'{len(reviews)} avis importés avec succès', 'success')
    else:
        flash('Format de fichier invalide. Utilisez un fichier .txt', 'error')
    
    return redirect(url_for('order_details', order_id=order_id))

@app.route('/review/<int:review_id>/delete', methods=['POST'])
@login_required
def delete_review_route(review_id):
    """Supprime un avis"""
    order_id = request.form.get('order_id')
    delete_review(review_id)
    flash('Avis supprimé', 'success')
    return redirect(url_for('order_details', order_id=order_id))

@app.route('/order/<order_id>/distribute', methods=['POST'])
@login_required
def distribute_order(order_id):
    """Distribue une commande aux workers"""
    order = get_order_by_id(order_id)
    reviews = get_order_reviews(order_id)
    
    if not reviews:
        flash('Veuillez d\'abord ajouter des avis à cette commande', 'error')
        return redirect(url_for('order_details', order_id=order_id))
    
    if len(reviews) < order['quantity']:
        flash(f'Attention : vous avez {len(reviews)} avis sur {order["quantity"]} demandés', 'warning')
    
    task_ids = distribute_tasks(order_id)
    
    workers = get_all_workers()
    active_workers = [w for w in workers if w['status'] == 'active']
    
    flash(f'{len(task_ids)} tâches créées et distribuées à {len(active_workers)} workers actifs', 'success')
    
    return redirect(url_for('dashboard'))

@app.route('/order/<order_id>/delete', methods=['POST'])
@login_required
def delete_order_route(order_id):
    """Supprime une commande"""
    delete_order(order_id)
    flash('Commande supprimée', 'success')
    return redirect(url_for('dashboard'))

@app.route('/worker/<worker_id>/status', methods=['POST'])
@login_required
def update_worker_status_route(worker_id):
    """Met à jour le statut d'un worker"""
    status = request.form.get('status')
    update_worker_status(worker_id, status)
    
    status_labels = {
        'active': 'activé',
        'pending': 'mis en attente',
        'blocked': 'bloqué'
    }
    
    flash(f'Worker {status_labels.get(status, "mis à jour")}', 'success')
    return redirect(url_for('dashboard'))

@app.route('/task/<task_id>/validate', methods=['POST'])
@login_required
def validate_task_route(task_id):
    """Valide une tâche soumise par un worker"""
    task = get_task_by_id(task_id)
    if not task:
        flash('Tâche non trouvée', 'error')
        return redirect(url_for('dashboard'))
    
    success = validate_task(task_id)
    
    if success:
        flash(f'Tâche validée ! {task["reward"]} USDT ajoutés au solde du worker', 'success')
        
        worker = get_worker_by_telegram_id(task['worker_id'])
        if worker:
            pass
    else:
        flash('Erreur lors de la validation', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/task/<task_id>/reject', methods=['POST'])
@login_required
def reject_task_route(task_id):
    """Rejette une tâche soumise par un worker"""
    reject_task(task_id)
    flash('Tâche rejetée et remise en disponible', 'warning')
    return redirect(url_for('dashboard'))

@app.route('/task/<task_id>/screenshot')
@login_required
def view_screenshot(task_id):
    """Affiche le screenshot d'une tâche"""
    task = get_task_by_id(task_id)
    if not task or not task['proof_screenshot']:
        flash('Screenshot non trouvé', 'error')
        return redirect(url_for('dashboard'))

    return render_template('screenshot.html', task=task)

@app.route('/health')
def health_check():
    """Endpoint de santé pour monitoring"""
    try:
        # Vérifier la connexion à la base de données
        from src.database import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.fetchone()

        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'service': 'marketplace'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

@app.route('/api/stats')
@login_required
def api_stats():
    """API endpoint pour obtenir les statistiques"""
    try:
        stats = get_stats()
        stats['timestamp'] = datetime.utcnow().isoformat()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def create_app():
    """Créer et configurer l'application Flask"""
    return app
