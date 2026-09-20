import sqlite3
import pandas as pd
import streamlit as st
import random

# Configuration de la page
st.set_page_config(
    page_title="Suivi de mensurations", page_icon="📏", layout="wide"
)

# 1. Connexion / Création de la base de données SQLite
conn = sqlite3.connect("mensurations.db")
c = conn.cursor()

# Création de la table avec 'a_jeun' et 'regles' (INTEGER: 1 pour Vrai, 0 pour Faux)
c.execute("""
    CREATE TABLE IF NOT EXISTS mesures (
        profil TEXT,
        date TEXT,
        a_jeun INTEGER DEFAULT 1,
        regles INTEGER DEFAULT 0,
        poids REAL,
        poitrine REAL,
        taille REAL,
        bras REAL,
        poignet REAL,
        cuisse REAL,
        genou REAL,
        mollet REAL,
        PRIMARY KEY (profil, date)
    )
""")
conn.commit()

# Migration au cas où les nouvelles colonnes n'existent pas encore
for col, def_val in [("a_jeun", 1), ("regles", 0)]:
    try:
        c.execute(
            f"ALTER TABLE mesures ADD COLUMN {col} INTEGER DEFAULT {def_val}"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass  # La colonne existe déjà

# Titre principal
st.title("📏 Suivi des mensurations")

# --- CITATION DE MOTIVATION ---
citations = [
    "« Le succès, c'est la somme de petits efforts répétés jour après jour. »",
    "« La discipline est le pont entre vos objectifs et vos réalisations. »",
    "« La seule mauvaise séance est celle que tu ne fais pas. »",
    "« Chaque petit progrès compte. »",
    "« La régularité est la clé de la réussite. »"
]
st.info(random.choice(citations))
# ------------------------------

# 2. Sélecteur de profil et Formulaire dans la barre latérale
with st.sidebar:
    st.header("👤 Profil")
    profil_actif = st.selectbox("Choisir le profil :", ["Anaïs", "Manon"])

    st.divider()

    st.header(f"Nouvelle entrée ({profil_actif})")
    with st.form("form_mesures"):
        date_saisie = st.date_input("Date")

        st.markdown("**Conditions du relevé :**")
        a_jeun = st.checkbox("Prise de mesure à jeun 🥣", value=True)
        regles = st.checkbox("Période de règles 🩸", value=False)

        st.divider()

        poids = st.number_input("Poids (kg)", min_value=0.0, step=0.1)
        poitrine = st.number_input(
            "Tour de poitrine (cm)", min_value=0.0, step=0.5
        )
        taille = st.number_input("Tour de taille (cm)", min_value=0.0, step=0.5)
        bras = st.number_input("Tour de bras (cm)", min_value=0.0, step=0.5)
        poignet = st.number_input("Tour de poignet (cm)", min_value=0.0, step=0.5)
        cuisse = st.number_input("Tour de cuisse (cm)", min_value=0.0, step=0.5)
        genou = st.number_input("Tour de genou (cm)", min_value=0.0, step=0.5)
        mollet = st.number_input("Tour de mollet (cm)", min_value=0.0, step=0.5)

        bouton_valider = st.form_submit_button("Enregistrer")

    if bouton_valider:
        c.execute(
            """
            INSERT INTO mesures (profil, date, a_jeun, regles, poids, poitrine, taille, bras, poignet, cuisse, genou, mollet)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(profil, date) DO UPDATE SET
                a_jeun=excluded.a_jeun,
                regles=excluded.regles,
                poids=excluded.poids,
                poitrine=excluded.poitrine,
                taille=excluded.taille,
                bras=excluded.bras,
                poignet=excluded.poignet,
                cuisse=excluded.cuisse,
                genou=excluded.genou,
                mollet=excluded.mollet
        """,
            (
                profil_actif,
                str(date_saisie),
                1 if a_jeun else 0,
                1 if regles else 0,
                poids,
                poitrine,
                taille,
                bras,
                poignet,
                cuisse,
                genou,
                mollet,
            ),
        )
        conn.commit()
        st.success(f"Mesures enregistrées pour {profil_actif} !")
        st.rerun()

# 3. Récupération des données filtrées par profil
df = pd.read_sql_query(
    "SELECT date, a_jeun, regles, poids, poitrine, taille, bras, poignet, cuisse, genou, mollet FROM mesures WHERE profil = ? ORDER BY date ASC",
    conn,
    params=(profil_actif,),
)

st.subheader(f"📊 Tableau de bord — {profil_actif}")

if not df.empty:
    tab1, tab2 = st.tabs(["📈 Évolution (Graphiques)", "📊 Historique (Tableau)"])

    with tab1:
        st.subheader("Poids (kg)")
        st.line_chart(df.set_index("date")[["poids"]])

        st.subheader("Haut du corps (cm)")
        st.line_chart(
            df.set_index("date")[["poitrine", "taille", "bras", "poignet"]]
        )

        st.subheader("Bas du corps (cm)")
        st.line_chart(df.set_index("date")[["cuisse", "genou", "mollet"]])

    with tab2:
        st.subheader("Historique des relevés")

        # Conversion des champs binaires (1/0) en icônes claires
        df_display = df.copy()
        df_display["a_jeun"] = df_display["a_jeun"].apply(
            lambda x: "Oui ✅" if x == 1 else "Non ❌"
        )
        df_display["regles"] = df_display["regles"].apply(
            lambda x: "Oui 🩸" if x == 1 else "Non ⚪"
        )

        df_display = df_display.sort_values(
            by="date", ascending=False
        ).rename(
            columns={
                "date": "Date",
                "a_jeun": "À jeun",
                "regles": "Règles",
                "poids": "Poids (kg)",
                "poitrine": "Poitrine (cm)",
                "taille": "Taille (cm)",
                "bras": "Bras (cm)",
                "poignet": "Poignet (cm)",
                "cuisse": "Cuisse (cm)",
                "genou": "Genou (cm)",
                "mollet": "Mollet (cm)",
            }
        )
        st.dataframe(df_display, use_container_width=True)
else:
    st.info(
        f"Aucune donnée enregistrée pour {profil_actif}. Utilise le formulaire à gauche pour ajouter une première mesure !"
    )
