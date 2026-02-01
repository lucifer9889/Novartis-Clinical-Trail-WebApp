"""
GenAI Services for Clinical Trial Control Tower.

Architecture Integration:
- GenAI Orchestrator (Governed) component
- Policy-aware retrieval + RAG
- Evidence-based recommendations
- Audit trail for all AI outputs

AI API Key Configuration:
- Set ANTHROPIC_API_KEY in your environment or .env file
- See README.md section "AI API Keys Setup" for instructions
- AI features gracefully degrade when key is not configured
"""

import logging
import anthropic
from django.conf import settings
from apps.core.models import Subject, Site
from apps.monitoring.models import Query, MissingVisit, MissingPage
from apps.metrics.models import CleanPatientStatus, DQIScoreSubject
from apps.safety.models import SAEDiscrepancy
import json

# Logger for GenAI services - NEVER log API keys
logger = logging.getLogger(__name__)


def _get_api_key():
    """
    Retrieve ANTHROPIC_API_KEY from settings/environment.
    
    Returns:
        str or None: The API key if configured and valid, None otherwise.
    
    Note: Never log or print the actual API key value.
    """
    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    
    # Check if key is actually set (not empty, not a placeholder)
    if not api_key or api_key.startswith('YOUR_') or api_key == 'your-api-key-here':
        return None
    
    return api_key


def is_ai_configured():
    """
    Check if AI services are properly configured.
    
    Returns:
        bool: True if ANTHROPIC_API_KEY is set and valid.
    """
    return _get_api_key() is not None


class ClinicalTrialAIService:
    """
    AI Service for Clinical Trial insights using Claude.
    
    Requires ANTHROPIC_API_KEY environment variable to be set.
    When not configured, AI features gracefully degrade to rule-based fallbacks.
    """

    def __init__(self):
        """
        Initialize the AI service.
        
        The Anthropic client is only initialized if a valid API key is configured.
        Check self.is_configured before making AI calls.
        """
        self.client = None
        self.is_configured = False
        self.model = "claude-sonnet-4-20250514"
        
        # Get API key securely from environment
        api_key = _get_api_key()
        
        if api_key:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
                self.is_configured = True
                logger.debug("Anthropic client initialized successfully")
            except Exception as e:
                # Log error without exposing key details
                logger.warning(f"Failed to initialize Anthropic client: {type(e).__name__}")
                self.is_configured = False
        else:
            logger.info(
                "ANTHROPIC_API_KEY not configured. AI features will use rule-based fallbacks. "
                "Set ANTHROPIC_API_KEY in your environment or .env file to enable AI features."
            )

    def generate_suggested_actions(self, study_id='Study_1', limit=3):
        """
        Generate AI-powered suggested actions for CRAs.

        Returns top priority actions based on current study data.
        Falls back to rule-based actions when AI is not configured.
        """
        # Gather evidence from database
        evidence = self._gather_study_evidence(study_id)

        # Graceful degradation: use fallback if AI not configured
        if not self.is_configured:
            logger.debug("AI not configured, using rule-based fallback for suggested actions")
            return self._fallback_actions(evidence, limit)

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
            # Log error without exposing sensitive details
            logger.warning(f"AI API error in generate_suggested_actions: {type(e).__name__}")
            # Fallback to rule-based actions
            return self._fallback_actions(evidence, limit)

    def generate_query_response_suggestion(self, query_id):
        """
        Generate AI suggestion for query response.

        Analyzes query context and suggests appropriate response.
        Returns a helpful fallback message when AI is not configured.
        """
        try:
            query = Query.objects.select_related('subject').get(query_id=query_id)
        except Exception:
            return {"error": "Query not found"}

        # Graceful degradation: return fallback if AI not configured
        if not self.is_configured:
            logger.debug("AI not configured, returning fallback for query suggestion")
            return {
                "query_id": query_id,
                "suggested_response": "AI suggestions unavailable. Please review query manually.",
                "confidence": "n/a",
                "requires_review": True,
                "ai_disabled": True,
                "message": "Set ANTHROPIC_API_KEY in .env to enable AI query suggestions."
            }

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
            logger.warning(f"AI API error in generate_query_response_suggestion: {type(e).__name__}")
            return {
                "query_id": query_id,
                "error": "AI service temporarily unavailable",
                "suggested_response": "Please review query manually."
            }

    def assess_subject_risk(self, subject_id):
        """
        AI-powered risk assessment for a subject.

        Analyzes all blockers and provides prioritized recommendations.
        Returns basic risk data when AI is not configured.
        """
        try:
            subject = Subject.objects.get(subject_id=subject_id)
            clean_status = CleanPatientStatus.objects.get(subject=subject)
            dqi_score = DQIScoreSubject.objects.get(subject=subject)
        except Exception:
            return {"error": "Subject data not found"}

        # Gather subject evidence
        evidence = self._gather_subject_evidence(subject, clean_status, dqi_score)

        # Graceful degradation: return basic assessment if AI not configured
        if not self.is_configured:
            logger.debug("AI not configured, returning rule-based risk assessment")
            return {
                "subject_id": subject_id,
                "risk_assessment": self._generate_fallback_assessment(evidence),
                "dqi_score": float(dqi_score.composite_dqi_score),
                "risk_band": dqi_score.risk_band,
                "is_clean": clean_status.is_clean,
                "ai_disabled": True,
                "message": "Set ANTHROPIC_API_KEY in .env to enable AI risk assessments."
            }

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
            logger.warning(f"AI API error in assess_subject_risk: {type(e).__name__}")
            return {
                "subject_id": subject_id,
                "error": "AI service temporarily unavailable",
                "risk_assessment": self._generate_fallback_assessment(evidence),
                "dqi_score": float(dqi_score.composite_dqi_score),
                "risk_band": dqi_score.risk_band,
                "is_clean": clean_status.is_clean
            }

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

    def _generate_fallback_assessment(self, evidence):
        """
        Generate a rule-based risk assessment when AI is not available.
        
        Provides basic analysis based on DQI score and blocker count.
        """
        risk_band = evidence.get('risk_band', 'Unknown')
        dqi_score = evidence.get('dqi_score', 0)
        blockers = evidence.get('blockers', [])
        is_clean = evidence.get('is_clean', False)
        
        # Build assessment text
        assessment_parts = []
        
        # Overall status
        if is_clean:
            assessment_parts.append(f"Subject is CLEAN with a DQI score of {dqi_score:.1f}%.")
        else:
            assessment_parts.append(f"Subject is BLOCKED with a DQI score of {dqi_score:.1f}% ({risk_band} risk).")
        
        # Blocker summary
        if blockers:
            assessment_parts.append(f"\n\nActive blockers ({len(blockers)}):")
            for blocker in blockers[:5]:  # Limit to 5 blockers
                assessment_parts.append(f"- {blocker}")
            if len(blockers) > 5:
                assessment_parts.append(f"  ...and {len(blockers) - 5} more")
        
        # Priority recommendation
        if risk_band == 'Critical':
            assessment_parts.append("\n\nRecommendation: Immediate attention required. Escalate to site coordinator.")
        elif risk_band == 'High':
            assessment_parts.append("\n\nRecommendation: Prioritize resolution within 48 hours.")
        elif risk_band == 'Medium':
            assessment_parts.append("\n\nRecommendation: Address blockers within the week.")
        else:
            assessment_parts.append("\n\nRecommendation: Monitor and maintain data quality.")
        
        assessment_parts.append("\n\n[Note: This is a rule-based assessment. Enable AI for detailed analysis.]")
        
        return "".join(assessment_parts)
