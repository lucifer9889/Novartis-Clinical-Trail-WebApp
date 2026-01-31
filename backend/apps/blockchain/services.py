"""
Blockchain Service for Clinical Trial Control Tower.

Simulates blockchain concepts with cryptographic hashing.
In production, would integrate with Ethereum, Hyperledger, or other blockchain.
"""

import hashlib
import json
from django.utils import timezone
from django.db import models
from .models import BlockchainTransaction, BlockchainAuditLog


class BlockchainService:
    """
    Service for recording immutable proofs on blockchain.

    Simulates blockchain for hackathon demo.
    Production would use web3.py or similar for real blockchain.
    """

    def __init__(self):
        self.chain_name = "CTCT-Clinical-Trial-Chain"

    def record_event(self, event_type, event_description, data_snapshot,
                     entity_type=None, entity_id=None, performed_by='system'):
        """
        Record an event on the blockchain.

        Args:
            event_type: Type of event (DQI_COMPUTED, QUERY_RESOLVED, etc.)
            event_description: Human-readable description
            data_snapshot: Dict of data to record
            entity_type: Type of entity (Subject, Site, etc.)
            entity_id: ID of entity
            performed_by: User/system recording event

        Returns:
            BlockchainTransaction object
        """
        # Get latest block number
        latest_block = BlockchainTransaction.objects.order_by('-block_number').first()
        block_number = (latest_block.block_number + 1) if latest_block else 1

        # Get previous hash for chain linkage
        previous_hash = latest_block.tx_hash if latest_block else '0' * 64

        # Compute data hash (fingerprint)
        data_str = json.dumps(data_snapshot, sort_keys=True)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()

        # Compute transaction hash (simulates blockchain tx hash)
        # In real blockchain, this would be the actual transaction hash
        tx_content = f"{block_number}{event_type}{data_hash}{previous_hash}{timezone.now().isoformat()}"
        tx_hash = hashlib.sha256(tx_content.encode()).hexdigest()

        # Create blockchain transaction
        transaction = BlockchainTransaction.objects.create(
            tx_hash=tx_hash,
            block_number=block_number,
            event_type=event_type,
            event_description=event_description,
            data_hash=data_hash,
            data_snapshot=data_snapshot,
            previous_hash=previous_hash,
            recorded_by=performed_by,
            timestamp=timezone.now()
        )

        # Create audit log entry if entity specified
        if entity_type and entity_id:
            BlockchainAuditLog.objects.create(
                transaction=transaction,
                entity_type=entity_type,
                entity_id=entity_id,
                action=event_type,
                changes=data_snapshot,
                performed_by=performed_by
            )

        return transaction

    def record_dqi_computation(self, study_id, dqi_data):
        """Record DQI computation on blockchain."""
        return self.record_event(
            event_type='DQI_COMPUTED',
            event_description=f'DQI scores computed for {study_id}',
            data_snapshot={
                'study_id': study_id,
                'total_subjects': dqi_data.get('total_subjects', 0),
                'clean_percentage': str(dqi_data.get('clean_percentage', 0)),
                'composite_dqi': str(dqi_data.get('composite_dqi_score', 0)),
                'timestamp': timezone.now().isoformat()
            },
            entity_type='Study',
            entity_id=study_id,
            performed_by='DQI Computation Service'
        )

    def record_query_resolution(self, query_id, query_data):
        """Record query resolution on blockchain."""
        return self.record_event(
            event_type='QUERY_RESOLVED',
            event_description=f'Query {query_id} resolved',
            data_snapshot={
                'query_id': str(query_id),
                'log_number': query_data.get('log_number', ''),
                'resolution_date': query_data.get('resolution_date', ''),
                'resolved_by': query_data.get('resolved_by', ''),
                'response': query_data.get('response', '')[:100]  # First 100 chars
            },
            entity_type='Query',
            entity_id=str(query_id),
            performed_by=query_data.get('resolved_by', 'system')
        )

    def record_clean_status_update(self, subject_id, clean_status_data):
        """Record clean patient status update on blockchain."""
        return self.record_event(
            event_type='CLEAN_STATUS_UPDATED',
            event_description=f'Clean status updated for {subject_id}',
            data_snapshot={
                'subject_id': subject_id,
                'is_clean': clean_status_data.get('is_clean', False),
                'blockers_count': len(clean_status_data.get('blockers', [])),
                'dqi_score': str(clean_status_data.get('dqi_score', 0)),
                'timestamp': timezone.now().isoformat()
            },
            entity_type='Subject',
            entity_id=subject_id,
            performed_by='Clean Status Service'
        )

    def record_database_lock(self, study_id):
        """Record database lock event (critical compliance event)."""
        return self.record_event(
            event_type='DATABASE_LOCK',
            event_description=f'Database lock initiated for {study_id}',
            data_snapshot={
                'study_id': study_id,
                'lock_timestamp': timezone.now().isoformat(),
                'locked_by': 'Data Management',
                'reason': 'Study completion - final analysis'
            },
            entity_type='Study',
            entity_id=study_id,
            performed_by='Data Management'
        )

    def verify_chain_integrity(self):
        """
        Verify entire blockchain chain integrity.

        Returns:
            - is_valid: Boolean
            - broken_links: List of broken chain links
            - tampered_blocks: List of blocks with data tampering
        """
        transactions = BlockchainTransaction.objects.order_by('block_number')

        broken_links = []
        tampered_blocks = []

        previous_tx = None
        for tx in transactions:
            # Check data integrity
            if not tx.verify_integrity():
                tampered_blocks.append({
                    'block_number': tx.block_number,
                    'tx_hash': tx.tx_hash,
                    'reason': 'Data hash mismatch'
                })

            # Check chain linkage
            if previous_tx:
                if tx.previous_hash != previous_tx.tx_hash:
                    broken_links.append({
                        'block_number': tx.block_number,
                        'expected_previous': previous_tx.tx_hash,
                        'actual_previous': tx.previous_hash
                    })

            previous_tx = tx

        is_valid = len(broken_links) == 0 and len(tampered_blocks) == 0

        return {
            'is_valid': is_valid,
            'total_blocks': transactions.count(),
            'broken_links': broken_links,
            'tampered_blocks': tampered_blocks
        }

    def get_entity_history(self, entity_type, entity_id):
        """
        Get complete blockchain audit history for an entity.

        Returns chronological list of all blockchain-recorded events.
        """
        audit_logs = BlockchainAuditLog.objects.filter(
            entity_type=entity_type,
            entity_id=entity_id
        ).select_related('transaction').order_by('timestamp')

        history = []
        for log in audit_logs:
            history.append({
                'timestamp': log.timestamp.isoformat(),
                'action': log.action,
                'tx_hash': log.transaction.tx_hash,
                'block_number': log.transaction.block_number,
                'performed_by': log.performed_by,
                'changes': log.changes,
                'verified': log.transaction.verified
            })

        return history

    def get_blockchain_stats(self):
        """Get blockchain statistics."""
        total_blocks = BlockchainTransaction.objects.count()
        verified_blocks = BlockchainTransaction.objects.filter(verified=True).count()

        event_types = BlockchainTransaction.objects.values('event_type').annotate(
            count=models.Count('event_type')
        )

        latest_block = BlockchainTransaction.objects.order_by('-block_number').first()

        return {
            'total_blocks': total_blocks,
            'verified_blocks': verified_blocks,
            'verification_rate': (verified_blocks / total_blocks * 100) if total_blocks > 0 else 0,
            'latest_block_number': latest_block.block_number if latest_block else 0,
            'event_type_distribution': list(event_types),
            'chain_name': self.chain_name
        }
