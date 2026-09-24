import base64
import io
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pdfplumber
from pypdf import PdfReader

DEPOSIT_WORDS = ["пополнение", "зачисление", "deposit", "credit"]

BANKS = {"kaspi": "Kaspi"}


class ParseError(Exception):
    pass


@dataclass
class Transaction:
    amount: float
    operation_date: str
    transaction_type: str
    details: str


@dataclass
class Statement:
    full_name: str = ""
    name: str = ""
    surname: str = ""
    patronymic: str = ""
    card_number: str = ""
    account_number: str = ""
    from_date: str = ""
    to_date: str = ""
    language: str = ""
    bank: str = ""
    transactions: list = field(default_factory=list)
    avg_sum: float = 0.0
    meta: dict = field(default_factory=dict)


def read_pdf(path):
    if path.suffix.lower() == ".pdf":
        return path.read_bytes()
    try:
        return base64.b64decode(path.read_text(encoding="utf-8").strip(), validate=True)
    except ValueError:
        raise ParseError("не получилось декодировать base64")


def get_meta(pdf_bytes):
    info = PdfReader(io.BytesIO(pdf_bytes)).metadata or {}
    meta = {}
    for key in ["title", "author", "subject", "producer", "creation_date", "modification_date"]:
        value = getattr(info, key, None)
        if value is None:
            meta[key] = ""
        elif isinstance(value, datetime):
            meta[key] = value.isoformat()
        else:
            meta[key] = str(value)
    return meta


def find(pattern, text):
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


def to_float(s):
    s = s.replace("\xa0", "").replace(" ", "").replace(",", ".")
    s = re.sub(r"[^0-9.\-+]", "", s)
    return float(s) if s else 0.0


def detect_language(text):
    lang = find(r"(?:Язык\s*выписки|Statement\s*language|Language)\s*[:\-]\s*(\w+)", text).lower()
    if lang.startswith(("rus", "рус")):
        return "rus"
    if lang.startswith(("eng", "англ")):
        return "eng"
    cyr = len(re.findall(r"[а-яА-ЯёЁ]", text))
    lat = len(re.findall(r"[a-zA-Z]", text))
    return "rus" if cyr >= lat else "eng"


def avg_deposit(transactions, to_date):
    try:
        end = datetime.strptime(to_date, "%d.%m.%Y")
    except ValueError:
        end = datetime.now()
    start = end - timedelta(days=183)  

    sums = []
    for t in transactions:
        tx_type = t.transaction_type.lower()
        is_deposit = False
        for w in DEPOSIT_WORDS:
            if w in tx_type:
                is_deposit = True
                break
        if not is_deposit:
            continue
        try:
            date = datetime.strptime(t.operation_date, "%d.%m.%Y")
        except ValueError:
            continue
        if date >= start:
            sums.append(t.amount)

    if not sums:
        return 0.0
    return round(sum(sums) / len(sums), 2)


def parse_statement(pdf_bytes):
    text = ""
    rows = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"
            for table in page.extract_tables():
                for row in table:
                    if row[0] and re.match(r"\d{2}\.\d{2}\.\d{4}", row[0]):
                        rows.append([c.strip() if c else "" for c in row])

    if not text.strip():
        raise ParseError("в pdf нет текста")

    st = Statement()
    st.full_name = find(r"(?:ФИО|Клиент|Full\s*name|Client)\s*[:\-]\s*(.+)", text)
    parts = st.full_name.split()
    if len(parts) > 0:
        st.surname = parts[0]
    if len(parts) > 1:
        st.name = parts[1]
    if len(parts) > 2:
        st.patronymic = parts[2]

    card = re.sub(r"\D", "", find(r"(?:Номер\s*карты|Card\s*number)\s*[:\-]\s*(.+)", text))
    st.card_number = card[-4:]
    st.account_number = find(r"(?:Номер\s*сч[её]та|Account\s*number|IBAN)\s*[:\-]\s*(\S+)", text)

    m = re.search(r"(?:Период|Period)\s*[:\-]\s*(\d{2}\.\d{2}\.\d{4})\s*(?:-|по|to)\s*(\d{2}\.\d{2}\.\d{4})",
                  text, re.IGNORECASE)
    if m:
        st.from_date, st.to_date = m.group(1), m.group(2)

    for key, bank_name in BANKS.items():
        if key in text.lower():
            st.bank = bank_name
            break

    st.language = detect_language(text)

    for row in rows:
        if len(row) >= 4:
            st.transactions.append(Transaction(to_float(row[1]), row[0], row[2], row[3]))

    st.avg_sum = avg_deposit(st.transactions, st.to_date)
    st.meta = get_meta(pdf_bytes)
    return st
