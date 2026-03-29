import streamlit as st

def login():
    if 'logado' not in st.session_state:
        st.session_state['logado'] = False

    if not st.session_state['logado']:
        st.markdown("<h1 style='text-align: center;'>Sistema Mais Brinquedos</h1>", unsafe_allow_html=True)

        with st.form("login"):
            u = st.text_input("Usuário").strip().lower()
            p = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                if u in st.secrets["usuarios"] and str(st.secrets["usuarios"][u]) == p:
                    st.session_state['logado'] = True
                    st.session_state['usuario_nome'] = u
                    st.rerun()
                else:
                    st.error("Login inválido")

        st.stop()