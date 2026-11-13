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

## 2026-11-13 : Choix de la phase 3

- Modèles Groq : les modèles par défaut de la spécification (llama-3.3-70b-versatile, llama-3.1-8b-instant) figurent sur la page de dépréciation de Groq avec un arrêt au 16/08/2026. Les défauts passent à openai/gpt-oss-120b (smart) et openai/gpt-oss-20b (fast), les remplaçants recommandés ; ils restent modifiables par variables d'environnement. Non testé avec une vraie clé : le mode JSON de ces modèles est à confirmer, et toute réponse invalide retombe sur le repli.
- Appel à Groq par httpx (API compatible OpenAI) plutôt que par le SDK groq, pour ne pas ajouter de dépendance (règle 0.7).
- Comparaison : délai de 2,5 s pour le modèle (AI_COMPARE_TIMEOUT_SECONDS), au-delà le verdict déterministe s'affiche. C'est ce qui tient la promesse « moins de 3 s hors cache ».
- Assistant : seules les questions précédentes de l'acheteur sont renvoyées au modèle (5 au plus), jamais les réponses reçues du navigateur ; le prénom et le nom du vendeur sont retirés des textes libres.
- Réponses du modèle vérifiées avant affichage : un chiffre absent des données fournies, un gagnant hors comparaison ou une promesse non vérifiable font utiliser le repli.
- Rédaction assistée : le texte de repli reprend les informations saisies ; il peut compter moins de 80 mots si peu de champs sont remplis.
- Dictée : sans clé Groq (donc sans transcription), le bouton n'est pas affiché. L'audio est lu en mémoire et n'est jamais enregistré ; Django peut toutefois le placer dans un fichier temporaire au-delà de 2,5 Mo (limite fixée à 3 Mo).
- Non faits : la requête « compare X et Y » saisie dans la recherche, et l'usage « Pro » (200 requêtes par jour) qui relève de la phase 5.

## 2026-11-13 : Choix de la phase 4

- Un paiement refusé ou non validé dans les 30 minutes annule la commande (comme dans la machine à états de la spécification) ; l'acheteur crée une nouvelle commande. Une commande « créée » non payée est annulée au bout de 30 minutes. Seules les commandes payées ou en cours de paiement bloquent l'annonce.
- Un litige peut être ouvert dès que le paiement est en séquestre, pas seulement après la remise : sans cela un vendeur qui ne se présente jamais bloquerait l'argent de l'acheteur.
- Un paiement qui réussit alors que l'annonce a été vendue entre-temps est remboursé aussitôt.
- Le versement et le remboursement du simulateur réussissent toujours. Si le versement échoue chez le fournisseur, la commande reste en litige à traiter par un modérateur.
- Champ `accepts_secure_payment` ajouté aux annonces (vrai par défaut, case à cocher à l'étape Prix) : il alimente le filtre `secure_payment` de la section 6.
- **FedaPay, non testé avec de vraies clés :** l'intégration suit la documentation publique (création de transaction, jeton de paiement, signature HMAC-SHA256 de `t.corps` dans `X-FEDAPAY-SIGNATURE`, versements par `/payouts`). Les noms de champs, les modes d'opérateur des versements (`mtn_open`, `moov`, `celtiis_bj`) et le remboursement par versement sont à confirmer dans le bac à sable. Les tests utilisent un faux serveur.
- Les webhooks sont rendus idempotents par un enregistrement `webhook:<fournisseur>:<id d'événement>` ; un horodatage de plus de 5 minutes est refusé.
- Données de démonstration : 10 commandes sandbox (libérées, en séquestre, remises, en litige, remboursée, annulée, en attente).

## 2026-11-13 : Choix de la phase 5

- Les analyses sont calculées à la demande depuis les événements bruts (index `type, created_at` et `shop, type, created_at`). Les agrégats quotidiens `DailyShopStats` et `DailyDemandStats` de la section 12 ne sont pas créés : ils n'apportent rien à ce volume et dupliqueraient les chiffres du rapport. À ajouter si les requêtes ralentissent.
- Radar (P1) : le texte tapé est rattaché à une catégorie par le catalogue ; la ville vient de l'événement. Une ville trop mince reste comptée dans la ligne « toutes villes » de la même famille ; la ligne « toutes villes » est omise quand elle répète à l'identique la seule ville. L'offre est comptée avec la même recherche texte que le site.
- Prix conseillé (P2) : 105 % de l'estimation si le prix la dépasse de plus de 10 %, 97 % s'il est sous elle de plus de 10 % (marge portée à 25 % quand l'estimation repose sur moins de 5 comparables). Le modèle n'écrit que l'explication.
- Stock dormant (P3) : « médiane » = médiane du taux de contact des annonces actives de la même catégorie. Les corrections de titre et de description sont le texte F2 (déjà contrôlé contre les faits de l'annonce) et le prix de P2 ; le modèle explique, il ne propose pas de chiffre. Cinq corrections au plus par requête.
- Rapport (P4) : sur les 7 derniers jours, e-mail par un `Notifier` (WhatsApp plus tard = une classe). Sans clé Groq, texte généré par gabarit.
- Chat (P5) : appel d'outils Groq sur cinq fonctions fermées ; sans clé, ou si le modèle cite un chiffre que les fonctions n'ont pas renvoyé, une lecture par mots-clés choisit la fonction. Les coordonnées tapées dans la question sont retirées avant envoi.
- Aperçu gratuit : P1 à P3 répondent aux boutiques gratuites avec le premier élément ; P4 à P7 répondent `403`. Le plan en vigueur est `plan = pro` et `plan_expires_at` non échu (sans date : accordé à la main, cas de la démo).
- Les erreurs DRF (`detail`) sont converties en `{code, message}` pour toute l'API.
- Données de démonstration : la boutique Pro a 16 annonces en ligne et une demande « macbook m1 » à moins de 400 000 FCFA à Cotonou, plantée sur la dernière semaine. Les écrans datent de `seed_demo` : relancer `seed_demo --reset` si les données ont plus de quelques jours.
## 2026-11-13 : Choix de la phase 6

- Alerte : le curseur de départ est la date de création, donc seules les annonces publiées ensuite déclenchent un message. La notification interne est toujours créée ; l'e-mail s'y ajoute pour le canal `email`. Le canal `whatsapp` est accepté et garde la notification interne : l'interface `Sender` est prête, l'envoi viendra avec l'intégration.
- Facettes : un groupe ignore son propre filtre (comportement usuel des marketplaces). Les compteurs réutilisent `search.apply_filters`, aucun filtre n'est réimplémenté. Une dizaine de requêtes par appel : acceptable à ce volume, à mettre en cache si besoin.
- Le filtre de garantie du panneau envoie un nombre de mois alors que l'API ne connaissait que « 1 » : corrigé côté API, avec test.
- Open Graph : une route attrape-tout de Django sert l'`index.html` construit ; en développement Vite sert les pages et il n'y a pas d'aperçu. Le texte d'une boutique ou d'une annonce est échappé avant d'entrer dans le HTML.
- Erreurs d'API : le `403` d'une fonction Pro et les autres erreurs DRF suivent le format `{code, message}` (phase 5).
- PostgreSQL : le script `scripts/test_postgres.py` démarre un serveur jetable (paquet `pgserver`) ; sous Windows ce paquet est livré sans les fichiers de fuseaux horaires de PostgreSQL, le script emprunte ceux de `tzdata`. Dépendances ajoutées hors liste (règle 0.7) : `psycopg[binary]` (pilote de production), `pgserver` et `tzdata` (tests locaux seulement).
- Lighthouse : pas installé sur la machine, lancé par `npx` ; Chrome ne démarrait pas depuis Lighthouse sous Windows, on lui fournit le Chromium de Playwright par le port de débogage. Résultats et méthode dans `docs/PERFORMANCE.md`.
- Pages légales : textes en langage simple qui décrivent ce que fait l'application. Ils n'ont pas été relus par un juriste et ne donnent pas d'adresse de contact : à compléter avant le lancement.
- Rappel de la checklist 15.12, repassée par recherche dans tout le code du front : aucun dégradé, flou, halo, police étrangère, bordure `rgba`, animation au défilement ni emoji ; seules les ombres des éléments flottants (`--shadow-float`) subsistent.
## A verifier plus tard

- Phase 4 : creer un compte FedaPay sandbox et verifier le parcours complet (paiement, webhook, versement) avec de vraies cles.
- Phase 3 : tester avec une vraie cle Groq (mode JSON des modeles `openai/gpt-oss-*`, transcription `whisper-large-v3`).
- Phase 5 : tester P1 à P7 avec une vraie cle Groq (appel d'outils de openai/gpt-oss-120b, JSON des textes) et verifier le paiement d'abonnement FedaPay.
