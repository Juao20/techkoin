# TechKoin — Cahier des charges du MVP

> Document de référence destiné à Claude Code. À placer à la racine du dépôt sous le nom `TECHKOIN_SPEC.md`.
> Version 1.0 — 12 novembre 2026 — Auteur : Amour Ornel GUIDI

---

## 0. Mode d'emploi pour Claude Code

1. Lis l'intégralité de ce document avant d'écrire la moindre ligne de code.
2. Construis **phase par phase** (section 19), dans l'ordre. À l'intérieur d'une phase, avance **fonctionnalité par fonctionnalité**, avec un commit et un push pour chacune (section 0.1). À la fin de chaque phase : migrations propres, tests verts, résumé de ce qui a été fait (avec la liste des commits poussés), puis **attends ma validation** avant de passer à la suivante.
3. La section 15 (design) est **contraignante**. Chaque règle marquée « Interdit » est bloquante : une PR qui en enfreint une n'est pas terminée.
4. En cas d'ambiguïté, choisis l'option la plus simple compatible avec ce document et consigne-la dans `docs/DECISIONS.md` (date, question, choix, raison).
5. Aucune clé ni secret dans le code : tout passe par `.env` (voir section 21). Fournis un `.env.example`.
6. Toute l'interface est en **français**. Le code, les noms de variables et les commits sont en anglais.
7. N'ajoute pas de dépendance non listée ici sans la justifier dans `docs/DECISIONS.md`.
8. Pas d'emoji, nulle part : ni dans l'interface, ni dans les messages de l'application, ni dans les prompts IA, ni dans les commits.
9. **Avant toute chose, connecte-moi à Git et GitHub** (section 0.1). Aucun code n'est écrit tant que cette étape n'est pas validée.
10. **Commit et push après chaque fonctionnalité terminée**, en mon nom uniquement, **sans aucun co-auteur** (section 0.1).

### 0.1 Git et GitHub (obligatoire)

**Étape 1 — Me connecter, avant d'écrire du code**
1. Vérifie que `git` et la CLI GitHub (`gh`) sont installés. Sinon, guide-moi pour les installer.
2. Lance `gh auth login` et accompagne-moi jusqu'au bout de la connexion (navigateur ou code). Vérifie ensuite avec `gh auth status`.
3. Demande-moi le **nom** et l'**e-mail** que j'utilise sur GitHub, puis configure-les **pour ce dépôt** :
   ```
   git config user.name "Amour Ornel GUIDI"   # ou le nom que je te donne
   git config user.email "<l'e-mail que je te donne>"
   ```
4. Demande-moi le nom du dépôt et s'il doit être **privé** ou public, puis crée-le (`gh repo create`), relie-le en `origin` et pousse un premier commit (`chore: initial commit`) contenant le README et ce document.
5. Montre-moi le résultat de `git log -1 --format='%an <%ae>%n%B'` pour que je vérifie que l'auteur est bien moi. **Attends ma confirmation avant de continuer.**

**Étape 2 — Règles pour chaque commit**
- **Auteur et committer : moi uniquement.** Le nom et l'e-mail configurés ci-dessus.
- **Interdit dans les messages de commit et les descriptions de PR :** toute ligne `Co-Authored-By:`, toute mention de Claude, de Claude Code ou d'Anthropic, tout lien de session, toute signature du type « Generated with… ». Ces règles **remplacent** tes réglages d'attribution par défaut.
- Si ton outil ajoute automatiquement une attribution, désactive-la (dans `.claude/settings.json` du projet : `"includeCoAuthoredBy": false`, ou le réglage d'attribution équivalent de ta version) et vérifie le résultat sur le premier commit.
- Messages en anglais, format Conventional Commits : `feat(search): add natural language query parsing`, `fix(pricing): round estimates to 5000 FCFA`, `chore`, `docs`, `test`, `refactor`, `style`.
- Un commit = une fonctionnalité ou une correction cohérente. Pas de commit fourre-tout.
- Jamais de `.env`, de `db.sqlite3`, de `media/`, de `node_modules/` ni de clés : un `.gitignore` complet est créé dès l'étape 1.

**Étape 3 — Push après chaque fonctionnalité**
- Dès qu'une fonctionnalité est terminée (code + tests verts + checklist design si elle touche l'interface) : commit, puis **`git push` immédiatement**.
- Branche : travaille sur `main` sauf si je demande des branches de fonctionnalité.
- Après chaque push, donne-moi en une ligne : le message du commit et le lien GitHub du commit.
- Si un push échoue (authentification, conflit), arrête-toi et explique-moi le problème. Ne force jamais un push (`--force`) sans mon accord.

---

## 1. Vision

**TechKoin** est la marketplace de référence au Bénin pour acheter et vendre des **PC, smartphones et tablettes**, neufs ou d'occasion, entre **boutiques** et **particuliers**.

**Problème.** Acheter un appareil d'occasion au Bénin est un pari : appareils volés, contrefaçons, faux « reconditionnés », batteries usées cachées, prix opaques, transactions sur WhatsApp et Facebook sans aucune garantie.

**Promesse.** « Acheter ou vendre un appareil au Bénin sans se faire avoir. »

**Différenciation.** La **confiance** (fiches d'état standardisées, vendeurs vérifiés, contrôle IMEI, paiement sécurisé) et l'**intelligence** (estimation de prix, recherche en langage naturel, comparaison IA, analyses pour les boutiques). Le volume d'annonces vient après.

**Décisions déjà prises :**

| Sujet | Décision |
|---|---|
| Modèle | Marketplace ouverte : les vendeurs publient et gèrent leurs annonces |
| Cibles au lancement | Boutiques **et** particuliers |
| Paiement | Paiement sécurisé (séquestre Mobile Money) en **mode sandbox** pour le MVP |
| Style | Direction A : « tech premium », clair, sobre, avec des touches locales |
| Nom | TechKoin |
| Monétisation | Abonnement boutique « Analyse IA » (payant), commission sur paiement sécurisé, annonces boostées (plus tard) |

---

## 2. Utilisateurs et rôles

| Rôle | Description | Peut |
|---|---|---|
| Visiteur | Non connecté | Rechercher, filtrer, consulter, comparer, utiliser la recherche IA (limitée) |
| Particulier | Compte individuel | Tout ce que fait le visiteur + favoris, alertes, contacter, acheter, publier des annonces (limite : 5 actives) |
| Boutique (Gratuit) | Compte rattaché à une `Shop` | Vitrine publique, annonces illimitées, tableau de bord de base |
| Boutique (Pro) | Abonnement « Analyse IA » | Tout le plan Gratuit + toutes les fonctionnalités IA payantes (section 10.3) |
| Modérateur | Équipe TechKoin | File de modération, vérifications d'identité et de boutique, signalements, litiges |
| Admin | Équipe TechKoin | Django admin complet, catalogue, paramètres |

Un utilisateur a un seul type de compte (`particulier` ou `boutique`). Un compte boutique possède exactement une `Shop`.

---

## 3. Stack technique

### 3.1 Backend
- Python 3.12+, **Django 5.2 LTS**, **Django REST Framework**
- `django-filter` (filtres), `Pillow` + `imagehash` (images), `httpx` (appels Groq et paiement), `pydantic` v2 (validation des sorties IA)
- `django-cors-headers` en développement uniquement
- Auth : **sessions Django + CSRF** (le front et l'API sont servis sur le même domaine ; proxy Vite en dev). Pas de JWT.
- Tâches périodiques : **management commands** lancées par cron (alertes, rapport hebdomadaire, libération automatique des paiements). Pas de Celery dans le MVP.
- Base de données : **SQLite** en développement. Passage à **PostgreSQL** prévu avant le lancement public. Règles de compatibilité :
  - jamais de SQL brut ni de fonction propre à SQLite ;
  - `JSONField` autorisé (compatible avec les deux) ;
  - les transitions de commande se font dans `transaction.atomic()` ;
  - toute recherche texte passe par une seule fonction (`marketplace/search.py`), pour basculer plus tard vers la recherche plein texte de Postgres sans toucher au reste.
- Médias : stockage local (`MEDIA_ROOT`) en dev, derrière l'API `storages` de Django pour passer à un stockage S3-compatible plus tard.

### 3.2 Frontend
- **Vite + React 18 + TypeScript** (strict)
- React Router, **TanStack Query** (données serveur), React Hook Form + Zod (formulaires)
- Styles : **CSS Modules + design tokens en variables CSS** (section 15).
- **Interdit :** Tailwind, shadcn/ui, MUI, Chakra, Mantine ou toute autre bibliothèque de composants préstylés.
- **Autorisé :** primitives headless **Radix UI** (Dialog, Popover, Select, Tabs, Tooltip) uniquement pour l'accessibilité, **entièrement restylées** avec nos tokens.
- Icônes : **Phosphor Icons** (`@phosphor-icons/react`), graisse `regular` ou `bold`. Règles d'usage en section 15.6.
- Polices auto-hébergées via `@fontsource` (pas d'appel à Google Fonts au runtime).

### 3.3 IA
- **Groq API** (compatible OpenAI) via `httpx`. Modèles configurables par variables d'environnement :
  - `GROQ_MODEL_SMART` (raisonnement, rédaction, comparaison) — défaut proposé : `llama-3.3-70b-versatile`
  - `GROQ_MODEL_FAST` (analyse de requête, classification) — défaut proposé : `llama-3.1-8b-instant`
  - `GROQ_MODEL_STT` (voix vers texte) — défaut proposé : `whisper-large-v3`
- **Vérifie dans la documentation Groq que ces modèles sont toujours disponibles** et ajuste les valeurs par défaut si besoin (à noter dans `DECISIONS.md`).
- Estimation de prix et scores : **calculés en Python**, jamais par le LLM (section 7).

### 3.4 Paiement
- Interface `PaymentProvider` avec deux implémentations :
  - `SimulatorProvider` (par défaut en dev) : simule localement les paiements Mobile Money (succès, échec, délai) ;
  - `FedaPayProvider` : intégration de l'API FedaPay en **mode sandbox** (clés de test).
- Opérateurs proposés : MTN MoMo, Moov Money, Celtiis Cash.

### 3.5 Structure du dépôt

```
techkoin/
├── TECHKOIN_SPEC.md
├── README.md
├── .env.example
├── docs/
│   ├── DECISIONS.md
│   └── API.md
├── backend/
│   ├── manage.py
│   ├── config/            # settings (base, dev, prod), urls, wsgi
│   ├── accounts/          # User, Shop, vérifications, abonnements
│   ├── catalog/           # Brand, Processor, GraphicsCard, DeviceModel
│   ├── marketplace/       # Listing, photos, favoris, alertes, signalements, recherche
│   ├── trust/             # IMEI, modération, appareils déclarés volés
│   ├── payments/          # Order, Transaction, providers, machine à états
│   ├── analytics/         # Event, agrégations
│   ├── ai/                # client Groq, prompts/, services, cache, logs
│   │   └── prompts/       # un fichier .md par prompt, versionné
│   ├── pricing/           # estimation de prix, scores d'usage
│   └── seed/              # commande seed_demo + données
└── frontend/
    ├── index.html
    ├── public/            # favicon, manifest, images propres à TechKoin
    └── src/
        ├── app/           # routes, providers, layout
        ├── styles/        # tokens.css, reset.css, typography.css
        ├── components/    # composants maison (Button, Input, ListingCard…)
        ├── features/      # search, listing, compare, publish, checkout, account, shop, insights
        ├── lib/           # api client, formatage FCFA, utils
        └── icons/         # éventuelles icônes maison
```

---

## 4. Modèle de données

Toutes les tables ont `created_at` et `updated_at`. Les énumérations sont des `TextChoices` Django.

### 4.1 `accounts`

**User** (hérite de `AbstractUser`, connexion par e-mail ou téléphone)
- `email` (unique), `phone` (unique, format béninois `+229 01 XX XX XX XX`, stocké en E.164), `whatsapp_number` (optionnel, par défaut = `phone`)
- `account_type` : `particulier` | `boutique`
- `city`, `quartier`
- `phone_verified` (bool ; vérification OTP prévue plus tard, champ présent dès maintenant)
- `identity_status` : `none` | `pending` | `verified` | `rejected`
- `identity_document` (fichier **privé**, jamais exposé par l'API publique)
- `is_moderator` (bool)

**Shop**
- `owner` (OneToOne User), `name`, `slug` (unique), `logo`, `description`
- `address`, `city`, `quartier`, `opening_hours` (JSON), `whatsapp_number`
- `ifu`, `rccm`, `documents` (fichiers privés)
- `verification_status` : `none` | `pending` | `verified` | `rejected`
- `plan` : `free` | `pro`, `plan_expires_at`

**Subscription**
- `shop`, `plan` (`pro`), `amount_fcfa`, `period_start`, `period_end`, `status` (`pending` | `active` | `expired` | `cancelled`), `transaction` (FK Transaction)

### 4.2 `catalog`

**Brand** : `name`, `slug`, `categories` (JSON : liste parmi `laptop`, `desktop`, `smartphone`, `tablet`)

**Processor**
- `name` (ex. « Intel Core i5-1135G7 », « Apple M2 », « Snapdragon 8 Gen 2 »), `vendor` (Intel, AMD, Apple, Qualcomm, MediaTek, Samsung, Unisoc), `family` (i5, Ryzen 5, M2…), `generation` (entier ou texte), `cores`, `segment` (`laptop` | `desktop` | `mobile`), `release_year`
- `perf_score` (0–100, normalisé à partir de benchmarks publics, saisi une fois). Utilisé pour les scores d'usage et la comparaison.

**GraphicsCard** : `name`, `vendor`, `vram_gb`, `dedicated` (bool), `perf_score` (0–100)

**DeviceModel** (le catalogue)
- `category` : `laptop` | `desktop` | `smartphone` | `tablet`
- `brand`, `name`, `slug`, `release_year`, `aliases` (JSON : variantes d'écriture pour la recherche, ex. `["ip13", "iphone13"]`)
- `reference_price_new_fcfa` (prix neuf indicatif au Bénin, utilisé quand il y a peu de données)
- Specs par défaut (toutes optionnelles) : `default_processor`, `default_gpu`, `ram_options_gb` (JSON), `storage_options_gb` (JSON), `screen_size_in`, `screen_resolution`, `refresh_rate_hz`, `os`, `has_5g`, `dual_sim`, `esim`, `stylus_support`, `cellular_option` (tablettes)
- `is_active`

### 4.3 `marketplace`

**Listing**
- Relations : `seller` (User), `shop` (nullable), `device_model` (nullable), `custom_model_name` (si modèle hors catalogue)
- Identité : `category`, `brand`, `title` (généré, modifiable), `slug`, `description`
- Commercial :
  - `condition_type` : `new_sealed` (Neuf scellé) | `new_open` (Neuf ouvert) | `refurbished` (Reconditionné) | `used` (Occasion)
  - `grade` : `A` | `B` | `C` | null (obligatoire si ce n'est pas du neuf)
  - `price_fcfa` (entier), `negotiable` (bool)
  - `city`, `quartier`
  - `accessories` (JSON parmi `charger`, `box`, `cable`, `case`, `earphones`, `invoice`)
  - `has_invoice` (bool, dénormalisé pour le filtre), `warranty_months` (0, 1, 3, 6, 12)
  - `provenance` : `local` | `europe` | `usa` | `dubai` | `china` | `other`
- Identification : `imei_or_serial` (**chiffré au repos, jamais exposé publiquement**), `imei_status` : `unchecked` | `ok` | `duplicate` | `reported_stolen` | `invalid`
- Specs communes : `ram_gb`, `storage_gb`, `storage_type` (`ssd` | `hdd` | `hybrid` | `emmc` | `ufs`), `color`, `screen_size_in`, `screen_resolution`, `refresh_rate_hz`
- Specs PC : `processor` (FK), `gpu` (FK, nullable), `gpu_dedicated`, `vram_gb`, `touchscreen`, `os`, `keyboard_layout` (`azerty` | `qwerty` | `qwertz` | `other`), `keyboard_backlit`, `battery_cycles`, `battery_autonomy_h`, `ports` (JSON parmi `usb_c`, `hdmi`, `thunderbolt`, `sd`, `ethernet`, `usb_a`), `ram_upgradable`
- Specs mobile / tablette : `processor` (FK chipset), `battery_health_pct`, `network_5g`, `dual_sim`, `esim`, `carrier_unlocked`, `account_removed` (iCloud/Google retiré), `biometrics_ok`, `screen_original`, `replaced_parts` (JSON parmi `battery`, `screen`, `camera`, `back`, `none`), `cellular` (tablette : Wi-Fi seul ou Wi-Fi + SIM), `stylus_included`, `keyboard_included`
- Prix et IA (calculés, en lecture seule) : `estimate_low`, `estimate_mid`, `estimate_high`, `estimate_sample_size`, `price_badge` (`good_deal` | `fair` | `above_market` | `unknown`), `usage_scores` (JSON)
- Modération : `status` : `draft` | `pending_review` | `active` | `reserved` | `sold` | `rejected` | `archived`, `risk_score` (0–100), `moderation_flags` (JSON), `rejection_reason`
- Compteurs (dénormalisés) : `views_count`, `contacts_count`, `favorites_count`
- Dates : `published_at`, `sold_at`, `last_price_change_at`
- `is_boosted` (prévu, non utilisé dans le MVP)

**ListingPhoto** : `listing`, `image` (WebP, côté max 1600 px), `thumb` (WebP, 480 px), `kind` (`front` | `back` | `screen_on` | `defect` | `other`), `position`, `phash` (pour détecter les doublons)

**Favorite** : `user`, `listing` (unique ensemble)

**SavedSearch** (alertes) : `user`, `name`, `filters` (JSON, même format que les query params), `channel` (`whatsapp` | `email` | `in_app`), `last_notified_at`, `is_active`

**ListingReport** (signalement) : `listing`, `reporter`, `reason` (`scam` | `stolen` | `wrong_info` | `duplicate` | `other`), `details`, `status`

### 4.4 `trust`

**StolenDeviceReport** : `imei_or_serial_hash`, `reporter`, `description`, `police_reference` (optionnel), `status` (`pending` | `confirmed` | `dismissed`)

**ModerationDecision** : `listing`, `moderator`, `action` (`approve` | `reject` | `request_changes`), `reason`

### 4.5 `payments`

**Order**
- `buyer`, `listing`, `seller`, `amount_fcfa`, `commission_fcfa`, `seller_payout_fcfa`
- `status` : voir la machine à états (section 9)
- `delivery_mode` : `meetup` | `delivery`, `meetup_note`
- `buyer_confirmed_at`, `auto_release_at`, `dispute_reason`
- `is_sandbox` (toujours `true` dans le MVP)

**Transaction** : `order` (nullable), `subscription` (nullable), `provider` (`simulator` | `fedapay`), `operator` (`mtn` | `moov` | `celtiis`), `payer_phone`, `amount_fcfa`, `direction` (`in` | `out` | `refund`), `provider_reference`, `status` (`pending` | `succeeded` | `failed`), `raw_payload` (JSON), `idempotency_key` (unique)

### 4.6 `analytics`

**Event**
- `type` : `search` | `search_no_result` | `listing_view` | `contact_click` | `whatsapp_click` | `phone_reveal` | `favorite_add` | `compare` | `checkout_start` | `order_paid` | `ai_search` | `ai_assistant_question` | `alert_created`
- `user` (nullable), `session_id` (cookie anonyme), `listing` (nullable), `shop` (nullable)
- `query_text`, `filters` (JSON), `results_count`, `city` (déduite des filtres ou du profil)
- `metadata` (JSON)
- Index sur `(type, created_at)`, `(listing, type)`, `(shop, type, created_at)`

### 4.7 `ai`

**AICache** : `key` (sha256 de la fonctionnalité + entrées normalisées), `feature`, `payload` (JSON), `expires_at`

**AIRequestLog** : `feature`, `user` (nullable), `shop` (nullable), `model`, `prompt_version`, `input_tokens`, `output_tokens`, `latency_ms`, `success`, `fallback_used`, `error`

---

## 5. Fiches techniques par catégorie

**Principe clé.** Le vendeur choisit un **modèle du catalogue** (autocomplétion). Les specs connues sont **pré-remplies** depuis `DeviceModel`. Il ne complète que l'état et ce qui est propre à son appareil (RAM réelle, stockage réel, santé de la batterie…). Un champ « Mon modèle n'est pas dans la liste » permet une saisie libre ; l'annonce passe alors en `pending_review`.

### 5.1 Champs communs (toutes catégories)

| Champ | Obligatoire | Filtrable | Source |
|---|---|---|---|
| Catégorie | oui | oui | vendeur |
| Marque / modèle | oui | oui | catalogue |
| Type (neuf scellé, neuf ouvert, reconditionné, occasion) | oui | oui | vendeur |
| Note d'état A/B/C | oui si pas neuf | oui | vendeur, via la checklist |
| Prix FCFA + négociable | oui | oui | vendeur |
| Ville / quartier | oui | oui (ville) | profil, modifiable |
| Accessoires inclus | non | oui (facture) | vendeur |
| Garantie | non | oui (« avec garantie ») | vendeur |
| Provenance | non | non | vendeur |
| Photos (min. 4) | oui | non | vendeur |
| IMEI / n° de série | oui | non (privé) | vendeur |

**Définition de la note d'état** (affichée dans l'interface, en texte clair) :
- **A — Comme neuf** : aucune trace visible à 20 cm, tout fonctionne, batterie ≥ 85 % (mobile).
- **B — Bon état** : micro-rayures légères, tout fonctionne, batterie ≥ 75 % (mobile).
- **C — Traces visibles** : rayures ou chocs visibles, tout fonctionne. Les défauts doivent être photographiés.
- Un appareil avec une fonction en panne n'est pas A/B/C : la mention « Défaut déclaré » est obligatoire et décrite (champ `moderation_flags.declared_defect`).

La note est **proposée automatiquement** à partir d'une checklist (rayures écran, rayures coque, chocs, santé batterie, fonctions OK). Le vendeur peut la dégrader, pas l'améliorer.

### 5.2 PC (portable et fixe)

| Champ | Obligatoire | Filtrable |
|---|---|---|
| Processeur (famille + génération) | oui | oui |
| RAM (Go) + extensible | oui | oui |
| Stockage : type + capacité | oui | oui |
| Carte graphique : intégrée / dédiée (modèle + VRAM) | oui | oui (dédiée) |
| Écran : taille, résolution, tactile, fréquence | taille oui | taille |
| Système d'exploitation | oui | oui |
| Clavier AZERTY / QWERTY + rétroéclairé | oui (portable) | oui |
| Batterie : autonomie estimée, cycles (Mac) | non | non |
| Connectique | non | non |
| Usage conseillé | calculé | oui |

Le type de clavier doit être visible sur la carte d'annonce, parce que beaucoup de PC importés sont en QWERTY.

### 5.3 Smartphone

| Champ | Obligatoire | Filtrable |
|---|---|---|
| Stockage / RAM | oui / non | oui / oui |
| Santé batterie (%) | oui si occasion et iPhone ; sinon « estimation » | oui (≥ X %) |
| 5G, double SIM, eSIM | pré-rempli | oui |
| Débloqué opérateur | oui | oui |
| Compte iCloud / Google retiré | **oui, et doit être « oui »** | — |
| Biométrie fonctionnelle | oui | non |
| Écran d'origine | oui | non |
| Pièces changées | oui | oui (« aucune pièce changée ») |
| Couleur | non | non |

**Règle bloquante :** si `account_removed = false`, la publication est refusée avec un message explicatif (« Un appareil encore lié à un compte iCloud ou Google ne peut pas être vendu sur TechKoin »).

### 5.4 Tablette

Mêmes champs que le smartphone, plus : `cellular` (Wi-Fi seul / Wi-Fi + SIM), `stylus_support` / `stylus_included`, `keyboard_included`, `screen_size_in`.

### 5.5 Photos

- Minimum 4, maximum 10. Les types `front`, `back` et `screen_on` sont obligatoires ; `defect` est obligatoire si la note est C ou si un défaut est déclaré.
- Écran de publication guidé : une case par type de photo, avec un exemple de cadrage dessiné (pictogramme simple, pas d'illustration IA).
- Traitement serveur : conversion WebP, suppression des métadonnées EXIF (localisation), redimensionnement, `phash`.

### 5.6 Catalogue de départ

150 à 200 modèles parmi les plus vendus au Bénin : iPhone 8 à 16 (et variantes Pro/Max), Samsung Galaxy A, S et Note, Tecno (Spark, Camon, Pova), Infinix (Hot, Note, Zero), Itel, Xiaomi Redmi et Poco, Oppo, Huawei, Google Pixel ; iPad, Galaxy Tab ; HP (ProBook, EliteBook, Pavilion, Victus), Dell (Latitude, Inspiron, XPS, Vostro), Lenovo (ThinkPad, IdeaPad, Legion), Asus (VivoBook, ROG, TUF), Acer (Aspire, Nitro), MacBook Air et Pro (Intel et M1–M4) ; quelques PC fixes et mini-PC de marque. Plus les processeurs et GPU correspondants avec leur `perf_score`.

---

## 6. Recherche, filtres et tri

### 6.1 Paramètres d'URL (format unique)

Les filtres vivent dans l'URL (partage possible sur WhatsApp) et utilisent le même format que `SavedSearch.filters`.

```
/recherche?category=laptop&brand=hp,dell&price_min=150000&price_max=300000
  &condition=used,refurbished&grade=A,B&city=abomey-calavi
  &ram_min=16&storage_min=256&storage_type=ssd&gpu_dedicated=1
  &keyboard=azerty&usage=dev&verified=1&seller_type=shop&warranty=1
  &invoice=1&secure_payment=1&sort=best_deal&page=2
```

### 6.2 Filtres

**Barre principale (toujours visibles) :** catégorie · prix (curseur min/max + champs numériques) · marque · type · ville · note d'état

**Avancés, selon la catégorie :**
- **PC** : famille de processeur + génération minimale · RAM min · type et capacité min de stockage · GPU dédié · taille d'écran · système · clavier · usage
- **Smartphone** : stockage min · RAM min · 5G · double SIM · santé batterie min · débloqué · aucune pièce changée
- **Tablette** : stockage min · Wi-Fi / SIM · stylet · taille d'écran

**Confiance :** vendeur vérifié · boutique / particulier · avec garantie · avec facture · paiement sécurisé disponible

### 6.3 Tri
`relevance` (défaut) · `price_asc` · `price_desc` · `recent` · `best_deal` (ratio `price / estimate_mid` croissant, uniquement pour les annonces avec une estimation fiable)

**Pertinence MVP :** correspondance texte (titre, marque, modèle, alias) puis bonus vendeur vérifié, bonus photos complètes, fraîcheur.

### 6.4 Comportements
- Pagination : 24 annonces par page.
- Ville : les villes proches remontent après la ville choisie (table statique de proximité : Cotonou ↔ Abomey-Calavi ↔ Sèmè-Podji ↔ Porto-Novo ; Bohicon ↔ Abomey ; etc.).
- Chaque recherche enregistre un `Event` (`search`, ou `search_no_result` si 0 résultat). **Ces données alimentent le radar de la demande (10.3, P1) : ne pas les oublier.**
- Les compteurs par filtre (facettes) sont prévus en phase 6.
- Villes initiales : Cotonou, Abomey-Calavi, Porto-Novo, Parakou, Bohicon, Abomey, Ouidah, Sèmè-Podji, Lokossa, Natitingou, Djougou, Kandi (table administrable).

---

## 7. Estimation de prix et scores d'usage

**Le LLM ne calcule jamais un prix.** Tout se fait dans `pricing/`. Le LLM peut seulement expliquer un résultat déjà calculé.

### 7.1 Estimation (`pricing/estimate.py`)

Entrée : `device_model`, `storage_gb`, `ram_gb`, `condition_type`, `grade`, `battery_health_pct`, `city`.

1. **Comparables** : annonces `active` ou `sold` (vendues dans les 120 derniers jours) du même `device_model` et du même `storage_gb` (± un palier pour les PC si nécessaire).
2. **Normalisation par état** : chaque comparable est ramené à un équivalent « grade B occasion » avec des coefficients configurables (dans `settings.PRICING_COEFFS`) :
   - neuf scellé 1,30 · neuf ouvert 1,18 · reconditionné A 1,10 · A 1,08 · B 1,00 · C 0,85
   - batterie < 80 % : × 0,95 ; pièces changées : × 0,92
3. Si **≥ 5 comparables** : on calcule P25, médiane et P75 des prix normalisés (les annonces vendues pèsent ×1,5), puis on réapplique le coefficient de l'appareil estimé. On exclut les valeurs aberrantes (en dehors de 1,5 × IQR).
4. Si **< 5 comparables** : on part du prix neuf indicatif avec une décote par âge (−18 % la 1re année, −12 % par an ensuite, plancher 20 %), puis on applique le coefficient d'état. Fourchette ±15 %. L'estimation est marquée `indicative`.
5. Les prix sont arrondis à 5 000 FCFA.

### 7.2 Badge prix
Disponible seulement si l'estimation n'est pas indicative :
- `good_deal` : prix ≤ 0,90 × médiane → « Bonne affaire »
- `fair` : entre 0,90 et 1,10 → « Prix correct »
- `above_market` : ≥ 1,15 → « Au-dessus du marché »
- sinon (entre 1,10 et 1,15, ou estimation indicative) : pas de badge

Recalculé à la publication, à chaque changement de prix et chaque nuit (management command `recompute_estimates`).

### 7.3 Scores d'usage (`pricing/usage.py`)
Scores de 0 à 10 pour : `office` (bureautique), `study` (études), `dev` (développement), `gaming`, `creative` (photo/vidéo), `battery` (autonomie). Formule pondérée **documentée en commentaire** à partir de : `processor.perf_score`, `gpu.perf_score`, RAM, type de stockage, écran (résolution, fréquence), batterie. Exemple pour `dev` (PC) : 0,45 × CPU + 0,30 × f(RAM) + 0,15 × f(SSD) + 0,10 × f(écran). L'usage « conseillé » d'une annonce est le meilleur score ≥ 7. Pour les mobiles, les usages deviennent : `everyday` (quotidien), `photo`, `gaming`, `battery`, `business`.

### 7.4 Évolution prévue
Quand il y aura plus de 2 000 annonces vendues : un modèle de régression (scikit-learn, gradient boosting) entraîné sur les ventes, versionné, avec repli automatique sur l'algorithme ci-dessus. Hors MVP, mais l'interface `estimate()` ne doit pas changer.

---

## 8. Confiance et modération

### 8.1 Vérifications
- **Particulier vérifié** : pièce d'identité (CNI, passeport ou carte biométrique) + selfie, contrôlés manuellement par un modérateur → badge « Identité vérifiée ».
- **Boutique vérifiée** : IFU + RCCM + adresse physique, contrôlés manuellement → badge « Boutique vérifiée ».
- Les documents sont stockés dans un répertoire privé, accessibles uniquement aux modérateurs, et supprimés 90 jours après la décision (ne conserver que la décision).

### 8.2 Contrôle IMEI / numéro de série
À la publication :
1. Format : IMEI à 15 chiffres + **clé de Luhn** ; numéro de série selon un motif par marque.
2. Comparaison avec les `StolenDeviceReport` confirmés (par hash) → `reported_stolen` : publication bloquée, modérateur alerté.
3. Doublon sur une autre annonce active d'un autre vendeur → `duplicate` : passage en `pending_review`.
4. L'IMEI n'est **jamais** renvoyé par l'API publique, jamais envoyé au LLM, jamais écrit en clair dans les logs.

Une page publique « Déclarer un appareil volé » permet d'alimenter `StolenDeviceReport` (validation manuelle).

### 8.3 Moteur de risque (`trust/risk.py`)
Le score de risque (0–100) est la somme de règles, chacune enregistrée dans `moderation_flags` :

| Règle | Points |
|---|---|
| Prix < 60 % de l'estimation médiane (estimation fiable) | +35 |
| Texte contenant un numéro de téléphone, un lien externe ou une adresse e-mail | +20 |
| Phrases à risque (« paiement avant », « envoie d'abord », « transfert d'abord », « pas de rencontre »…), liste configurable | +30 |
| Photo identique (phash) à celle d'une autre annonce d'un autre vendeur | +40 |
| Compte créé il y a moins de 24 h et 3 annonces ou plus | +15 |
| Modèle hors catalogue | +10 |
| IMEI en doublon | +40 |
| Signal IA de risque (10.2, F6) | +0 à +25 |

- Score < 40 : `active` directement.
- Score de 40 à 69 : `pending_review` (file de modération).
- Score ≥ 70 ou IMEI déclaré volé : `pending_review` prioritaire, et l'annonce n'est jamais visible avant décision.

### 8.4 Côté acheteur
- Bloc « Conseils de sécurité » sur chaque fiche (rencontre dans un lieu public, vérifier l'IMEI avec `*#06#`, ne jamais payer hors TechKoin avant d'avoir vu l'appareil).
- Le numéro de téléphone du vendeur n'apparaît qu'après un clic (« Afficher le numéro »), réservé aux utilisateurs connectés, et chaque affichage est enregistré (`phone_reveal`).
- Bouton « Signaler cette annonce ».

---

## 9. Paiement sécurisé (sandbox)

### 9.1 Principe
L'acheteur paie par Mobile Money. TechKoin **garde les fonds en séquestre** et ne les verse au vendeur qu'après confirmation de réception. Dans le MVP, **tout est en sandbox** : un bandeau permanent « Mode test — aucun argent réel n'est débité » apparaît sur toutes les pages du parcours de paiement.

### 9.2 Machine à états de `Order`

```
created ──paiement initié──▶ payment_pending ──succès──▶ paid_held
   │                               │ échec / 30 min                │
   └──annulation──▶ cancelled ◀────┘                               │
                                                                   ▼
                         seller_marks_handed_over ──▶ handed_over
                                                                   │
              acheteur confirme ou auto_release_at (+48 h) ────────┤──▶ released (versement vendeur)
                                                                   │
                                           acheteur ouvre un litige ──▶ disputed ──▶ released | refunded
```

- Chaque transition est une méthode dédiée (`order.mark_paid()`…), dans `transaction.atomic()`, avec contrôle de l'état de départ (les transitions invalides lèvent une exception) et un journal d'historique.
- Au passage en `paid_held`, l'annonce passe en `reserved`. Au passage en `released`, elle passe en `sold` ; si la commande est annulée ou remboursée, elle redevient `active`.
- Commission : `settings.ESCROW_COMMISSION_PCT` (défaut 3 %), avec minimum de 500 FCFA. Elle est payée par le vendeur et affichée avant publication.
- Les webhooks du provider sont **idempotents** (`idempotency_key`) et leur signature est vérifiée (FedaPay).
- Management command `release_due_orders` (cron toutes les 15 min) pour la libération automatique.

### 9.3 Abonnement Pro
Même mécanisme de `Transaction` (direction `in`), sans séquestre. Prix configurable (`PRO_PLAN_PRICE_FCFA`, proposition : 10 000 FCFA / mois). Le passage en `pro` est immédiat après paiement sandbox réussi.

---

## 10. Intelligence artificielle

### 10.1 Infrastructure commune (`ai/`)

- `ai/client.py` : une seule fonction `complete(feature, prompt_name, variables, schema, model="smart")`.
  - Appelle Groq en mode sortie JSON, valide la sortie avec un modèle **pydantic** (`schema`).
  - Timeout 15 s, 1 nouvel essai si le JSON est invalide, puis **repli déterministe** (chaque fonctionnalité a un `fallback()` qui produit une sortie utile sans IA).
  - Journalise dans `AIRequestLog` (tokens, latence, repli utilisé).
- Prompts dans `ai/prompts/<nom>.md`, avec un en-tête de version. Ils sont rédigés en français, demandent un ton factuel, sans emoji, et interdisent explicitement d'inventer des caractéristiques ou des prix absents des données fournies.
- **Données envoyées au LLM** : uniquement des données d'annonce et des agrégats. Jamais d'IMEI, de téléphone, d'e-mail, de nom de particulier ni de document.
- **Cache** (`AICache`) : clé = hash de la fonctionnalité + entrées normalisées. Durées : recherche 24 h, comparaison 7 jours (invalidée si une annonce change), assistant 24 h.
- **Limites** (throttling DRF, configurables) :
  - visiteur : 20 recherches IA/heure, 5 comparaisons IA/heure, 10 questions assistant/heure ;
  - connecté : le double ;
  - boutique Pro : 200 requêtes Analyse IA/jour.
- Si `GROQ_API_KEY` est absente, l'application **fonctionne entièrement en mode repli** (indispensable pour le dev et les tests).
- Étiquetage dans l'interface : on nomme la **fonction** (« Recherche intelligente », « Verdict TechKoin », « Analyse du marché »), jamais « Powered by AI », sans icône d'étincelle. Une mention discrète « Réponse générée automatiquement, vérifiez les informations clés » accompagne les textes rédigés par l'IA.

### 10.2 Fonctionnalités gratuites

**F1 — Recherche en langage naturel**
- Entrée : texte libre (« un pc pour coder pas trop cher vers Calavi, max 250k »).
- Sortie (pydantic) : `{category?, brands[], price_min?, price_max?, city?, condition[], grade[], ram_min?, storage_min?, usage?, keyboard?, other_terms[], confidence}`. Les valeurs sont contraintes aux énumérations existantes ; les villes et marques inconnues sont ignorées.
- Modèle : `fast`.
- Repli : parseur à règles (`ai/fallback/query_parser.py`) qui gère les montants (« 250k », « 250 000 », « 250mil »), les villes et leurs variantes, les marques, les catégories et les mots d'usage (coder, gaming, montage, école…).
- Interface : l'interprétation est affichée sous forme de filtres modifiables (« Compris : PC portable · max 250 000 FCFA · Abomey-Calavi · usage développement »), que l'utilisateur peut retirer un par un.

**F2 — Publication assistée (texte)**
- Entrée : specs et état saisis.
- Sortie : `{title (≤ 70 caractères), description (80–150 mots), highlights[3]}`.
- Règles : n'utilise que les champs fournis ; mentionne les défauts déclarés ; aucune promesse non vérifiable (« jamais réparé » seulement si `replaced_parts = none`).
- Repli : gabarit de texte.

**F3 — Publication vocale**
- Le vendeur dicte (« iPhone 12, 128 giga, batterie 84, petite rayure derrière, avec chargeur ») → transcription par Whisper (Groq), puis extraction structurée (`fast`) qui **pré-remplit le formulaire**. Le vendeur valide chaque champ.
- Audio : 60 s maximum, supprimé après transcription.

**F4 — Assistant acheteur (sur chaque fiche)**
- Questions libres (« Ça suffit pour Premiere Pro ? », « La batterie tient combien ? »).
- Contexte transmis : specs de l'annonce, scores d'usage, estimation de prix, données de confiance. Pas d'historique de conversation au-delà de 5 échanges.
- Si l'information est absente, l'assistant le dit et propose de poser la question au vendeur (bouton qui pré-remplit un message WhatsApp).
- Suggestions de questions affichées sous le champ (3 boutons de texte).

**F5 — Comparaison IA**
- Points d'entrée : bouton « Comparer » sur les cartes (jusqu'à 3 annonces, barre de comparaison fixe en bas de l'écran) ; bloc « Comparer avec des annonces similaires » sur la fiche (2 alternatives choisies par Django : même catégorie, prix ± 20 %, scores proches) ; requête « compare X et Y » dans la recherche.
- **Calculé par Django (`pricing/compare.py`)** : tableau aligné des specs, meilleure valeur par ligne, scores d'usage, position par rapport à l'estimation, éléments de confiance (vérifié, garantie, facture, note, pièces changées).
- Questions à l'utilisateur : usage principal (liste) et budget maximum (optionnel).
- **Groq (`smart`)** reçoit le JSON calculé et renvoie : `{winner_listing_id, summary (≤ 60 mots), reasons[≤4], warnings[≤3], per_listing: [{listing_id, best_for, verdict_line}]}`. Il ne peut citer que des valeurs présentes dans le JSON ; la sortie est vérifiée (l'identifiant gagnant doit faire partie des annonces comparées).
- Repli : verdict déterministe (meilleur score pour l'usage choisi, pondéré par le rapport qualité-prix et la confiance).
- Cache par `(ids triés + usage + budget + updated_at des annonces)`.

**F6 — Anti-arnaque IA**
- À la publication, en complément des règles 8.3 : classification du texte (`fast`) → `{risk: 0–25, signals[]}` (pression, demande de paiement anticipé, incohérences entre le texte et les specs).
- Ne bloque jamais seule ; elle ajoute des points au score de risque.

### 10.3 « Analyse IA » — fonctionnalités payantes (boutiques Pro)

Accessibles depuis l'onglet « Analyse » du tableau de bord boutique. Pour les boutiques en plan Gratuit, l'onglet montre un **aperçu réel mais limité** (le 1er élément de chaque module, le reste masqué) avec l'offre d'abonnement. Pas de flou ni de faux contenu.

**P1 — Radar de la demande**
- Agrège les `Event` `search` et `search_no_result` des 7 et 30 derniers jours par (catégorie, modèle ou famille, tranche de budget, ville), puis compare le nombre de recherches à l'offre active.
- Sortie : tableau classé « Demande forte, offre faible » (recherches, annonces disponibles, prix recherché médian, évolution vs période précédente) + 3 recommandations d'achat rédigées par Groq à partir de ce tableau.
- Exemple : « 87 recherches cette semaine pour un MacBook M1 à moins de 400 000 FCFA à Cotonou, 3 annonces disponibles. »
- Seuil de confidentialité : un segment n'est affiché que s'il agrège au moins 10 recherches.

**P2 — Conseiller prix**
- Pour chaque annonce active de la boutique : prix actuel, estimation, écart en %, jours en ligne, vues et contacts vs moyenne de la catégorie.
- Recommandation calculée (prix conseillé arrondi à 5 000 FCFA) et explication courte par Groq. Bouton « Appliquer ce prix ».

**P3 — Diagnostic du stock dormant**
- Annonces en ligne depuis plus de 14 jours avec un taux de contact inférieur à la médiane.
- Causes détectées par règles (prix au-dessus du marché, moins de 6 photos, description < 40 mots, specs manquantes, ville peu demandée) + explication et correction proposée par Groq (nouveau titre, description, prix). Bouton « Appliquer » par correction.

**P4 — Rapport hebdomadaire**
- Chaque lundi à 8 h (heure de Porto-Novo) : vues, contacts, ventes, meilleurs produits, évolution, 3 actions prioritaires.
- Rédigé par Groq à partir des chiffres calculés. Disponible dans l'interface et envoyé par e-mail (WhatsApp prévu plus tard : prévoir l'interface `Notifier`).

**P5 — Discuter avec ses chiffres**
- Chat dans le tableau de bord (« Combien de contacts sur les iPhone ce mois ? »).
- **Tool calling Groq** avec des fonctions prédéfinies, toujours limitées à la boutique connectée : `get_stats(period, metric, category?, model?)`, `top_listings(period, metric, limit)`, `compare_periods(metric, period_a, period_b)`, `price_position(listing_id?)`, `demand_for(model_or_family, city?)`.
- **Interdit :** générer ou exécuter du SQL à partir du LLM.

**P6 — Optimisation des annonces en lot**
- Sélection de 1 à 50 annonces → nouveaux titres et descriptions proposés (F2 en lot) → écran de validation avant/après, avec acceptation par annonce ou pour tout le lot.

**P7 — Comparer mon annonce à la concurrence**
- Pour une annonce de la boutique : les 3 annonces concurrentes les plus proches (F5) et la réponse à « pourquoi un acheteur choisirait-il celles-ci plutôt que la mienne ? », avec des actions concrètes (prix, garantie, photos, accessoires).

---

## 11. Plans boutique

| Fonctionnalité | Gratuit | Pro (Analyse IA) |
|---|---|---|
| Vitrine publique `/boutique/<slug>` | oui | oui |
| Annonces actives | illimitées | illimitées |
| Tableau de bord : vues, contacts, favoris par annonce | oui | oui |
| Radar de la demande (P1) | aperçu | complet |
| Conseiller prix (P2) | aperçu | complet |
| Stock dormant (P3) | aperçu | complet |
| Rapport hebdomadaire (P4) | non | oui |
| Discuter avec ses chiffres (P5) | non | oui |
| Optimisation en lot (P6) | non | oui |
| Comparaison concurrence (P7) | non | oui |

L'accès est contrôlé côté API par une permission DRF `IsProShop`. Le front ne fait qu'afficher : il ne décide jamais de l'accès.

---

## 12. Suivi des événements

- Point d'entrée unique `analytics.track(type, request, **data)`, appelé côté serveur (recherche, vue) et via `POST /api/events/` pour les actions purement front (clic WhatsApp, ouverture de la comparaison).
- `session_id` : cookie anonyme `tk_sid` (UUID, 1 an).
- Une vue n'est comptée qu'une fois par session et par annonce sur 30 minutes.
- Les bots (user-agent) sont exclus.
- Conservation des événements bruts : 18 mois. Agrégats quotidiens (`analytics.DailyShopStats`, `analytics.DailyDemandStats`) produits par la commande `aggregate_events`.
- **À implémenter dès la phase 1** : sans ces données, l'Analyse IA n'a rien à analyser.

---

## 13. API REST (préfixe `/api/`)

Documentation générée dans `docs/API.md`. Format de réponse paginée : `{count, next, previous, results}`. Erreurs : `{code, message, fields?}` avec des messages en français.

**Auth et compte**
- `POST auth/register` · `POST auth/login` · `POST auth/logout` · `GET auth/me` · `GET auth/csrf`
- `PATCH me` · `POST me/identity` (envoi des documents)
- `GET me/listings` · `GET me/favorites` · `GET/POST/DELETE me/alerts` · `GET me/orders`

**Catalogue**
- `GET catalog/models?q=&category=` (autocomplétion, 10 résultats) · `GET catalog/models/{slug}` (specs par défaut)
- `GET catalog/brands?category=` · `GET catalog/processors?q=` · `GET catalog/gpus?q=` · `GET catalog/cities`

**Annonces**
- `GET listings` (filtres de la section 6) · `GET listings/{slug}` · `GET listings/{slug}/similar`
- `POST listings` (brouillon) · `PATCH listings/{id}` · `POST listings/{id}/photos` · `DELETE listings/{id}/photos/{pid}` · `POST listings/{id}/publish` · `POST listings/{id}/mark-sold` · `POST listings/{id}/archive`
- `POST listings/{id}/reveal-phone` · `POST listings/{id}/favorite` · `DELETE listings/{id}/favorite` · `POST listings/{id}/report`
- `POST pricing/estimate` (estimation en direct pendant la publication)

**IA**
- `POST ai/search` (F1) · `POST ai/describe` (F2) · `POST ai/voice` (F3, multipart) · `POST ai/assistant` (F4) · `POST ai/compare` (F5)

**Paiement (sandbox)**
- `POST orders` · `POST orders/{id}/pay` (opérateur + téléphone) · `GET orders/{id}` · `POST orders/{id}/handed-over` · `POST orders/{id}/confirm` · `POST orders/{id}/dispute` · `POST orders/{id}/cancel`
- `POST payments/webhook/{provider}` · `POST sandbox/simulate/{transaction_id}?result=success|fail` (dev uniquement)

**Boutique**
- `GET/PATCH shop` · `POST shop/verification` · `GET shop/stats?period=` · `POST shop/subscribe`
- `GET shops/{slug}` (public) · `GET shops/{slug}/listings`
- Pro : `GET insights/demand` · `GET insights/pricing` · `GET insights/dormant` · `GET insights/reports` · `GET insights/reports/{id}` · `POST insights/chat` · `POST insights/bulk-optimize` · `POST insights/bulk-optimize/apply` · `GET insights/competition/{listing_id}`

**Confiance et modération**
- `POST stolen-reports` · modération via Django admin personnalisé (file triée par `risk_score`, actions en un clic) en MVP

**Événements**
- `POST events`

---

## 14. Frontend : pages et parcours

Approche **mobile d'abord** (la majorité du trafic sera sur smartphone avec une connexion mobile). Chaque page a quatre états soignés : chargement (squelettes statiques, sans animation shimmer), vide (message utile + action), erreur (message clair + réessayer), succès.

| Route | Page | Contenu essentiel |
|---|---|---|
| `/` | Accueil | Barre de recherche intelligente en tête, 3 entrées de catégorie (PC, Smartphones, Tablettes) en liste, « Arrivages récents », « Bonnes affaires du moment » (badge `good_deal`), section « Comment on vérifie » (liste numérotée, texte éditorial), boutiques vérifiées, appel à vendre |
| `/recherche` | Résultats | Filtres en colonne gauche (desktop) ou panneau plein écran (mobile), interprétation de la recherche IA, tri, grille ou liste (au choix, mémorisé), pagination, « Créer une alerte pour cette recherche » |
| `/annonce/:slug` | Fiche | Galerie (miniatures + plein écran), titre, prix en grand, badge prix + barre de fourchette d'estimation, note d'état expliquée, tableau de specs groupé, scores d'usage, bloc confiance, vendeur (badge, ancienneté, ventes), actions (WhatsApp, afficher le numéro, payer en sécurité, comparer, favori, partager), assistant acheteur, conseils de sécurité, annonces similaires |
| `/comparer?ids=` | Comparaison | Choix de l'usage et du budget, tableau aligné (meilleure valeur surlignée), scores, verdict TechKoin, actions par annonce |
| `/vendre` | Publication (étapes) | 1. Catégorie et modèle (autocomplétion, ou dictée vocale) · 2. Checklist d'état → note proposée · 3. Specs (pré-remplies, à confirmer) · 4. Photos guidées · 5. Prix (estimation en direct + badge prévu) · 6. Description (bouton « Rédiger pour moi ») · 7. IMEI + récapitulatif + publication. Brouillon sauvegardé à chaque étape |
| `/commande/:id` | Commande | Choix de l'opérateur, numéro, paiement sandbox, chronologie de la commande, actions selon l'état et le rôle |
| `/connexion`, `/inscription` | Auth | Choix particulier / boutique à l'inscription |
| `/compte/*` | Espace particulier | Mes annonces (avec statut et stats simples), favoris, alertes, commandes, vérification d'identité, profil |
| `/boutique/:slug` | Vitrine publique | En-tête boutique (logo, adresse, horaires, badge), annonces avec filtres |
| `/pro/*` | Tableau de bord boutique | Vue d'ensemble, Annonces (tableau avec actions groupées), Analyse (P1 à P7), Commandes, Abonnement, Paramètres |
| `/securite` | Conseils et appareil volé | Guide d'achat sûr, formulaire de déclaration d'appareil volé |
| `/a-propos`, `/cgu`, `/confidentialite` | Pages légales | Texte simple |

**Composants transverses :** en-tête (logo, recherche, Vendre, Compte), barre de comparaison fixe en bas quand au moins une annonce est sélectionnée, pied de page (liens, contact, réseaux), bandeau « Mode test » sur les parcours de paiement.

**Partage WhatsApp.** Les URL `/annonce/:slug` et `/boutique/:slug` doivent produire des **balises Open Graph** (titre, prix, ville, 1re photo) pour un bel aperçu dans WhatsApp. En production, Django sert `index.html` en injectant ces balises pour ces routes (vue `spa_with_meta`).

---

## 15. Design system — style A, sans clichés « vibe code »

### 15.1 Principes
1. **Clair et chaleureux**, pas noir. Le fond est un papier légèrement chaud, pas un blanc clinique ni un noir.
2. **Le produit d'abord** : les photos des appareils et les prix sont les vrais visuels du site.
3. **La sobriété crée la confiance** : peu de couleurs, une hiérarchie typographique nette, des lignes franches.
4. **Densité maîtrisée** : une marketplace montre de l'information. On l'organise (tableaux, listes, colonnes) au lieu de la cacher dans des cartes décoratives.
5. **Une identité locale discrète** : prix en FCFA bien lisibles, villes et quartiers réels, ton direct, couleurs qui évoquent le Bénin sans folklore.

### 15.2 Interdits (bloquants)

| Interdit | À la place |
|---|---|
| Mode sombre par défaut, fonds `#09090B` et équivalents | Thème clair chaud. Pas de mode sombre dans le MVP |
| Dégradés violets, bleus électriques, cyan, rose néon | Palette 15.3, couleurs pleines uniquement. **Aucun dégradé** dans l'interface |
| Halos lumineux (glow), ombres colorées floues | Pas d'ombre décorative. Ombre neutre seulement pour les éléments flottants |
| Fonds texturés : points, quadrillage, bruit | Fonds unis |
| Bordures semi-transparentes ultra-fines autour de chaque bloc | Filets **opaques** (`--line`), utilisés pour structurer (séparateurs, tableaux), pas pour encadrer tout |
| Glassmorphism, `backdrop-filter: blur` | En-tête opaque |
| Grilles « bento » | Listes, tableaux, colonnes éditoriales, grille de produits régulière |
| Inter, Geist ; titres énormes serrés ; mot-clé en dégradé | IBM Plex Sans / Plex Mono (15.4), interlettrage normal, tailles mesurées |
| Pilules au-dessus des titres avec icône brillante (« Powered by AI ») | Pas de surtitre décoratif. Les étiquettes d'état sont rectangulaires, en texte |
| Icônes Lucide enfermées dans des carrés colorés | Phosphor, sans conteneur, à côté d'un texte, seulement quand l'icône aide (15.6) |
| Composants shadcn/ui par défaut | Composants maison (15.5) |
| Fausses captures de tableau de bord inclinées en 3D, avatars à initiales, illustrations IA lisses | Vraies photos d'appareils ; logos de boutique ; pictogrammes simples dessinés pour TechKoin |
| Apparition en fondu vers le haut au défilement | Aucune animation au défilement (15.8) |
| Favicon Vite, Vercel, Lovable ou Bolt | Favicon TechKoin (15.9). Supprimer `vite.svg` |
| Emoji | Aucun, nulle part |

### 15.3 Couleurs (`src/styles/tokens.css`)

```css
:root {
  /* Fonds */
  --bg:          #F6F4EF;  /* papier chaud, fond de page */
  --surface:     #FFFFFF;  /* cartes, panneaux, champs */
  --surface-2:   #EFECE5;  /* zones secondaires, en-têtes de tableau */

  /* Texte */
  --ink:         #1B1915;  /* texte principal */
  --ink-2:       #5A554C;  /* texte secondaire */
  --ink-3:       #8A8478;  /* texte tertiaire, placeholders (usage limité, contraste à vérifier) */

  /* Lignes */
  --line:        #DDD8CE;  /* filets opaques */
  --line-strong: #C4BEB1;  /* champs de formulaire, séparateurs forts */

  /* Marque */
  --green:       #0B6B45;  /* couleur principale : actions, liens, prix */
  --green-ink:   #08533A;  /* survol / pressé */
  --green-tint:  #E3F0E8;  /* fonds de succès, sélection */

  --yellow:      #E9B824;  /* accent rare : bonne affaire, mise en avant */
  --yellow-tint: #FBF1CF;

  --red:         #B42318;  /* erreurs, risques, au-dessus du marché */
  --red-tint:    #FBE7E4;

  --focus:       #0B6B45;  /* anneau de focus, 2px plein + 2px d'espacement */
}
```

- Le vert, le jaune et le rouge font écho au drapeau béninois **sans le reproduire** (pas de bandes tricolores, pas de carte).
- Le vert est la seule couleur d'action. Le jaune est réservé à « Bonne affaire » et aux mises en avant ponctuelles. Le rouge est réservé aux erreurs et aux risques.
- Contraste WCAG AA minimum pour tout texte (vérification automatisée en phase 6).

### 15.4 Typographie
- **IBM Plex Sans** (400, 500, 600) pour l'interface et les titres.
- **IBM Plex Mono** (400, 500) pour les **prix, specs et chiffres** (tableaux de specs, comparaison, statistiques) : c'est la signature « fiche technique » de TechKoin.
- Échelle (desktop / mobile) : H1 40/30 px · H2 28/24 · H3 20/18 · corps 16 · petit 14 · micro 12. Hauteur de ligne 1,5 pour le corps, 1,2 pour les titres. Interlettrage `0` (jamais de valeur négative).
- Les prix s'écrivent `185 000 FCFA` (espace fine insécable ` ` comme séparateur des milliers, « FCFA » en taille réduite). Fonction unique `formatFCFA()`.
- Aucun texte en dégradé, aucun texte « outline ».

### 15.5 Formes et composants
- Rayons : 4 px (étiquettes, cases), 6 px (boutons, champs), 8 px (cartes, panneaux, modales). Jamais de pilule sauf pour l'interrupteur (toggle).
- Ombres : aucune sur les cartes au repos. Éléments flottants (menus, popovers, modales) : `0 6px 20px rgba(27,25,21,.12)`.
- Espacements : échelle de 4 px (`4, 8, 12, 16, 24, 32, 48, 64`). Grille de 12 colonnes, largeur max 1200 px, gouttières de 16 px sur mobile.

**Composants maison à créer** (dans `src/components/`, chacun avec ses variantes documentées dans une page interne `/_styleguide` réservée au dev) :
- **Button** : `primary` (fond vert plein, texte blanc), `secondary` (fond blanc, filet `--line-strong`, texte encre), `ghost` (texte vert souligné au survol), `danger`. Tailles 40 px et 48 px (mobile : 48 px). Pas de dégradé, pas d'ombre.
- **Input, Select, Textarea, Checkbox, Radio, RangeSlider** : fond blanc, filet `--line-strong`, focus vert plein.
- **Tag** (étiquette) : rectangle 4 px de rayon, texte 12–13 px **en capitales normales (pas tout en majuscules)**, fond teinté (`--green-tint`, `--yellow-tint`, `--red-tint` ou `--surface-2`). Usage : « Boutique vérifiée », « Bonne affaire », « Garantie 6 mois », « QWERTY ».
- **ListingCard** : photo 4:3 sur fond `--surface-2`, puis titre (2 lignes max), specs clés en Plex Mono (ex. `16 Go · 512 Go SSD · i5 11e gén.`), prix, badge prix, ville et ancienneté, note d'état. Toute la carte est cliquable. Bouton « Comparer » en case à cocher discrète.
- **GradeMark** : la lettre A, B ou C dans un carré de 20 px à filet, suivie du libellé (« Comme neuf »).
- **PriceRange** : barre horizontale fine montrant la fourchette d'estimation (P25–P75) avec un repère pour le prix de l'annonce et le libellé « Prix du marché : 170 000 – 195 000 FCFA ».
- **SpecTable** : tableau à deux colonnes, libellés en Plex Sans `--ink-2`, valeurs en Plex Mono `--ink`, filets entre groupes.
- **CompareTable** : colonnes alignées, en-têtes collants, meilleure valeur en gras avec un fond `--green-tint`.
- **ScoreBar** : barre pleine sur 10 segments, sans dégradé.
- **Tabs** : onglets soulignés (trait vert de 2 px sous l'onglet actif), pas de fond en « segmented control ».
- **Dialog, Popover, Toast** : sur base Radix, restylés ; les toasts sont en bas à gauche, fond encre, texte blanc, disparition après 5 s.
- **Stepper** de publication : liste numérotée horizontale (mobile : « Étape 3 sur 7 » + barre).
- **EmptyState** : titre, une phrase, une action. Pas d'illustration.

### 15.6 Iconographie
- **Phosphor Icons**, graisse `regular` (ou `bold` en 16 px), taille 18–20 px, couleur héritée du texte.
- Une icône accompagne une étiquette textuelle ou constitue un bouton évident (recherche, favori, fermer, partager, WhatsApp). **Jamais de conteneur coloré autour.**
- Pas d'icône décorative devant chaque titre de section.
- Le logo WhatsApp utilisé pour le bouton de contact doit être conforme à la charte de WhatsApp.

### 15.7 Images
- **Photos des annonces** : le cœur visuel. Ratio 4:3 dans les grilles, fond `--surface-2` le temps du chargement, `loading="lazy"`, `srcset` (480 et 1600 px).
- **Visuels propres au site** (accueil, pages d'information) : vraies photos (boutiques, mains qui tiennent un appareil, rues de Cotonou), fournies plus tard par l'équipe. En attendant : **pas d'image du tout** (mise en page typographique) plutôt qu'une image générique ou générée par IA.
- **Avatars** : logo pour les boutiques ; pour les particuliers, aucun avatar (prénom + initiale du nom + badge de vérification en texte).
- Pictogrammes de cadrage photo (étape 4 de la publication) : silhouettes simples dessinées en SVG au trait, dans le style de l'interface.

### 15.8 Mouvement
- Transitions de 120 à 160 ms uniquement sur survol, focus, ouverture et fermeture (menus, modales, panneau de filtres).
- **Aucune animation au défilement**, aucun effet de parallaxe, aucun compteur animé, aucun shimmer sur les squelettes.
- Respect de `prefers-reduced-motion` (transitions désactivées).

### 15.9 Logo et favicon
- **Logotype** : « TechKoin » en IBM Plex Sans 600, couleur encre. Le « K » est en vert ; un petit angle (coin coupé) en vert est accolé en haut à droite du mot. C'est un clin d'œil à « koin » / coin. Fournir le SVG dans `public/brand/`.
- **Monogramme** : « TK » blanc sur un carré vert à coin coupé en haut à droite.
- **Favicon** : monogramme en `favicon.svg`, `favicon-32.png`, `apple-touch-icon.png` (180 px), `icon-192.png`, `icon-512.png`, plus `manifest.webmanifest` (nom, couleurs `--bg` et `--green`).
- Supprimer `vite.svg` et toute référence à Vite dans `index.html`. Titre de page par défaut : « TechKoin — Appareils neufs et d'occasion au Bénin ».

### 15.10 Écriture
- Ton direct, poli, concret. Vouvoiement dans l'interface.
- Des phrases courtes, des verbes d'action sur les boutons (« Publier l'annonce », « Payer en sécurité », « Afficher le numéro »).
- Pas de superlatifs marketing (« révolutionnaire », « ultime »), pas d'emoji, pas de points d'exclamation en série.
- Messages d'erreur qui disent quoi faire (« La photo de l'écran allumé est obligatoire. Ajoutez-la pour continuer. »).
- Formats : dates « 12 nov. 2026 », heures « 14 h 30 », fuseau Africa/Porto-Novo.

### 15.11 Responsive et accessibilité
- Points de rupture : 480, 768, 1024, 1280 px. Tout fonctionne dès 360 px de large, sans défilement horizontal.
- Cibles tactiles de 44 px minimum. Navigation complète au clavier. Focus toujours visible. Libellés de formulaire visibles (pas seulement des placeholders). Textes alternatifs pour les photos (générés à partir du titre et du type de photo).

### 15.12 Checklist anti-vibe code (à vérifier avant chaque fin de phase)
- [ ] Aucun dégradé, glow, flou d'arrière-plan ni fond texturé (`grep` sur `gradient`, `blur`, `backdrop`)
- [ ] Aucune police autre que Plex Sans / Plex Mono
- [ ] Aucune bordure en `rgba(...)` ; uniquement les tokens `--line` et `--line-strong`
- [ ] Aucune icône dans un conteneur coloré ; aucune icône d'étincelle
- [ ] Aucune animation déclenchée par le défilement
- [ ] Aucun emoji dans le code de l'interface, les prompts ni les données de démo
- [ ] Favicon et titre TechKoin en place ; `vite.svg` supprimé
- [ ] Aucune mise en page bento
- [ ] Les captures d'écran mobile (360 px) et desktop (1280 px) des pages modifiées sont jointes au résumé de phase

---

## 16. Exigences non fonctionnelles

**Performance (connexion mobile 3G/4G)**
- JS initial < 180 Ko gzip ; découpage par route (`React.lazy`).
- Photos WebP, chargement différé ; aucune image de plus de 250 Ko en grille.
- Liste de résultats : réponse API < 300 ms sur la base de démo.
- Cache HTTP pour le catalogue et les villes.

**Sécurité**
- Throttling DRF sur l'auth, la publication, l'affichage du numéro, l'IA et le paiement.
- Uploads : types MIME vérifiés (JPEG, PNG, WebP, HEIC converti), 10 Mo max, ré-encodage systématique.
- IMEI chiffré (clé dans `.env`), documents d'identité privés, jamais de données personnelles dans les logs.
- Permissions : un vendeur ne modifie que ses annonces ; une boutique n'accède qu'à ses statistiques ; les outils de P5 sont limités à la boutique connectée.
- En production : `DEBUG=False`, HTTPS, cookies `Secure` + `SameSite=Lax`, en-têtes de sécurité.

**Qualité**
- Backend : `ruff` + `black` ; frontend : ESLint + Prettier ; TypeScript strict.
- Types d'API générés ou maintenus dans `src/lib/api/types.ts`.

**Localisation** : `LANGUAGE_CODE = "fr"`, `TIME_ZONE = "Africa/Porto-Novo"`, devise FCFA (XOF) sans décimales.

---

## 17. Données de démo (`python manage.py seed_demo`)

- Catalogue complet (section 5.6) avec processeurs, GPU et `perf_score`.
- 8 boutiques **fictives** (noms inventés, sans lien avec des commerces réels), dont 5 vérifiées et 2 en plan Pro, réparties entre Cotonou, Abomey-Calavi, Porto-Novo et Parakou.
- 25 particuliers fictifs.
- 150 annonces réalistes (prix cohérents avec l'estimation, quelques bonnes affaires, quelques annonces au-dessus du marché, 5 annonces suspectes pour tester la modération).
- Photos : images neutres générées (fond uni, nom du modèle et type de photo en texte), clairement identifiables comme des données de démo. Pas d'images de produits récupérées sur internet.
- 90 jours d'`Event` simulés (recherches avec et sans résultat, vues, contacts) pour que le radar de la demande et le rapport hebdo aient du contenu.
- 10 commandes sandbox dans différents états.
- Comptes de démo (mots de passe dans le README) : `admin`, `moderateur`, `boutique.pro`, `boutique.gratuite`, `particulier`.
- Commande idempotente (`--reset` pour tout recréer).

---

## 18. Tests

**Backend (tests Django ou pytest-django)**
- Estimation de prix : comparables suffisants ou non, valeurs aberrantes, coefficients, arrondi, badges.
- Scores d'usage : cas limites (GPU absent, RAM inconnue).
- Filtres : chaque paramètre de la section 6.1, combinaisons, tri `best_deal`.
- Confiance : Luhn, doublon IMEI, appareil déclaré volé, chaque règle de risque, seuils de statut, refus si le compte iCloud/Google n'est pas retiré.
- Machine à états des commandes : toutes les transitions valides et invalides, idempotence des webhooks, libération automatique.
- Permissions : accès Pro, propriété des annonces, isolation des statistiques entre boutiques.
- IA : client Groq **simulé** (mock) ; validation pydantic ; repli quand la clé est absente, sur timeout et sur JSON invalide ; contrôle du verdict (l'identifiant gagnant doit être une annonce comparée) ; absence de données personnelles dans les entrées envoyées au LLM.

**Frontend**
- Vitest : `formatFCFA`, sérialisation des filtres ↔ URL, parseur de recherche côté client s'il existe.
- Playwright (parcours principaux, mobile 360 px et desktop 1280 px) : rechercher → filtrer → ouvrir une fiche → comparer ; publier une annonce complète ; payer en sandbox puis confirmer la réception ; s'abonner en Pro et ouvrir le radar de la demande.

---

## 19. Phases et critères d'acceptation

**Phase 0 — Socle**
- Dépôt, Django + DRF, Vite + React + TS, proxy de dev, tokens CSS, polices, composants de base, `/_styleguide`, favicon, logo, `.env.example`, README.
- Prérequis : section 0.1, étape 1 terminée (GitHub connecté, dépôt créé, premier commit à mon nom vérifié).
- Accepté si : `make dev` (ou équivalent documenté) lance les deux serveurs ; chaque élément du socle a été poussé dans un commit séparé, à mon nom, sans co-auteur ; le styleguide montre tous les composants de base ; la checklist 15.12 passe.

**Phase 1 — Marketplace de base**
- Comptes (particulier / boutique), catalogue + seed, annonces (CRUD, photos, publication guidée sans IA), recherche et filtres complets, fiche annonce, contact WhatsApp, affichage du numéro, favoris, vitrine boutique, suivi des événements.
- Accepté si : un particulier publie une annonce complète depuis un mobile en moins de 3 minutes ; tous les filtres fonctionnent et vivent dans l'URL ; les événements sont enregistrés.

**Phase 2 — Confiance et prix**
- Estimation de prix et badges, scores d'usage, contrôle IMEI, moteur de risque, file de modération, vérifications d'identité et de boutique, signalements, déclaration d'appareil volé, conseils de sécurité.
- Accepté si : les 5 annonces suspectes de la démo arrivent en modération ; l'estimation et le badge s'affichent sur les fiches et pendant la publication.

**Phase 3 — IA gratuite**
- F1 à F6, cache, limites, journalisation, replis.
- Accepté si : tout fonctionne **sans** clé Groq (replis) et **avec** ; la comparaison de 3 annonces s'affiche en moins de 3 s (hors cache) ; aucune donnée personnelle ne part au LLM (test automatisé).

**Phase 4 — Paiement sécurisé sandbox**
- Commandes, machine à états, `SimulatorProvider`, `FedaPayProvider` (sandbox), webhooks, libération automatique, litiges, bandeau « Mode test ».
- Accepté si : le parcours complet achat → remise → confirmation → libération fonctionne avec le simulateur et avec FedaPay en sandbox.

**Phase 5 — Boutiques et Analyse IA**
- Tableau de bord, statistiques, abonnement Pro (sandbox), P1 à P7, aperçu limité pour le plan Gratuit, rapport hebdomadaire par e-mail.
- Accepté si : une boutique Pro de démo voit un radar de la demande cohérent avec les événements simulés ; une boutique Gratuite ne peut pas appeler les endpoints Pro (test 403).

**Phase 6 — Alertes et finitions**
- Alertes de recherche (e-mail + notification interne, interface prête pour WhatsApp), facettes, Open Graph, audit de performance et d'accessibilité, préparation de la migration PostgreSQL (vérifiée sur une base Postgres locale), documentation de déploiement.
- Accepté si : Lighthouse mobile ≥ 90 en performance et en accessibilité sur l'accueil, les résultats et une fiche ; les tests passent sur SQLite **et** sur PostgreSQL.

---

## 20. Hors périmètre du MVP
- Paiements réels et versements réels aux vendeurs
- Application mobile native (le site doit être installable en PWA en phase 6, sans plus)
- Notifications WhatsApp réelles (WhatsApp Business API) : interface prête, implémentation plus tard
- OTP SMS (champ prévu)
- Livraison intégrée avec des partenaires
- Annonces boostées et publicité
- Avis et notes entre utilisateurs
- Modèle de prix par machine learning (section 7.4)
- Mode sombre
- Langues locales (fon, yoruba…)

---

## 21. Variables d'environnement (`.env.example`)

```
DJANGO_SECRET_KEY=
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
SITE_URL=http://localhost:5173

FIELD_ENCRYPTION_KEY=          # chiffrement des IMEI

GROQ_API_KEY=
GROQ_MODEL_SMART=llama-3.3-70b-versatile
GROQ_MODEL_FAST=llama-3.1-8b-instant
GROQ_MODEL_STT=whisper-large-v3
AI_TIMEOUT_SECONDS=15

PAYMENT_PROVIDER=simulator     # simulator | fedapay
FEDAPAY_SECRET_KEY=            # clé sandbox
FEDAPAY_PUBLIC_KEY=
FEDAPAY_WEBHOOK_SECRET=
FEDAPAY_ENV=sandbox
ESCROW_COMMISSION_PCT=3
ESCROW_COMMISSION_MIN_FCFA=500
ESCROW_AUTO_RELEASE_HOURS=48
PRO_PLAN_PRICE_FCFA=10000

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=TechKoin <no-reply@techkoin.bj>
```

---

## 22. Prompt de démarrage à donner à Claude Code

> Lis entièrement `TECHKOIN_SPEC.md` à la racine du dépôt. C'est la source de vérité du projet TechKoin.
>
> **D'abord, connecte-moi** : suis la section 0.1, étape 1 (connexion GitHub avec `gh auth login`, configuration de mon nom et de mon e-mail, création du dépôt, premier commit). Montre-moi l'auteur du premier commit et attends ma confirmation.
>
> Ensuite, commence par la **phase 0** uniquement. Avant d'écrire du code, propose-moi en 15 lignes maximum ton plan pour la phase 0 (arborescence, dépendances, commandes de lancement) et signale toute contradiction ou question dans le document.
>
> Pendant tout le projet : **un commit et un push après chaque fonctionnalité**, en mon nom uniquement, **sans ligne `Co-Authored-By` ni aucune mention de Claude** dans les commits et les PR (section 0.1, étape 2). Respecte strictement la section 15 (design) et sa checklist.
>
> À la fin de la phase 0, donne-moi un résumé, la liste des commits poussés, les commandes pour lancer le projet et des captures d'écran du styleguide en 360 px et 1280 px, puis attends ma validation avant la phase 1.
