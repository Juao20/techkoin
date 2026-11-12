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

## 2026-11-12 : Choix de la phase 1

- Photos HEIC : refusées avec un message clair. Les accepter demande `pillow-heif` ; à valider. Le navigateur réduit déjà les photos en JPEG avant l'envoi quand il sait les décoder.
- Contact : l'affichage du numéro et le lien WhatsApp exigent une connexion (section 8.4) ; chaque clic est enregistré côté serveur, le front ne double pas l'événement.
- `has_imei` est exposé publiquement (booléen) ; l'IMEI lui-même ne sort jamais.
- Une annonce de démonstration n'est pas créée par l'API : `seed_demo` écrit en base, mais respecte les mêmes règles de publication (test automatisé).

## 2026-11-13 : Choix de la phase 2

- Estimation : un appareil neuf n'est jamais estimé au-dessus de son prix neuf indicatif (le coefficient 1,30 du neuf scellé s'applique aux comparables, pas au repli indicatif).
- Estimation indicative : pas de badge de prix (section 7.2) et pas de règle « prix trop bas » dans le moteur de risque.
- Score d'usage : une donnée manquante vaut 5/10 (neutre), jamais 0. Les formules sont documentées en tête de `pricing/usage.py`.
- Filtre `usage` : un appareil est retenu s'il a un score de 7 ou plus pour cet usage, comme l'usage « conseillé ».
- IMEI : un smartphone exige 15 chiffres avec clé de Luhn ; tablettes et ordinateurs acceptent aussi un numéro de série au format de la marque (motif générique si la marque est inconnue). Une empreinte SHA-256 (`imei_hash`) permet de détecter les doublons et les appareils volés sans lire l'IMEI chiffré.
- Appareil déclaré volé et confirmé : la publication n'est pas refusée avec un message qui l'indiquerait au vendeur ; l'annonce passe en `pending_review` prioritaire et n'est jamais visible.
- Moteur de risque : un modèle hors catalogue envoie toujours l'annonce en relecture (section 6), même si son score est inférieur à 40.
- Signalements : trois acheteurs différents remettent une annonce en ligne dans la file de modération (seuil non fixé par la spécification, `REPORTS_FOR_REVIEW`).
- Déclaration d'appareil volé : ouverte sans compte (page publique), limitée en fréquence ; seule une confirmation par un modérateur bloque des annonces.
- Modération : par le Django admin (section 11), file « file de modération » triée par score de risque, avec approbation, refus et demande de modifications. Chaque décision est conservée (`ModerationDecision`).
- Documents d'identité et de boutique : stockés dans `PRIVATE_MEDIA_ROOT`, jamais servis par `/media`, lus par un modérateur via une route protégée, supprimés 90 jours après la décision (`purge_verification_documents`, à planifier chaque jour).

## A verifier plus tard

- Phase 3 : disponibilite des modeles Groq par defaut (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `whisper-large-v3`) dans la documentation Groq.