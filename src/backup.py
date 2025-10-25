"""
Système de sauvegarde automatique de la base de données
"""
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

BACKUP_DIR = "backups"
DATABASE_PATH = "marketplace.db"
MAX_BACKUPS = 30  # Garder les 30 dernières sauvegardes

def create_backup():
    """Crée une sauvegarde de la base de données"""
    try:
        # Créer le dossier de sauvegarde s'il n'existe pas
        os.makedirs(BACKUP_DIR, exist_ok=True)

        # Vérifier que la base de données existe
        if not os.path.exists(DATABASE_PATH):
            logger.warning(f"Database file {DATABASE_PATH} does not exist, skipping backup")
            return None

        # Générer le nom du fichier de sauvegarde avec timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.db"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)

        # Copier la base de données
        shutil.copy2(DATABASE_PATH, backup_path)

        logger.info(f"✅ Backup created: {backup_path}")

        # Nettoyer les anciennes sauvegardes
        cleanup_old_backups()

        return backup_path

    except Exception as e:
        logger.error(f"❌ Failed to create backup: {e}")
        return None


def cleanup_old_backups():
    """Supprime les anciennes sauvegardes pour ne garder que les MAX_BACKUPS plus récentes"""
    try:
        if not os.path.exists(BACKUP_DIR):
            return

        # Lister tous les fichiers de backup
        backup_files = []
        for filename in os.listdir(BACKUP_DIR):
            if filename.startswith("backup_") and filename.endswith(".db"):
                filepath = os.path.join(BACKUP_DIR, filename)
                backup_files.append((filepath, os.path.getmtime(filepath)))

        # Trier par date de modification (plus récent d'abord)
        backup_files.sort(key=lambda x: x[1], reverse=True)

        # Supprimer les vieux backups
        for filepath, _ in backup_files[MAX_BACKUPS:]:
            os.remove(filepath)
            logger.info(f"🗑️  Removed old backup: {filepath}")

    except Exception as e:
        logger.error(f"❌ Failed to cleanup old backups: {e}")


def restore_backup(backup_path):
    """Restaure la base de données depuis une sauvegarde"""
    try:
        if not os.path.exists(backup_path):
            logger.error(f"Backup file {backup_path} does not exist")
            return False

        # Créer une sauvegarde de la base actuelle avant de restaurer
        if os.path.exists(DATABASE_PATH):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safety_backup = f"marketplace_before_restore_{timestamp}.db"
            shutil.copy2(DATABASE_PATH, safety_backup)
            logger.info(f"Safety backup created: {safety_backup}")

        # Restaurer depuis le backup
        shutil.copy2(backup_path, DATABASE_PATH)
        logger.info(f"✅ Database restored from: {backup_path}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to restore backup: {e}")
        return False


def list_backups():
    """Liste toutes les sauvegardes disponibles"""
    if not os.path.exists(BACKUP_DIR):
        return []

    backups = []
    for filename in os.listdir(BACKUP_DIR):
        if filename.startswith("backup_") and filename.endswith(".db"):
            filepath = os.path.join(BACKUP_DIR, filename)
            file_size = os.path.getsize(filepath)
            mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))

            backups.append({
                'filename': filename,
                'path': filepath,
                'size': file_size,
                'date': mod_time
            })

    # Trier par date (plus récent d'abord)
    backups.sort(key=lambda x: x['date'], reverse=True)
    return backups


if __name__ == '__main__':
    # Test du système de backup
    logging.basicConfig(level=logging.INFO)

    print("Creating backup...")
    backup_path = create_backup()

    if backup_path:
        print(f"\nBackup created: {backup_path}")

        print("\nAvailable backups:")
        for backup in list_backups():
            print(f"  - {backup['filename']} ({backup['size']} bytes) - {backup['date']}")
