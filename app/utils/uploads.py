import os

ALLOWED_EXT = {"pdf", "png", "jpg", "jpeg", "webp", "gif", "zip", "txt", "md", "py", "js", "ts", "html", "css", "json", "csv", "pptx", "docx", "ipynb"}
IMAGE_EXT = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_TOTAL_BYTES = 4 * 1024 * 1024


def _size(f):
    f.stream.seek(0, os.SEEK_END)
    n = f.stream.tell()
    f.stream.seek(0)
    return n


def validate_uploads(files, allowed=ALLOWED_EXT):
    """Return an error string, or None if every file is acceptable."""
    files = [f for f in files if f and f.filename]
    total = 0
    for f in files:
        ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if ext not in allowed:
            return f"'{f.filename}': file type .{ext or '?'} is not allowed."
        total += _size(f)
    if total > MAX_TOTAL_BYTES:
        return "Total upload size must be under 4 MB."
    return None