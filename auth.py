def login():
    import streamlit as st

    if 'logado' not in st.session_state:
        st.session_state['logado'] = False

    if st.session_state['logado']:
        return True

    st.markdown("<h2 style='text-align: center;'>Sistema Mais Brinquedos</h2>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 1, 2])

    with col2:
        st.markdown("### Login")

        with st.form("login_form"):
            u_raw = st.text_input("Usuário").strip().lower()
            p_raw = st.text_input("Senha", type="password")

            btn_login = st.form_submit_button("Entrar", use_container_width=True)

            if btn_login:
                if u_raw in st.secrets["usuarios"] and str(st.secrets["usuarios"][u_raw]) == p_raw:
                    st.session_state['logado'] = True
                    st.session_state['usuario_nome'] = u_raw
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

    return False
