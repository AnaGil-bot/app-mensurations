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

# Création de la table avec 'a_jeun' et 'regles'
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

# Migration automatique si besoin
for col, def_val in [("a_jeun", 1), ("regles", 0)]:
    try:
        c.execute(
            f"ALTER TABLE mesures ADD COLUMN {col} INTEGER DEFAULT {def_val}"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass

# Titre principal
st.title("📏 Suivi des mensurations")

# Citation de motivation
citations = [
    "« Le succès, c'est la somme de petits efforts répétés jour après jour. »",
    "« La discipline est le pont entre vos objectifs et vos réalisations. »",
    "« La seule mauvaise séance est celle que tu ne fais pas. »",
    "« Chaque petit progrès compte. »",
    "« La régularité est la clé de la réussite. »"
]
st.info(random.choice(citations))

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

        st.markdown("**Taille de référence (pour le calcul IMC) :**")
        taille_personne = st.number_input("Taille en cm (ex: 165)", min_value=100, max_value=230, value=165, step=1)

        st.divider()

        poids = st.number_input("Poids (kg)", min_value=0.0, step=0.1)
        poitrine = st.number_input("Tour de poitrine (cm)", min_value=0.0, step=0.5)
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
    # --- CARTES DE MÉTRIQUES (KPIs + IMC) ---
    st.markdown("##### 📌 Derniers résultats & Évolution")
    col1, col2, col3, col4, col5 = st.columns(5)

    derniere = df.iloc[-1]
    precedente = df.iloc[-2] if len(df) > 1 else None

    # Poids
    delta_poids = round(derniere["poids"] - precedente["poids"], 1) if precedente is not None and derniere["poids"] and precedente["poids"] else None
    col1.metric(
        label="⚖️ Poids",
        value=f"{derniere['poids']} kg" if derniere["poids"] else "—",
        delta=f"{delta_poids} kg" if delta_poids is not None else None,
        delta_color="inverse"
    )

    # Calcul IMC
    if derniere["poids"] and taille_personne:
        taille_m = taille_personne / 100
        imc = round(derniere["poids"] / (taille_m ** 2), 1)
        
        # Qualification OMS
        if imc < 18.5:
            cat_imc = "Insuffisance pondérale"
        elif 18.5 <= imc < 25:
            cat_imc = "Corpulence normale"
        elif 25 <= imc < 30:
            cat_imc = "Surpoids"
        else:
            cat_imc = "Obésité"

        # Calcul delta IMC si précédente existe
        delta_imc = None
        if precedente is not None and precedente["poids"]:
            imc_prec = round(precedente["poids"] / (taille_m ** 2), 1)
            delta_imc = round(imc - imc_prec, 1)

        col2.metric(
            label="📊 IMC",
            value=f"{imc}",
            delta=f"{cat_imc} ({delta_imc:+})" if delta_imc is not None else cat_imc,
            delta_color="inverse"
        )
    else:
        col2.metric(label="📊 IMC", value="—")

    # Tour de taille
    delta_taille = round(derniere["taille"] - precedente["taille"], 1) if precedente is not None and derniere["taille"] and precedente["taille"] else None
    col3.metric(
        label="📏 Tour de taille",
        value=f"{derniere['taille']} cm" if derniere["taille"] else "—",
        delta=f"{delta_taille} cm" if delta_taille is not None else None,
        delta_color="inverse"
    )

    # Tour de cuisse
    delta_cuisse = round(derniere["cuisse"] - precedente["cuisse"], 1) if precedente is not None and derniere["cuisse"] and precedente["cuisse"] else None
    col4.metric(
        label="🦵 Tour de cuisse",
        value=f"{derniere['cuisse']} cm" if derniere["cuisse"] else "—",
        delta=f"{delta_cuisse} cm" if delta_cuisse is not None else None,
        delta_color="inverse"
    )

    # Nombre total de relevés
    col5.metric(
        label="📅 Relevés",
        value=f"{len(df)}"
    )

    st.divider()

    # --- TAB1 / TAB2 ---
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
