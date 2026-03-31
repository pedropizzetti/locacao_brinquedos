import streamlit as st
from db import conectar
from utils import buscar_estoque_disponivel
from datetime import datetime
import uuid
import pandas as pd


def limpar_form():
    for key in list(st.session_state.keys()):
        if (
                key.startswith("qtd_")
                or key.startswith("val_")
                or key.startswith("brinquedos_select")
                or key.startswith("cliente_select")
        ):
            del st.session_state[key]

    campos = [
        "data_reserva",
        "hora_reserva",
        "zap_novo",
        "nome_novo",
        "frete",
        "desconto",
        "sinal",
        "obs",
        "escolha_cliente_existente"
    ]

    for c in campos:
        if c in st.session_state:
            del st.session_state[c]


def tela_nova_reserva():
    st.header("Nova Reserva")

    data = st.date_input("Data", key="data_reserva")
    hora = st.time_input("Hora", key="hora_reserva")

    conn = conectar()
    cursor = conn.cursor(dictionary=True)

    st.subheader("Cliente")
    tipo = st.radio("Cliente já cadastrado?", ["Sim", "Não"], horizontal=True)

    id_cliente = None
    usar_existente = False

    if tipo == "Sim":
        cursor.execute("""
                       SELECT id, nome_completo, whatsapp
                       FROM clientes
                       ORDER BY nome_completo
                       """)
        clientes = cursor.fetchall()

        mapa = {
            f"{c['nome_completo']} ({c['whatsapp']})": c['id']
            for c in clientes
        }

        selecionado = st.selectbox(
            "Selecione o cliente",
            list(mapa.keys()),
            index=None,
            key="cliente_select"
        )

        if selecionado:
            id_cliente = mapa[selecionado]

    else:
        col1, col2 = st.columns(2)

        zap_novo = col1.text_input("WhatsApp", key="zap_novo")
        nome_novo = col2.text_input("Nome", key="nome_novo").upper()

        zap_limpo = "".join(filter(str.isdigit, zap_novo))

        if len(zap_limpo) >= 10:
            cursor.execute(
                "SELECT id, nome_completo FROM clientes WHERE whatsapp=%s",
                (zap_limpo,)
            )
            existe = cursor.fetchone()

            if existe:
                st.warning(f"Já existe: {existe['nome_completo']}")

                escolha = st.radio(
                    "Deseja usar esse cliente?",
                    ["Sim", "Não"],
                    key="confirmar_cliente_existente"
                )

                if escolha == "Sim":
                    escolha_final = st.radio(
                        "O que deseja fazer?",
                        ["Usar cliente existente", "Criar novo mesmo assim"],
                        key="escolha_cliente_existente"
                    )

                    if escolha_final == "Usar cliente existente":
                        id_cliente = existe['id']
                        usar_existente = True

    estoque = buscar_estoque_disponivel(data)

    bris_dict = {}
    label_to_id = {}

    for row in estoque:
        restante = int(row["quantidade_disponivel"]) - int(row.get("ocupados", 0))
        label = f"{row['nome']} (disp: {restante})"

        bris_dict[row["id"]] = {
            "label": label,
            "restante": restante,
            "preco": float(row["preco_base"]),
            "nome": row["nome"]
        }

        label_to_id[label] = row["id"]

    opcoes = [v["label"] for v in bris_dict.values() if v["restante"] > 0]

    selecionados = st.multiselect("Brinquedos", opcoes, key="brinquedos_select")

    detalhes = []
    total = 0.0

    for label in selecionados:
        b_id = label_to_id[label]
        b = bris_dict[b_id]

        with st.expander(b["nome"]):
            col1, col2 = st.columns(2)

            qtd = col1.number_input(
                "Quantidade",
                min_value=1,
                max_value=b["restante"],
                value=1,
                key=f"qtd_{b_id}"
            )

            valor = col2.number_input(
                "Valor (R$)",
                min_value=0.0,
                value=b["preco"],
                key=f"val_{b_id}"
            )

        total += qtd * valor
        detalhes.append((b_id, qtd, valor))

    st.divider()

    frete = st.number_input("Frete", 0.0, key="frete")
    desconto = st.number_input("Desconto", 0.0, key="desconto")
    sinal = st.number_input("Adiantamento pago", 0.0, key="sinal")

    total_final = total + frete - desconto
    restante = total_final - sinal

    col1, col2 = st.columns(2)
    col1.metric("Total", f"R$ {total_final:.2f}")
    col2.metric("Restante", f"R$ {restante:.2f}")

    obs = st.text_area("Endereço / Observações", key="obs")

    if st.button("Salvar Reserva", type="primary"):

        if not detalhes:
            st.error("Selecione pelo menos um brinquedo")
            return

        if not id_cliente:
            if not st.session_state.get("nome_novo"):
                st.error("Informe o cliente")
                return

        # --- NOVA TRAVA DE SEGURANÇA: CHECAGEM DE ESTOQUE REAL-TIME ---
        # Re-checamos o estoque no clique do botão para evitar furos
        estoque_atualizado = buscar_estoque_disponivel(data)
        for b_id, qtd_desejada, _ in detalhes:
            item_estoque = next((item for item in estoque_atualizado if item["id"] == b_id), None)

            if item_estoque:
                disponivel = int(item_estoque["quantidade_disponivel"]) - int(item_estoque.get("ocupados", 0))
                if qtd_desejada > disponivel:
                    st.error(
                        f"⚠️ Erro de Disponibilidade: O item '{item_estoque['nome']}' só possui {disponivel} unidade(s) livre(s) para este dia.")
                    return
            else:
                st.error("Erro: Um dos brinquedos selecionados não foi encontrado no estoque.")
                return

        try:
            conn.autocommit = False
            cursor = conn.cursor()

            if not id_cliente and not usar_existente:
                zap_limpo = "".join(filter(str.isdigit, st.session_state.get("zap_novo", "")))
                cursor.execute(
                    "INSERT INTO clientes (nome_completo, whatsapp) VALUES (%s,%s)",
                    (st.session_state.get("nome_novo"), zap_limpo)
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
                               (brinquedo_id, cliente_id, data_inicio, valor_final, valor_pago, observacoes, grupo_id,
                                quantidade)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                               """, (b_id, id_cliente, data_hora, valor_total_item, pago, obs, grupo_id, qtd))

            if frete > 0:
                cursor.execute("""
                               INSERT INTO alugueis
                               (brinquedo_id, cliente_id, data_inicio, valor_final, valor_pago, observacoes, grupo_id,
                                quantidade)
                               VALUES (NULL, %s, %s, %s, 0, 'FRETE', %s, 1)
                               """, (id_cliente, data_hora, frete, grupo_id))

            if desconto > 0:
                cursor.execute("""
                               INSERT INTO alugueis
                               (brinquedo_id, cliente_id, data_inicio, valor_final, valor_pago, observacoes, grupo_id,
                                quantidade)
                               VALUES (NULL, %s, %s, %s, 0, 'DESCONTO', %s, 1)
                               """, (id_cliente, data_hora, -desconto, grupo_id))

            conn.commit()
            limpar_form()
            st.success("Reserva salva com sucesso!")
            st.rerun()

        except Exception as e:
            conn.rollback()
            st.error(f"Erro ao salvar: {e}")

        finally:
            conn.close()


def tela_gerenciar_reservas():
    st.header("Gerenciar Locações")
    busca = st.text_input("Buscar")
    conn = conectar()

    try:
        df = pd.read_sql("""
            SELECT a.id,
                   c.nome_completo as Cliente,
                   COALESCE(b.nome, a.observacoes) as Item,
                   a.quantidade as Qtd,
                   a.data_inicio as Data,
                   a.valor_final as Total,
                   a.valor_pago as Pago,
                   a.observacoes as Obs
            FROM alugueis a
            JOIN clientes c ON a.cliente_id = c.id
            LEFT JOIN brinquedos b ON a.brinquedo_id = b.id
            ORDER BY a.id DESC
        """, conn)

        if busca:
            df = df[df.apply(lambda row: busca.lower() in str(row).lower(), axis=1)]
        opcoes_id = ["Selecione um ID..."] + [str(id) for id in df["id"].tolist()]

        selecionado = st.selectbox(
            "Selecione uma reserva para editar",
            options=opcoes_id
        )

        st.dataframe(df, use_container_width=True, hide_index=True)

        if selecionado != "Selecione um ID...":
            cursor = conn.cursor(dictionary=True)
            id_atual = int(selecionado)

            cursor.execute("SELECT * FROM alugueis WHERE id=%s", (id_atual,))
            res = cursor.fetchone()

            if res:
                st.divider()
                st.subheader(f"Editando ID {id_atual}")

                with st.form("form_edit"):
                    data = st.date_input("Data", res['data_inicio'])
                    hora = st.time_input("Hora", res['data_inicio'].time())
                    valor = st.number_input("Valor", value=float(res['valor_final']))
                    pago = st.number_input("Pago", value=float(res['valor_pago']))
                    obs = st.text_area("Observações", value=res['observacoes'])

                    salvar = st.form_submit_button("Salvar alterações")
                    excluir = st.form_submit_button("Excluir")

                    if salvar:
                        nova_data = datetime.combine(data, hora)

                        cursor.execute("""
                            UPDATE alugueis
                            SET data_inicio=%s,
                                valor_final=%s,
                                valor_pago=%s,
                                observacoes=%s
                            WHERE id=%s
                        """, (nova_data, valor, pago, obs, id_atual))

                        conn.commit()
                        st.success("Atualizado com sucesso!")
                        st.rerun()

                    if excluir:
                        cursor.execute("DELETE FROM alugueis WHERE id=%s", (selecionado,))
                        conn.commit()

                        st.success("Excluído!")
                        st.rerun()

    finally:
        conn.close()
