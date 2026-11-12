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

### Filtres de `GET listings/`

`q`, `category`, `brand` (slugs séparés par des virgules), `price_min`, `price_max`, `condition`, `grade`, `city` (slug ; la ville choisie d'abord, puis les villes proches), `ram_min`, `storage_min`, `storage_type`, `gpu_dedicated`, `keyboard`, `os`, `screen_min`, `screen_max`, `cpu_family`, `cpu_gen_min`, `battery_min`, `5g`, `dual_sim`, `unlocked`, `no_replaced_parts`, `cellular`, `stylus`, `verified`, `seller_type` (`shop` ou `individual`), `warranty`, `invoice`, `sort` (`relevance`, `price_asc`, `price_desc`, `recent`, `best_deal`), `page`.

`usage` et `secure_payment` sont acceptés dans l'URL mais n'ont pas encore d'effet (scores d'usage en phase 2, paiement en phase 4).

### Règles de publication

- Photos : 4 à 10, dont face avant, face arrière et écran allumé ; une photo de défaut si la note est C.
- Smartphone et tablette : `account_removed` doit être vrai.
- Particulier : 5 annonces actives au maximum.
- Modèle hors catalogue : l'annonce passe en `pending_review`.
- L'IMEI ou le numéro de série est chiffré en base et n'est jamais renvoyé par l'API.