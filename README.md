# TechKoin

Marketplace de reference au Benin pour acheter et vendre des PC, smartphones et tablettes, neufs ou d'occasion.

Le cahier des charges complet se trouve dans [TECHKOIN_SPEC.md](TECHKOIN_SPEC.md). Les choix pris en cours de route sont dans [docs/DECISIONS.md](docs/DECISIONS.md).

Etat : phase 0 (socle) terminee, en attente de validation.

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

`seed_demo` cree 8 boutiques, 25 particuliers, 150 annonces avec photos generees (images neutres, pas de photos reelles) et 90 jours d'evenements. Les commandes de commande sandbox arriveront avec la phase 4.

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

## Tests de bout en bout

Serveurs lances et donnees de demo chargees : `npm --prefix frontend run e2e` (mobile 360 px et bureau 1280 px). Captures de la phase 1 : `npm --prefix frontend run screenshots:phase1`, resultat dans `docs/screenshots/phase1/`.