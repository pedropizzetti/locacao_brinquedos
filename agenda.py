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
        
    df["Inicio"] = pd.to_datetime(df["Inicio"])
    df = df.sort_values(["Inicio", "grupo_id"])

    for g_id in df["grupo_id"].unique():
        grupo = df[df["grupo_id"] == g_id]
        total = grupo["valor_final"].sum()
        pago = grupo["valor_pago"].sum()
        restante = total - pago

        nome = grupo["Cliente"].iloc[0]
        hora = grupo["Inicio"].iloc[0].strftime("%H:%M")

        icone = "✅" if restante <= 0 else "💰"

        with st.expander(f"{icone} {hora} - {nome} | R$ {total:.2f}"):

            st.markdown("### Itens da festa")

            col1, col2, col3 = st.columns([4, 1, 2])
            col1.caption("Item")
            col2.caption("Qtd")
            col3.caption("Valor")

            for _, item in grupo.iterrows():
                nome_item = item["Brinquedo"]
                qtd = int(item["quantidade"])
                valor = float(item["valor_final"])

                c1, c2, c3 = st.columns([4, 1, 2])

                if nome_item == "DESCONTO":
                    c1.markdown("**Desconto**")
                    c2.write("-")
                    c3.markdown(f"-R$ {abs(valor):.2f}")

                elif nome_item == "FRETE":
                    c1.markdown("**Frete**")
                    c2.write("-")
                    c3.write(f"R$ {valor:.2f}")

                else:
                    c1.write(nome_item)
                    c2.write(qtd)
                    c3.write(f"R$ {valor:.2f}")

            st.divider()

            c1, c2 = st.columns(2)
            c1.markdown(f"### Total: R$ {total:.2f}")
            c2.markdown(f"### Restante: R$ {restante:.2f}")

            col_end, col_contato = st.columns(2)

            with col_end:
                st.markdown(f"**Endereço:**\n{grupo['Endereco'].iloc[0]}")

            with col_contato:
                fone = grupo["Fone"].iloc[0]
                if fone:
                    numero = "".join(filter(str.isdigit, str(fone)))
                    st.markdown(f"**Contato:**\n{formatar_zap(numero)}")
                    st.link_button(
                        "Chamar no WhatsApp",
                        f"https://wa.me/55{numero}",
                        use_container_width=True
                    )

            if restante > 0:
                if st.button(f"Quitar R$ {restante:.2f}", key=g_id):
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE alugueis 
                        SET valor_pago = valor_final
                        WHERE grupo_id = %s
                    """, (g_id,))
                    conn.commit()
                    st.rerun()
