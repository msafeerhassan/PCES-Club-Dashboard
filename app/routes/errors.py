from flask import render_template, request, jsonify
from werkzeug.exceptions import HTTPException

MESSAGES = {
    400: ("Bad request", "Your session may have expired. Refresh the page and try again."),
    403: ("Not allowed", "You don't have permission to view this."),
    404: ("Not found", "That page doesn't exist."),
    413: ("File too large", "Uploads must be under 4 MB in total."),
    429: ("Slow down", "Too many attempts. Wait a minute and retry."),
    500: ("Something broke", "It's been logged. Try again shortly."),
}


def register_error_handlers(app):
    def handle(e):
        code = e.code if isinstance(e, HTTPException) else 500
        title, msg = MESSAGES.get(code, ("Error", "Something went wrong."))
        if request.path.startswith("/internal/"):
            return jsonify(error=title), code
        return render_template("errors/error.html", code=code, title=title, message=msg), code

    for c in MESSAGES:
        app.register_error_handler(c, handle)