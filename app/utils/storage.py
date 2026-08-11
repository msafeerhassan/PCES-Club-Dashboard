import requests
import uuid


def upload_submission_file(app, file_storage):
    if file_storage is None or file_storage.filename == "":
        return None, None

    ext = file_storage.filename.rsplit(".", 1)[-1] if "." in file_storage.filename else "bin"
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    url = f"{app.config['SUPABASE_URL']}/storage/v1/object/{app.config['SUPABASE_STORAGE_BUCKET']}/{unique_name}"
    headers = {
        "Authorization": f"Bearer {app.config['SUPABASE_SERVICE_ROLE_KEY']}",
        "Content-Type": file_storage.content_type or "application/octet-stream",
    }

    resp = requests.put(url, headers=headers, data=file_storage.read())
    if resp.status_code not in (200, 201):
        return None, None

    public_url = f"{app.config['SUPABASE_URL']}/storage/v1/object/public/{app.config['SUPABASE_STORAGE_BUCKET']}/{unique_name}"
    return public_url, file_storage.filename


def upload_submission_files(app, file_storage_list):
    results = []
    for f in file_storage_list:
        url, name = upload_submission_file(app, f)
        if url:
            results.append((url, name))
    return results