"""Shared extension instances. Imported everywhere; initialised in the app factory."""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
# async_mode is set from config at init time (see create_app).
socketio = SocketIO(cors_allowed_origins="*")
cors = CORS()
limiter = Limiter(key_func=get_remote_address, default_limits=[])
