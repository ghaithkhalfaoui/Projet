from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .db import execute, query
from .utils import delete_image, login_required, save_image

vendeur_bp = Blueprint("vendeur", __name__)

STATUTS_LIGNE = ["en_attente", "confirmee", "expediee", "livree", "annulee"]


@vendeur_bp.before_request
@login_required("vendeur")
def charger_boutique():
    g.boutique = query("SELECT * FROM boutiques WHERE owner_id = ?", (g.user["id"],), one=True)
    if g.boutique is None:
        abort(404)


def mon_produit(produit_id):
    p = query("SELECT * FROM produits WHERE id = ? AND boutique_id = ?", (produit_id, g.boutique["id"]), one=True)
    if not p:
        abort(404)
    return p


@vendeur_bp.route("/")
def dashboard():
    bid = g.boutique["id"]
    stats = {
        "produits": query("SELECT COUNT(*) n FROM produits WHERE boutique_id = ?", (bid,), one=True)["n"],
        "a_traiter": query("SELECT COUNT(*) n FROM commande_lignes WHERE boutique_id = ? AND statut = 'en_attente'",
                           (bid,), one=True)["n"],
        "ventes": query("""SELECT COALESCE(SUM(prix * quantite), 0) s FROM commande_lignes
                           WHERE boutique_id = ? AND statut != 'annulee'""", (bid,), one=True)["s"],
        "rupture": query("SELECT COUNT(*) n FROM produits WHERE boutique_id = ? AND stock = 0",
                         (bid,), one=True)["n"],
    }
    dernieres = query(
        """SELECT l.*, c.nom AS client, c.created_at FROM commande_lignes l
           JOIN commandes c ON c.id = l.commande_id
           WHERE l.boutique_id = ? ORDER BY l.id DESC LIMIT 6""",
        (bid,),
    )
    return render_template("vendeur/dashboard.html", stats=stats, dernieres=dernieres)


# ---------- Produits ----------

@vendeur_bp.route("/produits")
def produits():
    items = query("SELECT * FROM produits WHERE boutique_id = ? ORDER BY created_at DESC", (g.boutique["id"],))
    return render_template("vendeur/produits.html", produits=items)


@vendeur_bp.route("/produits/nouveau", methods=["GET", "POST"])
@vendeur_bp.route("/produits/<int:produit_id>/modifier", methods=["GET", "POST"])
def produit_form(produit_id=None):
    p = mon_produit(produit_id) if produit_id else None
    if request.method == "POST":
        f = request.form
        try:
            prix = float(f.get("prix", "").replace(",", "."))
            stock = int(f.get("stock", 0) or 0)
            assert prix >= 0 and stock >= 0
        except (ValueError, AssertionError):
            flash("Le prix et le stock doivent être des nombres positifs.", "error")
            return render_template("vendeur/produit_form.html", p=p, form=f)
        if not f.get("nom", "").strip():
            flash("Le nom du produit est obligatoire.", "error")
            return render_template("vendeur/produit_form.html", p=p, form=f)

        image = save_image(request.files.get("image"))
        valeurs = (f["nom"].strip(), f.get("description", "").strip(), prix, stock, 1 if f.get("actif") else 0)
        if p:
            if image:
                delete_image(p["image"])
            execute(
                "UPDATE produits SET nom=?, description=?, prix=?, stock=?, actif=?, image=? WHERE id=?",
                (*valeurs, image or p["image"], p["id"]),
            )
            flash("Produit modifié.", "success")
        else:
            execute(
                "INSERT INTO produits (nom, description, prix, stock, actif, image, boutique_id) VALUES (?,?,?,?,?,?,?)",
                (*valeurs, image, g.boutique["id"]),
            )
            flash("Produit ajouté.", "success")
        return redirect(url_for("vendeur.produits"))

    form = dict(p) if p else {"actif": 1, "stock": 1}
    return render_template("vendeur/produit_form.html", p=p, form=form)


@vendeur_bp.route("/produits/<int:produit_id>/supprimer", methods=["POST"])
def produit_supprimer(produit_id):
    p = mon_produit(produit_id)
    delete_image(p["image"])
    execute("DELETE FROM produits WHERE id = ?", (p["id"],))
    flash("Produit supprimé.", "success")
    return redirect(url_for("vendeur.produits"))


# ---------- Commandes recues ----------

@vendeur_bp.route("/commandes")
def commandes():
    lignes = query(
        """SELECT l.*, c.nom AS client, c.telephone, c.adresse, c.ville, c.created_at
           FROM commande_lignes l JOIN commandes c ON c.id = l.commande_id
           WHERE l.boutique_id = ? ORDER BY l.id DESC""",
        (g.boutique["id"],),
    )
    return render_template("vendeur/commandes.html", lignes=lignes, statuts=STATUTS_LIGNE)


@vendeur_bp.route("/commandes/<int:ligne_id>/statut", methods=["POST"])
def commande_statut(ligne_id):
    ligne = query("SELECT * FROM commande_lignes WHERE id = ? AND boutique_id = ?",
                  (ligne_id, g.boutique["id"]), one=True)
    statut = request.form.get("statut")
    if not ligne or statut not in STATUTS_LIGNE:
        abort(400)
    # Si la commande est annulee, on remet le produit en stock
    if statut == "annulee" and ligne["statut"] != "annulee" and ligne["produit_id"]:
        execute("UPDATE produits SET stock = stock + ? WHERE id = ?", (ligne["quantite"], ligne["produit_id"]))
    execute("UPDATE commande_lignes SET statut = ? WHERE id = ?", (statut, ligne_id))
    flash("Statut mis à jour.", "success")
    return redirect(url_for("vendeur.commandes"))


# ---------- Reglages de la boutique ----------

@vendeur_bp.route("/ma-boutique", methods=["GET", "POST"])
def reglages():
    if request.method == "POST":
        f = request.form
        if not f.get("nom", "").strip():
            flash("Le nom de la boutique est obligatoire.", "error")
        else:
            logo = save_image(request.files.get("logo"))
            if logo:
                delete_image(g.boutique["logo"])
            execute(
                "UPDATE boutiques SET nom=?, description=?, categorie=?, telephone=?, adresse=?, logo=? WHERE id=?",
                (f["nom"].strip(), f.get("description", "").strip(), f.get("categorie", "").strip(),
                 f.get("telephone", "").strip(), f.get("adresse", "").strip(),
                 logo or g.boutique["logo"], g.boutique["id"]),
            )
            flash("Boutique mise à jour.", "success")
            return redirect(url_for("vendeur.reglages"))
    return render_template("vendeur/reglages.html")
