from pydantic import BaseModel
from typing import List, Dict, Any

class QueryResult(BaseModel):
    chartType: str
    data: List[Dict[str, Any]]
    headers: List[str]
    rows: List[List[Any]]
    maxValue: float
    sql: str
    raw: List[Dict[str, Any]]