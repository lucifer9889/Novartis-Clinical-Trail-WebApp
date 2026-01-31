"""
GenAI Services for Clinical Trial Control Tower.

Architecture Integration:
- GenAI Orchestrator (Governed) component
- Policy-aware retrieval + RAG
- Evidence-based recommendations
- Audit trail for all AI outputs
"""

import anthropic
from django.conf import settings
from apps.core.models import Subject, Site
from apps.monitoring.models import Query, MissingVisit, MissingPage
from apps.metrics.models import CleanPatientStatus, DQIScoreSubject
from apps.safety.models import SAEDiscrepancy
import json


class ClinicalTrialAIService:
    """
    AI Service for Clinical Trial insights using Claude.
    """

    def __init__(self):
        # Initialize Anthropic client
        # Note: In production, use environment variable for API key
        # For hackathon, you can set it directly or use settings.py
        self.client = anthropic.Anthropic(
            api_key=getattr(settings, 'ANTHROPIC_API_KEY', 'your-api-key-here')
        )
        self.model = "claude-sonnet-4-20250514"

    def generate_suggested_actions(self, study_id='Study_1', limit=3):
        """
        Generate AI-powered suggested actions for CRAs.

        Returns top priority actions based on current study data.
        """
        # Gather evidence from database
        evidence = self._gather_study_evidence(study_id)

        # Create prompt for Claude
        prompt = self._build_suggested_actions_prompt(evidence)

        # Call Claude API
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Parse response
            response_text = message.content[0].text
            actions = self._parse_suggested_actions(response_text, limit)

            return actions

        except Exception as e:
            print(f"AI Error: {e}")
            # Fallback to rule-based actions
            return self._fallback_actions(evidence, limit)

    def generate_query_response_suggestion(self, query_id):
        """
        Generate AI suggestion for query response.

        Analyzes query context and suggests appropriate response.
        """
        try:
            query = Query.objects.select_related('subject').get(query_id=query_id)
        except:
            return {"error": "Query not found"}

        # Gather query context
        context = self._gather_query_context(query)

        # Create prompt
        prompt = self._build_query_response_prompt(context)

        # Call Claude
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            suggestion = message.content[0].text

            return {
                "query_id": query_id,
                "suggested_response": suggestion,
                "confidence": "high",
                "requires_review": True
            }

        except Exception as e:
            return {
                "query_id": query_id,
                "error": str(e),
                "suggested_response": "Please review query manually."
            }

    def assess_subject_risk(self, subject_id):
        """
        AI-powered risk assessment for a subject.

        Analyzes all blockers and provides prioritized recommendations.
        """
        try:
            subject = Subject.objects.get(subject_id=subject_id)
            clean_status = CleanPatientStatus.objects.get(subject=subject)
            dqi_score = DQIScoreSubject.objects.get(subject=subject)
        except:
            return {"error": "Subject data not found"}

        # Gather subject evidence
        evidence = self._gather_subject_evidence(subject, clean_status, dqi_score)

        # Create prompt
        prompt = self._build_risk_assessment_prompt(evidence)

        # Call Claude
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            assessment = message.content[0].text

            return {
                "subject_id": subject_id,
                "risk_assessment": assessment,
                "dqi_score": float(dqi_score.composite_dqi_score),
                "risk_band": dqi_score.risk_band,
                "is_clean": clean_status.is_clean
            }

        except Exception as e:
            return {"error": str(e)}

    def _gather_study_evidence(self, study_id):
        """Gather key metrics and issues from study."""

        # Count critical issues
        open_queries = Query.objects.filter(
            subject__study_id=study_id,
            query_status='Open'
        ).count()

        missing_visits = MissingVisit.objects.filter(
            subject__study_id=study_id
        ).count()

        missing_pages = MissingPage.objects.filter(
            subject__study_id=study_id
        ).count()

        sae_discrepancies = SAEDiscrepancy.objects.filter(
            study_id=study_id
        ).count()

        # Get at-risk subjects
        high_risk_subjects = DQIScoreSubject.objects.filter(
            subject__study_id=study_id,
            risk_band__in=['High', 'Critical']
        ).count()

        # Get sites needing attention
        sites_needing_attention = []
        from apps.metrics.models import DQIScoreSite
        at_risk_sites = DQIScoreSite.objects.filter(
            site__study_id=study_id,
            risk_band__in=['High', 'Critical']
        ).select_related('site')[:3]

        for site_dqi in at_risk_sites:
            sites_needing_attention.append({
                'site_number': site_dqi.site.site_number,
                'dqi_score': float(site_dqi.composite_dqi_score),
                'clean_pct': float(site_dqi.clean_percentage)
            })

        return {
            'study_id': study_id,
            'open_queries': open_queries,
            'missing_visits': missing_visits,
            'missing_pages': missing_pages,
            'sae_discrepancies': sae_discrepancies,
            'high_risk_subjects': high_risk_subjects,
            'at_risk_sites': sites_needing_attention
        }

    def _build_suggested_actions_prompt(self, evidence):
        """Build prompt for suggested actions."""

        prompt = f"""You are an AI assistant for a Clinical Trial Control Tower system.
Analyze the following study data and suggest the TOP 3 priority actions for Clinical Research Associates (CRAs).

Study Metrics:
- Open Queries: {evidence['open_queries']}
- Missing Visits: {evidence['missing_visits']}
- Missing Pages: {evidence['missing_pages']}
- SAE Discrepancies: {evidence['sae_discrepancies']} (CRITICAL)
- High-Risk Subjects: {evidence['high_risk_subjects']}
- At-Risk Sites: {len(evidence['at_risk_sites'])}

Top At-Risk Sites:
{json.dumps(evidence['at_risk_sites'], indent=2)}

Provide exactly 3 suggested actions in this JSON format:
[
  {{
    "title": "Action title (max 60 chars)",
    "description": "Why this action is important (max 150 chars)",
    "priority": "Critical|High|Medium",
    "category": "Enrollment|Query Management|Data Quality|Safety",
    "estimated_impact": "Brief impact statement"
  }}
]

Focus on:
1. SAE discrepancies (HIGHEST priority if present)
2. High-risk sites or subjects
3. Operational bottlenecks (queries, missing data)

Return ONLY valid JSON, no other text."""

        return prompt

    def _build_query_response_prompt(self, context):
        """Build prompt for query response suggestion."""

        prompt = f"""You are an AI assistant helping resolve clinical trial data queries.

Query Details:
- Query ID: {context['log_number']}
- Form: {context['form_name']}
- Field: {context['field_oid']}
- Subject: {context['subject_id']}
- Site: {context['site_number']}
- Days Open: {context['days_open']}
- Action Owner: {context['action_owner']}

Suggest a professional, concise response that:
1. Addresses the data clarification needed
2. Follows clinical trial documentation standards
3. Is appropriate for the action owner

Keep response under 200 words and professional tone.
"""

        return prompt

    def _build_risk_assessment_prompt(self, evidence):
        """Build prompt for subject risk assessment."""

        prompt = f"""Analyze this clinical trial subject's data quality and provide risk assessment.

Subject: {evidence['subject_id']}
Clean Status: {'CLEAN' if evidence['is_clean'] else 'BLOCKED'}
DQI Score: {evidence['dqi_score']} ({evidence['risk_band']} risk)

Active Blockers:
{json.dumps(evidence['blockers'], indent=2)}

Provide:
1. Primary risk factors (top 2-3)
2. Recommended actions (prioritized)
3. Estimated timeline to resolve

Keep response concise (under 250 words) and actionable for CRAs.
"""

        return prompt

    def _gather_query_context(self, query):
        """Gather context for query."""
        return {
            'log_number': query.log_number,
            'form_name': query.form_name,
            'field_oid': query.field_oid,
            'subject_id': query.subject.subject_external_id,
            'site_number': query.subject.site.site_number,
            'days_open': query.days_since_open,
            'action_owner': query.action_owner
        }

    def _gather_subject_evidence(self, subject, clean_status, dqi_score):
        """Gather evidence for subject risk assessment."""
        return {
            'subject_id': subject.subject_external_id,
            'is_clean': clean_status.is_clean,
            'dqi_score': float(dqi_score.composite_dqi_score),
            'risk_band': dqi_score.risk_band,
            'blockers': clean_status.get_blockers_list()
        }

    def _parse_suggested_actions(self, response_text, limit):
        """Parse Claude response into structured actions."""
        try:
            # Try to parse as JSON
            actions = json.loads(response_text)
            return actions[:limit]
        except:
            # Fallback: extract actions manually
            return self._fallback_actions({}, limit)

    def _fallback_actions(self, evidence, limit):
        """Fallback rule-based actions if AI fails."""
        actions = []

        if evidence.get('sae_discrepancies', 0) > 0:
            actions.append({
                'title': 'Resolve SAE Discrepancies',
                'description': f"{evidence['sae_discrepancies']} critical SAE discrepancies require immediate attention",
                'priority': 'Critical',
                'category': 'Safety',
                'estimated_impact': 'High - Regulatory compliance'
            })

        if evidence.get('open_queries', 0) > 50:
            actions.append({
                'title': 'Clear Query Backlog',
                'description': f"{evidence['open_queries']} open queries need resolution",
                'priority': 'High',
                'category': 'Query Management',
                'estimated_impact': 'Medium - Data cleaning progress'
            })

        if evidence.get('missing_visits', 0) > 10:
            actions.append({
                'title': 'Follow Up on Missing Visits',
                'description': f"{evidence['missing_visits']} overdue visits need scheduling",
                'priority': 'High',
                'category': 'Enrollment',
                'estimated_impact': 'High - Study timeline'
            })

        return actions[:limit]
