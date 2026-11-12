# Decisions

Format : date, question, choix, raison.

## 2026-11-12 : Dependances hors liste (regle 0.7)

- Question : quelles dependances ajouter en plus de celles de la section 3 ?
- Choix :
  - Backend : `cryptography` (chiffrement des IMEI, `FIELD_ENCRYPTION_KEY`), `python-dotenv` (lecture de `.env`), `dj-database-url` (lecture de `DATABASE_URL`), `pytest` et `pytest-django` (tests), `ruff` et `black` (qualite, section 16).
  - Frontend : `@radix-ui/react-slider` et `@radix-ui/react-toast` (RangeSlider et Toast, headless, restyles), `@hookform/resolvers` (lien entre React Hook Form et Zod), `vitest` et `jsdom` (tests), `@playwright/test` (tests de parcours et captures du styleguide), ESLint et Prettier.
- Raison : chaque element est necessaire a une exigence du document et evite de reecrire du code sensible (chiffrement) ou d'accessibilite (slider, toasts).

## 2026-11-12 : Lancement des deux serveurs sous Windows

- Question : `make dev` n'existe pas sous Windows.
- Choix : `npm run dev` a la racine appelle `scripts/dev.ps1`, qui lance Django (8000) et Vite (5173).
- Raison : pas d'outil supplementaire a installer.

## 2026-11-12 : Modele User defini des la phase 0

- Question : le modele `User` appartient a la phase 1 ; faut-il l'attendre ?
- Choix : `accounts.User` (section 4.1, sans `Shop`) est cree des la phase 0 avec `AUTH_USER_MODEL`.
- Raison : changer `AUTH_USER_MODEL` apres la premiere migration est tres couteux. Les endpoints d'authentification restent en phase 1 ; seule la configuration des sessions et du CSRF est faite (route `/api/auth/csrf/`).

## 2026-11-12 : Etiquettes (Tag)

- Question : « capitales normales (pas tout en majuscules) » (15.5).
- Choix : casse normale d'une phrase, jamais `text-transform: uppercase`.

## 2026-11-12 : Logo

- Question : le logotype utilise-t-il la police IBM Plex Sans en SVG ?
- Choix : `public/brand/logo.svg` reference la police par son nom avec repli Arial. Le monogramme et les icones sont dessines en formes geometriques, sans dependance a une police.
- Raison : le SVG utilise comme image ne peut pas charger les polices de la page. A remplacer par une version en contours quand le logo sera valide par l'equipe.

## 2026-11-12 : Outils de build frontend

- Question : versions retenues.
- Choix : Vite 8, TypeScript 6, ESLint 10, Vitest 5 (dernieres versions stables au moment du demarrage). React reste en 18 comme demande. L'alias `@` passe par `resolve.tsconfigPaths`.

## A verifier plus tard

- Phase 3 : disponibilite des modeles Groq par defaut (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `whisper-large-v3`) dans la documentation Groq.