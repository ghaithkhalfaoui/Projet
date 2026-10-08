import sqlite3

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .db import execute, get_db, query
from .utils import login_required, save_image

auth_bp = Blueprint("auth", __name__)


def load_user():
    g.user = None
    uid = session.get("user_id")
    if uid:
        user = query("SELECT * FROM users WHERE id = ?", (uid,), one=True)
        if user and user["actif"]:
            g.user = user
        else:
            session.pop("user_id", None)


def connecter(user_id):
    """Ouvre la session de l'utilisateur en gardant le panier fait avant la connexion."""
    panier = session.get("panier", {})
    session.clear()
    session["user_id"] = user_id
    session["panier"] = panier


def lien_sur(nxt):
    """N'accepte que les liens internes au site (evite les redirections vers d'autres sites)."""
    if nxt and nxt.startswith("/") and not nxt.startswith("//"):
        return nxt
    return None


def page_apres_connexion(user):
    if user["role"] == "admin":
        return url_for("admin.dashboard")
    if user["role"] == "vendeur":
        return url_for("vendeur.dashboard")
    return url_for("main.index")


def verifier_compte(form):
    """Controle commun aux deux formulaires d'inscription. Renvoie une erreur ou None."""
    if not form.get("nom", "").strip() or not form.get("email", "").strip():
        return "Le nom et l'e-mail sont obligatoires."
    if len(form.get("password", "")) < 6:
        return "Le mot de passe doit faire au moins 6 caractères."
    if form.get("password") != form.get("password2"):
        return "Les deux mots de passe ne sont pas identiques."
    if query("SELECT id FROM users WHERE email = ?", (form["email"].strip().lower(),), one=True):
        return "Un compte existe déjà avec cet e-mail."
    return None


# ---------- Inscription client ----------

@auth_bp.route("/inscription", methods=["GET", "POST"])
def inscription():
    if request.method == "POST":
        erreur = verifier_compte(request.form)
        if erreur:
            flash(erreur, "error")
        else:
            uid = execute(
                "INSERT INTO users (nom, email, telephone, password_hash, role) VALUES (?, ?, ?, ?, 'client')",
                (
                    request.form["nom"].strip(),
                    request.form["email"].strip().lower(),
                    request.form.get("telephone", "").strip(),
                    generate_password_hash(request.form["password"]),
                ),
            )
            connecter(uid)
            flash("Bienvenue ! Votre compte client est créé.", "success")
            return redirect(lien_sur(request.args.get("next")) or url_for("main.index"))
    return render_template("auth/inscription.html", form=request.form)


# ---------- Inscription vendeur : ouvrir une boutique ----------

@auth_bp.route("/ouvrir-ma-boutique", methods=["GET", "POST"])
def ouvrir_boutique():
    if g.user and g.user["role"] != "client":
        return redirect(page_apres_connexion(g.user))

    if request.method == "POST":
        f = request.form
        erreur = None if g.user else verifier_compte(f)
        if not erreur and not f.get("boutique_nom", "").strip():
            erreur = "Le nom de la boutique est obligatoire."
        if erreur:
            flash(erreur, "error")
            return render_template("auth/ouvrir_boutique.html", form=f)

        db = get_db()
        try:
            if g.user:  # un client existant devient vendeur
                uid = g.user["id"]
                db.execute("UPDATE users SET role = 'vendeur' WHERE id = ?", (uid,))
            else:
                uid = db.execute(
                    "INSERT INTO users (nom, email, telephone, password_hash, role) VALUES (?, ?, ?, ?, 'vendeur')",
                    (
                        f["nom"].strip(),
                        f["email"].strip().lower(),
                        f.get("telephone", "").strip(),
                        generate_password_hash(f["password"]),
                    ),
                ).lastrowid
            db.execute(
                """INSERT INTO boutiques (owner_id, nom, description, categorie, telephone, adresse, logo)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    uid,
                    f["boutique_nom"].strip(),
                    f.get("description", "").strip(),
                    f.get("categorie", "").strip(),
                    f.get("boutique_telephone", "").strip(),
                    f.get("adresse", "").strip(),
                    save_image(request.files.get("logo")),
                ),
            )
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            flash("Impossible de créer la boutique. Réessayez.", "error")
            return render_template("auth/ouvrir_boutique.html", form=f)

        connecter(uid)
        flash("Votre demande est envoyée ! L'administrateur doit valider votre boutique. "
              "En attendant, vous pouvez déjà ajouter vos produits.", "success")
        return redirect(url_for("vendeur.dashboard"))

    return render_template("auth/ouvrir_boutique.html", form={})


# ---------- Connexion (clients, vendeurs et admin) ----------

@auth_bp.route("/connexion", methods=["GET", "POST"])
def connexion():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = query("SELECT * FROM users WHERE email = ?", (email,), one=True)
        if not user or not check_password_hash(user["password_hash"], request.form.get("password", "")):
            flash("E-mail ou mot de passe incorrect.", "error")
        elif not user["actif"]:
            flash("Ce compte est désactivé. Contactez l'administrateur.", "error")
        else:
            connecter(user["id"])
            return redirect(lien_sur(request.args.get("next")) or page_apres_connexion(user))
    return render_template("auth/connexion.html")


@auth_bp.route("/deconnexion")
def deconnexion():
    session.clear()
    return redirect(url_for("main.index"))


# ---------- Mon compte ----------

@auth_bp.route("/mon-compte", methods=["GET", "POST"])
@login_required()
def mon_compte():
    if request.method == "POST":
        if request.form.get("action") == "profil":
            execute(
                "UPDATE users SET nom = ?, telephone = ? WHERE id = ?",
                (request.form.get("nom", "").strip() or g.user["nom"],
                 request.form.get("telephone", "").strip(), g.user["id"]),
            )
            flash("Profil mis à jour.", "success")
        else:
            if not check_password_hash(g.user["password_hash"], request.form.get("actuel", "")):
                flash("Mot de passe actuel incorrect.", "error")
            elif len(request.form.get("nouveau", "")) < 6:
                flash("Le nouveau mot de passe doit faire au moins 6 caractères.", "error")
            else:
                execute("UPDATE users SET password_hash = ? WHERE id = ?",
                        (generate_password_hash(request.form["nouveau"]), g.user["id"]))
                flash("Mot de passe modifié.", "success")
        return redirect(url_for("auth.mon_compte"))
    return render_template("auth/mon_compte.html")
