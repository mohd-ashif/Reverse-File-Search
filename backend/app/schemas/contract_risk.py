from pydantic import BaseModel


class ContractRiskFlag(BaseModel):
    risk: str
    present: bool
    explanation: str


class ContractRiskAnalysis(BaseModel):
    file_id: int
    filename: str
    risks: list[ContractRiskFlag]
