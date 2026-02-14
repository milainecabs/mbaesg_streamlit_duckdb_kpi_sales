# 🏛️ Dashboard d'Analyse Multi-Datasets (Sales Analytics)<br>
## 📋 Présentation du Projet<br>
Ce dashboard est une plateforme d'aide à la décision centralisée permettant d'analyser les performances de géants du commerce et de la restauration. Il permet aux analystes d'explorer des données provenant de **Amazon, McDonald's et Burger King** au sein d'une interface unique et intelligente.

## 🚀 Architecture Technique<br>
**1. Détection Intelligente** (utils/detection.py)<br>
Le système identifie le type de dataset dès l'importation en analysant la structure des colonnes :

**Amazon :** Identification par les IDs produits et les métriques d'évaluation.

**McDo :** Identification par les indicateurs financiers et le nombre de restaurants.

**Burger King :** Identification par les attributs temporels et la popularité des items.

**2. Nettoyage Dynamique** (utils/cleaning_data.py)<br>
Une pipeline de traitement assure la fiabilité des analyses :

**Extraction Numérique :** Utilisation de Regex pour isoler les valeurs calculables (suppression des symboles ₹, $, %, etc.).

**Ciblage par Mots-Clés :** Nettoyage automatique basé sur le nom des colonnes (price, rating, count).

## 📖 Mode d'Emploi <br>
**Lancement :** Exécutez streamlit run app.py dans votre terminal.

**Importation :** Chargez un fichier CSV compatible via la barre latérale.

**Exploration :** Le dashboard adapte ses graphiques instantanément. Utilisez les filtres (catégories, années) pour affiner votre analyse.

**Lecture :** Les indicateurs clés (KPIs) et les graphiques interactifs Plotly s'affichent automatiquement.

## 🛠️ Maintenance et Évolutions<br>
Le projet est conçu de manière modulaire pour faciliter les modifications :

**Ajouter un graphique :** Intervenez dans le fichier correspondant dans le dossier utils/ (ex: charts_bk.py).

**Modifier le nettoyage :** La logique globale de traitement se trouve dans utils/cleaning_data.py.

**Ajuster l'interface :** Le fichier principal app.py gère le layout et le style CSS des KPIs.

**Base de données :** Les requêtes SQL performantes sont gérées via duckdb_utils.py ou db_manager.py.

## ⚡ Installation rapide<br>
PowerShell
pip install streamlit pandas plotly duckdb
streamlit run app.py