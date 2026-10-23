import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Тесты изолированы от локального .env, демо-базы и папки загрузок.
# В pydantic-settings переменные окружения имеют приоритет над значениями из .env.
_test_root = Path(tempfile.mkdtemp(prefix="alfa-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_test_root / 'test.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(_test_root / "uploads")
os.environ["BANK_INTERNAL_KEY"] = "test-bank-internal-key"

atexit.register(lambda: shutil.rmtree(_test_root, ignore_errors=True))
