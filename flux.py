from django.core.management.base import BaseCommand
from bourse.tasks.flux_websocket import demarrer_flux_finnhub

class Command(BaseCommand):
    help = "Lance le flux WebSocket Finnhub en continu"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Démarrage du flux Finnhub..."))
        # Cette fonction contient une boucle infinie ou un processus bloquant
        demarrer_flux_finnhub()