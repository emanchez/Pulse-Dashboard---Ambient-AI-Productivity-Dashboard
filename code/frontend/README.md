# PersonalDash Frontend (scaffold)

Requirements
- Node: 20.x recommended
- npm: 8+

Quick start (local)

1. Install backend deps and start the backend (from repo root):

```bash
cd code/backend
python -m pip install -r requirements.txt
export PYTHONPATH=$(pwd)
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
```

2. Generate the TypeScript client (defaults to http://localhost:8000/openapi.json):

```bash
cd code/frontend
npm ci
./lib/generate-client.sh http://localhost:8000/openapi.json ./lib/generated
```

3. Start the frontend dev server:

```bash
npm run dev
```

Notes
- The generator script accepts an optional OPENAPI URL and output dir: `./lib/generate-client.sh [OPENAPI_URL] [OUT_DIR]`.
- CI runs the generator and build; ensure your local Node version matches CI (Node 20 recommended).
