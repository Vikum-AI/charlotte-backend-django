from pathlib import Path

import kagglehub
from django.conf import settings
from django.core.management.base import BaseCommand
from neomodel import clear_neo4j_database, db

from api.core.utils.seed_db import load_dataset


class Command(BaseCommand):
    help = 'Download datasets and seed Neo4j proof graph'

    def handle(self, *args, **options):
        self.stdout.write('Starting Neo4j seeding pipeline...')

        clear_neo4j_database(db)

        for dataset in settings.PRELOADING_DATASETS:
            self.stdout.write(f"Downloading {dataset['name']}")
            path = Path(kagglehub.dataset_download(dataset['kaggle']))
            self.stdout.write(f'Loaded at {path}')
            load_dataset(dataset['name'], path)

        self.stdout.write('Seeding complete')
