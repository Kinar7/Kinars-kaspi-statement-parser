from typing import List, Optional

from pydantic import BaseModel


class TransactionDetail(BaseModel):
    amount: float
    operationDate: str
    transactionType: str
    details: str


class Metrics(BaseModel):
    from_date: str
    to_date: str
    statement_language: str
    name: str
    surname: str
    patronymic: str
    full_name: str
    fin_institut: str
    card_number: str
    number_account: str
    avg_sum: float


class StatementData(BaseModel):
    financialInstitutionName: str
    cardNumber: str
    fromDate: str
    toDate: str
    details: List[TransactionDetail]
    metrics: Metrics
    statementLanguage: str
    fullName: str


class ParseResponse(BaseModel):
    success: bool
    msg: Optional[str] = None
    msgType: Optional[str] = None
    data: Optional[StatementData] = None
