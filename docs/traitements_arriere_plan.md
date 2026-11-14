# Traitements serveur en arrière-plan

Appliquer `venv/bin/python manage.py migrate` avant de redémarrer le serveur web.
La validation d'un virement crée désormais une confirmation à envoyer dans la même
transaction que le paiement : aucun PDF ni appel SMTP dans la requête HTTP.
Aucun Redis ou service supplémentaire n'est nécessaire.

Installer ces deux entrées dans la crontab de l'utilisateur du service, en adaptant
`/srv/appartements` au chemin de déploiement (le dossier doit être accessible en écriture
pour les fichiers de verrouillage) :

```cron
* * * * * cd /srv/appartements && /usr/bin/flock -n .expiration.lock venv/bin/python manage.py expirer_reservations >> /var/log/appartements-expiration.log 2>&1
* * * * * cd /srv/appartements && /usr/bin/flock -n .confirmations.lock venv/bin/python manage.py envoyer_confirmations --limite 100 >> /var/log/appartements-confirmations.log 2>&1
```

Créer les fichiers de journal avec les droits appropriés avant activation ; prévoir
leur rotation. Utiliser les mêmes variables d'environnement et la même base que le
serveur web. Le fichier `.env` est chargé par les réglages Django.

L'expiration globale n'est plus déclenchée par les listes, le tableau de bord ou
l'export. Leurs statuts peuvent donc avoir jusqu'à une minute de retard. Les contrôles
ciblés sur une réservation et les exclusions des attentes périmées pour les
disponibilités/quota restent actifs, même si cron est momentanément arrêté.

Les confirmations sont persistées dans `payments.ConfirmationEmail` et traitées par
lots. En cas d'échec, reprise après 2, 4, 8… minutes, plafonnée à une heure. Une tâche
interrompue est récupérable après 15 minutes. Le délai SMTP est limité à 30 secondes
(`EMAIL_TIMEOUT`). Ne pas lancer de traitement dont la durée dépasse le bail de
15 minutes. Les tâches envoyées ne sont pas reprises ; un jeton empêche deux workers
de prendre simultanément une tâche. SMTP ne garantit toutefois pas l'envoi exactement
une fois : un arrêt après acceptation par SMTP et avant enregistrement peut entraîner
un doublon lors de la reprise.

Surveiller les codes de sortie et les journaux des commandes, ainsi que les tâches
non envoyées (`envoye_le IS NULL`), leur ancienneté et `tentatives`. `derniere_erreur`
conserve le type d'erreur, les détails sont dans les journaux serveur. Les anciens
paiements ne sont pas remis en file automatiquement afin d'éviter les renvois.

Vérification manuelle : valider un nouveau virement, constater la réponse immédiate
et la tâche en base, puis lancer `venv/bin/python manage.py envoyer_confirmations`.
Vérifier la réception et le PDF. Relancer la commande ne doit pas renvoyer le message.
