import os
import asyncio
import logging
import sys
from threading import Thread
from datetime import datetime, timedelta
from dotenv import load_dotenv

from src.database import init_database
from src.client_bot import setup_client_bot
from src.worker_bot import setup_worker_bot
from src.web_admin import create_app
from src.backup import create_backup

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)

def validate_environment():
    """Valide que toutes les variables d'environnement requises sont définies"""
    required_vars = {
        'CLIENT_BOT_TOKEN': 'Token du bot client Telegram',
        'WORKER_BOT_TOKEN': 'Token du bot worker Telegram',
        'ADMIN_PASSWORD': 'Mot de passe admin',
        'FLASK_SECRET_KEY': 'Clé secrète Flask'
    }

    missing = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing.append(f"  - {var}: {description}")

    if missing:
        logger.error("❌ Variables d'environnement manquantes:")
        for item in missing:
            logger.error(item)
        logger.info("\nVeuillez configurer ces variables dans votre fichier .env")
        logger.info("Consultez .env.example pour un modèle")
        logger.info("\nPour obtenir les tokens Telegram: https://t.me/BotFather")
        return False

    logger.info("✅ Variables d'environnement validées")
    return True

def run_flask_app():
    """Lance l'application Flask dans un thread séparé"""
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

async def periodic_backup():
    """Effectue une sauvegarde automatique toutes les 24 heures"""
    while True:
        try:
            await asyncio.sleep(86400)  # 24 heures
            logger.info("🔄 Lancement de la sauvegarde automatique...")
            backup_path = create_backup()
            if backup_path:
                logger.info(f"✅ Sauvegarde automatique réussie: {backup_path}")
            else:
                logger.warning("⚠️  Échec de la sauvegarde automatique")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde automatique: {e}")

async def main():
    """
    Point d'entrée principal
    Lance les 2 bots Telegram et le dashboard Flask en parallèle
    """
    logger.info("🚀 Démarrage de la Marketplace d'avis...")

    # Valider les variables d'environnement
    if not validate_environment():
        sys.exit(1)

    # Initialiser la base de données
    try:
        init_database()
        logger.info("✅ Base de données initialisée")
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation de la base de données: {e}")
        sys.exit(1)

    # Créer une sauvegarde initiale
    try:
        logger.info("💾 Création de la sauvegarde initiale...")
        backup_path = create_backup()
        if backup_path:
            logger.info(f"✅ Sauvegarde initiale créée: {backup_path}")
    except Exception as e:
        logger.warning(f"⚠️  Impossible de créer la sauvegarde initiale: {e}")

    CLIENT_BOT_TOKEN = os.getenv('CLIENT_BOT_TOKEN')
    WORKER_BOT_TOKEN = os.getenv('WORKER_BOT_TOKEN')

    logger.info("🤖 Configuration des bots Telegram...")
    client_app = setup_client_bot(CLIENT_BOT_TOKEN)
    worker_app = setup_worker_bot(WORKER_BOT_TOKEN)

    logger.info("🌐 Démarrage du dashboard Flask...")
    flask_thread = Thread(target=run_flask_app, daemon=True)
    flask_thread.start()

    logger.info("✅ Tous les services sont démarrés !")
    logger.info("\n" + "="*50)
    logger.info("📊 Dashboard Admin: http://0.0.0.0:5000")
    logger.info("   Username: admin")
    logger.info("   Password: (configuré dans les secrets)")
    logger.info("="*50 + "\n")

    async with client_app, worker_app:
        await client_app.start()
        await client_app.updater.start_polling()
        logger.info("✅ Bot Client démarré et en écoute")

        await worker_app.start()
        await worker_app.updater.start_polling()
        logger.info("✅ Bot Worker démarré et en écoute")

        # Lancer la tâche de sauvegarde périodique
        backup_task = asyncio.create_task(periodic_backup())
        logger.info("💾 Système de sauvegarde automatique activé (toutes les 24h)")

        logger.info("\n🎉 Marketplace opérationnelle !")
        logger.info("Vous pouvez maintenant :")
        logger.info("  - Accéder au dashboard admin")
        logger.info("  - Parler aux bots sur Telegram")
        logger.info("\nAppuyez sur Ctrl+C pour arrêter\n")

        await asyncio.Event().wait()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Arrêt de la marketplace...")
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}", exc_info=True)
