# Test de charge : sessions persistantes et 30 % de réservants

## Scénario

Chaque utilisateur virtuel prend un compte CSV exclusif, se connecte **une seule
fois dans `on_start`**, puis conserve ses cookies jusqu'à son arrêt. Les parcours
ne vident plus les cookies et ne déconnectent plus l'utilisateur. Une connexion
refusée arrête cet utilisateur sans boucle de nouvelles tentatives : vérifier
que le nombre d'utilisateurs actifs atteint bien le palier demandé.

Deux classes pondérées définissent le mélange :

- `BrowsingUser`, poids 7 : accueil, recherche de disponibilités et consultation
  de 1 à 3 appartements, sans ouverture du formulaire ni POST de réservation.
- `BookingUser`, poids 3 : même navigation, puis formulaire, lecture des conditions,
  création, instructions de virement, liste et détail de la réservation.

Le ratio concerne les **utilisateurs concurrents**, pas les requêtes HTTP ou le
taux de réussite des réservations. Les réservants répètent leur parcours pendant
le test ; ce n'est pas une limite de 30 réservations au total. Les parcours de
réservation sont plus longs. À 100 utilisateurs, la répartition cible est 70
navigateurs et 30 réservants ; à 50, 35 et 15 ; à 75, environ 52–53 et 22–23.
Ne sélectionner qu'une classe en ligne de commande changerait ce mélange.

Pauses aléatoires de 2 à 6 secondes entre les étapes et entre les parcours.
Dates choisies entre J+7 et J+365, pour 2 à 5 nuits, hors août réservé aux FM6.
Les appartements et réservations sont découverts dans les réponses, sans ID fixe.
Après trois recherches sans résultat, un événement `BUSINESS` signale l'épuisement
du stock. Les POST utilisent CSRF et Referer ; un HTTP 200 sur un formulaire refusé
compte comme un échec. Les redirections sont vérifiées et les pages suivantes
chargées séparément pour distinguer leurs temps de réponse.

La réservation est **en attente de virement**. Aucun paiement ni validation
administrateur n'est simulé. Ce modèle représente des clients déjà identifiés,
avec deux intentions de visite. Il ne prétend pas reproduire un taux de conversion
observé : ajuster les poids/pauses plus tard avec les données d'usage réelles.

## Préparation

Utiliser une instance de test PostgreSQL avec les migrations appliquées, le
serveur WSGI du déploiement, `DEBUG=False`, des appartements disponibles et au
moins **100 comptes clients réguliers actifs**, avec mot de passe local. Éviter
les administrateurs et les comptes FM6 dont les quotas fausseraient les tests.
Ne pas utiliser les données de réservation réelles.

```bash
venv/bin/python -m pip install -r requirements-loadtest.txt
```

Créer `loadtest-users.csv` à la racine avec des comptes existants :

```csv
email,password
charge001@example.test,mot-de-passe-du-compte-001
charge002@example.test,mot-de-passe-du-compte-002
```

Le fichier est ignoré par Git et ne crée pas de comptes dans Django.
`LOADTEST_USERS_CSV` permet un autre chemin. Un CSV absent/invalide empêche le
démarrage ; un manque de comptes produit une erreur `CONFIG` et arrête les
utilisateurs excédentaires. Ne publier ni le CSV ni les mots de passe.

Exécuter Locust sur une **autre machine** que les 2 vCPU mesurés. Surveiller aussi
le CPU du générateur. En mode distribué, fournir à chaque worker un CSV distinct :
le pool de comptes est local au processus. Le ratio peut subir des arrondis par
worker ; vérifier les nombres réels.

## Réservations et nettoyage

Pour ces campagnes prolongées, lancer avec `LOADTEST_CANCEL=1`. Cela annule chaque
réservation de test après consultation, libère les dates/quota et conserve la
ligne annulée. Le nettoyage ajoute sa propre charge, visible dans `13 Formulaire
annulation` et `14 Annulation de test` : conserver la même option dans tous les
runs et relever ces coûts séparément. Ce comportement sert à stabiliser le stock,
ce n'est pas une hypothèse sur le taux d'annulation réel des clients.

Sans cette option, les réservations bloquent les dates pendant 24 heures. Même
avec elle, une interruption forcée ou une panne peut laisser des réservations
en attente. Restaurer le **même jeu de données initial** entre campagnes, en
particulier les réservations, paiements et notifications. Garder les mêmes tâches
de fond et réglages serveur d'un run à l'autre.

## Durée recommandée et montée en charge

Commencer par un smoke test de 5 utilisateurs pendant 2 minutes. Vérifier les
connexions, créations et annulations avant de charger davantage.

Puis réaliser trois campagnes **séparées**, dans cet ordre, avec une montée à
**2 utilisateurs/seconde**. Proposition de départ pour cette application :

| Utilisateurs | Montée approximative | Montée + chauffe, exclues des mesures | Mesure au palier | Durée totale |
| --- | ---: | ---: | ---: | ---: |
| 50 | 25 s | 5 min depuis le lancement | 15 min | **20 min** |
| 75 | 38 s | 5 min depuis le lancement | 20 min | **25 min** |
| 100 | 50 s | 5 min depuis le lancement | 30 min | **35 min** |

Les cinq premières minutes comprennent la montée, la connexion unique de chaque
utilisateur et la chauffe des caches. Ne commencer la fenêtre de mesure que si le
nombre cible est atteint et stable ; sinon prolonger ou corriger le test. Les
durées indiquées ne garantissent pas assez d'échantillons : relever le nombre de
POST de réservation et prolonger si trop peu ont été exécutés pour interpréter
les percentiles. Un p99 avec quelques dizaines de requêtes est peu représentatif.

Attendre le retour du CPU et des files d'attente au repos entre runs. Restaurer
les données, puis recommencer la chauffe. Refaire chaque palier au moins une
seconde fois pour vérifier la reproductibilité. Après un palier 100 stable, un
run optionnel de 60 minutes au palier peut révéler une dérive mémoire/connexions.

### Avec l'interface web (mesure de palier simple)

```bash
LOADTEST_CANCEL=1 venv/bin/locust -f locustfile.py --host http://SERVEUR_TEST:8000
```

Ouvrir http://localhost:8089, choisir 50, 75 ou 100 utilisateurs, montée à 2/s.
Avant la remise à zéro, vérifier que `03 Connexion` a environ une requête par
utilisateur démarré, sans échec. À la fin des 5 minutes de chauffe, **réinitialiser
les statistiques dans l'interface, sans arrêter les utilisateurs**, puis mesurer
15, 20 ou 30 minutes suivant le palier. Exporter le rapport et les statistiques.
Les sessions restent connectées ; une réinitialisation des statistiques ne crée
pas de nouvelles connexions utilisateur.

### Sans interface

Remplacer `SERVEUR_TEST` par l'hôte de staging. Exécuter chaque commande séparément,
avec restauration des données entre les campagnes :

```bash
mkdir -p loadtest-results

LOADTEST_CANCEL=1 venv/bin/locust -f locustfile.py \
  --host http://SERVEUR_TEST:8000 --headless \
  --users 50 --spawn-rate 2 --run-time 20m --stop-timeout 120 \
  --csv-full-history --csv loadtest-results/50-users --html loadtest-results/50-users.html

LOADTEST_CANCEL=1 venv/bin/locust -f locustfile.py \
  --host http://SERVEUR_TEST:8000 --headless \
  --users 75 --spawn-rate 2 --run-time 25m --stop-timeout 120 \
  --csv-full-history --csv loadtest-results/75-users --html loadtest-results/75-users.html

LOADTEST_CANCEL=1 venv/bin/locust -f locustfile.py \
  --host http://SERVEUR_TEST:8000 --headless \
  --users 100 --spawn-rate 2 --run-time 35m --stop-timeout 120 \
  --csv-full-history --csv loadtest-results/100-users --html loadtest-results/100-users.html
```

`--run-time` commence au lancement, pas à la fin de la montée. L'arrêt gracieux
peut ajouter jusqu'à 120 secondes pour terminer les parcours. Les CSV/rapports
finaux incluent la chauffe ; utiliser l'historique horodaté pour examiner la
fenêtre stable et identifier les dérives. Ne pas présenter les percentiles
cumulés comme ceux du seul palier, ni faire une moyenne de percentiles. Pour des
percentiles agrégés propres au palier, utiliser la remise à zéro de l'interface
ci-dessus. `--reset-stats` ne remplace pas les 5 minutes : il réinitialise à la fin
de la montée, avant la fin de la chauffe.

## Ce qu'il faut noter

Pour chaque campagne, enregistrer :

1. **Conditions** : commit, migrations, nombre de logements/réservations initial,
   PostgreSQL local ou séparé, workers/threads, `DEBUG`, réglages de connexion,
   tâches de fond, machine Locust, option d'annulation et heure début/fin.
2. **Charge réelle** : utilisateurs actifs stables, répartition des classes,
   débit HTTP et nombre de connexions initiales. 100 utilisateurs ne signifie
   pas 100 requêtes simultanées : les pauses font partie du modèle.
3. **Latence par endpoint** : p50/p95/p99 de `05 Recherche disponibilités`,
   `06 Détail appartement`, `09 Création réservation`, `11 Mes réservations` et
   `12 Détail réservation`, ainsi que leur nombre de requêtes. Garder aussi
   les résultats des instructions de virement et du nettoyage.
4. **Résultat métier** : tentatives de création, créations réussies (requêtes
   `09` moins échecs), réservations réussies/minute, annulations réussies et
   en attente restantes. Des recherches seules ne prouvent pas la capacité
   de réservation.
5. **Erreurs** : taux HTTP global et par endpoint, 5xx/timeouts, redirections de
   session expirée, refus de formulaire, erreurs `CONFIG` et ruptures de stock
   `BUSINESS`. Séparer indisponibilité concurrente attendue et erreur technique.
6. **Serveur**, échantillons toutes les 5–10 secondes : CPU application et CPU
   PostgreSQL séparés, CPU machine, RAM/RSS, swap, I/O disque, connexions SQL,
   requêtes actives et attentes de verrous. Noter si l'outil affiche 100 % par
   cœur ou pour la machine entière : sur certains outils 200 % occupe 2 vCPU.
7. **Dérive** : comparer le début et la fin du palier. Un débit stable avec p95,
   mémoire, connexions ou files d'attente croissantes n'est pas un run stable.

Tableau de synthèse à remplir avec les mesures de la fenêtre stable :

| Utilisateurs | RPS | Recherche p95 | Réservation p95 / p99 | Créations réussies/min | Erreurs techniques % | CPU app / DB | RAM max | Attentes SQL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 50 | | | | | | | | |
| 75 | | | | | | | | |
| 100 | | | | | | | | |

Objectifs initiaux proposés, à adapter au produit : **p95 < 2 s** pour les pages
clés et la création, **erreurs techniques < 1 %**, créations réellement réussies,
pas de hausse continue de latence/RAM ni de saturation CPU durable. Si un palier
échoue, conserver ses résultats et profiler avant de monter au suivant. Ne pas
compter une panne de données/configuration comme une limite de capacité serveur.

Locust mesure les pages HTTP dynamiques, sans JavaScript ni chargement automatique
des images/CSS/polices. Il ne mesure pas le rendu du navigateur. La latence et le
CPU doivent être comparés à scénario, données et configuration identiques.

## Validation du scénario

```bash
venv/bin/python -m unittest discover -s tools/tests -v
venv/bin/locust -f locustfile.py --list
```

Les tests vérifient la connexion unique, la conservation des cookies, le retour
exclusif des comptes, l'arrêt sur échec de connexion, l'absence de réservation
chez les navigateurs, le parcours complet et le nettoyage, CSRF et redirections.

Références : [sessions, poids et tâches Locust 2.47](https://docs.locust.io/en/2.47.0/writing-a-locustfile.html),
[durée et arrêt gracieux](https://docs.locust.io/en/2.47.0/running-without-web-ui.html).

## Préparer 500 comptes

Le fichier local `loadtest-users.csv` a été étendu de `charge001@example.test` à
`charge500@example.test`. Les 100 premières lignes sont conservées ; les 400
nouvelles ont des mots de passe aléatoires individuels. La sauvegarde privée
`loadtest-users-100-backup.csv` contient les 100 comptes initiaux. Ces CSV sont
ignorés par Git : un `git pull` ne les transfère pas.

Copier le CSV complet sur la VM et déployer la commande Django, puis exécuter
**sur la VM**, dans le dossier du projet et avec son environnement de base :

```bash
venv/bin/python manage.py import_loadtest_users --csv loadtest-users.csv
```

L'import crée les comptes manquants et vérifie rôle, activation et mot de passe
des comptes déjà présents. Il ne change aucun compte existant et refuse les
adresses autres que `chargeNNN@example.test`. Si les 100 comptes initiaux sont
présents et correspondent au CSV, le résultat attendu est :

```text
400 comptes créés ; 100 comptes existants vérifiés ; 500 comptes prêts.
```

La création des mots de passe peut prendre quelques minutes. Utiliser le même
CSV sur le PC où Locust s'exécute. L'ajout de lignes au CSV seul ne crée aucun
compte sur la VM. L'import peut être relancé sans dupliquer les comptes.

Lancer ensuite l'interface habituelle et choisir 500 utilisateurs : 350
navigateurs et 150 réservants. Monter progressivement depuis les paliers déjà
validés ; 500 utilisateurs n'est pas une capacité garantie sur 2 vCPU.
