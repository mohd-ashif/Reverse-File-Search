from pydantic import BaseModel


class FileCompareRequest(BaseModel):
    file_id_a: int
    file_id_b: int


class FileCompareResult(BaseModel):
    file_a: str
    file_b: str
    summary: str
    differences: list[str]
    added_clauses: list[str]
    removed_clauses: list[str]
    financial_changes: list[str]
