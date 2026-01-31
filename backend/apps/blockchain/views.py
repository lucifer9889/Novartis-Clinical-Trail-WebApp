"""Blockchain API Views."""

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

    GET /api/v1/blockchain/stats/
    """
    service = BlockchainService()
    stats = service.get_blockchain_stats()

    return Response(stats)


@api_view(['GET'])
def verify_chain(request):
    """
    Verify blockchain chain integrity.

    GET /api/v1/blockchain/verify/
    """
    service = BlockchainService()
    verification = service.verify_chain_integrity()

    return Response(verification)


@api_view(['GET'])
def entity_history(request):
    """
    Get blockchain audit history for an entity.

    GET /api/v1/blockchain/history/?entity_type=Subject&entity_id=Study_1_0-001
    """
    entity_type = request.query_params.get('entity_type')
    entity_id = request.query_params.get('entity_id')

    if not entity_type or not entity_id:
        return Response(
            {'error': 'entity_type and entity_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )

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

    GET /api/v1/blockchain/transactions/?limit=20
    """
    limit = int(request.query_params.get('limit', 20))

    transactions = BlockchainTransaction.objects.order_by('-timestamp')[:limit]

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
            'data_intact': tx.verify_integrity()
        })

    return Response({
        'transactions': data,
        'count': len(data)
    })


@api_view(['POST'])
def verify_transaction(request):
    """
    Verify a specific transaction.

    POST /api/v1/blockchain/verify-transaction/
    Body: { "tx_hash": "..." }
    """
    tx_hash = request.data.get('tx_hash')

    if not tx_hash:
        return Response(
            {'error': 'tx_hash required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        tx = BlockchainTransaction.objects.get(tx_hash=tx_hash)

        # Verify data integrity
        is_valid = tx.verify_integrity()

        # Update verification status
        if is_valid and not tx.verified:
            from django.utils import timezone
            tx.verified = True
            tx.verification_timestamp = timezone.now()
            tx.save()

        return Response({
            'tx_hash': tx_hash,
            'is_valid': is_valid,
            'block_number': tx.block_number,
            'event_type': tx.event_type,
            'verified': tx.verified,
            'verification_timestamp': tx.verification_timestamp.isoformat() if tx.verification_timestamp else None
        })

    except BlockchainTransaction.DoesNotExist:
        return Response(
            {'error': 'Transaction not found'},
            status=status.HTTP_404_NOT_FOUND
        )
