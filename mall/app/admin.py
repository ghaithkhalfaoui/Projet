from datetime import date, timedelta

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .db import execute, query
from .utils import login_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.before_request
@login_required("admin")
def proteger():
    pass


def compter(sql, args=()):
    return query(sql, args, one=True)[0]


@admin_bp.route("/")
def dashboard():
    stats = {
        "clients": compter("SELECT COUNT(*) FROM users WHERE role = 'client'"),
        "boutiques": compter("SELECT COUNT(*) FROM boutiques WHERE statut = 'approuvee'"),
        "en_attente": compter("SELECT COUNT(*) FROM boutiques WHERE statut = 'en_attente'"),
        "produits": compter("SELECT COUNT(*) FROM produits"),
        "commandes": compter("SELECT COUNT(*) FROM commandes"),
        "ventes": compter("SELECT COALESCE(SUM(prix * quantite), 0) FROM commande_lignes WHERE statut != 'annulee'"),
    }

    # Commandes des 7 derniers jours (pour le graphique)
    jours = [date.today() - timedelta(days=i) for i in range(6, -1, -1)]
    par_jour = dict(query(
        "SELECT date(created_at) d, COUNT(*) FROM commandes WHERE date(created_at) >= ? GROUP BY d",
        (jours[0].isoformat(),),
    ))
    chart = [{"label": j.strftime("%d/%m"), "value": par_jour.get(j.isoformat(), 0)} for j in jours]
    chart_max = max([c["value"] for c in chart] + [1])

    demandes = query(
        """SELECT b.*, u.nom AS proprietaire, u.email FROM boutiques b JOIN users u ON u.id = b.owner_id
           WHERE b.statut = 'en_attente' ORDER BY b.created_at"""
    )
    return render_template("admin/dashboard.html", stats=stats, chart=chart, chart_max=chart_max, demandes=demandes)


# ---------- Boutiques ----------

@admin_bp.route("/boutiques")
def boutiques():
    statut = request.args.get("statut", "")
    sql = """SELECT b.*, u.nom AS proprietaire, u.email,
                    (SELECT COUNT(*) FROM produits p WHERE p.boutique_id = b.id) AS nb_produits
             FROM boutiques b JOIN users u ON u.id = b.owner_id"""
    args = ()
    if statut:
        sql += " WHERE b.statut = ?"
        args = (statut,)
    return render_template("admin/boutiques.html", boutiques=query(sql + " ORDER BY b.created_at DESC", args),
                           filtre=statut)


@admin_bp.route("/boutiques/<int:boutique_id>/statut", methods=["POST"])
def boutique_statut(boutique_id):
    statut = request.form.get("statut")
    if statut not in ("approuvee", "refusee", "suspendue", "en_attente"):
        abort(400)
    execute("UPDATE boutiques SET statut = ? WHERE id = ?", (statut, boutique_id))
    messages = {"approuvee": "Boutique approuvée : elle est maintenant visible.",
                "refusee": "Boutique refusée.", "suspendue": "Boutique suspendue.",
                "en_attente": "Boutique remise en attente."}
    flash(messages[statut], "success")
    return redirect(request.referrer or url_for("admin.boutiques"))


# ---------- Utilisateurs ----------

@admin_bp.route("/utilisateurs")
def utilisateurs():
    role = request.args.get("role", "")
    sql, args = "SELECT * FROM users", ()
    if role:
        sql += " WHERE role = ?"
        args = (role,)
    return render_template("admin/utilisateurs.html", users=query(sql + " ORDER BY created_at DESC", args),
                           filtre=role)


@admin_bp.route("/utilisateurs/<int:user_id>/actif", methods=["POST"])
def utilisateur_actif(user_id):
    if user_id == g.user["id"]:
        flash("Vous ne pouvez pas désactiver votre propre compte.", "error")
    else:
        execute("UPDATE users SET actif = 1 - actif WHERE id = ?", (user_id,))
        flash("Compte mis à jour.", "success")
    return redirect(request.referrer or url_for("admin.utilisateurs"))


# ---------- Commandes ----------

@admin_bp.route("/commandes")
def commandes():
    items = query(
        """SELECT c.*, u.email,
                  (SELECT COUNT(*) FROM commande_lignes l WHERE l.commande_id = c.id) AS nb_articles,
                  (SELECT GROUP_CONCAT(DISTINCT b.nom) FROM commande_lignes l
                     JOIN boutiques b ON b.id = l.boutique_id WHERE l.commande_id = c.id) AS boutiques
           FROM commandes c JOIN users u ON u.id = c.client_id ORDER BY c.id DESC"""
    )
    return render_template("admin/commandes.html", commandes=items)
