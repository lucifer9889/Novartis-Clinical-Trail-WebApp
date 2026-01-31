"""
Blockchain Models for Audit Trail.

Stores immutable proofs of critical clinical trial events.
"""

from django.db import models
from django.utils import timezone
import hashlib
import json


class BlockchainTransaction(models.Model):
    """
    Represents a blockchain transaction for audit trail.

    In production, this would integrate with real blockchain (Ethereum, Hyperledger).
    For hackathon, this simulates blockchain concepts with cryptographic hashing.
    """

    # Transaction identification
    tx_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA-256 hash of transaction (simulates blockchain tx hash)"
    )

    block_number = models.IntegerField(
        help_text="Block number in chain"
    )

    # Event metadata
    event_type = models.CharField(
        max_length=100,
        choices=[
            ('DQI_COMPUTED', 'DQI Score Computed'),
            ('CLEAN_STATUS_UPDATED', 'Clean Status Updated'),
            ('QUERY_RESOLVED', 'Query Resolved'),
            ('SAE_REPORTED', 'SAE Reported'),
            ('DATABASE_LOCK', 'Database Lock Initiated'),
            ('STUDY_COMPLETION', 'Study Completion'),
            ('DATA_FREEZE', 'Data Freeze'),
            ('PROTOCOL_DEVIATION', 'Protocol Deviation Logged'),
        ],
        help_text="Type of clinical trial event"
    )

    event_description = models.TextField(
        help_text="Human-readable description of event"
    )

    # Data fingerprint
    data_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 hash of data snapshot"
    )

    data_snapshot = models.JSONField(
        help_text="Snapshot of data at time of event (for verification)"
    )

    # Chain linkage
    previous_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Hash of previous transaction (blockchain chain)"
    )

    # Timestamp
    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text="When transaction was recorded"
    )

    # Audit
    recorded_by = models.CharField(
        max_length=100,
        help_text="User or system that recorded this event"
    )

    # Verification
    verified = models.BooleanField(
        default=False,
        help_text="Whether transaction has been verified"
    )

    verification_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When transaction was verified"
    )

    class Meta:
        db_table = 'blockchain_transactions'
        ordering = ['-block_number', '-timestamp']
        indexes = [
            models.Index(fields=['event_type', '-timestamp']),
            models.Index(fields=['block_number']),
        ]

    def __str__(self):
        return f"Block {self.block_number}: {self.event_type} - {self.tx_hash[:16]}..."

    def verify_integrity(self):
        """
        Verify transaction integrity by recomputing hash.

        Returns True if data matches hash, False if tampered.
        """
        # Recompute data hash
        data_str = json.dumps(self.data_snapshot, sort_keys=True)
        computed_hash = hashlib.sha256(data_str.encode()).hexdigest()

        # Check if matches stored hash
        return computed_hash == self.data_hash

    def get_chain_position(self):
        """Get position in blockchain."""
        return f"Block #{self.block_number}"


class BlockchainAuditLog(models.Model):
    """
    High-level audit log linking business events to blockchain transactions.
    """

    # Link to blockchain transaction
    transaction = models.ForeignKey(
        BlockchainTransaction,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )

    # Business entity reference
    entity_type = models.CharField(
        max_length=50,
        help_text="Type of entity (Subject, Site, Study, Query, etc.)"
    )

    entity_id = models.CharField(
        max_length=100,
        help_text="ID of the entity"
    )

    # Event details
    action = models.CharField(
        max_length=100,
        help_text="Action performed"
    )

    changes = models.JSONField(
        null=True,
        blank=True,
        help_text="Before/after changes"
    )

    # Metadata
    performed_by = models.CharField(
        max_length=100,
        help_text="User who performed action"
    )

    timestamp = models.DateTimeField(
        default=timezone.now
    )

    class Meta:
        db_table = 'blockchain_audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['-timestamp']),
        ]

    def __str__(self):
        return f"{self.entity_type} {self.entity_id}: {self.action}"
