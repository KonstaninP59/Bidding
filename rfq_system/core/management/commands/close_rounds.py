from django.core.management.base import BaseCommand
from core.services import ensure_round_states

class Command(BaseCommand):
    help = "Обновляет состояния раундов и фиксирует предложения по дедлайнам."

    def handle(self, *args, **options):
        ensure_round_states()
        self.stdout.write(self.style.SUCCESS("Готово: состояния раундов обновлены."))
