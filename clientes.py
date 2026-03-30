import streamlit as st
import pandas as pd
from db import conectar

def tela_clientes():
    st.header("Gerenciar Clientes")

    busca = st.text_input("Pesquisar cliente").strip().upper()

    conn = conectar()

    try:
        cursor = conn.cursor(dictionary=True)
        if busca:
            cursor.execute(
                "SELECT * FROM clientes WHERE nome_completo LIKE %s ORDER BY nome_completo",
                (f"%{busca}%",)
            )
        else:
            cursor.execute("SELECT * FROM clientes ORDER BY nome_completo")

        clientes = cursor.fetchall()

        if not clientes:
            st.warning("Nenhum cliente encontrado.")
            return

        for c in clientes:
            with st.expander(f"{c['nome_completo']}"):

                tab1, tab2 = st.tabs(["Dados", "Histórico"])

                with tab1:
                    with st.form(f"form_cli_{c['id']}"):
                        nome = st.text_input("Nome", value=c['nome_completo']).upper()
                        zap = st.text_input("WhatsApp", value=c['whatsapp'])

                        if st.form_submit_button("Salvar"):
                            cursor.execute(
                                "UPDATE clientes SET nome_completo=%s, whatsapp=%s WHERE id=%s",
                                (nome, "".join(filter(str.isdigit, zap)), c['id'])
                            )
                            conn.commit()
                            st.success("Atualizado!")
                            st.rerun()

                    if st.button(f"Excluir cliente", key=f"del_{c['id']}"):
                        cursor.execute(
                            "SELECT COUNT(*) as total FROM alugueis WHERE cliente_id = %s",
                            (c['id'],)
                        )
                        if cursor.fetchone()['total'] > 0:
                            st.error("Cliente possui reservas. Não pode excluir.")
                        else:
                            cursor.execute("DELETE FROM clientes WHERE id = %s", (c['id'],))
                            conn.commit()
                            st.success("Cliente excluído!")
                            st.rerun()

                with tab2:
                    df_hist = pd.read_sql("""
                        SELECT 
                            a.data_inicio as Data,
                            COALESCE(b.nome, a.observacoes) as Item,
                            a.valor_final as Valor
                        FROM alugueis a
                        LEFT JOIN brinquedos b ON a.brinquedo_id = b.id
                        WHERE a.cliente_id = %s
                        ORDER BY a.data_inicio DESC
                    """, conn, params=(c['id'],))

                    if df_hist.empty:
                        st.info("Sem histórico.")
                    else:
                        st.dataframe(df_hist, use_container_width=True, hide_index=True)

    finally:
        conn.close()
