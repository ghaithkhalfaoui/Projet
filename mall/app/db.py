"""Connexion a la base de donnees SQLite (aucune librairie a installer)."""
import os
import sqlite3

from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, args=(), one=False):
    rows = get_db().execute(sql, args).fetchall()
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def init_db(app):
    with app.app_context():
        db = get_db()
        with open(os.path.join(os.path.dirname(__file__), "schema.sql"), encoding="utf-8") as f:
            db.executescript(f.read())

        # Cree le compte administrateur la premiere fois
        if not query("SELECT id FROM users WHERE role = 'admin'", one=True):
            execute(
                "INSERT INTO users (nom, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
                (
                    "Administrateur",
                    app.config["ADMIN_EMAIL"],
                    generate_password_hash(app.config["ADMIN_PASSWORD"]),
                ),
            )
            print(f" * Compte admin cree : {app.config['ADMIN_EMAIL']} / {app.config['ADMIN_PASSWORD']}")
        close_db()
