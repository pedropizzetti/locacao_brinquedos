import streamlit as st
from auth import login
from agenda import tela_agenda
from reservas import tela_nova_reserva
from clientes import tela_clientes
from financeiro import tela_financeiro

st.set_page_config(page_title="Mais Brinquedos", layout="wide")

if not login():
    st.stop()

st.sidebar.title(f"Olá, {st.session_state['usuario_nome'].capitalize()}!")

menu = st.sidebar.selectbox("Navegação:", [
    "Agenda",
    "Nova Reserva",
    "Gerenciar Reservas",
    "Clientes",
    "Financeiro/Admin"
])

if st.sidebar.button("Sair"):
    st.session_state['logado'] = False
    st.rerun()

if menu == "Agenda":
    tela_agenda()
elif menu == "Nova Reserva":
    tela_nova_reserva()
elif menu == "Gerenciar Reservas":
    tela_gerenciar_reservas()
elif menu == "Clientes":
    tela_clientes()
elif menu == "Financeiro/Admin":
    tela_financeiro()
