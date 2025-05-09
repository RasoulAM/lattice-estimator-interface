from app import app, db  # Or whatever your main app file is named
with app.app_context():
    db.create_all()
