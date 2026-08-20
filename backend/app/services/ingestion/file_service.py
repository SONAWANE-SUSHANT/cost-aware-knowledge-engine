from pathlib import Path
import shutil


BASE_DIR = Path(__file__).resolve().parents[4]

RAW_DOCUMENTS_DIR = BASE_DIR / "documents" / "raw"

RAW_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


def save_uploaded_file(upload_file):
    file_path = RAW_DOCUMENTS_DIR / upload_file.filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    return file_path