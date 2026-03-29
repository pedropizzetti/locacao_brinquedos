import streamlit as st
from db import conectar
from utils import buscar_estoque_disponivel
from datetime import datetime
import uuid
import pandas as pd

def tela_nova_reserva():
    import pandas as pd
    from datetime import datetime
    import uuid

    st.header("Nova Reserva")

    data = st.date_input("Data")
    hora = st.time_input("Hora")

    conn = conectar()
    cursor = conn.cursor(dictionary=True)

    st.subheader("Cliente")

    tipo = st.radio("Cliente já cadastrado?", ["Sim", "Não"], horizontal=True)

    id_cliente = None
    nome_novo = ""
    zap_novo = ""

    if tipo == "Sim":
        cursor.execute("SELECT id, nome_completo, whatsapp FROM clientes ORDER BY nome_completo")
        clientes = cursor.fetchall()

        mapa = {
            f"{c['nome_completo']} ({c['whatsapp']})": c['id']
            for c in clientes
        }

        selecionado = st.selectbox("Selecione o cliente", list(mapa.keys()), index=None)

        if selecionado:
            id_cliente = mapa[selecionado]

    else:
        col1, col2 = st.columns(2)

        zap_novo = col1.text_input("WhatsApp")
        nome_novo = col2.text_input("Nome").upper()

        zap_limpo = "".join(filter(str.isdigit, zap_novo))

        if len(zap_limpo) >= 10:
            cursor.execute("SELECT id FROM clientes WHERE whatsapp=%s", (zap_limpo,))
            existe = cursor.fetchone()

            if existe:
                id_cliente = existe['id']
                st.info("Cliente já cadastrado encontrado!")

    estoque = buscar_estoque_disponivel(data)

    bris_dict = {b['nome']: b for b in estoque}

    selecionados = st.multiselect("Brinquedos", list(bris_dict.keys()))

    detalhes = []
    total = 0.0

    if selecionados:
        for nome in selecionados:
            b = bris_dict[nome]

            qtd = st.number_input(
                f"{nome} - Quantidade",
                1,
                int(b["quantidade_disponivel"]),
                key=f"q_{nome}"
            )

            valor = st.number_input(
                f"{nome} - Valor",
                value=float(b["preco_base"]),
                key=f"v_{nome}"
            )

            total += qtd * valor
            detalhes.append((b["id"], qtd, valor))

    st.divider()

    frete = st.number_input("Frete", 0.0)
    desconto = st.number_input("Desconto", 0.0)
    sinal = st.number_input("Adiantamento pago", 0.0)

    total_final = total + frete - desconto
    restante = total_final - sinal

    col1, col2 = st.columns(2)
    col1.metric("Total", f"R$ {total_final:.2f}")
    col2.metric("Restante", f"R$ {restante:.2f}")

    obs = st.text_area("Endereço / Observações")

    if st.button("Salvar Reserva", type="primary"):

        if not detalhes:
            st.error("Selecione pelo menos um brinquedo")
            return

        if not id_cliente and not nome_novo:
            st.error("Informe o cliente")
            return

        try:
            conn.autocommit = False
            cursor = conn.cursor()

            if not id_cliente:
                zap_limpo = "".join(filter(str.isdigit, zap_novo))
                cursor.execute(
                    "INSERT INTO clientes (nome_completo, whatsapp) VALUES (%s,%s)",
                    (nome_novo, zap_limpo)
                )
                id_cliente = cursor.lastrowid

            grupo_id = uuid.uuid4().hex
            data_hora = datetime.combine(data, hora)

            sinal_restante = sinal

            for b_id, qtd, valor in detalhes:
                valor_total_item = qtd * valor

                pago = min(sinal_restante, valor_total_item)
                sinal_restante -= pago

                cursor.execute("""
                    INSERT INTO alugueis 
                    (brinquedo_id, cliente_id, data_inicio, valor_final, valor_pago, observacoes, grupo_id, quantidade)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (b_id, id_cliente, data_hora, valor_total_item, pago, obs, grupo_id, qtd))

            if frete > 0:
                cursor.execute("""
                    INSERT INTO alugueis 
                    (brinquedo_id, cliente_id, data_inicio, valor_final, valor_pago, observacoes, grupo_id, quantidade)
                    VALUES (NULL,%s,%s,%s,0,'FRETE',%s,1)
                """, (id_cliente, data_hora, frete, grupo_id))

            if desconto > 0:
                cursor.execute("""
                    INSERT INTO alugueis 
                    (brinquedo_id, cliente_id, data_inicio, valor_final, valor_pago, observacoes, grupo_id, quantidade)
                    VALUES (NULL,%s,%s,%s,0,'DESCONTO',%s,1)
                """, (id_cliente, data_hora, -desconto, grupo_id))

            conn.commit()
            st.success("Reserva salva com sucesso!")
            st.rerun()

        except Exception as e:
            conn.rollback()
            st.error(f"Erro: {e}")

        finally:
            conn.close()


def tela_gerenciar_reservas():
    st.header("Gerenciar Locações")

    busca = st.text_input("Buscar").strip()

    conn = conectar()

    try:
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT a.id,
                   a.grupo_id,
                   c.nome_completo as Cliente,
                   COALESCE(b.nome, a.observacoes) as Item,
                   a.quantidade as Qtd,
                   a.data_inicio as Data,
                   a.valor_final as Total,
                   a.valor_pago as Pago,
                   a.observacoes as Endereco
            FROM alugueis a
            JOIN clientes c ON a.cliente_id = c.id
            LEFT JOIN brinquedos b ON a.brinquedo_id = b.id
            WHERE c.nome_completo LIKE %s
               OR b.nome LIKE %s
               OR a.observacoes LIKE %s
            ORDER BY a.id DESC
            LIMIT 100
        """

        param = f"%{busca}%"
        df = pd.read_sql(query, conn, params=(param, param, param))

        if df.empty:
            st.info("Nenhuma locação encontrada.")
            return

        st.dataframe(df.drop(columns=["grupo_id"]), use_container_width=True, hide_index=True)

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Editar")

            id_edit = st.number_input("ID para editar", min_value=0, step=1)

            if id_edit > 0:
                cursor.execute("SELECT * FROM alugueis WHERE id=%s", (id_edit,))
                res = cursor.fetchone()

                if res:
                    with st.form(f"form_edit_{id_edit}"):
                        data = st.date_input("Data", res['data_inicio'])
                        hora = st.time_input("Hora", res['data_inicio'].time())
                        valor = st.number_input("Valor", value=float(res['valor_final']))
                        pago = st.number_input("Pago", value=float(res['valor_pago']))
                        obs = st.text_area("Obs", value=res['observacoes'])

                        if st.form_submit_button("Salvar"):
                            nova_data = datetime.combine(data, hora)

                            cursor.execute("""
                                UPDATE alugueis
                                SET data_inicio=%s,
                                    valor_final=%s,
                                    valor_pago=%s,
                                    observacoes=%s
                                WHERE id=%s
                            """, (nova_data, valor, pago, obs, id_edit))

                            conn.commit()
                            st.success("Atualizado!")
                            st.rerun()

        with col2:
            st.subheader("Excluir")

            id_del = st.number_input("ID para excluir", min_value=0, step=1, key="del_id")

            if "confirmando_exclusao" not in st.session_state:
                st.session_state.confirmando_exclusao = False

            if id_del > 0 and not st.session_state.confirmando_exclusao:
                if st.button("Excluir", type="primary"):
                    st.session_state.confirmando_exclusao = True
                    st.rerun()

            if st.session_state.confirmando_exclusao:
                st.warning(f"Tem certeza que deseja excluir o ID {id_del}?")

                col_c1, col_c2 = st.columns(2)

                if col_c1.button("Sim, excluir"):
                    cursor.execute("DELETE FROM alugueis WHERE id=%s", (id_del,))
                    conn.commit()

                    st.success("Registro excluído!")
                    st.session_state.confirmando_exclusao = False
                    st.rerun()

                if col_c2.button("Cancelar"):
                    st.session_state.confirmando_exclusao = False
                    st.rerun()

    finally:
        conn.close()
