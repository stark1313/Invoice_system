# Invoice System 배포 가이드

## 1. 배포 옵션 요약

| 방식 | 난이도 | 비용 | 데이터 영속성 |
|------|--------|------|---------------|
| [Render.com](#1-rendercom) | 쉬움 | 무료~ | 재배포 시 DB/업로드 초기화* |
| [VPS 직접 배포](#2-vps-직접-배포) | 중간 | 서버 비용 | 영구 보존 |

\* Render 유료 플랜에서 Persistent Disk 추가 시 영속 가능

---

## 1. Render.com

이미 `render.yaml`이 설정되어 있어 GitHub 연동만 하면 됩니다.

### 1-1. 사전 준비

1. [Render](https://render.com) 회원가입
2. GitHub 저장소에 `invoice_system` 푸시

### 1-2. 배포 절차

1. Render 대시보드 → **New** → **Blueprint**
2. GitHub 저장소 연결 후 `render.yaml` 자동 인식
3. **Apply** 클릭

또는 **New** → **Web Service** 선택 후:

- **Build Command**: `pip install -r requirements.txt && mkdir -p instance`
- **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --log-level info app:app`
- **Environment**: `SECRET_KEY` (Generate 클릭)

### 1-3. 환경 변수 (선택)

Render 대시보드 → Service → **Environment**에서 추가:

| 변수 | 설명 | 예시 |
|------|------|------|
| `SECRET_KEY` | 세션 암호화 (필수) | Render 자동 생성 권장 |
| `SUPPLIER_NAME` | 공급자 상호 | (주)회사명 |
| `SUPPLIER_BIZ_NO` | 사업자번호 | 123-45-67890 |
| `SUPPLIER_ADDRESS` | 사업장 주소 | 서울시 ... |
| `SUPPLIER_PHONE` | 전화번호 | 02-1234-5678 |
| `SUPPLIER_FAX` | 팩스 | 02-1234-5679 |
| `SUPPLIER_CONTACT` | 담당자 | 홍길동 |

> 환경 변수로 설정하면 회사정보 기본값으로 사용됩니다. 배포 후 **회사정보** 메뉴에서 수정·직인 등록도 가능합니다.

### 1-4. Render 주의사항

- **무료 플랜**: 재배포·재시작 시 SQLite DB와 업로드(직인, 첨부파일)가 **초기화**됩니다.
- **데이터 유지**: 유료 플랜에서 [Persistent Disk](https://render.com/docs/disks)를 `instance` 경로에 마운트하면 DB·업로드가 유지됩니다.

---

## 2. VPS 직접 배포

Ubuntu 22.04 기준입니다.

### 2-1. 서버 준비

```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv nginx
```

### 2-2. 앱 배치

```bash
# 프로젝트 클론 (또는 scp/rsync로 업로드)
cd /opt
sudo git clone https://github.com/YOUR_USER/invoice_system.git
# 또는: sudo unzip invoice_system.zip -d invoice_system && cd invoice_system

cd invoice_system
sudo python3 -m venv venv
sudo venv/bin/pip install -r requirements.txt
sudo mkdir -p instance/uploads/documents instance/uploads/items
sudo chown -R www-data:www-data /opt/invoice_system  # nginx 사용자
```

### 2-3. 환경 변수

```bash
sudo nano /opt/invoice_system/.env
```

```
SECRET_KEY=여기에-강력한-랜덤-문자열-생성
SUPPLIER_NAME=(주)회사명
SUPPLIER_BIZ_NO=123-45-67890
SUPPLIER_ADDRESS=서울시 ...
SUPPLIER_PHONE=02-1234-5678
SUPPLIER_FAX=02-1234-5679
SUPPLIER_CONTACT=홍길동
```

`config.py`가 `.env`를 자동으로 로드합니다. 프로젝트 루트에 `.env` 파일을 두면 됩니다.

### 2-4. Gunicorn systemd 서비스

```bash
sudo nano /etc/systemd/system/invoice-system.service
```

```ini
[Unit]
Description=Invoice System
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/invoice_system
Environment="PATH=/opt/invoice_system/venv/bin"
EnvironmentFile=/opt/invoice_system/.env
ExecStart=/opt/invoice_system/venv/bin/gunicorn --bind 127.0.0.1:5001 --workers 2 --timeout 120 --log-level info app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable invoice-system
sudo systemctl start invoice-system
sudo systemctl status invoice-system
```

### 2-5. Nginx 리버스 프록시

```bash
sudo nano /etc/nginx/sites-available/invoice-system
```

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 또는 IP

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/invoice-system /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 2-6. HTTPS (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 3. 로컬 실행 (개발/테스트)

```bash
cd invoice_system
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

브라우저: http://127.0.0.1:5001

---

## 4. 배포 후 확인 사항

1. **회사정보**: `/company`에서 상호, 사업자번호, 대표, 주소, 직인 등 입력
2. **거래처·품목**: 데이터 등록
3. **직인**: 회사정보에서 PNG 이미지 업로드 (거래명세서·세금계산서 등에 사용)

---

## 5. 트러블슈팅

| 증상 | 확인 |
|------|------|
| 502 Bad Gateway | `systemctl status invoice-system` 확인, gunicorn 실행 여부 |
| DB 오류 | `instance/` 폴더 권한, `invoice.db` 존재 여부 |
| 직인/파일 업로드 안 됨 | `instance/uploads/` 생성 및 쓰기 권한 |
| 인쇄 시 레이아웃 깨짐 | 브라우저 인쇄 설정, PDF로 저장 후 확인 |
