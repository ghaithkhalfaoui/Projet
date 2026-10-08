# Mon Mall — centre commercial en ligne

Plusieurs boutiques, un seul panier. Trois types de comptes :
- **Client** : achète dans toutes les boutiques.
- **Vendeur** : ouvre sa boutique, ajoute ses produits, gère ses commandes.
- **Admin** : valide les boutiques, gère les utilisateurs, voit toutes les commandes.

## Lancer le site (Windows, PowerShell)
Depuis le dossier `NProjet\mall` :
```
..\venv\Scripts\python.exe -m pip install -r requirements.txt
..\venv\Scripts\python.exe run.py
```
Puis ouvrez http://127.0.0.1:5000 (laissez le terminal ouvert).


## Compte administrateur
- Page : http://127.0.0.1:5000/connexion (la même pour tout le monde)
- E-mail : `admin@mall.tn`
- Mot de passe : `admin123`
- Après connexion, vous arrivez sur http://127.0.0.1:5000/admin
- **Changez le mot de passe** dans « Mon compte ».

## Fonctionnement
1. Un vendeur s'inscrit sur « Ouvrir ma boutique » → sa boutique est **en attente**.
2. L'admin l'**approuve** dans le tableau de bord → la boutique et ses produits deviennent visibles.
3. Un client ajoute des produits au panier, crée son compte et commande (paiement à la livraison).
4. Chaque vendeur voit les commandes de **sa** boutique et change le statut :
   en attente → confirmée → expédiée → livrée (ou annulée : le stock est remis).

## La base de données
Fichier SQLite : **`instance/mall.db`**, créé automatiquement au premier lancement.
Pour l'ouvrir : logiciel gratuit « DB Browser for SQLite ».
Pour repartir de zéro : arrêtez le site et supprimez ce fichier.
Les photos envoyées sont dans `app/static/uploads/`.

| Table             | Contenu                                   |
|-------------------|-------------------------------------------|
| users             | tous les comptes (client, vendeur, admin) |
| boutiques         | les boutiques et leur statut              |
| produits          | les produits de chaque boutique           |
| commandes         | les commandes des clients                 |
| commande_lignes   | les produits de chaque commande + statut  |

## Fichiers
```
run.py                    lance le site
app/__init__.py           réglages (nom du site, base, compte admin)
app/schema.sql            structure de la base de données
app/db.py                 connexion à la base
app/auth.py               inscription client, ouverture de boutique, connexion
app/main.py               accueil, boutiques, produits, panier, commandes
app/vendeur.py            espace vendeur
app/admin.py              espace admin
app/templates/            les pages HTML
app/static/css/style.css  design du site (couleurs en haut du fichier)
app/static/css/dash.css   design des espaces vendeur et admin
```
Pour changer le nom « Mon Mall » : `SITE_NAME` dans `app/__init__.py`.
