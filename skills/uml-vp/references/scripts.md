# Scripts hors ligne pour les diagrammes VP

Les fichiers `scripts/vp_layout.py`, `vp_geometry.py` et `vp_routing.py` utilisent seulement la bibliothèque standard de Python 3.10+. Ils ne contactent aucun serveur, ne modifient aucun projet et n’installent aucune dépendance. Les commandes suivantes se lancent depuis le dossier du skill ; remplacer `python` par l’interpréteur disponible si nécessaire. Les sorties refusent d’écraser un fichier existant : choisir un nom de révision distinct.

## Capturer et auditer

Avec le MCP, vérifier `getProjectInfo`, choisir le diagramme puis enregistrer le résultat JSON de `getDiagramSnapshot` dans `avant.json`. Utiliser l’objet décodé avec `diagramId`, `name`, `type` et `elements`, pas l’enveloppe JSON-RPC ou le tableau de blocs MCP. Conserver aussi les détails des relations et des éléments métier lorsqu’une préservation sémantique complète doit être vérifiée.

```bash
python scripts/vp_layout.py audit avant.json --output audit-avant.json
```

Le rapport compte les intersections par paire de connecteurs, hors points d’attache communs au même élément. Les superpositions collinéaires sont mesurées séparément en longueur. Il signale également segments diagonaux, traversées de formes, chevauchements de formes, passages sur certaines légendes et extrémités manquantes.

Les rectangles de classes et états sont des approximations des contours. Les emboîtements de conteneurs, la géométrie particulière des séquences et toutes les collisions de texte ne sont pas analysés exhaustivement. Les légendes des classes peuvent avoir des coordonnées locales : elles ne sont pas traitées comme des légendes absolues de connecteurs.

## Proposer un tracé

```bash
python scripts/vp_layout.py simplify avant.json --output proposition-traces.json
```

L’algorithme teste différentes attaches et des chemins comportant zéro, un ou deux coudes. Il rejette les passages dans les formes, les attaches trop proches et les candidats qui augmentent le nombre de croisements calculés, les superpositions collinéaires, la longueur ou les coudes. Il conserve les boucles réflexives. Les séquences sont reconnues par leur type et leurs éléments, sans dépendre du nom du diagramme, et sont laissées à un traitement spécifique.

Les positions des blocs restent inchangées. Ce simplificateur local ne remplace pas un travail de disposition générale : il peut ne trouver aucune amélioration alors qu’un déplacement de classes aiderait. Les connecteurs déjà diagonaux, les formes non prises en charge et les séquences sont ignorés et signalés. L’audit reste disponible sur ces données.

Options : `--passes` de 1 à 10, `--candidate-limit` de 1 à 2000, `--clearance` de 0 à 100 unités du canevas. Valeurs par défaut : 3, 180, 10. Le résultat contient les opérations proposées, l’empreinte du snapshot, les mesures initiales et les mesures géométriques prédites. Les mesures prédites ne sont pas une validation d’un rendu VP.

## Contrôler puis appliquer avec le MCP

Relire `getDiagramSnapshot` immédiatement avant la modification et enregistrer `courant.json`.

```bash
python scripts/vp_layout.py check-plan proposition-traces.json --current courant.json --output arguments-traces.json
```

Cette commande compare l’empreinte complète du snapshot, indépendamment de l’ordre des éléments. Elle vérifie l’identité du diagramme, limite les opérations aux tracés et libellés, contrôle l’orthogonalité et la cohérence des ratios d’attache avec les points extrêmes. Une différence d’état refuse la proposition : la recalculer, même si le changement semble seulement lié au rendu VP.

Le résultat fournit `diagramName` et `editsJson`, à passer à **`editDiagramViews`** avec les outils MCP disponibles. Aucune application automatique n’est effectuée par le script. Une liste vide n’exige aucun appel d’édition. L’extension locale accepte au plus 1000 opérations : pour un grand plan, traiter des sous-ensembles avec un nouveau snapshot et une nouvelle proposition entre les lots. Ne pas fabriquer une succession de lots sur une empreinte devenue périmée.

La vérification ne verrouille pas VP. Éviter toute modification concurrente entre le contrôle et l’application. Les appels d’édition ne sont pas transactionnels : après un échec ou une réponse ambiguë, inspecter le diagramme et recalculer ; ne pas rejouer aveuglément le lot.

## Repositionner les libellés

Après les tracés, récupérer un nouveau snapshot dans `apres-traces.json` :

```bash
python scripts/vp_layout.py labels apres-traces.json --output proposition-libelles.json
```

Contrôler cette proposition avec `check-plan` sur un snapshot frais, puis appliquer les arguments MCP obtenus. Le placement réutilise les dimensions des rectangles existants et cherche une position moins encombrée. Il ne modifie ni noms métier, ni texte, ni police. Les libellés absents, invisibles, sans dimensions utiles et ceux des messages de séquence sont laissés en place. Vérifier les dimensions et la lisibilité sur l’image ; la méthode ne mesure pas les glyphes ni toutes les multiplicités absentes du snapshot.

## Comparer et inspecter

```bash
python scripts/vp_layout.py audit avant.json --after apres.json --output comparaison.json
```

La commande retourne le code 2 si les identifiants de vues/modèles, types, noms ou modèles aux extrémités des relations ont changé. Une modification de présentation conserve ces données. Ce contrôle ne prouve pas à lui seul la conservation des attributs, rôles, multiplicités et gardes absents du snapshot : comparer aussi les détails métier récupérés auprès du MCP.

Pour préparer les recadrages, déterminer d’abord les dimensions de l’image exportée, l’échelle native et l’origine réelle du canevas dans l’image. Ne pas supposer que les coordonnées du canevas sont celles de l’image. L’exemple suivant n’est valide que si l’origine `(100, 80)`, l’échelle `1` et l’image `3000 × 2200` ont été vérifiées :

```bash
python scripts/vp_layout.py inspection-plan apres.json --plan proposition-traces.json --origin-x 100 --origin-y 80 --scale 1 --image-width 3000 --image-height 2200 --size 1200 --output cadrages.json
```

La conversion est `pixel = (coordonnée_canevas - origine_canevas) × échelle`. Les recadrages ciblent les extrémités des relations modifiées et sont limités aux dimensions de l’image. Ils complètent la vue d’ensemble ; ils ne couvrent pas nécessairement le milieu d’une très longue relation. Si l’origine ne peut pas être établie, utiliser les recadrages du MCP directement à partir de l’image inspectée.

Appeler `inspectDiagramImage` pour les cadrages utiles et ouvrir réellement les images retournées. Corriger les défauts visibles, réexporter et sauvegarder le VPP uniquement après les derniers ajustements.

## Tests

```bash
python -m unittest discover -s scripts -p "test_*.py" -v
```

Les tests couvrent la suppression d’un détour, les obstacles, les relations réflexives, les séquences, les diagonales, les intersections et superpositions, les plans périmés, les opérations interdites, la cohérence des attaches, la conservation des textes, le cadrage et la préservation des fichiers de preuve. Ils ne nécessitent pas VP et ne modifient pas le projet ouvert.
