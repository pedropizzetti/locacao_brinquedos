import streamlit as st
import mysql.connector
import pandas as pd
from datetime import datetime, time
import uuid

def conectar():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"]
    )

def formatar_zap(num):
    num = "".join(filter(str.isdigit, str(num)))
    if len(num) == 11:
        return f"({num[:2]}) {num[2:7]}-{num[7:]}"
    elif len(num) == 10:
        return f"({num[:2]}) {num[2:6]}-{num[6:]}"
    return num

st.set_page_config(page_title="Mais Brinquedos", layout="wide")

if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    st.markdown("<h1 style='text-align: center;'>Sistema Mais Brinquedos</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        u_raw = st.text_input("Usuário:").strip().lower()
        p_raw = st.text_input("Senha:", type="password")
        if st.button("Entrar", use_container_width=True):
            if u_raw in st.secrets["usuarios"] and str(st.secrets["usuarios"][u_raw]) == p_raw:
                st.session_state['logado'] = True
                st.session_state['usuario_nome'] = u_raw
                st.empty()
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    st.stop()

st.sidebar.title(f"Olá, {st.session_state['usuario_nome'].capitalize()}!")
menu = st.sidebar.selectbox("Navegação:", ["Agenda", "Nova Reserva", "Gerenciar Reservas", "Clientes", "Financeiro/Admin"])

if st.sidebar.button("Sair"):
    st.session_state['logado'] = False
    st.rerun()

if menu == "Agenda":
    st.subheader("Roteiro de Entregas")
    c1, c2 = st.columns([1, 2])
    data_sel = c1.date_input("Data:", datetime.now())
    busca = c2.text_input("Buscar Cliente ou Endereço:").strip()

    inicio_dt = datetime.combine(data_sel, time.min)
    fim_dt = datetime.combine(data_sel, time.max)

    conn = conectar()
    try:
        query = """
                SELECT c.nome_completo as Cliente, c.whatsapp as Fone, a.observacoes as Endereco,
                       b.nome as Brinquedo, a.quantidade, a.data_inicio as Inicio,
                       a.valor_final, a.valor_pago, a.grupo_id
                FROM alugueis a
                JOIN clientes c ON a.cliente_id = c.id
                JOIN brinquedos b ON a.brinquedo_id = b.id
                WHERE a.data_inicio >= %s AND a.data_inicio <= %s
                """
        df_dia = pd.read_sql(query, conn, params=(inicio_dt, fim_dt))

        if not df_dia.empty:
            df_agrupado = df_dia.groupby(['grupo_id', 'Cliente', 'Fone', 'Endereco', 'Inicio']).apply(
                lambda x: pd.Series({
                    'valor_total': x['valor_final'].sum(),
                    'valor_pago': x['valor_pago'].sum()
                })
            ).reset_index()

            if busca:
                df_agrupado = df_agrupado[df_agrupado['Cliente'].str.contains(busca, case=False, na=False) |
                                          df_agrupado['Endereco'].str.contains(busca, case=False, na=False)]

            df_agrupado = df_agrupado.sort_values('Inicio')

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Entregas", len(df_agrupado))
            m2.metric("Total", f"R$ {df_agrupado['valor_total'].sum():.2f}")
            m3.metric("A Receber", f"R$ {(df_agrupado['valor_total'].sum() - df_agrupado['valor_pago'].sum()):.2f}")
            m4.metric("Itens Total", int(df_dia['quantidade'].sum()))

            st.divider()

            for _, r in df_agrupado.iterrows():
                restante = round(r['valor_total'] - r['valor_pago'], 2)
                hora_str = pd.to_datetime(r['Inicio']).strftime('%H:%M')
                icone = "✅" if restante <= 0 else "💰"
                status_txt = "QUITADO" if restante <= 0 else f"PENDENTE: R$ {restante:.2f}"

                with st.expander(f"{icone} {hora_str} - {r['Cliente']} | {status_txt}"):
                    st.markdown("### Itens da Locação")
                    itens_do_grupo = df_dia[df_dia['grupo_id'] == r['grupo_id']]
                    col_h1, col_h2, col_h3 = st.columns([3, 1, 2])
                    col_h1.caption("Brinquedo")
                    col_h2.caption("Qtd")
                    col_h3.caption("Valor Item")

                    for _, item in itens_do_grupo.iterrows():
                        c_it, c_qt, c_v = st.columns([3, 1, 2])
                        c_it.write(f"**{item['Brinquedo']}**")
                        c_qt.write(f"{int(item['quantidade'])}")
                        c_v.write(f"R$ {item['valor_final']:.2f}")

                    st.divider()
                    c_t1, c_t2 = st.columns([4, 2])
                    c_t1.markdown("### TOTAL DA FESTA:")
                    c_t2.markdown(f"### R$ {r['valor_total']:.2f}")

                    restante = round(r['valor_total'] - r['valor_pago'], 2)
                    if restante > 0:
                        st.warning(f"**FALTA RECEBER: R$ {restante:.2f}**")

                    col_end, col_contato = st.columns([2, 1])
                    with col_end:
                        st.markdown(f"**ENTREGA:**\n{r['Endereco']}")
                    with col_contato:
                        num = "".join(filter(str.isdigit, str(r['Fone'])))
                        if num:
                            st.markdown(f"**CONTATO:**\n{formatar_zap(num)}")
                            st.link_button("Chamar no WhatsApp", f"https://wa.me/55{num}", use_container_width=True)

                    if restante > 0:
                        if st.button(f"Confirmar Recebimento de R$ {restante:.2f}", key=f"pay_{r['grupo_id']}", use_container_width=True):
                            cursor = conn.cursor()
                            cursor.execute("""
                                           UPDATE alugueis
                                           SET valor_pago       = valor_final,
                                               status_pagamento = 'pago'
                                           WHERE grupo_id = %s
                                           """, (r['grupo_id'],))
                            conn.commit()
                            st.rerun()
        else:
            st.info("Sem reservas para esta data.")
    finally:
        conn.close()

elif menu == "Nova Reserva":
    st.header("Nova Reserva")
    conn = conectar()
    try:
        cursor = conn.cursor(dictionary=True)

        c_data, c_hora = st.columns(2)
        d_festa = c_data.date_input("Data da Festa:", datetime.now())
        h_festa = c_hora.time_input("Horário:", value=time(8, 0))

        inicio_est = datetime.combine(d_festa, time.min)
        fim_est = datetime.combine(d_festa, time.max)
        cursor.execute("""
                       SELECT b.id,
                              b.nome,
                              b.quantidade_disponivel,
                              b.preco_base,
                              COALESCE((SELECT SUM(a.quantidade)
                                        FROM alugueis a
                                        WHERE a.brinquedo_id = b.id
                                          AND a.data_inicio >= %s
                                          AND a.data_inicio <= %s), 0) as ocupados
                       FROM brinquedos b
                       """, (inicio_est, fim_est))
        estoque_data = cursor.fetchall()

        bris_dict = {row['id']: {
            "label": f"{row['nome']} - (Disp: {row['quantidade_disponivel'] - int(row['ocupados'])})",
            "restante": row['quantidade_disponivel'] - int(row['ocupados']),
            "nome": row['nome'].strip(),
            "preco": float(row['preco_base'])
        } for row in estoque_data}

        label_to_id = {v["label"]: k for k, v in bris_dict.items()}

        tipo = st.radio("Cliente cadastrado?", ["Sim", "Não"], horizontal=True)
        id_cli_final = None
        n_nome = ""
        z_limpo = ""

        if tipo == "Sim":
            cursor.execute("SELECT id, nome_completo, whatsapp FROM clientes ORDER BY nome_completo")
            clis = {f"{r['nome_completo']} ({formatar_zap(r['whatsapp'])})": r['id'] for r in cursor.fetchall()}
            cli_sel = st.selectbox("Selecione o Cliente:", options=list(clis.keys()), index=None)
            if cli_sel: id_cli_final = clis[cli_sel]
        else:
            col_z1, col_z2 = st.columns([1, 2])
            n_zap = col_z1.text_input("WhatsApp (DDD + Número):").strip()
            n_nome = col_z2.text_input("Nome do Cliente:").strip().upper()
            z_limpo = "".join(filter(str.isdigit, n_zap))
            if len(z_limpo) >= 10:
                cursor.execute("SELECT id FROM clientes WHERE whatsapp = %s", (z_limpo,))
                ex = cursor.fetchone()
                if ex:
                    id_cli_final = ex['id']
                    st.info("Cliente já cadastrado encontrado!")

        st.write("---")
        opcoes_disp = [v["label"] for v in bris_dict.values() if v["restante"] > 0]
        sel_labels = st.multiselect("Selecione os Brinquedos:", options=opcoes_disp)

        detalhes_reserva = []
        soma_brinquedos = 0.0

        if sel_labels:
            st.subheader("Ajuste de Itens")
            for lb in sel_labels:
                b_id = label_to_id[lb]
                b_info = bris_dict[b_id]

                with st.expander(f"{b_info['nome']}", expanded=False):
                    col_q, col_v = st.columns(2)
                    qtd = col_q.number_input(f"Qtd:", min_value=1, max_value=b_info["restante"], value=1,
                                             key=f"q_{b_id}")
                    v_uni = col_v.number_input(f"Valor Unit. R$:", min_value=0.0, value=b_info["preco"],
                                               key=f"v_{b_id}")

                soma_brinquedos += (v_uni * qtd)
                detalhes_reserva.append({'id': b_id, 'qtd': qtd, 'valor': v_uni, 'nome': b_info['nome']})

            st.write("---")
            v_frete = st.number_input("Deslocamento (R$):", min_value=0.0, value=0.0, step=5.0)
            v_desc = st.number_input("Desconto (R$):", min_value=0.0, value=0.0, step=5.0)
            v_sin = st.number_input("Adiantamento Pago (R$):", min_value=0.0, value=0.0)

            total_final = soma_brinquedos + v_frete - v_desc
            st.divider()
            st.metric("TOTAL A PAGAR", f"R$ {total_final:.2f}")

            obs = st.text_area("Endereço da Entrega:").strip().upper()

            if st.button("Finalizar e Gravar Reserva", use_container_width=True, type="primary"):
                if not detalhes_reserva:
                    st.error("Selecione pelo menos um brinquedo!")
                else:
                    if tipo == "Não" and not id_cli_final:
                        cursor.execute("INSERT INTO clientes (nome_completo, whatsapp) VALUES (%s, %s)",
                                       (n_nome, z_limpo))
                        id_cli_final = cursor.lastrowid

                    id_g = uuid.uuid4().hex
                    dt_f = datetime.combine(d_festa, h_festa)

                    for item in detalhes_reserva:
                        cursor.execute("""
                                       INSERT INTO alugueis (brinquedo_id, cliente_id, data_inicio, valor_final,
                                                             valor_pago,
                                                             observacoes, grupo_id, quantidade)
                                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                       """,
                                       (item['id'], id_cli_final, dt_f, (item['valor'] * item['qtd']), 0, obs, id_g,
                                        item['qtd']))

                    if v_frete > 0:
                        cursor.execute(
                            "INSERT INTO alugueis (brinquedo_id, cliente_id, data_inicio, valor_final, valor_pago, observacoes, grupo_id, quantidade) VALUES (NULL, %s, %s, %s, 0, 'FRETE', %s, 1)",
                            (id_cli_final, dt_f, v_frete, id_g))
                    if v_desc > 0:
                        cursor.execute(
                            "INSERT INTO alugueis (brinquedo_id, cliente_id, data_inicio, valor_final, valor_pago, observacoes, grupo_id, quantidade) VALUES (NULL, %s, %s, %s, 0, 'DESCONTO', %s, 1)",
                            (id_cli_final, dt_f, -v_desc, id_g))

                    cursor.execute("UPDATE clientes SET endereco_entrega = %s WHERE id = %s", (obs, id_cli_final))

                    conn.commit()
                    st.success(f"Reserva gravada com sucesso!")
                    st.rerun()
    finally:
        conn.close()

elif menu == "Gerenciar Reservas":
    st.header("Gerenciar Locações")
    conn = conectar()
    try:
        cursor = conn.cursor(dictionary=True)
        busca_loc = st.text_input("Pesquisar por Cliente ou Brinquedo:").strip()

        query_loc = """
                    SELECT a.id, \
                           a.grupo_id, \
                           c.nome_completo                 as Cliente,
                           COALESCE(b.nome, a.observacoes) as Item, \
                           a.quantidade                    as Qtd,
                           a.data_inicio                   as Data, \
                           a.valor_final                   as Total, \
                           a.valor_pago                    as Pago, \
                           a.observacoes                   as Endereco
                    FROM alugueis a
                             JOIN clientes c ON a.cliente_id = c.id
                             LEFT JOIN brinquedos b ON a.brinquedo_id = b.id
                    WHERE c.nome_completo LIKE %s \
                       OR b.nome LIKE %s \
                       OR a.observacoes LIKE %s
                    ORDER BY a.id DESC LIMIT 100
                    """
        param = f"%{busca_loc}%"
        df = pd.read_sql(query_loc, conn, params=(param, param, param))

        if df.empty:
            st.info("Nenhuma locação encontrada.")
        else:
            st.dataframe(df.drop(columns=['grupo_id', 'Endereco']), use_container_width=True, hide_index=True)
            st.divider()
            col_ed, col_del = st.columns(2)

            with col_ed:
                st.subheader("Editar Linha")
                id_edit = st.number_input("Digite o ID da linha para editar:", min_value=0, step=1, key="input_edit")

                if id_edit > 0:
                    cursor.execute("SELECT * FROM alugueis WHERE id = %s", (id_edit,))
                    res = cursor.fetchone()

                    if res:
                        with st.form(key=f"form_ed_reserva_{id_edit}"):
                            st.write(f"Editando ID: {id_edit}")

                            ed_data = st.date_input("Data:", res['data_inicio'])
                            ed_hora = st.time_input("Horário:", res['data_inicio'].time())
                            ed_val = st.number_input("Valor Total do Item (R$):", value=float(res['valor_final']))
                            ed_pago = st.number_input("Quanto já foi pago (R$):", value=float(res['valor_pago']))
                            ed_obs = st.text_area("Endereço/Observações:", value=res['observacoes']).upper()

                            btn_salvar = st.form_submit_button("Salvar Alterações", type="primary")

                            if btn_salvar:
                                nova_data_completa = datetime.combine(ed_data, ed_hora)

                                sql_update = """
                                             UPDATE alugueis
                                             SET data_inicio=%s, \
                                                 valor_final=%s, \
                                                 valor_pago=%s, \
                                                 observacoes=%s
                                             WHERE id = %s \
                                             """
                                cursor.execute(sql_update, (nova_data_completa, ed_val, ed_pago, ed_obs, id_edit))
                                conn.commit()
                                st.success("Alterações salvas com sucesso!")
                                st.rerun()
                    else:
                        st.error("ID não encontrado no banco de dados.")

            with col_del:
                st.subheader("🗑️ Cancelar/Remover")
                id_del = st.number_input("ID para excluir:", min_value=0, step=1, key="input_del")
                confirmar = st.checkbox(f"Confirmar exclusão definitiva do ID {id_del}")

                if st.button("Excluir Agora", type="primary", disabled=not confirmar):
                    if id_del > 0:
                        cursor.execute("DELETE FROM alugueis WHERE id = %s", (id_del,))
                        conn.commit()
                        st.success(f"ID {id_del} removido!")
                        st.rerun()
    finally:
        conn.close()

elif menu == "Clientes":
    st.header("Gerenciar Clientes")
    conn = conectar()
    try:
        cursor = conn.cursor(dictionary=True)
        busca_cli = st.text_input("Pesquisar Cliente pelo nome:").strip().upper()
        if busca_cli:
            cursor.execute("SELECT * FROM clientes WHERE nome_completo LIKE %s ORDER BY nome_completo", (f"%{busca_cli}%",))
        else:
            cursor.execute("SELECT * FROM clientes ORDER BY nome_completo")
        clientes = cursor.fetchall()
        if not clientes:
            st.warning("Nenhum cliente encontrado.")
        else:
            for c in clientes:
                with st.expander(f"{c['nome_completo']}"):
                    tab1, tab2 = st.tabs(["Dados Cadastrais", "Histórico de Locações"])
                    with tab1:
                        with st.form(f"edit_cli_{c['id']}"):
                            novo_nome = st.text_input("Nome:", value=c['nome_completo']).upper()
                            novo_zap = st.text_input("WhatsApp:", value=c['whatsapp'])
                            if st.form_submit_button("Salvar Alterações"):
                                cursor.execute("UPDATE clientes SET nome_completo=%s, whatsapp=%s WHERE id=%s", (novo_nome, "".join(filter(str.isdigit, novo_zap)), c['id']))
                                conn.commit()
                                st.rerun()
                        if st.button(f"Excluir permanentemente {c['nome_completo']}", key=f"btn_del_{c['id']}"):
                            cursor.execute("SELECT COUNT(*) as total FROM alugueis WHERE cliente_id = %s", (c['id'],))
                            if cursor.fetchone()['total'] > 0:
                                st.error("Não é possível excluir. Exclua as reservas primeiro.")
                            else:
                                cursor.execute("DELETE FROM clientes WHERE id = %s", (c['id'],))
                                conn.commit()
                                st.rerun()
                    with tab2:
                        df_hist = pd.read_sql("SELECT a.data_inicio as Data, b.nome as Brinquedo, a.valor_final as Valor FROM alugueis a JOIN brinquedos b ON a.brinquedo_id = b.id WHERE a.cliente_id = %s ORDER BY a.data_inicio DESC", conn, params=(c['id'],))
                        st.dataframe(df_hist, use_container_width=True, hide_index=True)
    finally:
        conn.close()

elif menu == "Financeiro/Admin":
    st.header("Painel Financeiro")
    if st.session_state['usuario_nome'] == "pedro":
        conn = conectar()
        try:
            df_f = pd.read_sql("SELECT SUM(valor_final) as T, SUM(valor_pago) as R FROM alugueis", conn)
            t, r = float(df_f['T'].iloc[0] or 0), float(df_f['R'].iloc[0] or 0)
            c1, c2, c3 = st.columns(3)
            c1.metric("Faturamento Bruto", f"R$ {t:.2f}")
            c2.metric("Total Recebido", f"R$ {r:.2f}")
            c3.metric("Pendente", f"R$ {(t - r):.2f}")
        finally:
            conn.close()
    else:
        st.error("Acesso restrito.")
