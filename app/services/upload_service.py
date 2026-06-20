"""Local-filesystem image upload with resize. Served via /uploads/<...>."""
import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

from app.utils.helpers import allowed_file

# subfolder -> max dimension (px); image is downscaled to fit
SUBFOLDERS = {
    'avatars': 512,
    'covers': 1280,
    'portfolios': 1280,
    'style_boards': 1280,
    'services': 800,
    'barbers': 512,
    'reviews': 1024,
}


def save_image(file_storage, subfolder):
    """Validate, resize and persist an uploaded image. Returns absolute URL."""
    if subfolder not in SUBFOLDERS:
        raise ValueError(f'Invalid upload target: {subfolder}')
    if not file_storage or file_storage.filename == '':
        raise ValueError('No file provided')

    allowed = current_app.config['ALLOWED_EXTENSIONS']
    if not allowed_file(file_storage.filename, allowed):
        raise ValueError('File type not allowed')

    ext = secure_filename(file_storage.filename).rsplit('.', 1)[1].lower()
    fname = f'{uuid.uuid4().hex}.{ext}'
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, fname)

    max_dim = SUBFOLDERS[subfolder]
    try:
        from PIL import Image
        img = Image.open(file_storage.stream)
        img.thumbnail((max_dim, max_dim))
        if img.mode in ('RGBA', 'P') and ext in ('jpg', 'jpeg'):
            img = img.convert('RGB')
        img.save(path)
    except Exception:
        # If Pillow can't process it, fall back to raw save.
        file_storage.stream.seek(0)
        file_storage.save(path)

    base = current_app.config['BASE_URL'].rstrip('/')
    return f'{base}/uploads/{subfolder}/{fname}'
