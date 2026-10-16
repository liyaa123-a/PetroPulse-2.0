"""LOCAL PREVIEW ONLY: runs the real Flask API on an in-memory SQLite test database with demo data, so the UI can be
viewed without Oracle. Never used for deployment. Demo login: demo@petropulse.example / PreviewDemo1"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402
from app.seed import seed_demo  # noqa: E402
from tests.sqlite_backend import SqliteDatabase  # noqa: E402

db = SqliteDatabase()
s = db.session()
seed_demo(s, "PreviewDemo1")
s.commit()
app = create_app(Config(env="testing", secret_key="preview-only-" + "x" * 30, frontend_origins=["http://localhost:5173"], rate_limit_enabled=False), db)
app.run(port=5000, threaded=False)
