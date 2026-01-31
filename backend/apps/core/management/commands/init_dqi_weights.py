"""
Initialize DQI weight configuration.

Usage:
    python manage.py init_dqi_weights

Loads default DQI weights from Project Document Section 9.3.
"""

from django.core.management.base import BaseCommand
from apps.metrics.models import DQIWeightConfig


class Command(BaseCommand):
    help = 'Initialize DQI weight configuration'

    def handle(self, *args, **options):
        self.stdout.write('Initializing DQI weights...')

        weights = [
            {
                'metric_name': 'sae_unresolved_count',
                'weight': 0.25,
                'description': 'Unresolved SAE discrepancies (highest severity blocker)'
            },
            {
                'metric_name': 'missing_visits_days_overdue',
                'weight': 0.15,
                'description': 'Overdue projected visits (operational urgency)'
            },
            {
                'metric_name': 'open_queries_count',
                'weight': 0.15,
                'description': 'Open unresolved queries (data cleaning workload)'
            },
            {
                'metric_name': 'missing_pages_count',
                'weight': 0.10,
                'description': 'Missing CRF pages (completeness risk)'
            },
            {
                'metric_name': 'non_conformant_count',
                'weight': 0.10,
                'description': 'Non-conformant data items (compliance risk)'
            },
            {
                'metric_name': 'sdv_incomplete_pct',
                'weight': 0.10,
                'description': 'SDV/verification incomplete (monitoring readiness)'
            },
            {
                'metric_name': 'pi_signature_incomplete_pct',
                'weight': 0.05,
                'description': 'PI signatures pending (inspection readiness)'
            },
            {
                'metric_name': 'coding_uncoded_count',
                'weight': 0.05,
                'description': 'Uncoded medical terms (analysis readiness)'
            },
            {
                'metric_name': 'edrr_open_issue_count',
                'weight': 0.05,
                'description': '3rd-party reconciliation open issues'
            },
        ]

        created = 0
        updated = 0

        for weight_config in weights:
            obj, created_flag = DQIWeightConfig.objects.update_or_create(
                metric_name=weight_config['metric_name'],
                defaults={
                    'weight': weight_config['weight'],
                    'description': weight_config['description'],
                    'is_active': True
                }
            )
            if created_flag:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created} weights, Updated {updated} weights'))
        self.stdout.write('DQI weights initialized successfully')
