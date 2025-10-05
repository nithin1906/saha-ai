from django.core.management.base import BaseCommand
from advisor.data_service import stock_data_service
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update fallback stock prices daily from web scraping'

    def handle(self, *args, **options):
        self.stdout.write('Starting daily fallback price update...')
        
        try:
            stock_data_service.update_fallback_prices_daily()
            self.stdout.write(
                self.style.SUCCESS('Successfully updated fallback prices')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating fallback prices: {e}')
            )
            logger.error(f'Daily price update failed: {e}')
