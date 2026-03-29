import streamlit as st
from db import conectar
from datetime import datetime
import uuid
import pandas as pd


def limpar_form():
    for key in list(st.session_state.keys()):
        if key.startswith("qtd_") or key.startswith("val_"):
            del st.session_state[key]

    campos = [
        "data_reserva",
        "hora_reserva",
        "brinquedos_select",
        "cliente_select",
        "zap_novo",
        "nome_novo",
        "frete",
        "desconto",
        "sinal",
        "obs"
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

    if tipo == "Sim":
        cursor.execute("SELECT id, nome_completo, whatsapp FROM clientes ORDER BY nome_completo")
        clientes = cursor.fetchall()

        mapa_clientes = {
            f"{c['nome_completo']} ({c['whatsapp']})": c['id']
            for c in clientes
        }

        selecionado = st.selectbox(
            "Selecione o cliente",
            list(mapa_clientes.keys()),
            index=None,
            key="cliente_select"
        )

        if selecionado:
            id_cliente = mapa_clientes[selecionado]

    else:
        col1, col2 = st.columns(2)

        zap_novo = col1.text_input("WhatsApp", key="zap_novo")
        nome_novo = col2.text_input("Nome", key="nome_novo").upper()

        zap_limpo = "".join(filter(str.isdigit, zap_novo))

        if len(zap_limpo) >= 10:
            cursor.execute("SELECT id FROM clientes WHERE whatsapp=%s", (zap_limpo,))
            existe = cursor.fetchone()

            if existe:
                id_cliente = existe['id']
                st.info("Cliente já cadastrado encontrado!")

cursor.execute("""
    SELECT 
        b.id,
        b.nome,
        b.quantidade_disponivel,
        b.preco_base,
        COALESCE(SUM(a.quantidade), 0) as reservado
    FROM brinquedos b
    LEFT JOIN alugueis a 
        ON b.id = a.brinquedo_id
        AND DATE(a.data_inicio) = %s
    GROUP BY b.id
    ORDER BY b.nome
""", (data,))

estoque = cursor.fetchall()

mapa = {}
for b in estoque:
    disponivel = b["quantidade_disponivel"] - b["reservado"]

    mapa[b["id"]] = {
        "nome": b["nome"],
        "disponivel": max(disponivel, 0),
        "preco": float(b["preco_base"])
    }

opcoes = list(mapa.keys())


if "brinquedos_select" not in st.session_state:
    st.session_state["brinquedos_select"] = []


def atualizar_selecao():
    st.session_state["brinquedos_select"] = [
        x for x in st.session_state["brinquedos_select"] if x in mapa
    ]

st.multiselect(
    "Brinquedos",
    options=opcoes,
    default=st.session_state["brinquedos_select"],
    format_func=lambda x: f"{mapa[x]['nome']} (disp: {mapa[x]['disponivel']})",
    key="brinquedos_select",
    on_change=atualizar_selecao
)

selecionados = st.session_state["brinquedos_select"]

detalhes = []
total = 0.0

for b_id in selecionados:
    if b_id not in mapa:
        continue

    b = mapa[b_id]

    with st.expander(b["nome"], expanded=False):
        col1, col2 = st.columns(2)

        qtd = col1.number_input(
            "Quantidade",
            min_value=1,
            max_value=max(1, int(b["disponivel"])),
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

        try:
            conn.autocommit = False
            cursor = conn.cursor()

            if not id_cliente:
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

            limpar_form()
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

    finally:
        conn.close()
