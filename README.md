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

Les comptes de demo (`admin`, `moderateur`, `boutique.pro`, `boutique.gratuite`, `particulier`) arrivent avec la commande `seed_demo` (phase 1).