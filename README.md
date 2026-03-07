# 거래·세금 관리 시스템

## 실행 방법

```bash
cd invoice_system
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

브라우저에서 http://127.0.0.1:5001 접속.

## 폴더 구조

```
invoice_system/
├── app.py              # Flask 앱 진입점
├── config.py           # 설정
├── extensions.py       # SQLAlchemy 인스턴스
├── models.py           # Customer, Item, Transaction, TransactionItem
├── routes.py           # 라우트 (거래처/품목/거래/출력/PDF)
├── pdf_utils.py        # 납품서·청구서·견적서 PDF 생성
├── requirements.txt
├── instance/           # SQLite DB (자동 생성)
└── templates/
    ├── base.html
    ├── customers/      # list, form
    ├── items/          # list, form
    ├── transactions/   # list, form
    └── print/          # napum, cheonggu, gyeonjeok
```

## 기능

- 거래처: 추가/수정/삭제
- 품목: 추가/수정/삭제 (단가 입력)
- 거래 입력: 거래처 선택, 품목 여러 개 추가, 수량 입력 시 단가 자동 반영·공급가/부가세/합계 자동 계산
- 납품서·청구서·견적서: 화면 출력 + PDF 다운로드
