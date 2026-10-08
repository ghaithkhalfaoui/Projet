from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for

from .db import get_db, query
from .utils import login_required

main_bp = Blueprint("main", __name__)

# Seuls les produits actifs des boutiques approuvees sont visibles par les visiteurs
PRODUITS_VISIBLES = """
    SELECT p.*, b.nom AS boutique_nom, b.id AS boutique_id
    FROM produits p JOIN boutiques b ON b.id = p.boutique_id
    WHERE p.actif = 1 AND b.statut = 'approuvee'
"""


@main_bp.route("/")
def index():
    boutiques = query("SELECT * FROM boutiques WHERE statut = 'approuvee' ORDER BY created_at DESC LIMIT 8")
    produits = query(PRODUITS_VISIBLES + " ORDER BY p.created_at DESC LIMIT 12")
    return render_template("index.html", boutiques=boutiques, produits=produits)


@main_bp.route("/boutiques")
def boutiques():
    q = request.args.get("q", "").strip()
    sql = "SELECT * FROM boutiques WHERE statut = 'approuvee'"
    args = ()
    if q:
        sql += " AND (nom LIKE ? OR categorie LIKE ? OR description LIKE ?)"
        args = (f"%{q}%",) * 3
    return render_template("boutiques.html", boutiques=query(sql + " ORDER BY nom", args), q=q)


@main_bp.route("/produits")
def produits():
    q = request.args.get("q", "").strip()
    sql, args = PRODUITS_VISIBLES, ()
    if q:
        sql += " AND (p.nom LIKE ? OR p.description LIKE ? OR b.nom LIKE ?)"
        args = (f"%{q}%",) * 3
    return render_template("produits.html", produits=query(sql + " ORDER BY p.created_at DESC", args), q=q)


@main_bp.route("/boutique/<int:boutique_id>")
def boutique(boutique_id):
    b = query("SELECT * FROM boutiques WHERE id = ?", (boutique_id,), one=True)
    proprietaire = g.user and b and g.user["id"] == b["owner_id"]
    if not b or (b["statut"] != "approuvee" and not proprietaire and not (g.user and g.user["role"] == "admin")):
        abort(404)
    produits = query("SELECT * FROM produits WHERE boutique_id = ? AND actif = 1 ORDER BY created_at DESC",
                     (boutique_id,))
    return render_template("boutique.html", b=b, produits=produits)


@main_bp.route("/produit/<int:produit_id>")
def produit(produit_id):
    p = query(PRODUITS_VISIBLES + " AND p.id = ?", (produit_id,), one=True)
    if not p:
        abort(404)
    autres = query(PRODUITS_VISIBLES + " AND b.id = ? AND p.id != ? LIMIT 4", (p["boutique_id"], p["id"]))
    return render_template("produit.html", p=p, autres=autres)


# ---------- Panier (garde dans la session du navigateur) ----------

def lire_panier():
    """Renvoie (lignes, total) a partir du panier de la session."""
    panier = session.get("panier", {})
    lignes, total = [], 0
    for pid, qte in list(panier.items()):
        p = query(PRODUITS_VISIBLES + " AND p.id = ?", (int(pid),), one=True)
        if not p or p["stock"] <= 0:
            panier.pop(pid)
            continue
        qte = min(qte, p["stock"])
        panier[pid] = qte
        lignes.append({"p": p, "qte": qte, "sous_total": p["prix"] * qte})
        total += p["prix"] * qte
    session["panier"] = panier
    return lignes, total


@main_bp.route("/panier")
def panier():
    lignes, total = lire_panier()
    return render_template("panier.html", lignes=lignes, total=total)


@main_bp.route("/panier/ajouter/<int:produit_id>", methods=["POST"])
def panier_ajouter(produit_id):
    p = query(PRODUITS_VISIBLES + " AND p.id = ?", (produit_id,), one=True)
    if not p or p["stock"] <= 0:
        flash("Ce produit n'est plus disponible.", "error")
        return redirect(request.referrer or url_for("main.index"))
    panier = session.get("panier", {})
    qte = max(1, int(request.form.get("qte", 1) or 1))
    panier[str(produit_id)] = min(panier.get(str(produit_id), 0) + qte, p["stock"])
    session["panier"] = panier
    flash(f"« {p['nom']} » ajouté au panier.", "success")
    return redirect(request.referrer or url_for("main.panier"))


@main_bp.route("/panier/modifier/<int:produit_id>", methods=["POST"])
def panier_modifier(produit_id):
    panier = session.get("panier", {})
    qte = int(request.form.get("qte", 0) or 0)
    if qte <= 0:
        panier.pop(str(produit_id), None)
    else:
        panier[str(produit_id)] = qte
    session["panier"] = panier
    return redirect(url_for("main.panier"))


# ---------- Commande ----------

@main_bp.route("/commander", methods=["GET", "POST"])
@login_required("client")
def commander():
    lignes, total = lire_panier()
    if not lignes:
        flash("Votre panier est vide.", "error")
        return redirect(url_for("main.panier"))

    if request.method == "POST":
        f = request.form
        champs = ["nom", "telephone", "adresse", "ville"]
        if not all(f.get(c, "").strip() for c in champs):
            flash("Merci de remplir toutes les informations de livraison.", "error")
            return render_template("commander.html", lignes=lignes, total=total, form=f)

        db = get_db()
        # Verifie le stock une derniere fois puis enregistre tout en une seule transaction
        for l in lignes:
            stock = db.execute("SELECT stock FROM produits WHERE id = ?", (l["p"]["id"],)).fetchone()["stock"]
            if stock < l["qte"]:
                flash(f"Stock insuffisant pour « {l['p']['nom']} ».", "error")
                return redirect(url_for("main.panier"))

        cid = db.execute(
            "INSERT INTO commandes (client_id, total, nom, telephone, adresse, ville) VALUES (?, ?, ?, ?, ?, ?)",
            (g.user["id"], total, *(f[c].strip() for c in champs)),
        ).lastrowid
        for l in lignes:
            db.execute(
                """INSERT INTO commande_lignes (commande_id, produit_id, boutique_id, nom_produit, prix, quantite)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (cid, l["p"]["id"], l["p"]["boutique_id"], l["p"]["nom"], l["p"]["prix"], l["qte"]),
            )
            db.execute("UPDATE produits SET stock = stock - ? WHERE id = ?", (l["qte"], l["p"]["id"]))
        db.commit()
        session["panier"] = {}
        flash(f"Merci ! Votre commande n° {cid} est enregistrée. Paiement à la livraison.", "success")
        return redirect(url_for("main.mes_commandes"))

    form = {"nom": g.user["nom"], "telephone": g.user["telephone"] or ""}
    return render_template("commander.html", lignes=lignes, total=total, form=form)


@main_bp.route("/mes-commandes")
@login_required("client")
def mes_commandes():
    commandes = query("SELECT * FROM commandes WHERE client_id = ? ORDER BY id DESC", (g.user["id"],))
    lignes = {}
    for c in commandes:
        lignes[c["id"]] = query(
            """SELECT l.*, b.nom AS boutique_nom FROM commande_lignes l
               JOIN boutiques b ON b.id = l.boutique_id WHERE l.commande_id = ?""",
            (c["id"],),
        )
    return render_template("mes_commandes.html", commandes=commandes, lignes=lignes)
