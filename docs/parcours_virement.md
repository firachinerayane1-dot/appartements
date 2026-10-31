# Réservation, virement et validation

Le client coche les conditions sur le formulaire de réservation. Les conditions complètes sont accessibles sans connexion, depuis ce formulaire et le pied de page. Le consentement et la version des conditions sont enregistrés à la création. Aucun email de politiques n’est envoyé.

La réservation bloque les dates pendant 24 heures. Le client consulte les coordonnées de virement puis ouvre WhatsApp avec son numéro de réservation prérempli et joint lui-même le reçu. Le support contacte le client. Dans **Réservations → Vérifier le virement**, l’administrateur renseigne la référence bancaire et atteste avoir vérifié le montant reçu et le contact avec le client. Cette validation confirme le séjour et déclenche l’email de confirmation avec PDF.

Les contrôles de disponibilité excluent les attentes de 24 heures ou plus, même sans tâche planifiée. Pour mettre à jour les statuts et notifier les clients en l’absence de visites, exécuter régulièrement la commande existante `python manage.py expirer_reservations` (par exemple toutes les minutes via le planificateur du serveur). Une réservation expirée ne peut pas être confirmée ; le support doit traiter séparément tout virement reçu tardivement.

## Configuration

Renseigner dans `.env`, puis redémarrer le serveur :

- `PAYMENT_BANK_NAME` : banque ;
- `PAYMENT_ACCOUNT_HOLDER` : titulaire ;
- `PAYMENT_RIB` : RIB ;
- `PAYMENT_IBAN` et `PAYMENT_BIC` : facultatifs ;
- `SUPPORT_WHATSAPP_NUMBER` : numéro international, indicatif inclus, sans zéro national.

Aucune coordonnée fictive n’est affichée en l’absence de configuration. La page indique que les coordonnées restent à publier. Les migrations `reservations.0004` et `payments.0003` ajoutent la traçabilité des annulations et des validations.

## Annulation et remboursement

Règle confirmée par le propriétaire :

- Annulation à plus de 72 heures de l’arrivée : 50 % des sommes reçues, y compris dans les 48 heures suivant la réservation.
- Annulation à 72 heures ou moins de l’arrivée : 0 %.
- Non-présentation : 0 %.
- Erreur imputable à l’établissement : 100 %, indépendamment du délai.

L’arrivée est calculée selon `RAHAL_STAY_CHECK_IN` (format `HH:MM`) dans le fuseau `Africa/Casablanca`. La borne exacte de 72 heures est non remboursable. L’annulation enregistre le motif, la date et le montant à rembourser ; elle ne déclenche aucun transfert bancaire. Le support organise et suit le remboursement réel. Les paiements non encore vérifiés, les paiements tardifs et les situations exceptionnelles nécessitent une vérification par le support.

Les conditions ajoutent la procédure de réclamation, les modifications soumises à accord, le traitement des virements tardifs et la réserve des droits impératifs. Référence consultée : [loi marocaine 31-08, notamment articles 29, 32 et 42](https://www.wipo.int/wipolex/fr/legislation/details/19773). L’article 42 prévoit des règles particulières pour l’hébergement à dates déterminées : la période de 48 heures n’est pas présentée comme un délai légal de rétractation. Faire valider le texte contractuel final par un juriste local, notamment l’identité du prestataire, les modalités de réclamation et le délai effectif de remboursement.
