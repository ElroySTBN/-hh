import logging
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from src.database import get_or_create_client, create_order, get_client_orders, get_order_by_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# États de conversation
class OrderState:
    PLATFORM = 'platform'
    QUANTITY = 'quantity'
    URL = 'url'
    INSTRUCTIONS = 'instructions'
    CONTENT_CHOICE = 'content_choice'
    USER_CONTENT = 'user_content'
    RECAP = 'recap'
    CONFIRM = 'confirm'

# Prix de base
BASE_PRICE_PER_REVIEW = 5.0
CONTENT_GENERATION_FEE = 0.5
PAYMENT_ADDRESS = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"  # Bitcoin random pour MVP

# Stockage temporaire des données de commande
user_data_store = {}
user_order_states = {}

def generate_tracking_number():
    """Génère un numéro de suivi"""
    return f"LB{random.randint(100000, 999999)}"

def format_price(quantity, has_content_generation):
    """Calcule le prix total"""
    base_price = quantity * BASE_PRICE_PER_REVIEW
    if has_content_generation:
        base_price += quantity * CONTENT_GENERATION_FEE
    return base_price

def build_recap_text(data):
    """Construit le texte de récapitulatif"""
    price = format_price(data['quantity'], data.get('content_generation', False))
    recap = f"""📋 Récapitulatif de votre commande

━━━━━━━━━━━━━━━━━━
📊 Plateforme : {data['platform']}
🔢 Nombre d'avis : {data['quantity']}
📍 URL cible : {data['target_link'][:50]}...
💭 Instructions : {data.get('instructions', 'Aucune')[:50]}...
🤖 Génération : {'Oui (+0.5 USDT/avis)' if data.get('content_generation') else 'Vous fournissez le contenu'}
━━━━━━━━━━━━━━━━━━
💰 Prix total : {price:.2f} USDT
━━━━━━━━━━━━━━━━━━
"""
    return recap

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Message de bienvenue du bot client"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    client = get_or_create_client(user_id)
    
    # Sauvegarder le username Telegram
    from src.database import update_client_username
    if username:
        update_client_username(user_id, username)
    
    # Nettoyer tous les états (y compris support_mode)
    context.user_data.clear()
    if user_id in user_data_store:
        del user_data_store[user_id]
    if user_id in user_order_states:
        del user_order_states[user_id]
    
    welcome_text = """🔐 Le Bon Mot
Service Anonyme de E-réputation

━━━━━━━━━━━━━━━━━━
🌍 Avis 100% authentiques et géolocalisés
🔒 Anonymat total garanti
🎯 IP réelles, comptes vérifiés
💳 Paiement crypto uniquement
━━━━━━━━━━━━━━━━━━
✅ Plus de 15 000 avis livrés avec succès
✅ Délai moyen de livraison : 48-72h
━━━━━━━━━━━━━━━━━━

Votre ID : #{}""".format(client['client_id'])
    
    keyboard = [
        [InlineKeyboardButton("📝 Commander des avis", callback_data="order:start")],
        [InlineKeyboardButton("📦 Mes commandes", callback_data="orders:list")],
        [InlineKeyboardButton("💬 Contacter le support", callback_data="support:contact")],
        [InlineKeyboardButton("🛡️ Garanties", callback_data="info:guarantees")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les clics sur les boutons"""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Erreur lors de l'answer du callback (normal si bot redémarré): {e}")
    
    data = query.data
    if ':' not in data:
        return
    
    action, param = data.split(':', 1)
    
    if action == 'order':
        await handle_order_flow(query, context, param)
    elif action == 'orders':
        await handle_orders(query, context, param)
    elif action == 'support':
        await handle_support(query, context, param)
    elif action == 'info':
        await handle_info(query, context, param)
    elif action == 'back':
        await handle_back(query, context, param)
    elif action == 'recap':
        if param == 'confirm':
            await confirm_order(query, context)
        elif param == 'with_gen':
            await recap_with_generation(query, context)
        elif param == 'edit':
            await edit_recap(query, context)
    elif action == 'confirm':
        if param == 'final':
            await finalize_order(query, context)
    elif action == 'payment':
        if param.startswith('proof_'):
            order_id = param.replace('proof_', '')
            context.user_data['awaiting_payment_proof'] = order_id
            await query.edit_message_text(
                "📸 Envoi de la preuve de paiement\n\n"
                "Envoyez-moi la capture d'écran de votre paiement.\n\n"
                "Vous pouvez envoyer :\n"
                "• Une photo\n"
                "• Un document",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Annuler", callback_data="back:menu")]])
            )
    elif action == 'menu':
        await back_to_menu(query, context)

async def handle_order_flow(query, context, step):
    """Gère le workflow de commande"""
    user_id = query.from_user.id
    
    if step == 'start':
        # Désactiver le mode support si actif
        if 'support_mode' in context.user_data:
            del context.user_data['support_mode']
        
        # Étape 1: Choix de la plateforme
        user_order_states[user_id] = {'step': OrderState.PLATFORM}
        
        text = """📋 Étape 1/6 : Choix de la plateforme

Sur quelle plateforme souhaitez-vous des avis ?"""
        
        keyboard = [
            [InlineKeyboardButton("📍 Google Reviews", callback_data="order:platform_google")],
            [InlineKeyboardButton("⭐ Trustpilot", callback_data="order:platform_trustpilot")],
            [InlineKeyboardButton("🌐 Autres plateformes", callback_data="order:platform_autre")],
            [InlineKeyboardButton("🏠 Retour au menu", callback_data="back:menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    elif step.startswith('platform_'):
        # Plateforme sélectionnée
        platform = step.split('_', 1)[1]
        platform_names = {
            "google": "📍 Google Reviews",
            "trustpilot": "⭐ Trustpilot",
            "autre": "🌐 Autres plateformes"
        }
        
        user_data_store[user_id] = {'platform': platform_names.get(platform, "🌐 Autres")}
        user_order_states[user_id]['step'] = OrderState.QUANTITY
        
        # Récapitulatif
        recap = f"""📋 Récapitulatif
━━━━━━━━━━━━━━━━━━
📊 Plateforme : {user_data_store[user_id]['platform']}
━━━━━━━━━━━━━━━━━━

📝 Étape 2/6 : Nombre d'avis

Combien d'avis souhaitez-vous ?
(Entrez un nombre)"""
        
        keyboard = [[InlineKeyboardButton("« Retour", callback_data="order:start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(recap, reply_markup=reply_markup)
        
        context.user_data['awaiting'] = OrderState.QUANTITY
    
    elif step == 'content_self':
        # L'utilisateur rédige lui-même
        user_data_store[user_id]['content_generation'] = False
        user_order_states[user_id]['step'] = OrderState.RECAP
        
        recap = build_recap_text(user_data_store[user_id])
        recap += f"""
📝 Étape 5/6 : Validation

Vérifiez les informations ci-dessus.
Souhaitez-vous confirmer cette commande ?"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Confirmer et payer", callback_data="confirm:final")],
            [InlineKeyboardButton("✏️ Modifier", callback_data="recap:edit")],
            [InlineKeyboardButton("❌ Annuler", callback_data="back:menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(recap, reply_markup=reply_markup)
    
    elif step == 'content_generated':
        # Le Bon Mot génère le contenu
        user_data_store[user_id]['content_generation'] = True
        user_order_states[user_id]['step'] = OrderState.INSTRUCTIONS
        
        recap = f"""📋 Récapitulatif
━━━━━━━━━━━━━━━━━━
📊 Plateforme : {user_data_store[user_id]['platform']}
🔢 Nombre d'avis : {user_data_store[user_id]['quantity']}
📍 URL : {user_data_store[user_id]['target_link'][:30]}...
🤖 Génération : Le Bon Mot (+0.5€/avis)
━━━━━━━━━━━━━━━━━━

📝 Étape 5/6 : Instructions

Décrivez ce que vous souhaitez :
• Points à mentionner
• Ton souhaité (professionnel, décontracté...)
• Note moyenne souhaitée
• Mots-clés importants

Ou tapez "Passer" pour des avis génériques."""
        
        keyboard = [[InlineKeyboardButton("« Retour", callback_data="order:start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(recap, reply_markup=reply_markup)
        
        context.user_data['awaiting'] = OrderState.INSTRUCTIONS

async def handle_orders(query, context, param):
    """Gère l'affichage des commandes"""
    if param == 'list':
        await show_my_orders(query, context)

async def handle_support(query, context, param):
    """Gère le support"""
    if param == 'contact':
        ticket_num = generate_tracking_number()
        await query.edit_message_text(
            f"""💬 Contacter le support

━━━━━━━━━━━━━━━━━━
📧 Ticket créé : #{ticket_num}
⏱️ Temps de réponse : < 2h
━━━━━━━━━━━━━━━━━━

Envoyez votre question directement ici.
Notre équipe vous répondra sous 2 heures.

Vous pouvez joindre :
• Capture d'écran
• Photo
• Fichier

Un support humain traitera votre demande.

💡 Tous vos messages seront automatiquement transférés au support jusqu'à ce que vous reveniez au menu.""",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Retour au menu", callback_data="back:menu")]])
        )
        context.user_data['support_ticket'] = ticket_num
        context.user_data['support_mode'] = True  # Active le mode support

async def handle_info(query, context, param):
    """Gère les informations"""
    if param == 'guarantees':
        await show_guarantees(query, context)

async def handle_back(query, context, param):
    """Gère la navigation retour"""
    if param == 'menu':
        await back_to_menu(query, context)

async def back_to_menu(query, context):
    """Retour au menu principal"""
    user_id = query.from_user.id
    client = get_or_create_client(user_id)
    
    welcome_text = """🔐 Le Bon Mot
Service Anonyme de E-réputation

━━━━━━━━━━━━━━━━━━
🌍 Avis 100% authentiques et géolocalisés
🔒 Anonymat total garanti
🎯 IP réelles, comptes vérifiés
💳 Paiement crypto uniquement
━━━━━━━━━━━━━━━━━━
✅ Plus de 15 000 avis livrés avec succès
✅ Délai moyen de livraison : 48-72h
━━━━━━━━━━━━━━━━━━

Votre ID : #{}""".format(client['client_id'])
    
    keyboard = [
        [InlineKeyboardButton("📝 Commander des avis", callback_data="order:start")],
        [InlineKeyboardButton("📦 Mes commandes", callback_data="orders:list")],
        [InlineKeyboardButton("💬 Contacter le support", callback_data="support:contact")],
        [InlineKeyboardButton("🛡️ Garanties", callback_data="info:guarantees")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Nettoyer l'état de conversation (y compris support_mode)
    context.user_data.clear()
    if user_id in user_data_store:
        del user_data_store[user_id]
    if user_id in user_order_states:
        del user_order_states[user_id]
    
    await query.edit_message_text(welcome_text, reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les messages texte selon l'état de la conversation"""
    user_id = update.effective_user.id
    awaiting = context.user_data.get('awaiting')
    
    # Mode support : tous les messages sont transférés automatiquement
    if context.user_data.get('support_mode'):
        from src.database import save_support_message, get_or_create_client
        
        client = get_or_create_client(user_id)
        username = update.effective_user.username or ''
        
        # Sauvegarder le message dans la base
        save_support_message(client['client_id'], update.message.text, 'client', username)
        
        await update.message.reply_text(
            f"""✅ Message envoyé au support
            
Votre message a bien été transmis.
Notre équipe vous répondra sous peu.

Pour revenir au menu principal, cliquez ci-dessous :""",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Retour au menu", callback_data="back:menu")
            ]])
        )
        return
    
    if awaiting == OrderState.QUANTITY:
        try:
            quantity = int(update.message.text)
            if quantity < 1:
                await update.message.reply_text("❌ Veuillez entrer un nombre valide (minimum 1).")
                return
            
            user_data_store[user_id]['quantity'] = quantity
            user_order_states[user_id]['step'] = OrderState.URL
            
            # Récapitulatif
            recap = f"""📋 Récapitulatif
━━━━━━━━━━━━━━━━━━
📊 Plateforme : {user_data_store[user_id]['platform']}
🔢 Nombre d'avis : {quantity}
━━━━━━━━━━━━━━━━━━

📝 Étape 3/6 : URL cible

Entrez l'URL ou l'identifiant de la page cible"""
            
            await update.message.reply_text(recap)
            context.user_data['awaiting'] = OrderState.URL
            
        except ValueError:
            await update.message.reply_text("❌ Veuillez entrer un nombre valide.")
    
    elif awaiting == OrderState.URL:
        user_data_store[user_id]['target_link'] = update.message.text
        user_order_states[user_id]['step'] = OrderState.CONTENT_CHOICE
        
        recap = f"""📋 Récapitulatif
━━━━━━━━━━━━━━━━━━
📊 Plateforme : {user_data_store[user_id]['platform']}
🔢 Nombre d'avis : {user_data_store[user_id]['quantity']}
📍 URL : {update.message.text[:50]}...
━━━━━━━━━━━━━━━━━━

📝 Étape 4/6 : Qui rédige les avis ?

📝 Option 1 - Vous rédigez
• Vous fournissez le contenu
• Prix : {user_data_store[user_id]['quantity'] * BASE_PRICE_PER_REVIEW:.2f} USDT

🤖 Option 2 - Le Bon Mot rédige ✨
• Notre équipe génère les avis
• Avis authentiques et variés
• Prix : {format_price(user_data_store[user_id]['quantity'], True):.2f} USDT
• (+0.50 USDT par avis)"""
        
        keyboard = [
            [InlineKeyboardButton("📝 Je rédige moi-même", callback_data="order:content_self")],
            [InlineKeyboardButton("🤖 Le Bon Mot rédige ✨", callback_data="order:content_generated")],
            [InlineKeyboardButton("« Retour", callback_data="order:start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(recap, reply_markup=reply_markup)
        
        context.user_data['awaiting'] = None
    
    elif awaiting == OrderState.INSTRUCTIONS:
        user_data_store[user_id]['instructions'] = update.message.text if update.message.text.lower() != 'passer' else ''
        user_order_states[user_id]['step'] = OrderState.RECAP
        
        # Afficher le récapitulatif final
        recap = build_recap_text(user_data_store[user_id])
        recap += f"""
📝 Étape 6/6 : Validation

Vérifiez les informations ci-dessus.
Souhaitez-vous confirmer cette commande ?"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Confirmer et payer", callback_data="confirm:final")],
            [InlineKeyboardButton("✏️ Modifier", callback_data="recap:edit")],
            [InlineKeyboardButton("❌ Annuler", callback_data="back:menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(recap, reply_markup=reply_markup)
        
        context.user_data['awaiting'] = None
    
    elif awaiting == OrderState.USER_CONTENT:
        # L'utilisateur fournit son contenu (non implémenté pour MVP)
        await update.message.reply_text("✅ Contenu enregistré !")
    
    # Support
    elif 'support_ticket' in context.user_data:
        ticket = context.user_data['support_ticket']
        # Sauvegarder le message en base de données (à impl émenter dans database.py)
        from src.database import save_support_message
        client = get_or_create_client(user_id)
        save_support_message(client['client_id'], update.message.text, 'client', update.effective_user.username)
        
        await update.message.reply_text(
            f"✅ Message envoyé au support (Ticket #{ticket})\n\n"
            "Notre équipe vous répondra sous 2h.\n\n"
            "Vous pouvez continuer à utiliser le bot normalement.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="back:menu")]])
        )
        context.user_data.pop('support_ticket', None)
    
    # Preuve de paiement
    elif 'awaiting_payment_proof' in context.user_data:
        await update.message.reply_text(
            "✅ Merci ! Veuillez maintenant envoyer la capture d'écran de votre paiement."
        )

async def recap_with_generation(query, context):
    """Affiche le récapitulatif avec génération de contenu"""
    user_id = query.from_user.id
    user_data_store[user_id]['content_generation'] = True
    
    recap = build_recap_text(user_data_store[user_id])
    recap += f"""
📋 Étape 6/6 : Validation

Vérifiez les informations ci-dessus.
Souhaitez-vous confirmer cette commande ?"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirmer et payer", callback_data="confirm:final")],
        [InlineKeyboardButton("✏️ Modifier", callback_data="recap:edit")],
        [InlineKeyboardButton("❌ Annuler", callback_data="back:menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(recap, reply_markup=reply_markup)

async def confirm_order(query, context):
    """Affiche le récapitulatif final"""
    user_id = query.from_user.id
    user_data_store[user_id]['content_generation'] = False
    
    recap = build_recap_text(user_data_store[user_id])
    recap += f"""
📋 Étape 6/6 : Validation

Vérifiez les informations ci-dessus.
Souhaitez-vous confirmer cette commande ?"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirmer et payer", callback_data="confirm:final")],
        [InlineKeyboardButton("✏️ Modifier", callback_data="recap:edit")],
        [InlineKeyboardButton("❌ Annuler", callback_data="back:menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(recap, reply_markup=reply_markup)

async def edit_recap(query, context):
    """Permet de modifier le récapitulatif"""
    await query.edit_message_text(
        "✏️ Modification de la commande\n\n"
        "Pour modifier votre commande, utilisez /start pour recommencer.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Retour au menu", callback_data="back:menu")]])
    )

async def finalize_order(query, context):
    """Finalise la commande"""
    user_id = query.from_user.id
    client = get_or_create_client(user_id)
    data = user_data_store[user_id]
    
    # Créer la commande en base
    order_id = create_order(
        client['client_id'],
        data['platform'],
        data['quantity'],
        data['target_link'],
        data.get('instructions', '')
    )
    
    # Calcul du prix
    price = format_price(data['quantity'], data.get('content_generation', False))
    tracking = generate_tracking_number()
    
    # Message de confirmation
    confirm_text = f"""✅ Commande confirmée !

━━━━━━━━━━━━━━━━━━
📋 Numéro de suivi : #{tracking}
📋 Référence commande : {order_id}
━━━━━━━━━━━━━━━━━━

📊 Récapitulatif :
• Plateforme : {data['platform']}
• Nombre d'avis : {data['quantity']}
• Génération : {'Oui' if data.get('content_generation') else 'Non'}
• Prix total : **{price:.2f} USDT**
━━━━━━━━━━━━━━━━━━

💳 Paiement

Adresse Bitcoin :
`{PAYMENT_ADDRESS}`

⚠️ **IMPORTANT - FRAIS DE RÉSEAU**
• Calculez les frais de réseau de votre wallet
• Envoyez : **{price:.2f} USDT** + frais réseau
• Le montant reçu doit être **exactement {price:.2f} USDT**
• Sinon, vous perdrez de l'argent !

📞 **Prochaines étapes** :
1. Effectuez le paiement à l'adresse ci-dessus
2. Notre support vous contactera pour confirmer la réception
3. Confirmation sous 2h

⏳ Livraison : 48-72h après confirmation du paiement

💡 Besoin d'aide ? Utilisez "💬 Contacter le support" depuis le menu principal."""
    
    keyboard = [
        [InlineKeyboardButton("📋 Voir mes commandes", callback_data="orders:list")],
        [InlineKeyboardButton("💬 Contacter le support", callback_data="support:contact")],
        [InlineKeyboardButton("🏠 Retour au menu", callback_data="back:menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(confirm_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # Nettoyer
    user_data_store.pop(user_id, None)
    user_order_states.pop(user_id, None)
    context.user_data.clear()

async def show_my_orders(query, context):
    """Affiche les commandes du client"""
    user_id = query.from_user.id
    client = get_or_create_client(user_id)
    orders = get_client_orders(client['client_id'])
    
    if not orders:
        await query.edit_message_text(
            "📦 Mes commandes\n\n"
            "Vous n'avez pas encore de commandes.\n\n"
            "Commencez votre première commande !\n\n"
            "━━━━━━━━━━━━━━━━━━",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📝 Commander des avis", callback_data="order:start")]])
        )
        return
    
    text = "📦 Mes commandes\n\n━━━━━━━━━━━━━━━━━━\n"
    
    status_info = {
        'pending': ('⏳ En attente de paiement', ''),
        'paid': ('✅ Payé', 'En cours de traitement'),
        'distributed': ('🔄 En cours', 'Livraison en cours'),
        'completed': ('✅ Livré', 'Commande terminée'),
        'cancelled': ('❌ Annulée', 'Commande annulée')
    }
    
    for order in orders[:10]:
        status_emoji, status_desc = status_info.get(order['status'], ('❓', ''))
        text += f"{status_emoji} {order['order_id']}\n"
        text += f"📊 {order['platform']}\n"
        text += f"🔢 {order['quantity']} avis\n"
        text += f"💰 {order['price']:.2f} USDT\n"
        if status_desc:
            text += f"💬 {status_desc}\n"
        text += "━━━━━━━━━━━━━━━━━━\n"
    
    keyboard = [
        [InlineKeyboardButton("📝 Nouvelle commande", callback_data="order:start")],
        [InlineKeyboardButton("💬 Support", callback_data="support:contact")],
        [InlineKeyboardButton("🏠 Menu", callback_data="back:menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def show_guarantees(query, context):
    """Affiche les garanties et sécurité"""
    guarantees_text = """🛡️ Garanties et sécurité

━━━━━━━━━━━━━━━━━━
✅ GARANTIES
━━━━━━━━━━━━━━━━━━
• Avis 100% authentiques et vérifiés
• Livraison garantie sous 72h
• Remplacement gratuit si problème
• Satisfaction ou remboursement
• Support réactif 24/7

━━━━━━━━━━━━━━━━━━
🔒 SÉCURITÉ & ANONYMAT
━━━━━━━━━━━━━━━━━━
• Anonymat total garanti
• Aucune donnée personnelle stockée
• IP réelles uniquement
• Comptes vérifiés et actifs
• Paiement crypto sécurisé

━━━━━━━━━━━━━━━━━━
💳 MÉTHODES DE PAIEMENT
━━━━━━━━━━━━━━━━━━
• Bitcoin (BTC)
• Ethereum (ETH)
• USDT (TRC20/ERC20)
• Autres cryptos sur demande"""
    
    keyboard = [
        [InlineKeyboardButton("📝 Commander", callback_data="order:start")],
        [InlineKeyboardButton("💬 Support", callback_data="support:contact")],
        [InlineKeyboardButton("🏠 Menu", callback_data="back:menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(guarantees_text, reply_markup=reply_markup)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la réception de photos (mode support)"""
    user_id = update.effective_user.id
    
    # Si en mode support, enregistrer comme message
    if context.user_data.get('support_mode'):
        from src.database import save_support_message, get_or_create_client
        
        client = get_or_create_client(user_id)
        username = update.effective_user.username or ''
        
        # Sauvegarder le message dans la base
        save_support_message(client['client_id'], "[📸 Photo envoyée]", 'client', username)
        
        await update.message.reply_text(
            f"""✅ Photo envoyée au support
            
Votre photo a bien été transmise.
Notre équipe vous répondra sous peu.

Pour revenir au menu principal, cliquez ci-dessous :""",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Retour au menu", callback_data="back:menu")
            ]])
        )
    else:
        await update.message.reply_text(
            "Je n'ai pas compris. Utilisez les boutons du menu.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="back:menu")]])
        )

def setup_client_bot(token):
    """Configure et retourne l'application du bot client"""
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    return application
