import streamlit as st
from db import conectar
import pandas as pd

def tela_financeiro():
    st.header("Financeiro")

    conn = conectar()

    try:
        query = """
            SELECT 
                DATE(data_inicio) as Data,
                SUM(valor_final) as Total_dia,
                SUM(valor_pago) as Recebido_dia
            FROM alugueis
            WHERE data_inicio >= CURDATE() - INTERVAL 30 DAY
            GROUP BY DATE(data_inicio)
            ORDER BY Data DESC
        """

        df = pd.read_sql(query, conn)

        if df.empty:
            st.info("Nenhum dado encontrado.")
            return

        df = df.rename(columns={
            "Data": "Data",
            "Total_dia": "Total",
            "Recebido_dia": "Recebido"
        })

        total_geral = df["Total"].sum()
        recebido_geral = df["Recebido"].sum()

        col1, col2 = st.columns(2)
        col1.metric("Total (30 dias)", f"R$ {total_geral:,.2f}")
        col2.metric("Recebido (30 dias)", f"R$ {recebido_geral:,.2f}")

        df["Total"] = df["Total"].map(lambda x: f"R$ {x:,.2f}")
        df["Recebido"] = df["Recebido"].map(lambda x: f"R$ {x:,.2f}")

        st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            disabled=True
        )

    finally:
        conn.close()
