import sqlite3
import pandas as pd
import streamlit as st
import random
import numpy as np
import altair as alt

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

    # Attribution automatique de la taille selon le profil choisi
    tailles_profils = {
        "Anaïs": 167,
        "Manon": 160
    }
    taille_personne = tailles_profils[profil_actif]

    st.caption(f"📏 Taille enregistrée pour {profil_actif} : **{taille_personne} cm**")

    st.divider()

    st.header(f"Nouvelle entrée ({profil_actif})")
    with st.form("form_mesures"):
        date_saisie = st.date_input("Date")

        st.markdown("**Conditions du relevé :**")
        a_jeun = st.checkbox("Prise de mesure à jeun 🥣", value=True)
        regles = st.checkbox("Période de règles 🩸", value=False)

        st.divider()
        st.caption("💡 Laisse à 0.0 les mesures non prises (elles seront lissées sur le graphique).")

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
        def val_ou_none(valeur):
            return valeur if valeur > 0 else None

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
                val_ou_none(poids),
                val_ou_none(poitrine),
                val_ou_none(taille),
                val_ou_none(bras),
                val_ou_none(poignet),
                val_ou_none(cuisse),
                val_ou_none(genou),
                val_ou_none(mollet),
            ),
        )
        conn.commit()
        st.success(f"Mesures enregistrées pour {profil_actif} !")
        st.rerun()

# 3. Récupération des données filtrées par profil
df_raw = pd.read_sql_query(
    "SELECT date, a_jeun, regles, poids, poitrine, taille, bras, poignet, cuisse, genou, mollet FROM mesures WHERE profil = ? ORDER BY date ASC",
    conn,
    params=(profil_actif,),
)

st.subheader(f"📊 Tableau de bord — {profil_actif}")

if not df_raw.empty:
    cols_mesures = ["poids", "poitrine", "taille", "bras", "poignet", "cuisse", "genou", "mollet"]
    df = df_raw.copy()
    df[cols_mesures] = df[cols_mesures].replace(0, np.nan)

    # Lissage des données
    df_interp = df.copy()
    df_interp[cols_mesures] = df_interp[cols_mesures].interpolate(method='linear', limit_direction='both').ffill().bfill()

    # --- CARTES DE MÉTRIQUES (KPIs + IMC) ---
    st.markdown("##### 📌 Derniers résultats & Évolution")
    col1, col2, col3, col4, col5 = st.columns(5)

    derniere = df_interp.iloc[-1]
    precedente = df_interp.iloc[-2] if len(df_interp) > 1 else None

    # Poids
    poids_val = round(derniere["poids"], 1) if pd.notna(derniere["poids"]) else None
    delta_poids = round(derniere["poids"] - precedente["poids"], 1) if precedente is not None and pd.notna(derniere["poids"]) and pd.notna(precedente["poids"]) else None
    col1.metric(
        label="⚖️ Poids",
        value=f"{poids_val} kg" if poids_val else "—",
        delta=f"{delta_poids} kg" if delta_poids is not None else None,
        delta_color="inverse"
    )

    # Calcul IMC
    if poids_val:
        taille_m = taille_personne / 100
        imc = round(poids_val / (taille_m ** 2), 1)
        
        if imc < 18.5:
            cat_imc = "Insuffisance pondérale"
        elif 18.5 <= imc < 25:
            cat_imc = "Corpulence normale"
        elif 25 <= imc < 30:
            cat_imc = "Surpoids"
        else:
            cat_imc = "Obésité"

        delta_imc = None
        if precedente is not None and pd.notna(precedente["poids"]):
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
    taille_val = round(derniere["taille"], 1) if pd.notna(derniere["taille"]) else None
    delta_taille = round(derniere["taille"] - precedente["taille"], 1) if precedente is not None and pd.notna(derniere["taille"]) and pd.notna(precedente["taille"]) else None
    col3.metric(
        label="📏 Tour de taille",
        value=f"{taille_val} cm" if taille_val else "—",
        delta=f"{delta_taille} cm" if delta_taille is not None else None,
        delta_color="inverse"
    )

    # Tour de cuisse
    cuisse_val = round(derniere["cuisse"], 1) if pd.notna(derniere["cuisse"]) else None
    delta_cuisse = round(derniere["cuisse"] - precedente["cuisse"], 1) if precedente is not None and pd.notna(derniere["cuisse"]) and pd.notna(precedente["cuisse"]) else None
    col4.metric(
        label="🦵 Tour de cuisse",
        value=f"{cuisse_val} cm" if cuisse_val else "—",
        delta=f"{delta_cuisse} cm" if delta_cuisse is not None else None,
        delta_color="inverse"
    )

    # Nombre total de relevés
    col5.metric(
        label="📅 Relevés",
        value=f"{len(df_raw)}"
    )

    st.divider()

    # --- TAB1 / TAB2 ---
    tab1, tab2 = st.tabs(["📈 Évolution (Graphiques)", "📊 Historique (Tableau)"])

    # Fonction pour générer des graphiques avec axe Y ajusté
    def creer_graphique_ajuste(df_data, colonnes, titre_y):
        df_melted = df_data.melt(id_vars=["date"], value_vars=colonnes, var_name="Mesure", value_name="Valeur")
        
        # Calcul des bornes Min et Max pour caler l'axe Y
        val_min = df_melted["Valeur"].min()
        val_max = df_melted["Valeur"].max()
        
        if pd.isna(val_min) or pd.isna(val_max):
            domain_y = [0, 100]
        else:
            marge = max((val_max - val_min) * 0.15, 1.0)  # Marge d'aération
            domain_y = [max(0, round(val_min - marge, 1)), round(val_max + marge, 1)]

        chart = alt.Chart(df_melted).mark_line(point=True).encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("Valeur:Q", scale=alt.Scale(domain=domain_y), title=titre_y),
            color=alt.Color("Mesure:N", title="Légende"),
            tooltip=["date:T", "Mesure:N", "Valeur:Q"]
        ).properties(
            height=350
        ).interactive()

        return chart

    with tab1:
        st.subheader("Poids (kg)")
        st.altair_chart(creer_graphique_ajuste(df_interp, ["poids"], "Poids (kg)"), use_container_width=True)

        st.subheader("Haut du corps (cm)")
        st.altair_chart(creer_graphique_ajuste(df_interp, ["poitrine", "taille", "bras", "poignet"], "Mesure (cm)"), use_container_width=True)

        st.subheader("Bas du corps (cm)")
        st.altair_chart(creer_graphique_ajuste(df_interp, ["cuisse", "genou", "mollet"], "Mesure (cm)"), use_container_width=True)

    with tab2:
        st.subheader("Historique des relevés")

        df_display = df_raw.copy()
        df_display["a_jeun"] = df_display["a_jeun"].apply(
            lambda x: "Oui ✅" if x == 1 else "Non ❌"
        )
        df_display["regles"] = df_display["regles"].apply(
            lambda x: "Oui 🩸" if x == 1 else "Non ⚪"
        )

        df_display[cols_mesures] = df_display[cols_mesures].replace(0, np.nan).fillna("—")

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
