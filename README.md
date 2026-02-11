# Git Activity Dashboard

GitHub の活動データを自動収集し、Gemini API で分析・可視化するダッシュボードアプリケーション。

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16 (App Router) / TypeScript / Tailwind CSS v4 / Recharts |
| Backend | FastAPI / SQLAlchemy 2.0 (async) / Pydantic v2 |
| Database | PostgreSQL 17 (パーティション + マテリアライズドビュー) |
| External | GitHub REST API / Google Gemini API (gemini-2.5-flash) |
| Infra | Docker Compose / GitHub Actions CI |

## Features

- GitHub リポジトリ・コミット・PR の自動同期
- Gemini API によるコミット分析（技術タグ・作業カテゴリ分類）
- リポジトリごとの技術スタック自動検出
- ダッシュボード: コミット推移 / 言語比率 / リポジトリ別比率 / 時間帯ヒートマップ
- トレンド: 技術トレンド推移 / 作業カテゴリ比率
- JWT 認証 + AES-256-GCM によるトークン暗号化

## Prerequisites

- Docker & Docker Compose
- (ローカル開発時) Python 3.12 / Node.js 20+/ PostgreSQL 17

## Quick Start (Docker)

```bash
# 1. リポジトリをクローン
git clone <repo-url> && cd web_app

# 2. バックエンド環境変数を設定
cp backend/.env.example backend/.env
# backend/.env を編集: SECRET_KEY, ENCRYPTION_KEY, GEMINI_API_KEY を設定

# 3. 起動
docker compose up --build -d

# 4. DB マイグレーション
docker compose exec backend alembic upgrade head
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Local Development

### Backend

```bash
cd backend

# 仮想環境のセットアップ
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac

# 依存パッケージ
pip install -r requirements.txt

# DB マイグレーション
alembic upgrade head

# 起動
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend

npm install
npm run dev
```

http://localhost:3000 でアクセス。

## Testing

```bash
# Backend (38 tests)
cd backend
pytest tests/ -v

# Frontend (23 tests)
cd frontend
npx vitest run
```

## Project Structure

```
web_app/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI エントリポイント
│   │   ├── config.py            # 環境変数設定
│   │   ├── database.py          # SQLAlchemy async engine
│   │   ├── models/              # SQLAlchemy モデル (7 テーブル)
│   │   ├── api/v1/              # API エンドポイント
│   │   │   ├── auth.py          #   認証 (register/login/me)
│   │   │   ├── dashboard.py     #   ダッシュボードデータ
│   │   │   ├── settings.py      #   ユーザー設定
│   │   │   ├── sync.py          #   GitHub 同期トリガー
│   │   │   ├── repositories.py  #   リポジトリ一覧
│   │   │   └── summaries.py     #   週次サマリー
│   │   ├── services/            # ビジネスロジック
│   │   ├── external/            # 外部 API クライアント
│   │   │   ├── github_client.py #   GitHub REST API
│   │   │   └── gemini_client.py #   Gemini API
│   │   ├── core/                # セキュリティ・例外・レート制限
│   │   ├── tasks/               # バックグラウンドタスク
│   │   └── schemas/             # Pydantic スキーマ
│   ├── alembic/                 # DB マイグレーション
│   ├── tests/                   # pytest テスト
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/                 # ページ (/, /login, /settings, /trends)
│   │   ├── components/          # UI コンポーネント・チャート
│   │   ├── contexts/            # AuthContext
│   │   ├── hooks/               # データ取得フック
│   │   ├── lib/api/             # API クライアント
│   │   └── types/               # TypeScript 型定義
│   ├── vitest.config.ts
│   ├── Dockerfile
│   └── .env.example
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | ユーザー登録 |
| POST | `/api/v1/auth/login` | ログイン |
| GET | `/api/v1/auth/me` | 認証ユーザー情報 |
| GET | `/api/v1/dashboard/stats` | 統計カード |
| GET | `/api/v1/dashboard/commit-activity` | コミット推移 |
| GET | `/api/v1/dashboard/language-breakdown` | 言語比率 |
| GET | `/api/v1/dashboard/repository-breakdown` | リポジトリ別比率 |
| GET | `/api/v1/dashboard/hourly-heatmap` | 時間帯ヒートマップ |
| GET | `/api/v1/dashboard/tech-trends` | 技術トレンド |
| GET | `/api/v1/dashboard/category-breakdown` | 作業カテゴリ比率 |
| GET | `/api/v1/dashboard/repo-tech-stacks` | 技術スタック分析 |
| POST | `/api/v1/sync/trigger` | GitHub 同期実行 |
| GET | `/api/v1/repositories` | リポジトリ一覧 |
| GET | `/api/v1/settings` | ユーザー設定取得 |
| PUT | `/api/v1/settings` | ユーザー設定更新 |
| GET | `/api/v1/summaries/weekly` | 週次サマリー |

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL 接続 URL | `postgresql+asyncpg://postgres:postgres@localhost:5432/git_dashboard` |
| `SECRET_KEY` | JWT 署名キー | (必須) |
| `ENCRYPTION_KEY` | AES-256-GCM キー (64 hex chars) | (必須) |
| `GEMINI_API_KEY` | Google Gemini API キー | (必須) |
| `CORS_ORIGINS` | 許可オリジン (カンマ区切り) | `http://localhost:3000` |

### Frontend (`frontend/.env.local`)

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API の URL | `http://localhost:8000` |
