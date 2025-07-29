import os
from pathlib import Path


# Global Vars
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
gpuid = 0
tileSize = 192
inputType = "Image"

# From env
base_url = os.getenv("BASE_URL", "http://localhost:9000/static")
base_path = Path(os.getenv("BASE_PATH", "./"))
is_production = os.getenv("production") == "true"
