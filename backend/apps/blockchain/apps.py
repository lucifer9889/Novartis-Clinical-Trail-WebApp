"""Blockchain app configuration."""

from django.apps import AppConfig


class BlockchainConfig(AppConfig):
    """Configuration for blockchain ledger app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.blockchain'
    verbose_name = 'Blockchain Ledger'
