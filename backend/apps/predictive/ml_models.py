"""
Predictive ML Models for Clinical Trial Control Tower.

Architecture Integration:
- Predictive AI Platform component
- Model Registry (trained models stored in ML_MODELS_DIR)
- Feature engineering from Data Pods
- Predictions used by GenAI Orchestrator for enhanced recommendations
"""

import os
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from django.conf import settings
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, mean_absolute_error, r2_score

from apps.core.models import Subject, Site, Study
from apps.monitoring.models import Query, MissingVisit
from apps.metrics.models import DQIScoreSubject, DQIScoreSite, CleanPatientStatus


class PredictiveMLService:
    """
    Machine Learning service for clinical trial predictions.

    Models:
    1. Dropout Risk Prediction - Predicts likelihood of patient dropout
    2. Query Resolution Time - Predicts days to resolve queries
    3. Site Performance - Predicts site DQI scores
    4. Enrollment Forecast - Forecasts enrollment timeline
    """

    def __init__(self):
        """Initialize ML service and set up model storage directory."""
        # Set up model storage directory
        self.models_dir = getattr(
            settings,
            'ML_MODELS_DIR',
            os.path.join(settings.BASE_DIR, 'ml_models')
        )
        os.makedirs(self.models_dir, exist_ok=True)

        # Model file paths
        self.dropout_model_path = os.path.join(self.models_dir, 'dropout_risk_model.pkl')
        self.query_time_model_path = os.path.join(self.models_dir, 'query_resolution_model.pkl')
        self.site_perf_model_path = os.path.join(self.models_dir, 'site_performance_model.pkl')

    # ========================================================================
    # 1. DROPOUT RISK PREDICTION
    # ========================================================================

    def train_dropout_risk_model(self, study_id='Study_1'):
        """
        Train dropout risk prediction model.

        Features:
        - Missing visits count
        - Open queries count
        - Days since enrollment
        - DQI score
        - Site performance

        Target: Binary (0=active, 1=dropout)
        """
        print("Training Dropout Risk Model...")

        # Gather training data
        subjects = Subject.objects.filter(study_id=study_id).select_related('site')

        features_list = []
        targets = []

        for subject in subjects:
            try:
                # Get subject metrics
                clean_status = CleanPatientStatus.objects.get(subject=subject)
                dqi_score = DQIScoreSubject.objects.get(subject=subject)

                missing_visits = MissingVisit.objects.filter(subject=subject).count()
                open_queries = Query.objects.filter(
                    subject=subject,
                    query_status='Open'
                ).count()

                # Calculate days since enrollment
                if subject.enrollment_date:
                    days_enrolled = (datetime.now().date() - subject.enrollment_date).days
                else:
                    days_enrolled = 0

                # Get site DQI as proxy for site quality
                try:
                    site_dqi = DQIScoreSite.objects.get(site=subject.site)
                    site_score = float(site_dqi.composite_dqi_score)
                except:
                    site_score = 0.5  # Neutral default

                # Features
                features = [
                    missing_visits,
                    open_queries,
                    days_enrolled,
                    float(dqi_score.composite_dqi_score),
                    site_score,
                    int(clean_status.has_sae_discrepancies),
                    int(clean_status.has_missing_pages)
                ]

                # Target: Consider dropout if subject has critical issues
                # In real scenario, would use actual dropout status
                is_dropout = (
                    missing_visits > 2 or
                    (open_queries > 5 and float(dqi_score.composite_dqi_score) < 0.4) or
                    clean_status.has_sae_discrepancies
                )

                features_list.append(features)
                targets.append(int(is_dropout))

            except Exception as e:
                continue

        if len(features_list) < 10:
            print("Insufficient data for training. Need at least 10 subjects.")
            return None

        # Convert to numpy arrays
        X = np.array(features_list)
        y = np.array(targets)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Train Random Forest Classifier
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42
        )
        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        accuracy = (y_pred == y_test).mean()

        print(f"Dropout Model Accuracy: {accuracy:.2%}")
        print(f"Training samples: {len(X_train)}, Test samples: {len(X_test)}")

        # Save model
        joblib.dump(model, self.dropout_model_path)
        print(f"Model saved to: {self.dropout_model_path}")

        return {
            'model': model,
            'accuracy': accuracy,
            'feature_importance': model.feature_importances_.tolist(),
            'samples': len(X)
        }

    def predict_dropout_risk(self, subject_id):
        """Predict dropout risk for a specific subject."""
        # Load model
        if not os.path.exists(self.dropout_model_path):
            return {'error': 'Model not trained. Run train_ml_models command first.'}

        model = joblib.load(self.dropout_model_path)

        try:
            subject = Subject.objects.get(subject_id=subject_id)
            clean_status = CleanPatientStatus.objects.get(subject=subject)
            dqi_score = DQIScoreSubject.objects.get(subject=subject)

            missing_visits = MissingVisit.objects.filter(subject=subject).count()
            open_queries = Query.objects.filter(
                subject=subject,
                query_status='Open'
            ).count()

            if subject.enrollment_date:
                days_enrolled = (datetime.now().date() - subject.enrollment_date).days
            else:
                days_enrolled = 0

            try:
                site_dqi = DQIScoreSite.objects.get(site=subject.site)
                site_score = float(site_dqi.composite_dqi_score)
            except:
                site_score = 0.5

            features = np.array([[
                missing_visits,
                open_queries,
                days_enrolled,
                float(dqi_score.composite_dqi_score),
                site_score,
                int(clean_status.has_sae_discrepancies),
                int(clean_status.has_missing_pages)
            ]])

            # Predict
            dropout_prob = model.predict_proba(features)[0][1]  # Probability of dropout
            dropout_prediction = model.predict(features)[0]

            return {
                'subject_id': subject.subject_external_id,
                'dropout_risk': 'High' if dropout_prob > 0.7 else 'Medium' if dropout_prob > 0.4 else 'Low',
                'dropout_probability': float(dropout_prob),
                'prediction': 'At Risk' if dropout_prediction == 1 else 'Active',
                'features': {
                    'missing_visits': missing_visits,
                    'open_queries': open_queries,
                    'days_enrolled': days_enrolled,
                    'dqi_score': float(dqi_score.composite_dqi_score)
                }
            }

        except Exception as e:
            return {'error': str(e)}

    # ========================================================================
    # 2. QUERY RESOLUTION TIME PREDICTION
    # ========================================================================

    def train_query_resolution_model(self, study_id='Study_1'):
        """
        Train query resolution time prediction model.

        Features:
        - Query age (days open)
        - Form complexity (derived from form name)
        - Site performance
        - Action owner

        Target: Days to resolution
        """
        print("Training Query Resolution Time Model...")

        # Get all queries (both open and closed)
        queries = Query.objects.filter(
            subject__study_id=study_id
        ).select_related('subject__site')

        features_list = []
        targets = []

        for query in queries:
            try:
                # Features
                days_open = query.days_since_open if query.days_since_open else 1

                # Form complexity heuristic (page-level vs subject-level)
                form_complexity = 1 if 'Page' in query.form_name else 2

                # Site performance
                try:
                    site_dqi = DQIScoreSite.objects.get(site=query.subject.site)
                    site_score = float(site_dqi.composite_dqi_score)
                except:
                    site_score = 0.5

                # Action owner encoding
                owner_encoding = {
                    'CRA': 1,
                    'Site': 2,
                    'Sponsor': 3,
                    'DMC': 4
                }.get(query.action_owner, 1)

                features = [
                    days_open,
                    form_complexity,
                    site_score,
                    owner_encoding
                ]

                # Target: For closed queries, use actual resolution time
                # For open queries, estimate based on current days open
                if query.query_status == 'Closed':
                    resolution_days = days_open
                else:
                    # Estimate: queries typically take 1.5x current age
                    resolution_days = days_open * 1.5

                features_list.append(features)
                targets.append(resolution_days)

            except Exception as e:
                continue

        if len(features_list) < 20:
            print("Insufficient query data for training. Need at least 20 queries.")
            return None

        X = np.array(features_list)
        y = np.array(targets)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Train Gradient Boosting Regressor
        model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        print(f"Query Resolution Model - MAE: {mae:.2f} days, R²: {r2:.3f}")
        print(f"Training samples: {len(X_train)}, Test samples: {len(X_test)}")

        # Save model
        joblib.dump(model, self.query_time_model_path)
        print(f"Model saved to: {self.query_time_model_path}")

        return {
            'model': model,
            'mae': mae,
            'r2_score': r2,
            'samples': len(X)
        }

    def predict_query_resolution_time(self, query_id):
        """Predict resolution time for a specific query."""
        if not os.path.exists(self.query_time_model_path):
            return {'error': 'Model not trained. Run train_ml_models command first.'}

        model = joblib.load(self.query_time_model_path)

        try:
            query = Query.objects.select_related('subject__site').get(query_id=query_id)

            days_open = query.days_since_open if query.days_since_open else 1
            form_complexity = 1 if 'Page' in query.form_name else 2

            try:
                site_dqi = DQIScoreSite.objects.get(site=query.subject.site)
                site_score = float(site_dqi.composite_dqi_score)
            except:
                site_score = 0.5

            owner_encoding = {
                'CRA': 1,
                'Site': 2,
                'Sponsor': 3,
                'DMC': 4
            }.get(query.action_owner, 1)

            features = np.array([[
                days_open,
                form_complexity,
                site_score,
                owner_encoding
            ]])

            predicted_days = model.predict(features)[0]

            return {
                'query_id': query.log_number,
                'current_days_open': days_open,
                'predicted_resolution_days': round(predicted_days, 1),
                'estimated_completion_date': (
                    datetime.now().date() + timedelta(days=int(predicted_days))
                ).isoformat(),
                'action_owner': query.action_owner
            }

        except Exception as e:
            return {'error': str(e)}

    # ========================================================================
    # 3. SITE PERFORMANCE PREDICTION
    # ========================================================================

    def train_site_performance_model(self, study_id='Study_1'):
        """
        Train site performance prediction model.

        Features:
        - Number of enrolled subjects
        - Average query rate per subject
        - Missing visit rate
        - SAE discrepancy count

        Target: Site DQI score
        """
        print("Training Site Performance Model...")

        sites = Site.objects.filter(study_id=study_id)

        features_list = []
        targets = []

        for site in sites:
            try:
                # Get site metrics
                site_dqi = DQIScoreSite.objects.get(site=site)

                subjects = Subject.objects.filter(site=site)
                subject_count = subjects.count()

                if subject_count == 0:
                    continue

                # Calculate rates
                total_queries = Query.objects.filter(subject__site=site).count()
                query_rate = total_queries / subject_count

                total_missing_visits = MissingVisit.objects.filter(subject__site=site).count()
                missing_visit_rate = total_missing_visits / subject_count

                from apps.safety.models import SAEDiscrepancy
                sae_count = SAEDiscrepancy.objects.filter(
                    study_id=study_id,
                    site_number=site.site_number
                ).count()

                features = [
                    subject_count,
                    query_rate,
                    missing_visit_rate,
                    sae_count
                ]

                target_dqi = float(site_dqi.composite_dqi_score)

                features_list.append(features)
                targets.append(target_dqi)

            except Exception as e:
                continue

        if len(features_list) < 5:
            print("Insufficient site data for training. Need at least 5 sites.")
            return None

        X = np.array(features_list)
        y = np.array(targets)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Train Random Forest Regressor
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        print(f"Site Performance Model - MAE: {mae:.3f}, R²: {r2:.3f}")
        print(f"Training samples: {len(X_train)}, Test samples: {len(X_test)}")

        # Save model
        joblib.dump(model, self.site_perf_model_path)
        print(f"Model saved to: {self.site_perf_model_path}")

        return {
            'model': model,
            'mae': mae,
            'r2_score': r2,
            'samples': len(X)
        }

    def predict_site_performance(self, site_number, study_id='Study_1'):
        """Predict DQI score for a site."""
        if not os.path.exists(self.site_perf_model_path):
            return {'error': 'Model not trained. Run train_ml_models command first.'}

        model = joblib.load(self.site_perf_model_path)

        try:
            site = Site.objects.get(site_number=site_number, study_id=study_id)

            subjects = Subject.objects.filter(site=site)
            subject_count = subjects.count()

            if subject_count == 0:
                return {'error': 'No subjects enrolled at this site'}

            total_queries = Query.objects.filter(subject__site=site).count()
            query_rate = total_queries / subject_count

            total_missing_visits = MissingVisit.objects.filter(subject__site=site).count()
            missing_visit_rate = total_missing_visits / subject_count

            from apps.safety.models import SAEDiscrepancy
            sae_count = SAEDiscrepancy.objects.filter(
                study_id=study_id,
                site_number=site.site_number
            ).count()

            features = np.array([[
                subject_count,
                query_rate,
                missing_visit_rate,
                sae_count
            ]])

            predicted_dqi = model.predict(features)[0]

            return {
                'site_number': site_number,
                'predicted_dqi_score': round(predicted_dqi, 4),
                'predicted_risk_band': self._dqi_to_risk_band(predicted_dqi),
                'current_metrics': {
                    'subjects': subject_count,
                    'query_rate': round(query_rate, 2),
                    'missing_visit_rate': round(missing_visit_rate, 2),
                    'sae_count': sae_count
                }
            }

        except Exception as e:
            return {'error': str(e)}

    # ========================================================================
    # 4. ENROLLMENT FORECASTING
    # ========================================================================

    def forecast_enrollment(self, study_id='Study_1', days_ahead=30):
        """
        Simple enrollment forecast based on recent enrollment rate.

        Uses moving average of enrollment rate to project future enrollment.
        """
        try:
            # Get subjects with enrollment dates
            subjects = Subject.objects.filter(
                study_id=study_id,
                enrollment_date__isnull=False
            ).order_by('enrollment_date')

            if subjects.count() < 10:
                return {'error': 'Insufficient enrollment data'}

            # Calculate enrollment by week
            enrollment_dates = [s.enrollment_date for s in subjects]
            df = pd.DataFrame({
                'date': enrollment_dates,
                'count': 1
            })

            df['week'] = pd.to_datetime(df['date']).dt.to_period('W')
            weekly_enrollment = df.groupby('week')['count'].sum()

            # Calculate moving average (last 4 weeks)
            recent_avg = weekly_enrollment.tail(4).mean()

            # Project forward
            current_total = subjects.count()
            weeks_ahead = days_ahead // 7
            projected_new_enrollments = int(recent_avg * weeks_ahead)
            projected_total = current_total + projected_new_enrollments

            return {
                'study_id': study_id,
                'current_enrollment': current_total,
                'forecast_days': days_ahead,
                'projected_total': projected_total,
                'projected_new_enrollments': projected_new_enrollments,
                'weekly_rate': round(recent_avg, 2),
                'forecast_date': (datetime.now().date() + timedelta(days=days_ahead)).isoformat()
            }

        except Exception as e:
            return {'error': str(e)}

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def _dqi_to_risk_band(self, dqi_score):
        """Convert DQI score to risk band."""
        if dqi_score >= 0.8:
            return 'Low'
        elif dqi_score >= 0.6:
            return 'Medium'
        elif dqi_score >= 0.4:
            return 'High'
        else:
            return 'Critical'
