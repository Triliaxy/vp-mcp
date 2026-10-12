---
name: uml-vp
description: "Créer, modifier et rendre lisibles des diagrammes UML natifs dans Visual Paradigm avec vp-mcp. Appliquer les préférences de mise en page de l’utilisateur : aucun bloc titre/commentaire ajouté, attaches pertinentes, tracés orthogonaux courts et réduction des croisements. À utiliser pour les travaux UML dans VP, pas pour des diagrammes hors VP."
---

# UML dans Visual Paradigm

Produire des diagrammes UML natifs, lisibles et faciles à modifier manuellement. Utiliser le MCP Visual Paradigm disponible. Ces conventions reprennent les préférences de l’utilisateur ; une consigne explicite plus récente reste prioritaire.

## Présentation du canevas

- Ne pas ajouter de blocs de titre, bandeaux, cartouches de commentaires ou notes décoratives, notamment les blocs bleus et jaunes en haut ou en bas du diagramme. Nommer le diagramme dans VP ; placer les explications dans sa documentation ou dans le rapport associé.
- Lors d’une reprise, retirer les blocs de présentation concernés de la vue et conserver leur contenu utile dans la documentation. Ne pas supprimer silencieusement une contrainte UML portée par une note : conserver sa signification dans le modèle ou dans un emplacement adapté.
- Conserver les noms des classes, acteurs, cas d’utilisation et états, les compartiments, les gardes, multiplicités et rôles. L’interdiction des blocs décoratifs ne vise pas ces libellés ni les conteneurs UML nécessaires, tels que la frontière du système et les fragments de séquence.
- Organiser les éléments proches fonctionnellement à proximité, avec des alignements et des espaces suffisants pour les attaches et les textes. Éviter les cadres et couleurs qui ajoutent du bruit visuel.
- Conserver le périmètre et le nombre de diagrammes demandés. Si un modèle global unique est demandé, ne pas le remplacer par plusieurs diagrammes ou panneaux indépendants. Ne pas supprimer de classes, attributs ou relations pour obtenir une image plus simple.
- Préférer une occurrence par élément. Des références graphiques répétées ne sont une solution que si la demande les autorise ; elles doivent désigner le même objet UML et être reconnaissables.

## Routage des associations et autres connecteurs

Appliquer ces règles aux associations, généralisations, dépendances et transitions, en respectant la notation propre aux séquences.

1. Choisir les points d’attache en même temps que le tracé. Privilégier les côtés qui se font face. Ne pas conserver une attache sur le dessus d’un bloc si une attache latérale offre un trajet plus simple.
2. Préférer un segment horizontal ou vertical direct. Sinon, essayer un seul coude à 90°, puis deux si nécessaire. Conserver davantage de coudes seulement lorsqu’un obstacle, un libellé ou une relation voisine le justifie. Il s’agit d’un ordre de préférence, pas d’un plafond qui imposerait des croisements.
3. Utiliser des segments droits et des angles droits francs, sans courbes ni angles arrondis. Dans VP, activer le style rectiligne natif quand l’outil le permet ; fournir seulement une liste de points orthogonaux en mode oblique ne garantit pas leur maintien au rendu.
4. Rechercher et éliminer les détours en U, petits décrochements, retours en arrière et contournements inutiles. Tester d’autres bords d’arrivée et de départ avant d’ajouter des points de passage.
5. Ne pas traverser les blocs ou leurs textes. Écarter les attaches voisines pour distinguer les relations, flèches, losanges et multiplicités. Éviter de superposer des associations distinctes sur un même segment.
6. Réduire les croisements en ajustant ensemble la disposition des blocs, les côtés d’attache et les couloirs de passage. Un trajet plus court n’est pas meilleur s’il crée des croisements ou rend une relation ambiguë. Ne pas déplacer toute une vue pour corriger un défaut local si une correction limitée suffit.
7. Conserver les véritables relations réflexives et transitions vers le même état. Dans les séquences, conserver les appels à soi-même, l’ordre des messages, les activations et les fragments. Une boucle ayant un sens UML ne doit pas être confondue avec un détour graphique inutile.

Exemple : si `Formule` est au-dessus d’`Abonnement`, une liaison verticale entre le bas de `Formule` et le haut d’`Abonnement` peut suffire. Une autre classe située à gauche peut rejoindre le côté gauche d’`Abonnement`, plutôt que passer sur son dessus et croiser la première liaison. Choisir selon la géométrie réelle, sans imposer cette disposition à tous les modèles.

## Travail dans VP

- Inspecter le projet actif et les diagrammes avant modification. Partir des objets existants, conserver leurs identifiants et distinguer modèle UML et occurrence graphique. Sauvegarder une version récupérable avant une reprise importante.
- Pour une modification de présentation, préserver la sémantique : types de relations, extrémités métier, sens des flèches, rôles, multiplicités, compositions, gardes et contenu. Ne pas recréer le modèle à partir de son apparence.
- Utiliser les outils MCP disponibles pour placer les formes, régler les attaches et tracer les connecteurs, puis positionner les libellés après stabilisation de la géométrie. Lire [la référence vp-mcp](references/vp-mcp.md) pour les paramètres de l’extension et ses particularités.
- Si une capacité manque, identifier précisément la limite. Ne pas prétendre l’avoir exécutée et ne pas passer silencieusement à Computer Use. Une extension du MCP est un travail distinct à entreprendre lorsque la demande l’autorise.
- Pour un travail de conception UML, utiliser également `uml-diagrams` s’il est disponible ou expressément demandé, afin de respecter ses conventions de modélisation. La présente compétence complète ces conventions par les règles de présentation VP ; une simple mise en page ne nécessite pas de recréer les sources PlantUML.

## Vérification avant livraison

### Outils Python réutilisables

Lire [le mode d’emploi des scripts](references/scripts.md) pour automatiser une reprise. Les scripts fonctionnent hors ligne sur des snapshots JSON avec Python 3.10 ou ultérieur, sans dépendance externe. Ils produisent des propositions et des rapports ; les mutations restent effectuées par les outils MCP natifs.

- `vp_layout.py simplify` : proposer des attaches et tracés plus simples sans augmenter les croisements calculés ni les superpositions de segments. Préserver les relations réflexives et traiter les séquences séparément.
- `vp_layout.py labels` : proposer le repositionnement des libellés et multiplicités sans renommer les objets ni réécrire leurs textes.
- `vp_layout.py audit` : mesurer la géométrie ; avec `--after`, comparer aussi les identifiants, types, noms et extrémités des relations. Compléter par les détails métier absents du snapshot.
- `vp_layout.py check-plan` : refuser une proposition périmée ou des opérations étrangères à la présentation, puis produire les arguments de `editDiagramViews`.
- `vp_layout.py inspection-plan` : calculer des recadrages des zones modifiées à partir d’une correspondance canevas/image vérifiée. Ces recadrages doivent être exportés puis réellement examinés.

Utiliser l’ordre **snapshot → proposition → contrôle sur snapshot frais → application MCP → nouveau snapshot → libellés → audit et inspection visuelle → sauvegarde**. Ce contrôle n’ajoute pas de demande de confirmation lorsque la modification est déjà autorisée. Ne pas appliquer une proposition dont le diagramme source a changé ; la recalculer. Après une application partielle ou un échec MCP, inspecter l’état réel avant toute reprise.

Examiner un export natif d’ensemble, puis des recadrages lisibles des zones modifiées et denses. Après une correction, réexaminer le rendu correspondant. Une exportation réussie ou un audit géométrique seul ne valide pas la lisibilité.

Contrôler les points suivants selon le travail effectué :

- Absence de blocs décoratifs titre/commentaire ajoutés.
- Absence de chevauchements de formes et de passages à travers des blocs étrangers.
- Attaches sur des côtés pertinents, segments orthogonaux, absence de détours évitables ; relations voisines distinguables.
- Noms, gardes, rôles et multiplicités lisibles, proches de la bonne relation et sans collision gênante avec les traits.
- Conservation des éléments et relations UML ; périmètre global préservé si demandé.
- Pour les séquences : temps vertical, messages horizontaux, appels à soi-même et fragments cohérents.

Les croisements peuvent rester nécessaires dans un modèle dense. Comparer avant et après avec une méthode constante si des chiffres sont annoncés ; distinguer croisements entre lignes, superpositions de segments et collisions avec les textes. Ne jamais affirmer « aucun croisement » ou « lisibilité validée » sans contrôle correspondant réellement exécuté.

Sauvegarder le projet VPP et actualiser les exports touchés après les dernières modifications. Présenter le résultat avec des liens vers les fichiers et les limites constatées. Si des sources PlantUML antérieures ne reproduisent plus la disposition VP, l’indiquer clairement.
