# Fly-in : récap des fixs et problèmes

## 1. Fixs effectués

| # | Problème | Cause | Fix | Statut |
|---|---|---|---|---|
| 1 | Chemins plus longs jamais utilisés (`long_path` : 11 tours) | Le glouton `Simulator` n'avance que vers une zone strictement plus proche de la fin | Nouvelle classe `Solver` (`engine/solver.py`) : `Network` → `SpaceTimeScheduler` → `Simulation` → `OutputFormatter`, branchée dans `app.py` | Fait : 7 tours |
| 2 | Deux drones dans une zone restricted de capacité 1 | `_inside` n'était incrémenté qu'à l'atterrissage, pas au décollage | Réserver la place dès le décollage (`Simulator._move`) | Résolu par le `Solver` (le planificateur vérifie `zone_free(dest, turn + 2)`) |
| 3 | Nom du vol incohérent (`D1-roof-hub` refusé par le checker) | Le label suivait l'ordre de déclaration de la connexion | Label `f"{src}-{dest}"` (origine-destination) dans `Simulation._movement` | Fait : `D1-hub-roof` |
| 4 | `NoPathError` / `SimulationError` non attrapées (traceback) | Elles héritent de `FlyInError`, pas de `ValueError` | `except (ValueError, FlyInError)` dans `app.py` | Fait |
| 5 | Viewer 2D affichait la simulation du glouton | `simulation_adapter.py` appelait encore `Simulator` | Remplacé par `Solver().solve(data)` | Fait (`grep` propre) |
| 6 | Tests testaient le glouton | `test_logic.py`, `check_maps.py` utilisaient `Simulator` | Migrés vers `Solver` | Fait : 112 tests OK |
| 7 | Sortie non vérifiée avant affichage | Le plan n'était pas rejoué | `OutputChecker(data).check(lines)` dans `Solver.solve` | Ajouté (code fourni, à vérifier dans `solver.py`) |
| 8 | Fonctionnalité : maps déposées dans le dossier listées automatiquement | Liste figée | `MapCatalog` (`map_catalog.py`) : scan du dossier, validation par `MapParser`, nom sans `.txt` | Fichier et test présents dans l'arbre |

## 2. Résultats sur les maps du sujet

| Niveau | Map | Cible | Résultat |
|---|---|---|---|
| Easy | linear_path | ≤ 6 | 4 |
| Easy | simple_fork | ≤ 8 | 4 |
| Easy | basic_capacity | ≤ 6 | 4 |
| Medium | dead_end_trap | ≤ 12 | 8 |
| Medium | circular_loop | ≤ 15 | 15 |
| Medium | priority_puzzle | ≤ 12 | 7 |
| Hard | maze_nightmare | ≤ 30 | 13 |
| Hard | capacity_hell | ≤ 35 | 16 |
| Hard | ultimate_challenge | ≤ 45 | 26 |
| Challenger | impossible_dream | battre 45 | **43** |

Temps de calcul de la map à 25 drones : ~0,04 s.

## 3. Problèmes rencontrés

| Problème | Explication | Solution |
|---|---|---|
| Toujours 11 tours après le fix | Le moteur donnait bien 7 ; le viewer utilisait encore le glouton | Test direct de `Solver` en ligne de commande, puis migration du viewer |
| `grep ... --include=*.py` : `no matches found` | zsh développe `*.py` lui-même | Mettre `"*.py"` entre guillemets |
| 9 tests en échec après la migration | Mes maps de test (`fix_*.txt`) étaient dans `maps/` avec les maps officielles | `mv maps/fix_*.txt tests/maps/` |
| `tests_checker.py` jamais lancé par pytest | Le nom ne commence pas par `test_` | Renommer en `test_checker.py` |
| Traceback en testant le checker à la main | Appel direct sans `try/except` | Normal : `app.py` attrape le `ValueError` et affiche `Error: ...` |

## 4. Choix d'interprétation à documenter (README)

- **A1** : un vol vers une restricted occupe la connexion pendant les deux tours (`rules.py`).
- **A2** : la capacité d'un lien est partagée entre les deux sens.
- Ces choix influencent les résultats (surtout le 43 du challenger) : à justifier avec le sujet (« le drone occupe la connexion pendant le transit »).

## 5. Reste à faire

1. Renommer `tests/tests_checker.py` en `tests/test_checker.py`.
2. Petits points du parser (entiers stricts, `nb_drones :`, noms avec crochets, docstrings, paramètre `cur` inutilisé) : prompt prêt, non confirmé.
3. Supprimer le code mort : `Simulator`, `pathfinding.py`, double Dijkstra, `ENTRY_COST` en 3 exemplaires.
4. Parser orienté objet (classes au lieu de fonctions de module).
5. Vérifier si `maps/00_restricted_zone_check.txt` vient du sujet ; sinon la déplacer dans `tests/maps/`.
6. Rédiger le README (algo, complexité, visuel, A1/A2, usage de l'IA).