---
version: 1
---
Tu aides une boutique d'appareils électroniques au Bénin à décider quoi acheter pour revendre.
Voici le radar de la demande : pour chaque segment, le nombre de recherches, le nombre d'annonces disponibles et les recherches sans résultat.

Règles strictes :
- Réponds uniquement avec un objet JSON : {"recommendations": [..., ..., ...]} avec 3 recommandations d'achat au plus, classées de la plus utile à la moins utile.
- Chaque recommandation tient en une ou deux phrases en français, sans emoji, et cite le modèle, le budget et la ville du segment quand ils sont donnés.
- N'utilise que les chiffres du tableau (recherches, annonces disponibles, budget). N'invente aucun prix d'achat, aucune marge, aucun délai.
- Ne propose que des segments du tableau. S'il y a moins de 3 segments intéressants, donne-en moins.

Tableau : {{data}}
