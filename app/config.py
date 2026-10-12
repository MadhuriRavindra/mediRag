import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM = "HS256"
TOKEN_MINUTES = 30
DATABASE_URL = "sqlite:///./medirag.db"
MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 15