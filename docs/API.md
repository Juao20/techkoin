# API

Préfixe : `/api/`. Réponses paginées (24 par page) : `{count, next, previous, results}`. Erreurs : `{code, message, fields?}` en français. Authentification par session Django et jeton CSRF (`GET /api/auth/csrf/` pose le cookie, à renvoyer dans l'en-tête `X-CSRFToken`).

## Système

| Méthode | Route | Description |
|---|---|---|
| GET | `health/` | Sonde de disponibilité |
| GET | `auth/csrf/` | Pose le cookie CSRF |
| POST | `events/` | Événements côté front : `whatsapp_click`, `compare`, `contact_click`, `checkout_start` |

## Comptes

| Méthode | Route | Description |
|---|---|---|
| POST | `auth/register/` | Inscription (particulier ou boutique). Connecte l'utilisateur. Crée la `Shop` si `account_type=boutique` |
| POST | `auth/login/` | `{identifier, password}` : e-mail ou téléphone béninois |
| POST | `auth/logout/` | Déconnexion |
| GET | `auth/me/` | `{user}` ou `{user: null}` |
| PATCH | `me/` | Mise à jour du profil |
| GET / PATCH | `shop/` | Boutique du compte connecté |

## Catalogue (cache public de 5 minutes pour marques et villes)

| Méthode | Route | Description |
|---|---|---|
| GET | `catalog/models/?q=&category=` | Autocomplétion, 10 résultats, alias inclus (`ip13`) |
| GET | `catalog/models/{slug}/` | Spécifications par défaut |
| GET | `catalog/brands/?category=` | Marques |
| GET | `catalog/processors/?q=` / `catalog/gpus/?q=` | Composants |
| GET | `catalog/cities/` | Villes |

## Annonces

| Méthode | Route | Description |
|---|---|---|
| GET | `listings/` | Recherche publique, filtres ci-dessous |
| POST | `listings/` | Crée un brouillon (connecté) |
| GET | `listings/{slug}/` | Fiche publique (compte une vue par session et par 30 minutes) |
| GET | `listings/{slug}/similar/` | Jusqu'à 6 annonces, même catégorie, prix à plus ou moins 20 % |
| GET / PATCH | `listings/{id}/` | Lecture et modification par le propriétaire |
| POST | `listings/{id}/photos/` | Multipart `image` + `kind` ; conversion WebP, EXIF supprimé, `phash` |
| DELETE | `listings/{id}/photos/{photo_id}/` | Supprime une photo |
| POST | `listings/{id}/publish/` | Publie. Erreurs détaillées par champ dans `fields` |
| POST | `listings/{id}/mark-sold/` · `archive/` | Changement d'état |
| POST | `listings/{id}/reveal-phone/` | Connecté. Renvoie le numéro, enregistre `phone_reveal` |
| POST | `listings/{id}/whatsapp/` | Connecté. Renvoie le lien `wa.me` pré-rempli |
| POST / DELETE | `listings/{id}/favorite/` | Favori |
| GET | `me/listings/` · `me/favorites/` | Mes annonces et favoris |
| GET | `shops/{slug}/` · `shops/{slug}/listings/` | Vitrine publique |
| POST | `listings/{id}/report/` | Connecté. `{reason, details}` : `scam`, `stolen`, `wrong_info`, `duplicate`, `other`. Un seul signalement par utilisateur ; trois utilisateurs différents remettent l'annonce en modération |

### Filtres de `GET listings/`

`q`, `category`, `brand` (slugs séparés par des virgules), `price_min`, `price_max`, `condition`, `grade`, `city` (slug ; la ville choisie d'abord, puis les villes proches), `ram_min`, `storage_min`, `storage_type`, `gpu_dedicated`, `keyboard`, `os`, `screen_min`, `screen_max`, `cpu_family`, `cpu_gen_min`, `battery_min`, `5g`, `dual_sim`, `unlocked`, `no_replaced_parts`, `cellular`, `stylus`, `verified`, `seller_type` (`shop` ou `individual`), `warranty`, `invoice`, `sort` (`relevance`, `price_asc`, `price_desc`, `recent`, `best_deal`), `page`.

`usage` (`office`, `study`, `dev`, `gaming`, `creative`, `battery` pour les PC ; `everyday`, `photo`, `gaming`, `battery`, `business` pour les mobiles) ne garde que les annonces dont le score d'usage est d'au moins 7. `secure_payment` est accepté dans l'URL mais n'a pas encore d'effet (paiement en phase 4).

### Règles de publication

- Photos : 4 à 10, dont face avant, face arrière et écran allumé ; une photo de défaut si la note est C.
- Smartphone et tablette : `account_removed` doit être vrai.
- Particulier : 5 annonces actives au maximum.
- Modèle hors catalogue : l'annonce passe en `pending_review`.
- IMEI : 15 chiffres avec clé de Luhn pour un smartphone ; numéro de série au format de la marque accepté pour les tablettes et les ordinateurs.
- À la publication, le moteur de risque calcule `risk_score` : moins de 40, l'annonce est `active` ; de 40 à 69, `pending_review` ; 70 ou plus, ou appareil déclaré volé, `pending_review` prioritaire. Les règles déclenchées sont dans `moderation_flags.risk_rules`.
- L'IMEI ou le numéro de série est chiffré en base et n'est jamais renvoyé par l'API.
## Prix et usages

| Méthode | Route | Description |
|---|---|---|
| POST | `pricing/estimate/` | `{device_model, storage_gb, ram_gb, condition_type, grade, battery_health_pct, price_fcfa}`. Renvoie `{available, low, mid, high, sample_size, indicative, badge}`, utilisé pendant la publication |

La fiche annonce renvoie `estimate_low` / `estimate_mid` / `estimate_high`, `estimate_indicative`, `price_badge`, `usage_scores` et `advised_usage`. Le badge n'existe que si l'estimation n'est pas indicative. Commande nocturne : `manage.py recompute_estimates`.

## Confiance

| Méthode | Route | Description |
|---|---|---|
| POST | `stolen-reports/` | Public. `{imei_or_serial, description, police_reference?}`. Seule une empreinte est conservée ; la déclaration doit être confirmée par un modérateur |
| POST | `me/identity/` | Connecté. Multipart `document` + `selfie` (image ou PDF, 8 Mo). Passe l'identité en `pending` |
| POST | `shop/verification/` | Compte boutique. Multipart `ifu`, `rccm`, `address`, `document` |
| GET | `private-files/{kind}/{id}/` | Modérateurs uniquement ; `kind` vaut `identity`, `selfie` ou `shop-document` |

La modération se fait dans le Django admin (`/admin/`) : « file de modération » triée par risque, approbation, refus, demande de modifications ; vérifications d'identité et de boutique ; déclarations d'appareils volés ; signalements. Commande quotidienne : `manage.py purge_verification_documents` (supprime les documents 90 jours après la décision).
## Intelligence artificielle

Sans `GROQ_API_KEY`, tout fonctionne en mode repli. Limites par heure (visiteur, connecté) : recherche 20/40, comparaison 5/10, assistant 10/20.

| Méthode | Route | Description |
|---|---|---|
| GET | `ai/status/` | `{model_available, voice_available}` |
| POST | `ai/search/` | F1. `{query}`. Renvoie `{filters, chips, confidence, used_ai}` ; `filters` est directement la query string de la recherche |
| POST | `ai/describe/` | F2. Connecté, propriétaire. `{listing_id}`. Renvoie `{title, description, highlights, used_ai}` |
| POST | `ai/voice/` | F3. Connecté. Multipart `audio` (60 s, 3 Mo). Renvoie les champs extraits ou `{available: false}` |
| POST | `ai/assistant/` | F4. `{listing_id, question, history: [questions]}`. Renvoie `{answer, information_missing, suggested_seller_question, used_ai}` |
| POST | `ai/compare/` | F5. `{ids: [2 à 3], usage?, budget?}`. Renvoie `{rows, verdict, listings, used_ai}` |
| GET | `ai/compare/suggestions/?listing_id=` | Deux alternatives choisies par Django |
| POST | `listings/{id}/whatsapp/` | accepte maintenant `{message}` (300 caractères) pour la question au vendeur |

F6 (anti-arnaque) n'a pas de route : elle ajoute de 0 à 25 points au score de risque à la publication (règle `ai_signal`) et ne bloque jamais seule. Chaque appel est journalisé dans `AIRequestLog` (visible dans l'admin).
## Paiement sécurisé (sandbox)

Tout est en mode test. Fournisseur choisi par `PAYMENT_PROVIDER` (`simulator` par défaut, `fedapay`). Commission : `ESCROW_COMMISSION_PCT` (3 %), minimum `ESCROW_COMMISSION_MIN_FCFA` (500), payée par le vendeur.

| Méthode | Route | Description |
|---|---|---|
| POST | `orders/` | `{listing_id, delivery_mode?, meetup_note?}`. Crée la commande (une commande « créée » de l'acheteur est réutilisée) |
| GET / PATCH | `orders/{id}/` | Acheteur, vendeur ou modérateur. Le GET interroge le fournisseur si un paiement est en attente. PATCH : mode de remise, avant paiement |
| POST | `orders/{id}/pay/` | `{operator: mtn\|moov\|celtiis, phone}`. En-tête `Idempotency-Key` facultatif |
| POST | `orders/{id}/handed-over/` | Vendeur : l'appareil est remis |
| POST | `orders/{id}/confirm/` | Acheteur : réception confirmée, fonds versés |
| POST | `orders/{id}/dispute/` | Acheteur : `{reason}` (10 caractères au moins) |
| POST | `orders/{id}/cancel/` | Acheteur, avant paiement |
| GET | `me/orders/` | Mes achats et mes ventes |
| GET | `payments/commission/?price=` | Commission et montant reçu par le vendeur |
| POST | `payments/webhooks/fedapay/` | Webhook signé (`X-FEDAPAY-SIGNATURE`), idempotent |
| POST | `orders/{id}/simulator-settle/` | Développement seulement : valide un paiement simulé resté en attente |

États : `created` → `payment_pending` → `paid_held` → `handed_over` → `released`, avec `disputed` (puis `released` ou `refunded`), `cancelled` et `refunded`. La commission n'est visible que du vendeur. Chaque transition est journalisée (`OrderEvent`). Le simulateur choisit le résultat selon la fin du numéro : `00` refusé, `77` validé après 5 secondes, `99` reste en attente, autre : validé.

Commande planifiée toutes les 15 minutes : `manage.py release_due_orders` (libération 48 h après la remise sans réaction de l'acheteur, annulation des commandes non payées après 30 minutes). Les litiges se tranchent dans l'admin Django, « Commandes » : verser au vendeur ou rembourser l'acheteur. Le filtre `secure_payment=1` ne garde que les annonces qui acceptent le paiement sécurisé.

## Boutique et analyse (phase 5)

Compte boutique obligatoire (`403` sinon). `IsProShop` est la seule barrière des routes Pro : le front affiche, il ne décide jamais. Les erreurs ont toujours la forme `{code, message, fields?}`, y compris les `403` et `404` de DRF.

| Méthode | Route | Plan | Description |
|---|---|---|---|
| GET | `shop/stats/?period=7\|30\|90` | tous | Vues, contacts, favoris, ventes, taux de contact, évolution, série par jour, tableau par annonce |
| GET | `shop/subscription/` | tous | Plan en vigueur, prix, historique ; règle un paiement en attente |
| POST | `shop/subscribe/` | tous | `{operator, phone}`. Un mois de Pro, plan actif dès le paiement réussi ; payer à nouveau prolonge d'un mois |
| POST | `shop/subscription/settle/` | tous | Développement seulement (numéro finissant par 99) |
| GET | `insights/demand/?period=7\|30` | aperçu | P1 : recherches par (catégorie, modèle, budget, ville) face à l'offre ; segments de 10 recherches au moins ; recommandations (Pro) |
| GET | `insights/pricing/` | aperçu | P2 : prix, estimation, écart, prix conseillé arrondi à 5 000 FCFA, activité face à la moyenne de la catégorie |
| GET | `insights/dormant/` | aperçu | P3 : annonces de plus de 14 jours sous la médiane de contact, causes par règles, corrections (Pro) |
| POST | `insights/listings/{id}/apply/` | Pro | `{price_fcfa?, title?, description?}` : applique un conseil |
| GET / POST | `insights/reports/` | Pro | P4 : liste ; génération immédiate |
| GET | `insights/reports/{id}/` | Pro | Détail d'un rapport |
| POST | `insights/chat/` | Pro | P5 : `{question}` ; réponse calculée par des fonctions prédéfinies limitées à la boutique, jamais de SQL |
| POST | `insights/bulk-optimize/` | Pro | P6 : `{listing_ids}` (1 à 50) ; propositions avant/après, rien n'est écrit |
| POST | `insights/bulk-optimize/apply/` | Pro | `{items: [{listing_id, title, description}]}` : n'écrit que ce qui est accepté |
| GET | `insights/competition/{listing_id}/` | Pro | P7 : les 3 annonces concurrentes les plus proches et les actions conseillées |

« Aperçu » : une boutique gratuite reçoit le premier élément seulement, avec `preview: true`, `total` et `hidden`, sans recommandations ni corrections. Les textes rédigés par le modèle sont rejetés s'ils contiennent un chiffre absent des données (repli sur un texte généré). Commandes planifiées : `send_weekly_reports` (lundi 8 h, heure de Porto-Novo) et `release_due_orders` (toutes les 15 minutes, termine aussi les abonnements échus).

## Alertes, facettes et partage (phase 6)

| Méthode | Route | Description |
|---|---|---|
| GET / POST | `me/alerts/` | Mes recherches enregistrées. POST : `{filters, name?, channel?}`. Les filtres ont le format des paramètres d'URL de la recherche ; seuls les paramètres connus sont gardés (ni page, ni tri). 10 alertes au plus ; la même recherche n'est pas enregistrée deux fois. `channel` : `email` (par défaut), `in_app`, `whatsapp` (l'envoi WhatsApp n'est pas branché : la notification interne reste) |
| PATCH / DELETE | `me/alerts/{id}/` | Pause (`is_active`), canal, nom ; suppression |
| GET | `me/notifications/` | `{unread, results}` : notifications internes, la plus récente d'abord |
| POST | `me/notifications/` | Marque tout comme lu |
| GET | `listings/facets/` | Mêmes paramètres que `listings/`. Compteurs par option : `category`, `brand`, `condition`, `grade`, `seller_type`, `flags` et `total`. Chaque groupe ignore son propre filtre, pour montrer ce que donnerait un autre choix |

Le filtre `warranty` accepte maintenant un nombre de mois (`warranty=6`) ; `warranty=1` reste « avec garantie ».

Commande planifiée toutes les 15 minutes : `manage.py send_alerts`. Pour chaque alerte active, elle cherche les annonces publiées depuis la dernière notification qui correspondent aux filtres (hors annonces de l'utilisateur lui-même), crée une notification, envoie l'e-mail si le canal est `email`, puis avance le curseur : relancer la commande n'envoie jamais deux fois.

Hors `/api/` : `/annonce/<slug>` et `/boutique/<slug>` renvoient l'`index.html` construit avec les balises Open Graph et Twitter de la page (titre, prix, ville, première photo). Les brouillons et les annonces retirées ne sont jamais exposés. Les autres routes renvoient l'`index.html` tel quel. Voir `docs/DEPLOYMENT.md`.