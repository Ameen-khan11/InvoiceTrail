from flask_jwt_extended import get_jwt_identity


def current_user_id() -> int:
    """The JWT identity is always a string (Flask-JWT-Extended requirement),
    so every caller needs this cast. Centralizing it here means nobody
    forgets and nobody does it inconsistently.
    """
    return int(get_jwt_identity())


def scoped_or_404(model, record_id, user_id=None):
    """The ONE way any row is ever fetched by id in this app.

    WRONG (the bug this whole project is designed to teach):
        obj = Model.query.get(record_id)

    RIGHT (this function):
        obj = scoped_or_404(Model, record_id)

    Returns the row if it exists AND belongs to the current user, else None.
    Callers turn a None into a 404 - never a 403, so an attacker can't even
    tell whether the id exists at all.
    """
    uid = user_id if user_id is not None else current_user_id()
    return model.query.filter_by(id=record_id, user_id=uid).first()
