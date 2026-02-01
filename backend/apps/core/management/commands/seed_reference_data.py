"""
Management command to seed reference data (studies, countries).

Usage:
    python manage.py seed_reference_data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.models import Study, Country


class Command(BaseCommand):
    help = 'Seeds reference data including Study 1 and Study 2'

    def handle(self, *args, **options):
        self.stdout.write('Seeding reference data...\n')

        # Create Studies
        studies_data = [
            {
                'study_id': 'Study_1',
                'study_name': 'Study 1 - Clinical Trial Phase III',
                'region': 'APAC',
                'status': 'Active',
            },
            {
                'study_id': 'Study_2',
                'study_name': 'Study 2 - Clinical Trial Phase II',
                'region': 'EMEA',
                'status': 'Active',
            },
        ]

        for study_data in studies_data:
            study, created = Study.objects.update_or_create(
                study_id=study_data['study_id'],
                defaults={
                    'study_name': study_data['study_name'],
                    'region': study_data['region'],
                    'status': study_data['status'],
                    'snapshot_date': timezone.now().date(),
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created Study: {study.study_id}'))
            else:
                self.stdout.write(f'  Updated Study: {study.study_id}')

        # Create Countries for each study
        countries_data = [
            # Study 1 countries
            {'study_id': 'Study_1', 'country_code': 'IND', 'country_name': 'India', 'region': 'APAC'},
            {'study_id': 'Study_1', 'country_code': 'CHN', 'country_name': 'China', 'region': 'APAC'},
            {'study_id': 'Study_1', 'country_code': 'JPN', 'country_name': 'Japan', 'region': 'APAC'},
            {'study_id': 'Study_1', 'country_code': 'KOR', 'country_name': 'South Korea', 'region': 'APAC'},
            {'study_id': 'Study_1', 'country_code': 'AUS', 'country_name': 'Australia', 'region': 'APAC'},
            # Study 2 countries
            {'study_id': 'Study_2', 'country_code': 'USA', 'country_name': 'United States', 'region': 'Americas'},
            {'study_id': 'Study_2', 'country_code': 'GBR', 'country_name': 'United Kingdom', 'region': 'EMEA'},
            {'study_id': 'Study_2', 'country_code': 'DEU', 'country_name': 'Germany', 'region': 'EMEA'},
            {'study_id': 'Study_2', 'country_code': 'FRA', 'country_name': 'France', 'region': 'EMEA'},
            {'study_id': 'Study_2', 'country_code': 'ESP', 'country_name': 'Spain', 'region': 'EMEA'},
        ]

        for country_data in countries_data:
            study = Study.objects.get(study_id=country_data['study_id'])
            country, created = Country.objects.update_or_create(
                study=study,
                country_code=country_data['country_code'],
                defaults={
                    'country_name': country_data['country_name'],
                    'region': country_data['region'],
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f'  Created Country: {country.country_name} ({country.country_code}) for {study.study_id}'
                ))

        self.stdout.write(self.style.SUCCESS('\nReference data seeding complete!'))
        self.stdout.write(f'  Studies: {Study.objects.count()}')
        self.stdout.write(f'  Countries: {Country.objects.count()}')
