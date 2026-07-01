from pathlib import Path

import kagglehub
from django.conf import settings
from django.core.management.base import BaseCommand
from api.core.utils.seed_db import load_dataset, wipe_graph_if_populated

# !IMPORTANT: run this command once in the start, this will clear the db and get it back to a fresh state so data will be lost if exists


class Command(BaseCommand):
    help = 'Download datasets and seed Neo4j proof graph'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
        )

    def handle(self, *args, **options):
        limit = options['limit']
        if limit is None:
            limit = (
                settings.SEED_DEV_LIMIT if settings.DEBUG
                else settings.SEED_PROD_LIMIT
            )

        self.stdout.write('Starting Neo4j seeding pipeline...')
        if limit is not None:
            self.stdout.write(f'Row limit per dataset: {limit}')
        else:
            self.stdout.write('Row limit per dataset: none (full load)')

        if wipe_graph_if_populated():
            self.stdout.write('Existing graph data found — wiped database')
        else:
            self.stdout.write('Graph is empty — skipping wipe')

        for dataset in settings.PRELOADED_DATASETS:
            self.stdout.write(f"Downloading {dataset['name']}")
            path = Path(kagglehub.dataset_download(dataset['kaggle']))
            
            self.stdout.write(f'Loaded at {path}')
            load_dataset(dataset['name'], path, limit=limit)

        self.stdout.write('Seeding complete')
