# Performance et accessibilité

Mesures Lighthouse 12, profil mobile par défaut (écran 412 px, CPU ralenti 4x, réseau 4G simulé), sur le build de production servi par `vite preview` avec les données de démonstration. Seuil de la phase 6 : 90 ou plus en performance et en accessibilité.

| Page | Performance | Accessibilité | Bonnes pratiques | SEO | LCP | CLS |
|---|---|---|---|---|---|---|
| accueil | 97 | 100 | 100 | 100 | 2.1Â s | 0 |
| resultats | 92 | 100 | 100 | 100 | 3.0Â s | 0.003 |
| fiche | 96 | 100 | 100 | 100 | 2.6Â s | 0 |

Ce qui a été corrigé pour y arriver : les premières photos d'une page se chargent tout de suite (les autres restent différées), le pied de page ne bouge plus quand le contenu arrive, les liens et menus réduits à une icône ont un nom accessible, la liste de résultats a un titre de niveau 2, et `robots.txt` existe.

JS initial : 85 Ko gzip (seuil de la spécification : 180 Ko). Chaque page est un morceau séparé chargé à la demande.

## Refaire la mesure

```powershell
cd frontend
npm run build
npx vite preview --port 4173            # dans un autre terminal
npx lighthouse http://localhost:4173/ --only-categories=performance,accessibility,best-practices,seo
```

Sous Windows, si Lighthouse ne peut pas lancer Chrome lui-même, démarrer Chromium de Playwright avec `--remote-debugging-port=9222` et ajouter `--port=9222` à la commande.

## Limites

La mesure vient d'une machine de développement avec la base de démonstration, sans CDN ni compression Brotli du serveur : elle sert de garde-fou, pas de promesse sur une connexion 3G réelle. À refaire sur le serveur de production.