# TechKoin

Marketplace de reference au Benin pour acheter et vendre des PC, smartphones et tablettes, neufs ou d'occasion.

Le cahier des charges complet se trouve dans [TECHKOIN_SPEC.md](TECHKOIN_SPEC.md). Les choix pris en cours de route sont dans [docs/DECISIONS.md](docs/DECISIONS.md).

Etat : phase 6 (alertes et finitions) terminee, en attente de validation. Le MVP est complet.

## Installation (Windows, PowerShell)

Prerequis : Git, Python 3.12, Node.js LTS.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe backend\manage.py migrate
npm --prefix frontend install
```

## Lancement

```powershell
npm run dev
```

Lance l'API Django sur http://localhost:8000 et le front Vite sur http://localhost:5173 (proxy de `/api` vers Django). En dev, le styleguide est sur http://localhost:5173/_styleguide.

## Tests et qualite

```powershell
npm test                              # pytest puis vitest
npm --prefix frontend run lint
npm --prefix frontend run typecheck
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m black --check backend
```

Captures du styleguide (serveur Vite lance) : `npm --prefix frontend run screenshots`, resultat dans `docs/screenshots/`.

## Comptes de demo

```powershell
.\.venv\Scripts\python.exe backend\manage.py seed_catalog
.\.venv\Scripts\python.exe backend\manage.py seed_demo            # ajouter --reset pour recreer
```

`seed_demo` cree 8 boutiques, 25 particuliers, 150 annonces avec photos generees (images neutres, pas de photos reelles) et 90 jours d'evenements. Le compte Boutique Pro (Cotonou Tech) a 16 annonces et une demande MacBook M1 plantee pour le radar. Les ecrans de la phase 5 comptent les 7 et 30 derniers jours : relancer seed_demo --reset si les donnees ont vieilli.

Mot de passe de tous les comptes : `Demo2026!`

| Compte | E-mail |
|---|---|
| Administrateur | admin@demo.techkoin.test |
| Moderateur | moderateur@demo.techkoin.test |
| Boutique Pro | boutique.pro@demo.techkoin.test |
| Boutique gratuite | boutique.gratuite@demo.techkoin.test |
| Particulier | particulier@demo.techkoin.test |

## Moderation et taches planifiees

La moderation se fait dans l'admin Django (http://localhost:8000/admin/, compte `admin`) : « File de moderation » (annonces triees par score de risque, approbation, refus, demande de modifications), verifications d'identite et de boutique (utilisateurs et boutiques), declarations d'appareils voles, signalements.

A planifier en production :

```powershell
.\.venv\Scripts\python.exe backend\manage.py recompute_estimates            # chaque nuit : estimations, badges, scores d'usage
.\.venv\Scripts\python.exe backend\manage.py purge_verification_documents   # chaque jour : documents supprimes 90 jours apres la decision
```

## Paiement sandbox

Par defaut le simulateur (`PAYMENT_PROVIDER=simulator`). Numeros de test : fin en `00` refuse, `77` valide apres 5 secondes, `99` reste en attente (bouton « Valider le paiement simule » en developpement), tout autre numero est valide. Pour FedaPay : `PAYMENT_PROVIDER=fedapay` et les cles sandbox dans `.env`.

A planifier : `manage.py release_due_orders` toutes les 15 minutes (termine aussi les abonnements Pro echus) `manage.py send_alerts` toutes les 15 minutes (alertes de recherche) et `manage.py send_weekly_reports` chaque lundi a 8 h (heure de Porto-Novo) : rapport hebdomadaire des boutiques Pro par e-mail (console en developpement, SMTP en production via `EMAIL_BACKEND`).

## Tableau de bord boutique

Connexion avec un compte boutique puis "Espace pro" (`/pro`). L'offre Pro coute `PRO_PLAN_PRICE_FCFA` (10 000) par mois, payee avec les memes numeros de test que les commandes. Les routes Pro repondent 403 aux boutiques gratuites ; le plan est controle uniquement par le serveur.

## Tests de bout en bout

Serveurs lances et donnees de demo chargees : `npm --prefix frontend run e2e` (mobile 360 px et bureau 1280 px). Captures de la phase 1 : `npm --prefix frontend run screenshots:phase1`, resultat dans `docs/screenshots/phase1/`.

## PostgreSQL et deploiement

Les tests passent sur SQLite et sur PostgreSQL : `.\.venv\Scripts\python.exe scripts\test_postgres.py` demarre un PostgreSQL jetable et lance toute la suite dessus. Mise en ligne, nginx, taches planifiees : [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Performance et accessibilite : [docs/PERFORMANCE.md](docs/PERFORMANCE.md). Captures de la phase 6 : `npm --prefix frontend run screenshots:phase6`.
