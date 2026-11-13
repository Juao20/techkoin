# Déploiement

Cette page décrit une mise en ligne sur un seul serveur Linux. Rien de ce qui suit n'a été joué sur un vrai serveur : les commandes viennent du fonctionnement vérifié en local (tests sur SQLite et sur PostgreSQL, build de production servi en local). À dérouler une première fois sur un serveur de préproduction.

## Architecture

```
navigateur ── HTTPS ── nginx ─┬─ /assets, /brand, favicons, manifest ... → frontend/dist (fichiers)
                              ├─ /media/                                  → backend/media (fichiers)
                              └─ tout le reste (/api, /admin, /annonce/..., /boutique/...) → gunicorn (Django)
```

Django sert aussi `index.html` : pour `/annonce/<slug>` et `/boutique/<slug>` il y injecte les balises Open Graph (titre, prix, ville, première photo) qui donnent l'aperçu dans WhatsApp. Toutes les autres routes reçoivent l'`index.html` tel quel et le routeur React prend la suite. Un nginx qui enverrait ces deux familles d'URL directement au dossier `dist` ferait perdre les aperçus.

## Variables d'environnement

Voir `.env.example`. Le minimum en production :

| Variable | Valeur |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` (HTTPS forcé, cookies `Secure`, HSTS, `DEBUG=False`) |
| `DJANGO_SECRET_KEY` | longue chaîne aléatoire, obligatoire |
| `DJANGO_ALLOWED_HOSTS` | le nom de domaine |
| `CSRF_TRUSTED_ORIGINS` | `https://` + le nom de domaine |
| `SITE_URL` | `https://` + le nom de domaine (liens des e-mails, images Open Graph) |
| `DATABASE_URL` | `postgresql://utilisateur:motdepasse@hote:5432/techkoin` |
| `FIELD_ENCRYPTION_KEY` | clé Fernet : `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. **À sauvegarder** : sans elle les IMEI déjà enregistrés sont illisibles |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend`, avec `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` |
| `GROQ_API_KEY` | facultative : sans elle, toute l'IA tourne sur ses replis |
| `PAYMENT_PROVIDER`, `FEDAPAY_*` | `simulator` tant que FedaPay n'a pas été éprouvé avec de vraies clés |

## Mise en route

```bash
python -m venv .venv && .venv/bin/pip install -r backend/requirements.txt gunicorn
(cd frontend && npm ci && npm run build)          # produit frontend/dist
cd backend
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py seed_catalog         # marques, modèles, processeurs, villes
../.venv/bin/python manage.py collectstatic --noinput
../.venv/bin/python manage.py createsuperuser
../.venv/bin/gunicorn config.wsgi --bind 127.0.0.1:8000 --workers 3
```

Les documents d'identité sont écrits dans `backend/private_media`, qui ne doit **jamais** être servi par nginx. Les photos sont dans `backend/media` (servi sous `/media/`). Sauvegarder la base, `media/`, `private_media/` et la clé `FIELD_ENCRYPTION_KEY`.

## nginx (extrait)

```nginx
root /srv/techkoin/frontend/dist;

location /assets/ { expires 1y; add_header Cache-Control "public, immutable"; }
location = /robots.txt { }
location ~* ^/(brand/|favicon|apple-touch-icon|icon-|manifest\.webmanifest) { }

location /media/ { alias /srv/techkoin/backend/media/; expires 30d; }
location /static/ { alias /srv/techkoin/backend/staticfiles/; }

location / {                         # /api, /admin, /annonce/..., /boutique/..., routes du front
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
}
```

Activer la compression gzip (et Brotli si disponible) pour `text/html`, `application/javascript`, `text/css`, `application/json`.

## Tâches planifiées (cron)

Pas de Celery : chaque tâche est une commande Django. Fuseau du serveur : `Africa/Porto-Novo`.

```cron
*/15 * * * *  cd /srv/techkoin/backend && ../.venv/bin/python manage.py release_due_orders   # libération du séquestre, commandes non payées, abonnements échus
*/15 * * * *  cd /srv/techkoin/backend && ../.venv/bin/python manage.py send_alerts          # alertes de recherche
0 8 * * 1     cd /srv/techkoin/backend && ../.venv/bin/python manage.py send_weekly_reports  # rapport hebdomadaire des boutiques Pro
30 3 * * *    cd /srv/techkoin/backend && ../.venv/bin/python manage.py recompute_estimates   # estimations, badges, scores d'usage
0 4 * * *     cd /srv/techkoin/backend && ../.venv/bin/python manage.py purge_verification_documents  # documents supprimés 90 jours après la décision
```

## Passer de SQLite à PostgreSQL

Le code n'utilise ni SQL brut ni fonction propre à SQLite ; la recherche texte passe par `marketplace/search.py`.

1. Créer la base : `createdb techkoin` (ou l'équivalent chez l'hébergeur).
2. Renseigner `DATABASE_URL`, puis `manage.py migrate` et `manage.py seed_catalog`.
3. **Cas habituel (avant le lancement, données de démonstration seulement)** : repartir d'une base vide. `seed_demo` recrée la démonstration si elle est utile en préproduction.
4. **Si des données réelles existent sur SQLite** : `manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --exclude sessions > dump.json`, puis sur la base PostgreSQL migrée et vide `manage.py loaddata dump.json`. Les fichiers (`media/`, `private_media/`) se copient tels quels.
5. Vérifier : `manage.py check --deploy`, une inscription, une publication, un paiement simulé.

### Tester sur PostgreSQL en local

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\python.exe scripts\test_postgres.py
```

Le script démarre un PostgreSQL jetable (paquet `pgserver`), lance toute la suite de tests dessus et l'arrête. Avec un PostgreSQL déjà installé : `DATABASE_URL=postgresql://... pytest` depuis `backend/`. Résultat au moment de la phase 6 : les 302 tests passent sur SQLite et sur PostgreSQL.

## Avant d'ouvrir au public

- Faire relire un juriste : les pages `/cgu` et `/confidentialite` décrivent ce que fait l'application, mais ne sont pas un texte juridique validé. Renseigner une adresse de contact.
- Éprouver FedaPay avec de vraies clés sandbox, puis la production (paiement, webhook signé, versement, remboursement).
- Éprouver Groq avec une vraie clé (modèles `openai/gpt-oss-*`, transcription `whisper-large-v3`) et surveiller `AIRequestLog` dans l'admin.
- Refaire la mesure Lighthouse sur le serveur (voir `docs/PERFORMANCE.md`).
- Déclarer WhatsApp pour les alertes : l'interface existe (`marketplace/alerts.py`, `WhatsAppSender`), l'envoi n'est pas branché.
