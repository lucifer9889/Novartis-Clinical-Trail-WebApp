/**
 * Blockchain Service
 *
 * Handles blockchain verification and audit trail for Clinical Trial Control Tower.
 */

const BLOCKCHAIN_API_BASE = 'http://localhost:8000/api/v1/blockchain';

class BlockchainService {
    /**
     * Get blockchain statistics
     *
     * @returns {Promise<Object>} Blockchain stats with total_blocks, verification_rate, etc.
     */
    async getStats() {
        try {
            const response = await fetch(`${BLOCKCHAIN_API_BASE}/stats/`);
            return await response.json();
        } catch (error) {
            console.error('Blockchain stats error:', error);
            return { error: 'Failed to get blockchain stats' };
        }
    }

    /**
     * Verify blockchain chain integrity
     *
     * @returns {Promise<Object>} Verification result with is_valid, broken_links, tampered_blocks
     */
    async verifyChain() {
        try {
            const response = await fetch(`${BLOCKCHAIN_API_BASE}/verify/`);
            return await response.json();
        } catch (error) {
            console.error('Chain verification error:', error);
            return { error: 'Failed to verify chain' };
        }
    }

    /**
     * Get entity audit history
     *
     * @param {string} entityType - Type of entity (Subject, Site, Query, etc.)
     * @param {string} entityId - Entity identifier
     * @returns {Promise<Object>} Audit history with events
     */
    async getEntityHistory(entityType, entityId) {
        try {
            const response = await fetch(
                `${BLOCKCHAIN_API_BASE}/history/?entity_type=${entityType}&entity_id=${entityId}`
            );
            return await response.json();
        } catch (error) {
            console.error('History error:', error);
            return { history: [] };
        }
    }

    /**
     * Get recent blockchain transactions
     *
     * @param {number} limit - Maximum number of transactions to retrieve
     * @returns {Promise<Object>} Recent transactions with count
     */
    async getRecentTransactions(limit = 20) {
        try {
            const response = await fetch(
                `${BLOCKCHAIN_API_BASE}/transactions/?limit=${limit}`
            );
            return await response.json();
        } catch (error) {
            console.error('Transactions error:', error);
            return { transactions: [] };
        }
    }

    /**
     * Verify a specific transaction
     *
     * @param {string} txHash - Transaction hash to verify
     * @returns {Promise<Object>} Verification result
     */
    async verifyTransaction(txHash) {
        try {
            const response = await fetch(
                `${BLOCKCHAIN_API_BASE}/verify-transaction/`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ tx_hash: txHash })
                }
            );
            return await response.json();
        } catch (error) {
            console.error('Transaction verification error:', error);
            return { error: 'Failed to verify transaction' };
        }
    }
}

// Create global instance
const blockchainService = new BlockchainService();

// Make it available globally
if (typeof window !== 'undefined') {
    window.blockchainService = blockchainService;
}
