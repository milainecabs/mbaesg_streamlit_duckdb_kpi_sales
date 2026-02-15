# Dashboard KPI Sales (Streamlit + DuckDB)

## Présentation du projet

Ce projet propose un **dashboard interactif** développé avec **Streamlit**, permettant d’analyser trois jeux de données différents :

- 🛒 **Amazon** : produits, prix, remises, avis  
- 🍟 **McDonald’s** : données financières multi‑annuelles  
- 🍔 **Burger King** : indicateurs produits et attributs  

L’application utilise **DuckDB en mémoire** pour exécuter des requêtes SQL rapides et fiables, tout en offrant une interface visuelle moderne et intuitive.

---

## Installation & Exécution

### **Cloner le dépôt**

```bash
git clone https://github.com/milainecabs/mbaesg_streamlit_duckdb_kpi_sales.git
cd mbaesg_streamlit_duckdb_kpi_sales
```

---

### **Créer un environnement virtuel**

#### Sous Windows :

```bash
python -m venv venv
venv\Scripts\activate
```

#### Sous macOS / Linux :

```bash
python3 -m venv venv
source venv/bin/activate
```

---

### **Installer les dépendances**

```bash
pip install -r requirements.txt
```

---

### **Lancer l’application Streamlit**

```bash
streamlit run app.py
```

L’application s’ouvrira automatiquement dans votre navigateur.

---

## Fonctionnalités principales

### 🔍 Détection automatique du dataset
Le fichier CSV chargé est automatiquement classé en :
- `amazon`
- `mcdo`
- `burger_king`

Grâce au module `utils/detection.py`.

---

### 🛒 Amazon — Analyse complète
- KPI principaux :
  - Nombre de produits
  - Note moyenne
  - Prix moyen
  - Total des avis
  - Remise moyenne
  - Avis moyens par produit
- Graphiques :
  - 🏆 Top 10 des produits les plus populaires  
  - 📉 Scatter : **Prix vs Remise**  
  - 💰 Distribution des prix (densité)  
  - 🔥 Satisfaction par catégorie (palette personnalisée)

---

### McDonald’s — Analyse financière
- Nettoyage avancé des valeurs (dates, nombres, formats)
- KPI via SQL :
  - Chiffre d’affaires
  - Résultat opérationnel
  - Résultat net
- Graphiques dynamiques :
  - Revenus
  - Résultat opérationnel
  - Income statement
  - Assets
  - Store count
  - Comparaisons multi‑annuelles

---

### Burger King — Analyse attributaire
- KPI :
  - Nombre d’items
  - Nombre d’attributs
  - Nombre total d’entrées
- Graphique :
  - 🔥 Popularité des items (top valeurs)

---

## Architecture du projet

```
📦 mbaesg_streamlit_duckdb_kpi_sales
│
├── 📁 data/
│   ├── amazon.csv
│   ├── mcd.csv
│   └── bk.csv
│
├── 📁 utils/
│   ├── charts_amazon.py
│   ├── charts_mcdo.py
│   ├── charts_bk.py
│   ├── cleaning_data.py
│   └── detection.py
│
├── app.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Nettoyage des données

Chaque dataset bénéficie d’un nettoyage adapté :

### Amazon
- Conversion des colonnes numériques (`rating`, `discounted_price`, etc.)
- Extraction de `main_category`
- Gestion des valeurs manquantes

### McDonald’s
- Conversion des dates
- Nettoyage des valeurs financières (espaces, virgules, caractères spéciaux)
- Conversion en float

### Burger King
- Nettoyage des attributs
- Conversion des valeurs en numérique

---

## 🗄️ DuckDB — Pourquoi ce choix ?

- Ultra rapide  
- Parfait pour des requêtes SQL en mémoire  
- Idéal pour Streamlit (pas de fichier `.duckdb` nécessaire)  
- Uniformise l’analyse entre les trois datasets  

Chaque dataset est chargé ainsi :

```python
con = duckdb.connect(database=':memory:')
con.register("table_df", df)
con.execute("CREATE TABLE table AS SELECT * FROM table_df")
```

---

## Dépendances principales

- **Streamlit** — Interface web
- **DuckDB** — Moteur SQL en mémoire
- **Pandas** — Manipulation des données
- **Plotly Express** — Visualisations interactives

---

## Personnalisation visuelle

Le dashboard utilise :
- Des **KPI stylisés** (CSS custom)
- Une **palette personnalisée** pour Amazon :
  - Bleu foncé `#0A2A66`
  - Bleu clair `#4DA6FF`
  - Rouge `#E63946`
- Des graphes harmonisés pour une lecture fluide

---

## Auteurs

MEYOUDOM Milaine Cabrelle

TEUGOMO GEUVOU Irmeline

Thomas MARIE-ANNE

Thuy-Linh TO

SAMEDY Jeff



---

## Licence

Usage académique ou personnel.

