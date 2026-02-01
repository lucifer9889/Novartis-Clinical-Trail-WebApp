"""
Blockchain API Views for Clinical Trial Control Tower.

This module provides REST API endpoints for blockchain-backed audit
trails and data integrity verification. The blockchain ensures immutable
records of all data modifications in the clinical trial.

API Endpoints:
- GET /api/v1/blockchain/stats/ - Overall blockchain statistics
- GET /api/v1/blockchain/verify/ - Verify chain integrity
- GET /api/v1/blockchain/history/ - Entity modification history
- GET /api/v1/blockchain/transactions/ - Recent transactions
- POST /api/v1/blockchain/verify-transaction/ - Verify specific transaction

Architecture Integration:
- Blockchain Audit Trail component
- Data fingerprinting (SHA-256 hashes)
- Immutable transaction recording
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services import BlockchainService
from .models import BlockchainTransaction, BlockchainAuditLog
from django.db import models


@api_view(['GET'])
def blockchain_stats(request):
    """
    Get blockchain statistics.
    
    Purpose: Returns aggregate statistics about the blockchain
             including total blocks, verification rates, and chain health.
    
    Inputs (query parameters): None required
    
    Outputs: JSON object containing:
        - total_blocks: Number of blocks in the chain
        - verified_blocks: Number of verified blocks
        - verification_rate: Percentage of verified blocks
        - chain_health: Overall chain health status
        - distribution: Block type distribution
    
    Side effects: None (read-only database queries)
    
    Usage: GET /api/v1/blockchain/stats/
    """
    # Initialize blockchain service
    service = BlockchainService()
    
    # Get aggregate statistics from the blockchain
    stats = service.get_blockchain_stats()

    return Response(stats)


@api_view(['GET'])
def verify_chain(request):
    """
    Verify blockchain chain integrity.
    
    Purpose: Performs a full integrity check on the blockchain,
             verifying all block hashes and links are valid.
    
    Inputs (query parameters): None required
    
    Outputs: JSON object containing:
        - is_valid: Boolean indicating if chain is intact
        - blocks_checked: Number of blocks verified
        - errors: List of any integrity errors found
        - verification_timestamp: When verification was performed
    
    Side effects:
        - Intensive database reads to verify all blocks
        - May update verification timestamps
    
    Usage: GET /api/v1/blockchain/verify/
    """
    # Initialize blockchain service
    service = BlockchainService()
    
    # Perform full chain integrity verification
    verification = service.verify_chain_integrity()

    return Response(verification)


@api_view(['GET'])
def entity_history(request):
    """
    Get blockchain audit history for an entity.
    
    Purpose: Retrieves the complete modification history for a
             specific entity (Subject, Site, Study, etc.) from
             the blockchain audit trail.
    
    Inputs (query parameters):
        - entity_type: Required. Type of entity (Subject, Site, Study)
        - entity_id: Required. ID of the entity to look up
    
    Outputs: JSON object containing:
        - entity_type: The queried entity type
        - entity_id: The queried entity ID
        - history: Array of audit events in chronological order
        - total_events: Count of events in history
    
    Side effects: None (read-only database queries)
    
    Usage: GET /api/v1/blockchain/history/?entity_type=Subject&entity_id=Study_1_0-001
    """
    # Extract and validate required parameters
    entity_type = request.query_params.get('entity_type')
    entity_id = request.query_params.get('entity_id')

    # Both parameters are required for history lookup
    if not entity_type or not entity_id:
        return Response(
            {'error': 'entity_type and entity_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Initialize blockchain service and fetch history
    service = BlockchainService()
    history = service.get_entity_history(entity_type, entity_id)

    return Response({
        'entity_type': entity_type,
        'entity_id': entity_id,
        'history': history,
        'total_events': len(history)
    })


@api_view(['GET'])
def recent_transactions(request):
    """
    Get recent blockchain transactions.
    
    Purpose: Returns the most recent transactions recorded on
             the blockchain, useful for monitoring and auditing.
    
    Inputs (query parameters):
        - limit: Maximum transactions to return (default: 20)
    
    Outputs: JSON object containing:
        - transactions: Array of transaction objects
        - count: Number of transactions returned
    
    Side effects: None (read-only database queries)
    
    Usage: GET /api/v1/blockchain/transactions/?limit=20
    """
    # Validate and parse limit parameter
    try:
        limit = int(request.query_params.get('limit', 20))
        limit = max(1, min(limit, 100))  # Clamp between 1 and 100
    except ValueError:
        limit = 20

    # Fetch recent transactions ordered by timestamp descending
    transactions = BlockchainTransaction.objects.order_by('-timestamp')[:limit]

    # Build response data with verification status
    data = []
    for tx in transactions:
        data.append({
            'tx_hash': tx.tx_hash,
            'block_number': tx.block_number,
            'event_type': tx.event_type,
            'event_description': tx.event_description,
            'timestamp': tx.timestamp.isoformat(),
            'recorded_by': tx.recorded_by,
            'verified': tx.verified,
            'data_intact': tx.verify_integrity()  # Re-verify on each read
        })

    return Response({
        'transactions': data,
        'count': len(data)
    })


@api_view(['POST'])
def verify_transaction(request):
    """
    Verify a specific transaction.
    
    Purpose: Verifies the integrity of a specific transaction
             by recalculating its hash and comparing with stored value.
    
    Inputs (request body):
        - tx_hash: Required. The transaction hash to verify
    
    Outputs: JSON object containing:
        - tx_hash: The verified transaction hash
        - is_valid: Boolean indicating if transaction is intact
        - block_number: Block containing the transaction
        - event_type: Type of event recorded
        - verified: Boolean if previously verified
        - verification_timestamp: When last verified
    
    Side effects:
        - May update transaction verification status
        - Database write if verification status changes
    
    Usage: 
        POST /api/v1/blockchain/verify-transaction/
        Body: { "tx_hash": "abc123..." }
    """
    # Extract tx_hash from request body
    tx_hash = request.data.get('tx_hash')

    # tx_hash is required for verification
    if not tx_hash:
        return Response(
            {'error': 'tx_hash required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Look up the transaction by hash
        tx = BlockchainTransaction.objects.get(tx_hash=tx_hash)

        # Verify data integrity by recalculating hash
        is_valid = tx.verify_integrity()

        # Update verification status if valid and not already verified
        if is_valid and not tx.verified:
            from django.utils import timezone
            tx.verified = True
            tx.verification_timestamp = timezone.now()
            tx.save()  # Side effect: database write

        return Response({
            'tx_hash': tx_hash,
            'is_valid': is_valid,
            'block_number': tx.block_number,
            'event_type': tx.event_type,
            'verified': tx.verified,
            'verification_timestamp': tx.verification_timestamp.isoformat() if tx.verification_timestamp else None
        })

    except BlockchainTransaction.DoesNotExist:
        # Return 404 if transaction not found
        return Response(
            {'error': 'Transaction not found'},
            status=status.HTTP_404_NOT_FOUND
        )
