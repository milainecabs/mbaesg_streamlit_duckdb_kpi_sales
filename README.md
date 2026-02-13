🚀 Dashboard KPI Multi-Datasets (Amazon, BK, McDo)
Ce projet est une application d'analyse de données interactive permettant de visualiser des indicateurs clés (KPI) à partir de trois sources de données distinctes. L'application détecte automatiquement le type de fichier importé et adapte les analyses en conséquence.

📋 Fonctionnalités
Détection Automatique : Identifie si le fichier CSV provient d'Amazon, de Burger King ou de McDonald's en analysant les noms des colonnes.

Moteur DuckDB : Utilise DuckDB pour le stockage temporaire et la manipulation rapide des données.

Nettoyage de Données (Amazon) : Conversion automatique des prix (de devises ₹ vers float) et traitement des pourcentages et notations.

Visualisations Interactives : Graphiques Altair (Barres et Lignes) adaptés à chaque contexte métier.

🛠️ Stack Technique
Frontend : Streamlit

Analyse de données : Pandas

Moteur SQL : DuckDB

Visualisation : Altair

💻 Installation
1. Prérequis
Assurez-vous d'avoir Python 3.9 ou plus récent installé.

2. Configuration de l'environnement
PowerShell
# Activer l'environnement virtuel (déjà créé dans votre projet)
.\.venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
3. Lancement
PowerShell
streamlit run app.py
📖 Guide d'Utilisation
Importation : Utilisez la barre latérale (sidebar) pour uploader votre fichier CSV.

Analyse Amazon : Affiche les prix moyens (réduits vs réels), les remises moyennes et la répartition par catégorie de produits.

Analyse Fast Food :

Burger King : Visualisation des valeurs par item.

McDonald's : Analyse temporelle de l'évolution des valeurs.

📂 Structure du Projet
Plaintext
├── .venv/                # Environnement virtuel Python
├── app.py                # Code principal de l'application Streamlit
├── sales.duckdb          # Base de données locale DuckDB
├── requirements.txt      # Dépendances du projet
└── README.md             # Documentation

👥 Contributeurs
[Milaine, Thomas, Irmeline, Linh, Jeff]
