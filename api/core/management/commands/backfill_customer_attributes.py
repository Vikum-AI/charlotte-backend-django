from django.core.management.base import BaseCommand

from api.core.utils.backfill.customer_attributes import backfill_customer_attributes


class Command(BaseCommand):
    help = 'Backfill risk_rating and industry on Customer nodes; clears legacy kyc tier values'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of customers to process',
        )

    def handle(self, *args, **options):
        limit = options['limit']

        self.stdout.write('Starting customer attribute backfill...')
        if limit is not None:
            self.stdout.write(f'Customer limit: {limit}')
        else:
            self.stdout.write('Customer limit: none (full graph)')

        summary = backfill_customer_attributes(limit=limit)

        self.stdout.write('')
        self.stdout.write(f'Total customers processed: {summary.total_processed}')
        self.stdout.write(f'Customers with null attributes: {summary.null_count}')

        self.stdout.write('')
        self.stdout.write('KYC status distribution:')
        for value, count in summary.kyc_distribution:
            self.stdout.write(f'  {value}: {count}')

        self.stdout.write('')
        self.stdout.write('Risk rating distribution:')
        for value, count in summary.risk_distribution:
            self.stdout.write(f'  {value}: {count}')

        self.stdout.write('')
        self.stdout.write('Sample customers (10):')
        for customer_id, kyc_status, risk_rating, industry in summary.sample_customers:
            self.stdout.write(
                f'  {customer_id}: kyc={kyc_status}, risk={risk_rating}, industry={industry}',
            )

        self.stdout.write('')
        self.stdout.write('Backfill complete')
