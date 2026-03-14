"""
Singleton slowapi Limiter instance shared across the application.

The default_limits=["200 per minute"] acts as a global limit for all routes
that are wrapped with SlowAPIMiddleware. Login has its own tighter limit
applied via @limiter.limit() in api/auth.py.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["200 per minute"])
