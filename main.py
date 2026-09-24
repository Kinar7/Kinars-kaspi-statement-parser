import json
import sys
from datetime import datetime
from pathlib import Path

from excel_writer import write_to_excel
from parser import ParseError, parse_statement, read_pdf
from schemas import Metrics, ParseResponse, StatementData, TransactionDetail

OUTPUT_DIR = Path(__file__).parent / "output"


def iso(date):
    try:
        return datetime.strptime(date, "%d.%m.%Y").isoformat()
    except ValueError:
        return date


def make_response(st):
    details = [
        TransactionDetail(amount=t.amount, operationDate=t.operation_date,
                          transactionType=t.transaction_type, details=t.details)
        for t in st.transactions
    ]
    metrics = Metrics(
        from_date=iso(st.from_date),
        to_date=iso(st.to_date),
        statement_language=st.language,
        name=st.name,
        surname=st.surname,
        patronymic=st.patronymic,
        full_name=st.full_name,
        fin_institut=st.bank,
        card_number=st.card_number,
        number_account=st.account_number,
        avg_sum=st.avg_sum,
    )
    data = StatementData(
        financialInstitutionName=st.bank,
        cardNumber=st.card_number,
        fromDate=st.from_date,
        toDate=st.to_date,
        details=details,
        metrics=metrics,
        statementLanguage=st.language,
        fullName=st.full_name,
    )
    return ParseResponse(success=True, data=data)


def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = Path(input("Путь к pdf или txt с base64: ").strip().strip('"'))

    try:
        st = parse_statement(read_pdf(path))
        response = make_response(st)
    except (ParseError, OSError) as e:
        response = ParseResponse(success=False, msg=str(e), msgType="error")
    else:
        try:
            write_to_excel(st, OUTPUT_DIR / "statements.xlsx")
        except OSError as e:
            print("Не удалось записать Excel (возможно файл открыт):", e)

    result = json.dumps(response.model_dump(), ensure_ascii=False, indent=2)
    print(result)

    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "result.json").write_text(result, encoding="utf-8")
    print("\nСохранено в папку output")


if __name__ == "__main__":
    main()
    input("\nНажмите Enter для выхода")
