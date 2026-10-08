import os
import uuid
from functools import wraps

from flask import current_app, flash, g, redirect, request, url_for

IMAGES_AUTORISEES = {"png", "jpg", "jpeg", "webp", "gif"}


def login_required(*roles):
    """@login_required() pour tout utilisateur connecte, @login_required('admin') pour un role."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                flash("Connectez-vous pour continuer.", "error")
                return redirect(url_for("auth.connexion", next=request.full_path))
            if roles and g.user["role"] not in roles:
                flash("Vous n'avez pas accès à cette page.", "error")
                return redirect(url_for("main.index"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def save_image(file_storage):
    """Enregistre une image envoyee et renvoie son nom de fichier (ou None)."""
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in IMAGES_AUTORISEES:
        flash("Format d'image non accepté (png, jpg, jpeg, webp, gif).", "error")
        return None
    nom = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(current_app.config["UPLOAD_FOLDER"], nom))
    return nom


def delete_image(nom):
    if nom:
        chemin = os.path.join(current_app.config["UPLOAD_FOLDER"], nom)
        if os.path.exists(chemin):
            os.remove(chemin)
