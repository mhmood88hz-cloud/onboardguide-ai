"""Gemeinsame Limiter-Instanz für Login/Signup – schützt vor Brute-Force."""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
