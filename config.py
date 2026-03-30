import os

class Config:
    
    SECRET_KEY = os.environ.get("SECRET_KEY") or "super-secret-key"

    
    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://root:@localhost/estatelink_db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 
