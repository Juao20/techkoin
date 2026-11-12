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