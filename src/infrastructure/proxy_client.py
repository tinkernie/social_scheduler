# src/infrastructure/proxy_client.py
import httpx
import random
from typing import List, Optional

class ProxyManager:
    def __init__(self, proxies: Optional[List[str]] = None):
        self.proxies = proxies or []

    def pick(self) -> Optional[str]:
        if not self.proxies:
            return None
        return random.choice(self.proxies)

class ExternalAPIClient:
    def __init__(self, proxy_manager: Optional[ProxyManager] = None, timeout: int = 60):
        self.proxy_manager = proxy_manager
        self.timeout = timeout

    async def post(self, url, headers=None, json=None, files=None):
        proxy = self.proxy_manager.pick() if self.proxy_manager else None
        async with httpx.AsyncClient(proxies=proxy, timeout=self.timeout) as client:
            r = await client.post(url, headers=headers, json=json, files=files)
            r.raise_for_status()
            return r.json()

    async def get(self, url, headers=None, params=None):
        proxy = self.proxy_manager.pick() if self.proxy_manager else None
        async with httpx.AsyncClient(proxies=proxy, timeout=self.timeout) as client:
            r = await client.get(url, headers=headers, params=params)
            r.raise_for_status()
            return r.json()
