import os

from flask import Flask, g, session

from . import db


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.update(
        SITE_NAME="Mon Mall",
        SECRET_KEY=os.environ.get("SECRET_KEY", "changez-cette-cle-secrete"),
        # La base de donnees : fichier instance/mall.db
        DATABASE=os.path.join(app.instance_path, "mall.db"),
        # Photos des produits et logos des boutiques
        UPLOAD_FOLDER=os.path.join(app.root_path, "static", "uploads"),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,  # 5 Mo par photo
        # Compte admin cree au premier lancement
        ADMIN_EMAIL=os.environ.get("ADMIN_EMAIL", "admin@mall.tn"),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", "admin123"),
    )
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    app.teardown_appcontext(db.close_db)
    db.init_db(app)

    from .auth import auth_bp, load_user
    from .main import main_bp
    from .vendeur import vendeur_bp
    from .admin import admin_bp

    app.before_request(load_user)
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(vendeur_bp, url_prefix="/vendeur")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.template_filter("dt")
    def format_prix(value):
        """45.5 -> '45,500 DT' (dinar tunisien, 3 decimales)."""
        return f"{(value or 0):,.3f}".replace(",", " ").replace(".", ",") + " DT"

    @app.context_processor
    def inject_globals():
        panier = session.get("panier", {})
        return {
            "site_name": app.config["SITE_NAME"],
            "user": g.get("user"),
            "nb_panier": sum(panier.values()),
            "STATUTS": {
                "en_attente": "En attente",
                "approuvee": "Approuvée",
                "refusee": "Refusée",
                "suspendue": "Suspendue",
                "confirmee": "Confirmée",
                "expediee": "Expédiée",
                "livree": "Livrée",
                "annulee": "Annulée",
            },
        }

    return app
