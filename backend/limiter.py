# limiter.py — ElaConta v1.0
# Instância centralizada de rate limiting (slowapi)

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
