from __future__ import annotations

import socket


def is_connected(host: str = '8.8.8.8', port: int = 53, timeout: float = 2.0) -> bool:
    """Return True if we can reach the internet (DNS port on Google's resolver)."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
