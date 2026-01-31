"""
Management command to train all ML models for the Predictive AI Platform.

Usage:
    python manage.py train_ml_models [--study-id STUDY_1]

This command trains:
1. Dropout Risk Prediction Model
2. Query Resolution Time Prediction Model
3. Site Performance Prediction Model

Models are saved to ML_MODELS_DIR (default: backend/ml_models/)
"""

from django.core.management.base import BaseCommand
from apps.predictive.ml_models import PredictiveMLService


class Command(BaseCommand):
    help = 'Train all ML models for clinical trial predictions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--study-id',
            type=str,
            default='Study_1',
            help='Study ID to train models on (default: Study_1)'
        )

    def handle(self, *args, **options):
        study_id = options['study_id']

        self.stdout.write(self.style.SUCCESS(
            f'\n{"=" * 70}\n'
            f'  CLINICAL TRIAL ML MODEL TRAINING\n'
            f'{"=" * 70}\n'
        ))

        self.stdout.write(f'Study ID: {study_id}\n')

        # Initialize ML service
        ml_service = PredictiveMLService()

        # Track results
        results = {}

        # ====================================================================
        # 1. Train Dropout Risk Model
        # ====================================================================
        self.stdout.write(self.style.WARNING('\n[1/3] Training Dropout Risk Prediction Model...'))
        try:
            dropout_result = ml_service.train_dropout_risk_model(study_id)
            if dropout_result:
                results['dropout_risk'] = dropout_result
                self.stdout.write(self.style.SUCCESS(
                    f'  [OK] Dropout Model Trained\n'
                    f'    - Accuracy: {dropout_result["accuracy"]:.2%}\n'
                    f'    - Training Samples: {dropout_result["samples"]}\n'
                    f'    - Top Features: Missing Visits, Open Queries, DQI Score'
                ))
            else:
                self.stdout.write(self.style.ERROR('  [X] Insufficient data for dropout model'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  [X] Error: {e}'))

        # ====================================================================
        # 2. Train Query Resolution Time Model
        # ====================================================================
        self.stdout.write(self.style.WARNING('\n[2/3] Training Query Resolution Time Prediction Model...'))
        try:
            query_result = ml_service.train_query_resolution_model(study_id)
            if query_result:
                results['query_resolution'] = query_result
                self.stdout.write(self.style.SUCCESS(
                    f'  [OK] Query Resolution Model Trained\n'
                    f'    - MAE: {query_result["mae"]:.2f} days\n'
                    f'    - R² Score: {query_result["r2_score"]:.3f}\n'
                    f'    - Training Samples: {query_result["samples"]}'
                ))
            else:
                self.stdout.write(self.style.ERROR('  [X] Insufficient data for query resolution model'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  [X] Error: {e}'))

        # ====================================================================
        # 3. Train Site Performance Model
        # ====================================================================
        self.stdout.write(self.style.WARNING('\n[3/3] Training Site Performance Prediction Model...'))
        try:
            site_result = ml_service.train_site_performance_model(study_id)
            if site_result:
                results['site_performance'] = site_result
                self.stdout.write(self.style.SUCCESS(
                    f'  [OK] Site Performance Model Trained\n'
                    f'    - MAE: {site_result["mae"]:.3f}\n'
                    f'    - R² Score: {site_result["r2_score"]:.3f}\n'
                    f'    - Training Samples: {site_result["samples"]}'
                ))
            else:
                self.stdout.write(self.style.ERROR('  [X] Insufficient data for site performance model'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  [X] Error: {e}'))

        # ====================================================================
        # Summary
        # ====================================================================
        self.stdout.write(self.style.SUCCESS(
            f'\n{"=" * 70}\n'
            f'  TRAINING COMPLETE\n'
            f'{"=" * 70}\n'
        ))

        if results:
            self.stdout.write(self.style.SUCCESS(
                f'\nSuccessfully trained {len(results)} model(s):\n'
            ))
            for model_name, result in results.items():
                self.stdout.write(f'  [OK] {model_name}')

            self.stdout.write(self.style.SUCCESS(
                f'\nModels saved to: {ml_service.models_dir}\n'
                f'\nNext steps:\n'
                f'  1. Use models for predictions via API endpoints\n'
                f'  2. Integrate predictions with GenAI recommendations\n'
                f'  3. Retrain periodically as new data arrives\n'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                '\nNo models were trained. This usually means:\n'
                '  - Not enough data in the database\n'
                '  - Need to run: python manage.py import_study_data first\n'
                '  - Need to run: python manage.py compute_metrics first\n'
            ))

        self.stdout.write(self.style.SUCCESS('\nML Training session complete!\n'))
