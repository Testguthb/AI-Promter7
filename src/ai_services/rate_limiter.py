import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter to control API request frequency with Claude Sonnet 4 limits."""
    
    def __init__(self, max_requests_per_minute: int = 1000, 
                 max_input_tokens_per_minute: int = 450000,
                 max_output_tokens_per_minute: int = 90000):
        self.max_requests_per_minute = max_requests_per_minute
        self.max_input_tokens_per_minute = max_input_tokens_per_minute
        self.max_output_tokens_per_minute = max_output_tokens_per_minute
        self.request_times = []
        self.input_token_usage = []
        self.output_token_usage = []
        self.semaphore = asyncio.Semaphore(1)  # Single request at a time to avoid duplicates
        self.last_request_time = 0
        self.min_request_interval = 0.1  # Minimal interval for single request processing
    
    async def acquire(self, estimated_input_tokens: int = 4000, estimated_output_tokens: int = 2000):
        """Acquire permission to make an API request with Claude Sonnet 4 limits."""
        async with self.semaphore:
            current_time = time.time()
            
            # Enforce minimum interval between requests
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - time_since_last)
                current_time = time.time()
            
            # Clean old entries (older than 1 minute)
            cutoff_time = current_time - 60
            self.request_times = [t for t in self.request_times if t > cutoff_time]
            self.input_token_usage = [(t, tokens) for t, tokens in self.input_token_usage if t > cutoff_time]
            self.output_token_usage = [(t, tokens) for t, tokens in self.output_token_usage if t > cutoff_time]
            
            # Check request rate limit
            if len(self.request_times) >= self.max_requests_per_minute:
                wait_time = 60 - (current_time - self.request_times[0]) + 1
                logger.info(f"Request rate limit reached, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
                current_time = time.time()
            
            # Check input token rate limit
            current_input_usage = sum(tokens for _, tokens in self.input_token_usage)
            if current_input_usage + estimated_input_tokens > self.max_input_tokens_per_minute:
                wait_time = 60 - (current_time - self.input_token_usage[0][0]) + 1
                logger.info(f"Input token rate limit reached, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
                current_time = time.time()
            
            # Check output token rate limit
            current_output_usage = sum(tokens for _, tokens in self.output_token_usage)
            if current_output_usage + estimated_output_tokens > self.max_output_tokens_per_minute:
                wait_time = 60 - (current_time - self.output_token_usage[0][0]) + 1
                logger.info(f"Output token rate limit reached, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
                current_time = time.time()
            
            # Record this request
            self.request_times.append(current_time)
            self.input_token_usage.append((current_time, estimated_input_tokens))
            self.output_token_usage.append((current_time, estimated_output_tokens))
            self.last_request_time = current_time


# Global rate limiter instance
claude_rate_limiter = RateLimiter()