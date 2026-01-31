"""
Management command to record historical events on blockchain.

Usage:
    python manage.py record_blockchain_events --study_id=Study_1
"""

from django.core.management.base import BaseCommand
from apps.blockchain.services import BlockchainService
from apps.metrics.models import DQIScoreStudy, CleanPatientStatus
from apps.monitoring.models import Query
from apps.core.models import Subject


class Command(BaseCommand):
    help = 'Record historical events on blockchain for demo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--study_id',
            type=str,
            default='Study_1',
            help='Study ID to record events for'
        )

    def handle(self, *args, **options):
        study_id = options['study_id']

        self.stdout.write(self.style.SUCCESS(f'\n=== Recording Blockchain Events for {study_id} ===\n'))

        service = BlockchainService()
        events_recorded = 0

        # 1. Record DQI Computation
        self.stdout.write('1. Recording DQI computation...')
        try:
            study_dqi = DQIScoreStudy.objects.get(study_id=study_id)
            service.record_dqi_computation(study_id, {
                'total_subjects': study_dqi.total_subjects,
                'clean_percentage': float(study_dqi.clean_percentage),
                'composite_dqi_score': float(study_dqi.composite_dqi_score)
            })
            events_recorded += 1
            self.stdout.write(self.style.SUCCESS('   [OK] DQI computation recorded'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'   [!] DQI data not found: {e}'))

        # 2. Record Clean Status Updates (sample)
        self.stdout.write('\n2. Recording clean status updates...')
        try:
            clean_statuses = CleanPatientStatus.objects.filter(
                subject__study_id=study_id
            ).select_related('subject__dqi_score')[:10]  # First 10 for demo

            for clean_status in clean_statuses:
                try:
                    service.record_clean_status_update(
                        clean_status.subject.subject_id,
                        {
                            'is_clean': clean_status.is_clean,
                            'blockers': clean_status.get_blockers_list(),
                            'dqi_score': float(clean_status.subject.dqi_score.composite_dqi_score)
                        }
                    )
                    events_recorded += 1
                except Exception as e:
                    continue

            self.stdout.write(self.style.SUCCESS(f'   [OK] {len(clean_statuses)} clean status updates recorded'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'   [!] Clean status data not found: {e}'))

        # 3. Record Resolved Queries (sample)
        self.stdout.write('\n3. Recording resolved queries...')
        try:
            resolved_queries = Query.objects.filter(
                subject__study_id=study_id,
                query_status='Closed'
            )[:5]  # First 5 for demo

            for query in resolved_queries:
                service.record_query_resolution(
                    query.query_id,
                    {
                        'log_number': query.log_number,
                        'resolution_date': query.query_response_date.isoformat() if query.query_response_date else '',
                        'resolved_by': 'CRA',
                        'response': 'Query resolved'
                    }
                )
                events_recorded += 1

            self.stdout.write(self.style.SUCCESS(f'   [OK] {len(resolved_queries)} query resolutions recorded'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'   [!] Query data not found: {e}'))

        # 4. Verify chain integrity
        self.stdout.write('\n4. Verifying blockchain integrity...')
        verification = service.verify_chain_integrity()

        if verification['is_valid']:
            self.stdout.write(self.style.SUCCESS(f"   [OK] Blockchain is valid ({verification['total_blocks']} blocks)"))
        else:
            self.stdout.write(self.style.ERROR('   [X] Blockchain has integrity issues'))

        # 5. Display stats
        stats = service.get_blockchain_stats()
        self.stdout.write(f'\n=== Blockchain Stats ===')
        self.stdout.write(f'Total Blocks: {stats["total_blocks"]}')
        self.stdout.write(f'Latest Block: #{stats["latest_block_number"]}')
        self.stdout.write(f'Chain: {stats["chain_name"]}')

        self.stdout.write(self.style.SUCCESS(f'\n=== {events_recorded} Events Recorded on Blockchain ===\n'))
