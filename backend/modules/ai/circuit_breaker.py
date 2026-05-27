import pybreaker
import logging

logger = logging.getLogger(__name__)

class CircuitBreakerListener(pybreaker.CircuitBreakerListener):
    def state_change(self, cb, old_state, new_state):
        logger.warning(f"Circuit Breaker state changed from {old_state} to {new_state}")

# Open circuit after 5 consecutive failures, wait 60 seconds before half-open
ai_circuit_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    listeners=[CircuitBreakerListener()]
)
