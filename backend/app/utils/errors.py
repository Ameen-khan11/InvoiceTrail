from flask import jsonify


def error_response(message: str, status: int = 400, field: str | None = None):
    """Every error in this API looks like: {"error": "...", "field": "..."}
    `field` is omitted when the error isn't tied to one specific input.
    """
    body = {"error": message}
    if field:
        body["field"] = field
    return jsonify(body), status
