# API

Prefixe : `/api/`. Reponses paginees : `{count, next, previous, results}`. Erreurs : `{code, message, fields?}` en francais.

Cette page sera completee phase par phase. Etat actuel (phase 0) :

| Methode | Route | Description |
|---|---|---|
| GET | `/api/health/` | Sonde de disponibilite : `{"status": "ok"}` |
| GET | `/api/auth/csrf/` | Pose le cookie CSRF lu par le front pour les requetes non sures |