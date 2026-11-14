# Accès à la base

Les listes client affichent 12 réservations par page ; notifications, appartements
administratifs et périodes de vacances affichent 20 éléments. Réservations et
paiements administratifs étaient déjà paginés à 20 éléments. Le tri inclut la clé
primaire pour départager les dates/titres identiques. Les liens administratifs
conservent les filtres de recherche. Les compteurs client sont des agrégats SQL
sur l'historique complet.

Le préchargement SQL des photos est limité **par appartement** : trois pour les
cartes de recherche, une pour les réservations et la liste administrative.
Django utilise `ROW_NUMBER()` pour cette limite, avant de matérialiser les objets.
La galerie de détail conserve toutes ses photos.

## Déploiement et diagnostic

```sh
venv/bin/python manage.py migrate
venv/bin/python manage.py profile_queries --client-id 123 --repeat 10
# Facultatif : intervalle de disponibilité étudié
venv/bin/python manage.py profile_queries --client-id 123 --date-debut 2027-01-01 --date-fin 2027-01-02
```

Remplacer 123 par un identifiant client représentatif. La commande n'écrit aucune
donnée ; elle mesure les requêtes de listes (exécution et lecture des résultats,
sans cache ORM), affiche médiane/maximum et les plans `EXPLAIN`. Les mesures de
listes n'incluent pas le rendu HTML ni toutes les requêtes annexes d'une page.
Comparer avant/après migration sur une copie représentative de la base cible.
Les index ciblent le tri chronologique, les filtres client/statut, la recherche
de conflits de réservation et l'ordre des photos. Ils ne visent pas les recherches
`icontains`, pour lesquelles un index B-tree ordinaire ne suffit pas.

`DB_SLOW_QUERY_MS=200` journalise les exécutions SQL HTTP dépassant 200 ms via
`core.slow_queries`, y compris avec `DEBUG=False`. Le journal contient la durée,
l'alias de base, le nom de vue et une empreinte SQL ; il ne contient ni SQL brut,
ni paramètres, ni URL utilisateur. Régler `DB_SLOW_QUERY_MS=0` désactive la mesure.
Le seuil porte sur chaque exécution, pas sur le temps total de la page ou de lecture
du curseur. Les tâches hors HTTP ne passent pas par ce middleware.

## Mesure synthétique locale du 14 novembre 2026

Reproduction sans toucher aux données locales (SQLite en mémoire) :

```sh
venv/bin/python tools/benchmark_database.py
```

Jeu de données : 100 clients, 200 appartements, 4 000 photos, 20 000 réservations
et 20 000 notifications. Dix passages par requête, mêmes données, index ajoutés
retirés puis recréés. Médianes en millisecondes :

| Requête | Avant index | Après index |
| --- | ---: | ---: |
| Réservations administratives, 20 lignes | 10,406 | 0,630 |
| Réservations en attente, 20 lignes | 7,620 | 0,566 |
| Réservations client, 12 lignes | 0,618 | 0,465 |
| Notifications, 20 lignes | 0,494 | 0,387 |
| Photos, 3 lignes | 0,298 | 0,276 |

Les plans suppriment le tri temporaire des listes et utilisent les nouveaux index.
Le plan de disponibilité utilise `resa_apt_dispo_idx` ; celui des identifiants de
notifications non lues utilise `notif_client_lue_idx`. Les petits écarts de durée
ne constituent pas une preuve de gain en production. PostgreSQL n'était pas
accessible pendant cette intervention : migrations non appliquées à la base
configurée, mesures PostgreSQL à effectuer sur l'environnement cible.

Validation : suite Django existante (111 tests, dont 3 ignorés sur SQLite) et
six tests dédiés à la pagination, aux compteurs globaux, à l'isolation client,
aux limites SQL de photos et au journal des requêtes lentes.
