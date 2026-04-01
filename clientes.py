import streamlit as st
import pandas as pd
from db import conectar

def tela_clientes():
    st.header("Gerenciar Clientes")
    
    busca = st.text_input("Pesquisar cliente (Nome ou WhatsApp)").strip().upper()

    conn = conectar()

    try:
        cursor = conn.cursor(dictionary=True)
        
        if busca:
            query = """
                SELECT * FROM clientes 
                WHERE UPPER(nome_completo) LIKE %s 
                OR whatsapp LIKE %s
                ORDER BY nome_completo
            """
            params = (f"%{busca}%", f"%{busca}%")
            cursor.execute(query, params)
        else:
            cursor.execute("SELECT * FROM clientes ORDER BY nome_completo")

        clientes = cursor.fetchall()

        if not clientes:
            st.warning("Nenhum cliente encontrado.")
            return

        st.write(f"Exibindo {len(clientes)} cliente(s):")

        for c in clientes:
            with st.expander(f"{c['nome_completo']} - {c['whatsapp']}"):

                tab1, tab2 = st.tabs(["Dados", "Histórico"])

                with tab1:
                    with st.form(f"form_cli_{c['id']}"):
                        nome_edit = st.text_input("Nome", value=c['nome_completo']).upper()
                        zap_edit = st.text_input("WhatsApp", value=c['whatsapp'])

                        col1, col2 = st.columns([1, 4])
                        salvar = st.form_submit_button("Salvar Alterações")
                        
                        if salvar:
                            cursor.execute(
                                "UPDATE clientes SET nome_completo=%s, whatsapp=%s WHERE id=%s",
                                (nome_edit, "".join(filter(str.isdigit, zap_edit)), c['id'])
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
                            st.error("Este cliente possui reservas no histórico e não pode ser excluído.")
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
                        st.info("Este cliente ainda não realizou locações.")
                    else:
                        df_hist['Data'] = pd.to_datetime(df_hist['Data']).dt.strftime('%d/%m/%Y %H:%M')
                        st.dataframe(df_hist, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Erro ao carregar clientes: {e}")
        
    finally:
        conn.close()
