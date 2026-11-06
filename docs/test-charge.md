# Test de charge du parcours de réservation

Le fichier `locustfile.py` simule une visite complète : accueil, connexion par email,
profil authentifié, recherche de dates disponibles, consultation de 1 à 3 logements,
lecture des conditions, réservation, instructions de virement, consultation de la
réservation, puis déconnexion. Pauses de 2 à 6 secondes entre les étapes.
Chaque nouvelle visite refait la connexion. Les comptes sont réservés exclusivement
à un utilisateur virtuel pendant sa durée de vie.

La réservation créée est **en attente de virement**, comme dans l'application.
Aucun paiement ni validation administrateur n'est simulé. Les identifiants des
logements et réservations sont découverts dans les réponses, sans ID fixe.
Les POST utilisent les jetons CSRF des formulaires et le Referer ; un HTTP 200
sur un POST refusé compte comme un échec. Les redirections sont vérifiées et les
pages suivantes sont chargées séparément pour distinguer leurs temps de réponse.

## Préparation

Utiliser une instance de test avec des appartements disponibles et des comptes
clients actifs ayant un mot de passe local. Prévoir au moins autant de comptes
que d'utilisateurs simultanés ; éviter les administrateurs. Préférer les clients
réguliers, car les clients FM6 ont un quota annuel de nuitées.

```bash
venv/bin/python -m pip install -r requirements-loadtest.txt
```

Créer `loadtest-users.csv` à la racine avec les identifiants de ces comptes existants :

```csv
email,password
charge001@example.test,mot-de-passe-du-compte-001
charge002@example.test,mot-de-passe-du-compte-002
```

Ce fichier est ignoré par Git. Il ne crée pas les comptes dans Django.
`LOADTEST_USERS_CSV` permet de choisir un autre fichier. Une configuration CSV
absente/invalide empêche le démarrage des utilisateurs ; un manque de comptes
produit une erreur `CONFIG` et arrête les utilisateurs excédentaires.

## Lancement

Démarrer l'application séparément, puis lancer l'interface Locust :

```bash
LOADTEST_CANCEL=1 venv/bin/locust -f locustfile.py --host http://127.0.0.1:8000
```

Ouvrir http://localhost:8089, commencer à 5 utilisateurs et 1 nouvel utilisateur
par seconde. Augmenter ensuite par paliers (10, 25, 50, 100…) pendant plusieurs
minutes chacun. Le CSV doit couvrir le palier maximal.

Exemple sans interface, 50 utilisateurs, montée de 2 utilisateurs/seconde, 10 minutes :

```bash
mkdir -p loadtest-results
LOADTEST_CANCEL=1 venv/bin/locust -f locustfile.py \
  --host http://127.0.0.1:8000 --headless \
  --users 50 --spawn-rate 2 --run-time 10m --stop-timeout 120 \
  --csv loadtest-results/run --html loadtest-results/rapport.html
```

`LOADTEST_CANCEL=1` annule les réservations créées à la fin du parcours pour
libérer les dates et quotas. Cela ajoute des requêtes d'annulation à la charge,
et conserve les lignes annulées en base. Sans cette option, les réservations
restent en attente et bloquent les dates pendant 24 heures. Une interruption
brutale ou une panne peut laisser des réservations en attente même avec l'option.
Restaurer les données de test entre campagnes pour comparer les résultats.

Les dates sont choisies entre J+7 et J+365, pour 2 à 5 nuits, hors août réservé
aux FM6. Après trois recherches sans résultat, une erreur `BUSINESS` signale
l'épuisement du stock. Des réservations concurrentes peuvent aussi être refusées
entre la recherche et la confirmation : consulter les logs du serveur pour
distinguer conflits de disponibilité, quotas et erreurs techniques.

## Interprétation

Surveiller les percentiles p95/p99, le débit, les erreurs et surtout la ligne
`09 Création réservation`, ainsi que CPU, mémoire, connexions et verrous SQL.
Définir un objectif avant le test (par exemple p95 < 2 s et erreurs < 1 %).
La capacité correspond au dernier palier stable respectant cet objectif, avec
des réservations effectivement créées ; beaucoup de recherches sans stock ne
prouvent pas la capacité du parcours complet.

Pour estimer la capacité de déploiement, utiliser le serveur applicatif et la
base de données du déploiement, pas seulement `manage.py runserver`/SQLite.
Idéalement, exécuter Locust sur une autre machine et vérifier que le générateur
n'est pas lui-même saturé. Chaque worker distribué doit recevoir un CSV distinct
via `LOADTEST_USERS_CSV` : le pool de comptes est local à chaque processus.

Ce scénario mesure les pages HTTP dynamiques : il n'exécute pas JavaScript et ne
charge pas automatiquement CSS, images ou polices. Il ne mesure donc pas le
temps d'affichage d'un navigateur. Voir la [documentation Locust](https://docs.locust.io/en/stable/writing-a-locustfile.html).
