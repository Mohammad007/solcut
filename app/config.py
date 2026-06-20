import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))  # backend/


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')

    # SQLite lives in backend/instance/slotcut.db (Flask creates the instance dir)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL', 'sqlite:///slotcut.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # OTP (mock | twilio | msg91)
    OTP_PROVIDER = os.getenv('OTP_PROVIDER', 'mock')
    OTP_MOCK_CODE = os.getenv('OTP_MOCK_CODE', '123456')
    OTP_EXPIRY_MINUTES = int(os.getenv('OTP_EXPIRY_MINUTES', '5'))
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_VERIFY_SID = os.getenv('TWILIO_VERIFY_SID')
    MSG91_AUTH_KEY = os.getenv('MSG91_AUTH_KEY')
    MSG91_TEMPLATE_ID = os.getenv('MSG91_TEMPLATE_ID')

    # Firebase FCM
    FIREBASE_CREDENTIALS_PATH = os.getenv(
        'FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json'
    )

    # Razorpay
    RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
    RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')

    # File upload — override UPLOAD_FOLDER to a mounted volume in production
    # (e.g. UPLOAD_FOLDER=/data/uploads on Railway) so images survive redeploys.
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'uploads'))
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

    # Direct app download (APK served from the server until store listings go live).
    # Drop the built APK at backend/downloads/<APK_FILENAME> (or a mounted volume).
    DOWNLOAD_FOLDER = os.getenv('DOWNLOAD_FOLDER', os.path.join(BASE_DIR, 'downloads'))
    APK_FILENAME = os.getenv('APK_FILENAME', 'SlotCut.apk')
    APP_VERSION = os.getenv('APP_VERSION', '1.0')

    # Admin panel
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'slotcut@admin123')

    # SocketIO async mode — 'threading' works on Python 3.13 with no extra deps.
    # Switch to 'eventlet' or 'gevent' for production (and install the matching pkg).
    SOCKETIO_ASYNC_MODE = os.getenv('SOCKETIO_ASYNC_MODE', 'threading')

    BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')

    # Queue tuning
    DEFAULT_AVG_SERVICE_MINUTES = int(os.getenv('DEFAULT_AVG_SERVICE_MINUTES', '8'))


class DevConfig(Config):
    DEBUG = True


class ProdConfig(Config):
    DEBUG = False
