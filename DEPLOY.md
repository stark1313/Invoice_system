# Render 배포 가이드

## 1. GitHub에 코드 올리기

```bash
cd /Users/stark1313/invoice_system
git add .
git commit -m "Render 배포 준비"
```

GitHub에서 새 저장소 생성 후:

```bash
git remote add origin https://github.com/본인아이디/invoice_system.git
git push -u origin main
```

## 2. Render에서 배포하기

1. [render.com](https://render.com) 접속 → **Sign Up** (GitHub로 가입)
2. **Dashboard** → **New** → **Web Service**
3. **Connect a repository** → GitHub에서 `invoice_system` 선택
4. 설정이 자동으로 채워짐 (render.yaml 사용 시)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT app:app`
5. **Create Web Service** 클릭
6. 2~3분 후 배포 완료 → URL 확인 (예: `https://invoice-system-xxx.onrender.com`)

## 3. (선택) 회사정보 환경변수 설정

Render 대시보드 → 해당 서비스 → **Environment** → **Add Environment Variable**

| Key | Value |
|-----|-------|
| SUPPLIER_NAME | 회사명 |
| SUPPLIER_BIZ_NO | 사업자번호 |
| SUPPLIER_ADDRESS | 주소 |
| SUPPLIER_PHONE | 전화번호 |
| SUPPLIER_FAX | 팩스 |
| SUPPLIER_CONTACT | 담당자 |

## 주의사항

- **무료 플랜**: 15분 미사용 시 슬립 → 첫 접속 시 30초~1분 대기
- **데이터**: SQLite 사용 시 재배포하면 DB 초기화됨 (영구 저장 필요 시 PostgreSQL 사용)
