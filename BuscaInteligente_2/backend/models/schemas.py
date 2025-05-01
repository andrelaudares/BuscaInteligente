# Pydantic models for API request/response schemas

from pydantic import BaseModel
from typing import Optional, List

class Product(BaseModel):
    brand: Optional[str] = "Marca Desconhecida"
    title: str
    price: float
    store: str
    link: str
    query_date: Optional[str] = None # Será formatado depois
    image_url: Optional[str] = None # Campo adicionado para UI, opcional no CSV

class SearchResponse(BaseModel):
    results: List[Product] 