# 📦 Guide de Déploiement - Marketplace Bot

Ce guide présente plusieurs options d'hébergement pour votre bot, **du gratuit au faible coût**.

## 🎯 Prérequis

- 2 tokens de bot Telegram (obtenus sur [@BotFather](https://t.me/BotFather))
- Un mot de passe admin sécurisé
- Les fichiers de votre projet

---

## 🆓 Options d'Hébergement GRATUITES

### 1. **Railway.app** ⭐ RECOMMANDÉ

**✅ Avantages:**
- 500 heures gratuites/mois (suffisant pour 1 projet)
- Déploiement en 1 clic depuis GitHub
- Domaine HTTPS gratuit
- Logs et monitoring intégrés
- Support Docker

**📝 Étapes:**

1. Créer un compte sur [railway.app](https://railway.app)

2. Connecter votre repository GitHub

3. Créer un nouveau projet → "Deploy from GitHub repo"

4. Ajouter les variables d'environnement:
   ```
   CLIENT_BOT_TOKEN=votre_token_client
   WORKER_BOT_TOKEN=votre_token_worker
   ADMIN_PASSWORD=votre_mot_de_passe_admin
   FLASK_SECRET_KEY=une_cle_secrete_aleatoire
   ```

5. Railway détectera automatiquement le Dockerfile et déploiera

6. Exposer le port 5000 dans les paramètres

**⚠️ Limites:** 500 heures/mois gratuit, puis $5/mois

---

### 2. **Render.com**

**✅ Avantages:**
- Tier gratuit permanent
- SSL automatique
- Facile à configurer
- Bon uptime

**📝 Étapes:**

1. Créer un compte sur [render.com](https://render.com)

2. New → Web Service → Connecter GitHub

3. Configuration:
   - **Build Command:** `pip install -e .`
   - **Start Command:** `python main.py`
   - **Environment:** Python 3

4. Ajouter les variables d'environnement (onglet Environment)

5. Déployer!

**⚠️ Limites:** Le tier gratuit dort après 15 min d'inactivité (se réveille au 1er accès)

---

### 3. **Fly.io**

**✅ Avantages:**
- Tier gratuit généreux
- Support Docker natif
- Déploiement global (edge computing)
- Bon pour les bots (toujours actif)

**📝 Étapes:**

1. Installer Fly CLI:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. Se connecter:
   ```bash
   fly auth login
   ```

3. Lancer l'app depuis le dossier du projet:
   ```bash
   fly launch
   ```

4. Configurer les secrets:
   ```bash
   fly secrets set CLIENT_BOT_TOKEN=xxx WORKER_BOT_TOKEN=xxx ADMIN_PASSWORD=xxx FLASK_SECRET_KEY=xxx
   ```

5. Déployer:
   ```bash
   fly deploy
   ```

**⚠️ Limites:** 3 petites VMs gratuites, 160GB transfer/mois

---

### 4. **Oracle Cloud (Always Free)** 💎

**✅ Avantages:**
- VRAIMENT gratuit à vie
- 4 CPUs ARM, 24 GB RAM (très généreux!)
- Pas de carte bancaire requise
- Excellent pour les bots

**📝 Étapes:**

1. Créer un compte [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/)

2. Créer une VM Compute (ARM, Ubuntu 22.04)

3. Se connecter en SSH:
   ```bash
   ssh ubuntu@<IP_DE_VOTRE_VM>
   ```

4. Installer Docker:
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   ```

5. Cloner votre projet:
   ```bash
   git clone https://github.com/votre-repo/marketplace-bot.git
   cd marketplace-bot
   ```

6. Créer le fichier .env:
   ```bash
   nano .env
   # Coller vos variables d'environnement
   ```

7. Démarrer avec Docker Compose:
   ```bash
   docker-compose up -d
   ```

8. Configurer le pare-feu Oracle pour ouvrir le port 5000

**⚠️ Limites:** Aucune! Complètement gratuit à vie.

---

### 5. **Google Cloud Run**

**✅ Avantages:**
- 2 millions de requêtes gratuites/mois
- Scaling automatique
- Paiement uniquement à l'utilisation

**📝 Étapes:**

1. Installer [gcloud CLI](https://cloud.google.com/sdk/docs/install)

2. Configurer le projet:
   ```bash
   gcloud init
   gcloud auth configure-docker
   ```

3. Build et push l'image:
   ```bash
   docker build -t gcr.io/[PROJECT-ID]/marketplace-bot .
   docker push gcr.io/[PROJECT-ID]/marketplace-bot
   ```

4. Déployer:
   ```bash
   gcloud run deploy marketplace-bot \
     --image gcr.io/[PROJECT-ID]/marketplace-bot \
     --platform managed \
     --region us-central1 \
     --set-env-vars CLIENT_BOT_TOKEN=xxx,WORKER_BOT_TOKEN=xxx,ADMIN_PASSWORD=xxx,FLASK_SECRET_KEY=xxx
   ```

**⚠️ Limites:** Gratuit jusqu'à 2M requêtes/mois

---

## 💰 Options Hébergement BAS COÛT (< 5€/mois)

### 6. **Contabo VPS** (~3.99€/mois)

**✅ Avantages:**
- Le moins cher du marché
- 4 vCPU cores, 6 GB RAM, 200 GB SSD
- Excellent rapport qualité/prix
- Support 24/7

**📝 Étapes:**

1. Commander un VPS sur [contabo.com](https://contabo.com)

2. Recevoir les accès SSH par email

3. Se connecter:
   ```bash
   ssh root@votre-ip
   ```

4. Installer Docker (voir instructions Oracle Cloud ci-dessus)

5. Cloner et démarrer le projet avec Docker Compose

**💰 Prix:** 3.99€/mois (VPS S)

---

### 7. **Hetzner Cloud** (~3.79€/mois)

**✅ Avantages:**
- Datacenter en Europe (RGPD compliant)
- Très rapide
- Interface simple
- Bonne réputation

**📝 Étapes:**

1. Créer un compte [Hetzner Cloud](https://www.hetzner.com/cloud)

2. Créer un serveur CX11 (2 GB RAM, 1 vCPU, 20 GB SSD)

3. Suivre les mêmes étapes que Contabo (SSH, Docker, etc.)

**💰 Prix:** 3.79€/mois

---

### 8. **DigitalOcean** (~$4/mois)

**✅ Avantages:**
- Interface intuitive
- Marketplace d'apps pré-configurées
- Documentation excellente
- Monitoring inclus

**📝 Étapes:**

1. Créer un compte [DigitalOcean](https://www.digitalocean.com) ($200 de crédit pour nouveaux utilisateurs)

2. Créer un Droplet (Basic, $4/mois, 512MB RAM)

3. Choisir "Docker" dans le Marketplace

4. Se connecter et déployer votre projet

**💰 Prix:** $4/mois (Droplet basique)

---

## 🚀 Déploiement Rapide avec Docker

Une fois votre serveur configuré (VPS ou cloud):

```bash
# 1. Cloner le projet
git clone https://github.com/votre-repo/marketplace-bot.git
cd marketplace-bot

# 2. Créer le fichier .env
cat > .env << EOF
CLIENT_BOT_TOKEN=votre_token_client
WORKER_BOT_TOKEN=votre_token_worker
ADMIN_PASSWORD=votre_mot_de_passe_admin
FLASK_SECRET_KEY=$(openssl rand -hex 32)
EOF

# 3. Démarrer avec Docker Compose
docker-compose up -d

# 4. Vérifier les logs
docker-compose logs -f

# 5. Vérifier le statut
curl http://localhost:5000/health
```

---

## 📊 Comparatif des Options

| Service | Prix/Mois | RAM | CPU | Stockage | Limites | Uptime | Recommandation |
|---------|-----------|-----|-----|----------|---------|--------|----------------|
| **Railway** | Gratuit (500h) | 512MB | Partagé | 1GB | 500h/mois | 99.9% | ⭐⭐⭐⭐⭐ |
| **Render** | Gratuit | 512MB | Partagé | 1GB | Dort après 15min | 99% | ⭐⭐⭐ |
| **Fly.io** | Gratuit | 256MB | Partagé | 1GB | 3 VMs max | 99.9% | ⭐⭐⭐⭐ |
| **Oracle Cloud** | Gratuit à vie | 24GB | 4 ARM | 200GB | Aucune | 99.95% | ⭐⭐⭐⭐⭐ |
| **GCP Cloud Run** | Gratuit (2M req) | 1GB | Auto | - | 2M req/mois | 99.95% | ⭐⭐⭐⭐ |
| **Contabo** | 3.99€ | 6GB | 4 vCPU | 200GB | - | 99.9% | ⭐⭐⭐⭐⭐ |
| **Hetzner** | 3.79€ | 2GB | 1 vCPU | 20GB | - | 99.9% | ⭐⭐⭐⭐ |
| **DigitalOcean** | $4 | 512MB | 1 vCPU | 10GB | - | 99.99% | ⭐⭐⭐⭐ |

---

## 🎯 Recommandations par Cas d'Usage

### Pour débuter (budget 0€):
1. **Railway** - Le plus simple et fiable
2. **Oracle Cloud** - Si vous voulez du "always free" puissant
3. **Fly.io** - Bon compromis

### Pour production (petit budget):
1. **Contabo VPS** - Meilleur rapport qualité/prix
2. **Hetzner Cloud** - Si données en Europe
3. **Oracle Cloud Free** - Gratuit et très performant

### Pour scaling futur:
1. **Google Cloud Run** - Scaling automatique
2. **Railway** - Passage facile au plan payant
3. **DigitalOcean** - Écosystème complet

---

## 🔒 Sécurité et Bonnes Pratiques

### Variables d'environnement

Ne JAMAIS commiter le fichier `.env`. Toujours utiliser:
- Railway/Render: Interface web pour les variables
- VPS: Fichier `.env` avec permissions `chmod 600`

### Sauvegarde automatique

Ajouter un cron job pour backup quotidien:

```bash
# Éditer crontab
crontab -e

# Ajouter cette ligne (backup tous les jours à 2h du matin)
0 2 * * * cd /chemin/vers/projet && mkdir -p backups && cp marketplace.db backups/backup-$(date +\%Y\%m\%d-\%H\%M\%S).db
```

### Monitoring

Pour vérifier que votre bot fonctionne:

```bash
# Vérifier le health check
curl http://votre-domaine.com/health

# Voir les logs
docker-compose logs -f
```

### Mise à jour

```bash
# Récupérer les dernières modifications
git pull origin main

# Redémarrer les containers
docker-compose down
docker-compose up -d --build
```

---

## 🆘 Dépannage

### Le bot ne répond pas
```bash
# Vérifier les logs
docker-compose logs

# Vérifier que les containers tournent
docker-compose ps

# Redémarrer
docker-compose restart
```

### Base de données corrompue
```bash
# Restaurer depuis un backup
cp backups/backup-YYYYMMDD-HHMMSS.db marketplace.db
docker-compose restart
```

### Problème de mémoire
```bash
# Voir l'utilisation
docker stats

# Ajouter swap (VPS)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📚 Ressources Utiles

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Docker Documentation](https://docs.docker.com/)
- [Flask Deployment](https://flask.palletsprojects.com/en/latest/deploying/)
- [SQLite Backup](https://www.sqlite.org/backup.html)

---

## 🎉 Conclusion

**Pour 0€:** Utilisez **Railway** ou **Oracle Cloud Free Tier**

**Pour ~4€/mois:** Utilisez **Contabo** ou **Hetzner** pour des performances maximales

Tous ces services peuvent héberger votre bot de manière fiable. Le choix dépend de votre budget et de vos préférences!
