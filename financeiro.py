import streamlit as st
import pandas as pd
from db import conectar

def tela_financeiro():
    st.header("Painel Financeiro")

    if st.session_state.get('usuario_nome') != "pedro":
            st.error("Acesso restrito.")
            return

    conn = conectar()

    try:
        df = pd.read_sql("""
            SELECT 
                SUM(valor_final) as total,
                SUM(valor_pago) as recebido
            FROM alugueis
            WHERE data_inicio >= CURDATE() - INTERVAL 30 DAY
              AND data_inicio <= NOW()
        """, conn)

        total = float(df['total'].iloc[0] or 0)
        recebido = float(df['recebido'].iloc[0] or 0)
        pendente = total - recebido

        c1, c2, c3 = st.columns(3)

        c1.metric("Faturamento Bruto", f"R$ {total:,.2f}")
        c2.metric("Total Recebido", f"R$ {recebido:,.2f}")
        c3.metric("Pendente", f"R$ {pendente:,.2f}")

        st.divider()

        df_detalhado = pd.read_sql("""
            SELECT 
                DATE(data_inicio) as Data,
                SUM(valor_final) as Total_dia,
                SUM(valor_pago) as Recebido_dia
            FROM alugueis
            WHERE data_inicio >= CURDATE() - INTERVAL 30 DAY
                AND data_inicio <= NOW()
            GROUP BY DATE(data_inicio)
            ORDER BY Data DESC
        """, conn)

        if not df_detalhado.empty:
            df_detalhado = df_detalhado.rename(columns={
                "Total_dia": "Total",
                "Recebido_dia": "Recebido"
            })

            st.subheader("Últimos 30 dias")

            st.data_editor(
                df_detalhado,
                use_container_width=True,
                hide_index=True,
                disabled=True
            )
        else:
            st.info("Sem dados financeiros nos últimos 30 dias.")

    finally:
        conn.close()
