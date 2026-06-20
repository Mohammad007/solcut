from app import create_app
from app.extensions import db, socketio

app = create_app()


@app.shell_context_processor
def shell_context():
    from app import models
    return {'db': db, 'app': app, 'models': models}


if __name__ == '__main__':
    # Create tables on first run if the DB is empty (dev convenience).
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
