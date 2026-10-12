# Particularités de l’extension vp-mcp

Cette référence décrit les capacités utilisées sur l’installation locale de l’utilisateur. Découvrir les outils et leurs schémas réels au début du travail : une autre version du serveur peut ne pas exposer ces fonctions. Ne pas supposer un port réseau ou un chemin de projet fixe.

## Outils utiles

| Outil | Utilisation |
|---|---|
| `getProjectInfo`, `listDiagrams` | Vérifier le projet actif et choisir les diagrammes concernés. |
| `getDiagramSnapshot` | Inventorier modèles, occurrences, positions, polices, tracés et libellés. |
| `getRelationshipDetails` | Inspecter les propriétés sémantiques des associations, dont les multiplicités. |
| `editDiagramViews` | Éditer précisément les vues par identifiants stables. |
| `inspectDiagramImage` | Obtenir un export natif ou un recadrage sous forme de véritable image MCP. |
| `auditDiagramReadability` | Repérer chevauchements de formes, petites polices, connecteurs orphelins et passages à travers des formes. |
| `exportDiagramImage`, `saveProject` | Actualiser les images livrées et enregistrer le projet. |

Les outils automatiques `autoLayoutDiagram`, `rerouteConnectors` et `layoutConnectorLabels` peuvent remplacer un travail manuel fin. Ne pas les appeler systématiquement après une correction locale. Le reroutage centre à centre ne constitue pas une solution de réduction des croisements.

## Édition des connecteurs

Dans la version étendue, `editDiagramViews` reçoit `diagramName` et `editsJson`, ce dernier étant une chaîne JSON contenant un tableau d’opérations. Exemple schématique, à adapter à des identifiants et rectangles inspectés :

```json
[
  {
    "op": "connector",
    "viewId": "IDENTIFIANT_REEL_DU_CONNECTEUR",
    "points": [[400,300],[700,300],[700,500]],
    "fromPin": [1,0.5],
    "toPin": [0.5,0],
    "orthogonal": true
  }
]
```

- `points` utilise les coordonnées du canevas VP. Les points extrêmes doivent correspondre aux attaches indiquées et à la géométrie réelle des formes.
- `fromPin` et `toPin` sont des ratios `[x,y]` dans la forme, entre 0 et 1. Exemples : gauche `[0,0.5]`, droite `[1,0.5]`, haut `[0.5,0]`, bas `[0.5,1]`. Les acteurs, ellipses et pseudo-états nécessitent un contrôle de leur contour effectif.
- `orthogonal: true` utilise `IConnectorUIModel.CS_RECTI_LINEAR` et demande la reconstruction du connecteur dans l’extension locale. Vérifier sa disponibilité ; ne pas supposer que tous les serveurs vp-mcp le gèrent.
- Le mode oblique peut déplacer des points au rendu et introduire des segments diagonaux. Relire le snapshot et vérifier l’image après application du style natif.
- Un changement de côté d’attache modifie la géométrie, pas les objets `from` et `to` de la relation UML. Conserver le sens de la relation, en particulier pour les généralisations et les compositions.
- Les lots sont séquentiels et non transactionnels. Si un appel échoue, inspecter les opérations déjà appliquées avant de réessayer ; ne pas répéter aveuglément les créations.

## Étiquettes et vues

L’opération `labels` accepte des rectangles `[x,y,largeur,hauteur]` pour `caption`, `multA` et `multB`. Les libellés des connecteurs et acteurs utilisent des coordonnées absolues ; les compartiments des classes peuvent utiliser des coordonnées locales. La modification du tracé peut déplacer les libellés : finaliser ceux-ci après les attaches et vérifier le résultat.

`style` peut régler notamment `fontSize` et `captionSide`. L’extension locale utilise le côté libre natif pour les placements explicites. Préférer les paramètres documentés par la version réellement installée plutôt que recopier des constantes sans vérifier leur sens.

`removeView` supprime une occurrence graphique, tandis que certains outils de suppression de relations agissent sur le modèle. Pour enlever un commentaire décoratif, viser sa vue et conserver sa documentation utile. `duplicateView` garde le même `modelId` mais ajoute une occurrence ; ne l’utiliser que lorsque cette représentation convient à la demande.

## Vision et contrôle

Exemple de recadrage :

```json
{"diagramName":"Nom du diagramme","x":600,"y":300,"width":1400,"height":1000,"maxDimension":1600,"scale":1}
```

Dans `inspectDiagramImage`, `x`, `y`, `width` et `height` désignent des pixels de l’image native exportée, avant réduction, et non les coordonnées du canevas UML. Un décalage est donc possible. `width=height=0` sélectionne l’image entière. Lire les dimensions retournées et conserver une échelle permettant de lire les textes.

La vision repose sur la lecture effective de l’image par l’assistant ; le serveur ne juge pas seul la lisibilité. Un chemin retourné par un export doit être ouvert avec un outil de lecture d’image pour être inspecté. Le retour image du MCP local a été utilisé ; le fonctionnement multimodal d’un éventuel proxy Docker doit être vérifié séparément.

Les audits géométriques restent des heuristiques. Ils ne couvrent pas tous les libellés, croisements et superpositions. Pour compter des croisements, annoncer la méthode et ne pas confondre attaches communes, croisements de relations distinctes et segments collinéaires superposés.
