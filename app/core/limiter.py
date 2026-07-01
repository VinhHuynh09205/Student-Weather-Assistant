from slowapi import Limiter
from slowapi.util import get_remote_address

# Default limits of 100 requests per minute for overall APIs
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
