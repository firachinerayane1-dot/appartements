from django.core.management.base import BaseCommand, CommandError

from services.confirmation_queue import traiter_confirmations


class Command(BaseCommand):
    help = 'Génère les PDF et envoie les confirmations en attente, avec reprise sur échec.'

    def add_arguments(self, parser):
        parser.add_argument('--limite', type=int, default=100)

    def handle(self, *args, **options):
        if options['limite'] < 1:
            raise CommandError('--limite doit être strictement positif.')
        envoyes, erreurs = traiter_confirmations(options['limite'])
        self.stdout.write(f'{envoyes} confirmation(s) envoyée(s), {erreurs} échec(s).')
        if erreurs:
            raise CommandError('Les confirmations en échec seront réessayées automatiquement.')
