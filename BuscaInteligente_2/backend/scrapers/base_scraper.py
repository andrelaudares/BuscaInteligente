from abc import ABC, abstractmethod
from typing import List, Dict, Any
import aiohttp
from bs4 import BeautifulSoup

class BaseScraper(ABC):
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    @abstractmethod
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Search for products in the specific store"""
        pass
    
    async def fetch_page(self, url: str) -> str:
        """Fetch page content asynchronously"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                return await response.text()
    
    def parse_price(self, price_str: str) -> float:
        """Parse price string to float"""
        try:
            # Remove currency symbols and spaces
            price_str = price_str.replace('R$', '').replace(' ', '')
            # Replace comma with dot for decimal
            price_str = price_str.replace(',', '.')
            # Remove any non-numeric characters except dot
            price_str = ''.join(c for c in price_str if c.isdigit() or c == '.')
            return float(price_str)
        except (ValueError, TypeError):
            return 0.0 