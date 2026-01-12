import asyncio
import time
from collections import deque
from typing import Optional


class RateLimiter:
    """
    A rate limiter that ensures requests don't exceed the specified rate.
    """
    
    def __init__(self, max_requests: int, time_window: int):
        """
        Initialize the rate limiter.
        
        :param max_requests: Maximum number of requests allowed
        :param time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        
    async def acquire(self):
        """
        Acquire permission to make a request, waiting if necessary.
        """
        current_time = time.time()
        
        # Remove requests that are outside the time window
        while self.requests and self.requests[0] <= current_time - self.time_window:
            self.requests.popleft()
        
        # If we've reached the limit, wait until we can make another request
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (current_time - self.requests[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                # Recursively call acquire to check the condition again after sleeping
                await self.acquire()
                return
        
        # Add the current request timestamp
        self.requests.append(current_time)


class RateLimitManager:
    """
    Manages multiple rate limiters for different endpoints or purposes.
    """
    
    def __init__(self):
        self.limiters = {}
    
    def get_limiter(self, name: str, max_requests: int, time_window: int) -> RateLimiter:
        """
        Get or create a rate limiter with the given name and configuration.
        """
        if name not in self.limiters:
            self.limiters[name] = RateLimiter(max_requests, time_window)
        return self.limiters[name]
    
    async def acquire(self, name: str):
        """
        Acquire permission from the named rate limiter.
        """
        if name not in self.limiters:
            raise ValueError(f"No rate limiter registered with name: {name}")
        await self.limiters[name].acquire()


# Global rate limit manager instance
rate_limit_manager = RateLimitManager()