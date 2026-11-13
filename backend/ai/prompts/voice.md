---
version: 1
---
Un vendeur a dicté la description de son appareil. Tu en extrais les champs d'un formulaire d'annonce.

Règles strictes :
- Réponds uniquement avec un objet JSON des champs ci-dessous.
- Ne remplis que ce que le vendeur a dit. Ce qui n'est pas dit reste null (ou liste vide). N'invente rien.
- `model_text` : le nom du modèle tel que dit (« iPhone 12 », « Galaxy A54 »), sans la capacité.
- `category` : smartphone, tablet, laptop ou desktop.
- `storage_gb` et `ram_gb` en Go (1 To = 1024). `battery_health_pct` entre 1 et 100.
- `condition_type` : new_sealed, new_open, refurbished ou used.
- `grade` : A (comme neuf, aucun défaut), B (légères traces), C (traces visibles, fissure, défaut). Seulement si le vendeur décrit l'état.
- `accessories` : parmi charger, box, cable, case, earphones, invoice.
- `defects` : les défauts cités, avec les mots du vendeur.
- `price_fcfa` : un entier en FCFA, seulement si un prix est dit.

Champs : model_text, category, storage_gb, ram_gb, battery_health_pct, condition_type, grade, accessories, color, price_fcfa, defects.

Dictée : {{transcript}}
