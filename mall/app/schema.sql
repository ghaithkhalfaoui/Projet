-- Structure de la base de donnees du mall (fichier : instance/mall.db)

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nom           TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    telephone     TEXT,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('client', 'vendeur', 'admin')),
    actif         INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS boutiques (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id    INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    nom         TEXT NOT NULL,
    description TEXT,
    categorie   TEXT,
    telephone   TEXT,
    adresse     TEXT,
    logo        TEXT,
    statut      TEXT NOT NULL DEFAULT 'en_attente'
                CHECK (statut IN ('en_attente', 'approuvee', 'refusee', 'suspendue')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS produits (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    boutique_id INTEGER NOT NULL REFERENCES boutiques(id) ON DELETE CASCADE,
    nom         TEXT NOT NULL,
    description TEXT,
    prix        REAL NOT NULL CHECK (prix >= 0),
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    image       TEXT,
    actif       INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS commandes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id  INTEGER NOT NULL REFERENCES users(id),
    total      REAL NOT NULL,
    nom        TEXT NOT NULL,
    telephone  TEXT NOT NULL,
    adresse    TEXT NOT NULL,
    ville      TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Une ligne par produit commande. Chaque vendeur gere le statut de ses propres lignes.
CREATE TABLE IF NOT EXISTS commande_lignes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    commande_id INTEGER NOT NULL REFERENCES commandes(id) ON DELETE CASCADE,
    produit_id  INTEGER REFERENCES produits(id) ON DELETE SET NULL,
    boutique_id INTEGER NOT NULL REFERENCES boutiques(id),
    nom_produit TEXT NOT NULL,
    prix        REAL NOT NULL,
    quantite    INTEGER NOT NULL,
    statut      TEXT NOT NULL DEFAULT 'en_attente'
                CHECK (statut IN ('en_attente', 'confirmee', 'expediee', 'livree', 'annulee'))
);
