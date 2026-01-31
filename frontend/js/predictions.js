/**
 * Predictive AI Service
 *
 * Handles ML prediction API calls for Clinical Trial Control Tower.
 */

const PREDICTIONS_API_BASE = 'http://localhost:8000/api/v1/predictions';

class PredictiveAIService {
    /**
     * Get dropout risk prediction for subject
     *
     * @param {string} subjectId - Subject identifier
     * @returns {Promise<Object>} Prediction result with risk_probability, risk_level, confidence, top_drivers
     */
    async getDropoutRisk(subjectId) {
        try {
            const response = await fetch(
                `${PREDICTIONS_API_BASE}/dropout-risk/?subject_id=${subjectId}`
            );
            return await response.json();
        } catch (error) {
            console.error('Dropout prediction error:', error);
            return { error: 'Failed to get prediction' };
        }
    }

    /**
     * Get batch dropout risk predictions for multiple subjects
     *
     * @param {string} studyId - Study identifier (default: 'Study_1')
     * @param {number} limit - Maximum number of predictions (default: 10)
     * @returns {Promise<Object>} Batch predictions with count
     */
    async getBatchRiskPredictions(studyId = 'Study_1', limit = 10) {
        try {
            const response = await fetch(
                `${PREDICTIONS_API_BASE}/batch-risk/?study_id=${studyId}&limit=${limit}`
            );
            return await response.json();
        } catch (error) {
            console.error('Batch prediction error:', error);
            return { predictions: [], count: 0 };
        }
    }

    /**
     * Get enrollment forecast
     *
     * @param {string} studyId - Study identifier (default: 'Study_1')
     * @param {number} months - Months ahead to forecast (default: 6)
     * @returns {Promise<Object>} Forecast with historical and projected data
     */
    async getEnrollmentForecast(studyId = 'Study_1', months = 6) {
        try {
            const response = await fetch(
                `${PREDICTIONS_API_BASE}/enrollment-forecast/?study_id=${studyId}&months=${months}`
            );
            return await response.json();
        } catch (error) {
            console.error('Forecast error:', error);
            return { error: 'Failed to get forecast' };
        }
    }

    /**
     * Get query resolution time prediction
     *
     * @param {number} queryId - Query identifier
     * @returns {Promise<Object>} Prediction with estimated resolution days
     */
    async getQueryResolutionTime(queryId) {
        try {
            const response = await fetch(
                `${PREDICTIONS_API_BASE}/query-resolution-time/?query_id=${queryId}`
            );
            return await response.json();
        } catch (error) {
            console.error('Query prediction error:', error);
            return { error: 'Failed to get prediction' };
        }
    }

    /**
     * Get site performance prediction
     *
     * @param {string} siteNumber - Site number
     * @param {string} studyId - Study identifier (default: 'Study_1')
     * @returns {Promise<Object>} Prediction with DQI score and risk band
     */
    async getSitePerformance(siteNumber, studyId = 'Study_1') {
        try {
            const response = await fetch(
                `${PREDICTIONS_API_BASE}/site-performance/?site_number=${siteNumber}&study_id=${studyId}`
            );
            return await response.json();
        } catch (error) {
            console.error('Site performance prediction error:', error);
            return { error: 'Failed to get prediction' };
        }
    }
}

// Create global instance
const predictiveAI = new PredictiveAIService();

// Make it available globally
if (typeof window !== 'undefined') {
    window.predictiveAI = predictiveAI;
}
