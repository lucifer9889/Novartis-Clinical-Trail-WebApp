"""
Blockchain API URL Configuration for Clinical Trial Control Tower.

This module defines URL patterns for the Blockchain Audit Trail
REST API endpoints. All routes here are prefixed with /api/v1/blockchain/
from the main urls.py.

API Endpoints:
- GET /api/v1/blockchain/stats/ - Overall chain statistics
- GET /api/v1/blockchain/verify/ - Full chain integrity verification
- GET /api/v1/blockchain/history/ - Entity modification history
- GET /api/v1/blockchain/transactions/ - Recent transactions
- POST /api/v1/blockchain/verify-transaction/ - Verify specific transaction

Integration: Uses SHA-256 data fingerprinting for integrity verification.
"""

from django.urls import path
from . import views

# Namespace for blockchain URLs (used with {% url 'blockchain:verify-chain' %})
app_name = 'blockchain'

# URL patterns for Blockchain Audit Trail API
# Each endpoint provides blockchain-backed data integrity features
urlpatterns = [
    # Overall blockchain statistics and health
    path('stats/', views.blockchain_stats, name='blockchain-stats'),
    
    # Full chain integrity verification
    path('verify/', views.verify_chain, name='verify-chain'),
    
    # Entity modification history lookup
    path('history/', views.entity_history, name='entity-history'),
    
    # Recent transactions listing
    path('transactions/', views.recent_transactions, name='recent-transactions'),
    
    # Single transaction verification (POST)
    path('verify-transaction/', views.verify_transaction, name='verify-transaction'),
]
