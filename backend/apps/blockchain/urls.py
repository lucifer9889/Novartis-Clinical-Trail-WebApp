"""Blockchain API URLs."""

from django.urls import path
from . import views

app_name = 'blockchain'

urlpatterns = [
    path('stats/', views.blockchain_stats, name='blockchain-stats'),
    path('verify/', views.verify_chain, name='verify-chain'),
    path('history/', views.entity_history, name='entity-history'),
    path('transactions/', views.recent_transactions, name='recent-transactions'),
    path('verify-transaction/', views.verify_transaction, name='verify-transaction'),
]
