"""Production entrypoint for gunicorn (Railway).

    gunicorn --worker-class eventlet -w 1 wsgi:app --bind 0.0.0.0:$PORT

Unlike `run.py` (which only creates tables under `__main__`), gunicorn imports
this module, so we ensure the schema exists here. `create_all` is idempotent and
never drops data — safe to run on every boot. For a fresh DB you can also seed
demo data by setting SEED_ON_BOOT=1.
"""
import os

from app import create_app, models  # noqa: F401  (models import registers tables)
from app.config import ProdConfig
from app.extensions import db, socketio  # noqa: F401  (socketio used by gunicorn worker)

app = create_app(ProdConfig)

with app.app_context():
    db.create_all()
    if os.getenv('SEED_ON_BOOT') == '1':
        try:
            from app.seed import run_seed
            run_seed()
        except Exception as exc:  # pragma: no cover
            app.logger.warning(f'Seed skipped: {exc}')
