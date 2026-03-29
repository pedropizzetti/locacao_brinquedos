import streamlit as st
import pandas as pd
from datetime import datetime, time
from db import conectar
from utils import formatar_zap

def tela_agenda():
    st.subheader("Roteiro de Entregas")

    data_sel = st.date_input("Data", datetime.now())
    busca = st.text_input("Buscar")

    conn = conectar()

    inicio = datetime.combine(data_sel, time.min)
    fim = datetime.combine(data_sel, time.max)

    df = pd.read_sql("""
        SELECT c.nome_completo as Cliente,
               c.whatsapp as Fone,
               a.observacoes as Endereco,
               COALESCE(b.nome, a.observacoes) as Brinquedo,
               a.quantidade,
               a.data_inicio as Inicio,
               a.valor_final,
               a.valor_pago,
               a.grupo_id
        FROM alugueis a
        JOIN clientes c ON a.cliente_id = c.id
        LEFT JOIN brinquedos b ON a.brinquedo_id = b.id
        WHERE a.data_inicio BETWEEN %s AND %s
    """, conn, params=(inicio, fim))

    if df.empty:
        st.info("Sem reservas")
        return

    grupos = df.groupby("grupo_id")

    for g_id, grupo in grupos:
        total = grupo["valor_final"].sum()
        pago = grupo["valor_pago"].sum()
        restante = total - pago

        nome = grupo["Cliente"].iloc[0]
        hora = grupo["Inicio"].iloc[0]

        with st.expander(f"{nome} - R$ {total:.2f}"):
            for _, item in grupo.iterrows():
                st.write(f"{item['Brinquedo']} x{item['quantidade']}")

            st.write(f"Restante: R$ {restante:.2f}")

            if restante > 0:
                if st.button("Quitar", key=g_id):
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE alugueis 
                        SET valor_pago = valor_final
                        WHERE grupo_id = %s
                    """, (g_id,))
                    conn.commit()
                    st.rerun()
