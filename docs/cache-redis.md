# Cache Redis

Le client redis 6.4.0 est dans requirements.txt. Django utilise Redis par défaut
sur redis://127.0.0.1:6379/1 ; REDIS_URL permet de changer cette adresse.
CACHE_VERSION (v1 par défaut) doit être changé lors d'un déploiement modifiant
les templates ou les objets mis en cache. CACHE_BACKEND=locmem sert aux tests.

## Installation locale / serveur avec Podman

Le conteneur local appartements-redis a été créé avec :

```sh
podman run -d --name appartements-redis -p 127.0.0.1:6379:6379 docker.io/library/redis:7-alpine redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru --save '' --appendonly no
```

Pour le redémarrer : `podman start appartements-redis`.
Sur le serveur de production, installer séparément Redis et configurer son
redémarrage via le gestionnaire de services (ou Quadlet pour Podman).
Le conteneur local n'installe pas de service de démarrage système.
Ne pas exposer le port Redis sur Internet. Pour un serveur Redis distant,
configurer les identifiants et TLS (rediss://). Adapter les 128 Mo au serveur.
Redis est ici un cache jetable, sans données métier persistantes.

## Périmètre

- Pages complètes : accueil et confidentialité, 60 secondes, uniquement GET
  anonyme sans cookie ni Authorization. Les visiteurs connectés et les messages
  de session contournent ce cache. Les réponses restent private/no-store pour
  éviter un cache navigateur ou proxy qui masquerait les changements de session.
- SQL : détail d'appartement et relations photos/périodes préchargées, 300 secondes.
  Les signaux save/delete renouvellent la version du catalogue après commit.
  Les mises à jour directes QuerySet.update/bulk_create contournent les signaux :
  appeler apartments.cache.invalider_catalogue après ces opérations.
- Fragments : liens communs de navigation 600 secondes (par rôle et rubrique),
  footer 3600 secondes (par rôle et année), sections informatives de l'accueil
  3600 secondes. Nom, notifications et formulaire CSRF restent hors fragments.
- Disponibilités, quotas, paiements, sessions et recherche restent en base.

Une panne Redis fait revenir les lectures en base ; les écritures de cache sont
ignorées et journalisées. Une invalidation échouée peut laisser un ancien détail
jusqu'à son TTL de 300 secondes après récupération. Les contrôles de réservation
utilisent toujours les données fraîches de la base.

## Vérification

```sh
DB_NAME='' CACHE_BACKEND=locmem venv/bin/python manage.py test core.test_cache core.tests apartments.tests --noinput
podman exec appartements-redis redis-cli INFO stats
```

Comparer les mêmes campagnes Locust avant/après et relever hit/miss, latence et
mémoire Redis. Le scénario Locust authentifié contourne volontairement le cache
pleine page ; prévoir également un scénario anonyme pour mesurer celui-ci.
