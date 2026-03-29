from datetime import datetime, time
import streamlit as st
from db import conectar

def formatar_zap(num):
    num = "".join(filter(str.isdigit, str(num)))
    if len(num) == 11:
        return f"({num[:2]}) {num[2:7]}-{num[7:]}"
    elif len(num) == 10:
        return f"({num[:2]}) {num[2:6]}-{num[6:]}"
    return num


@st.cache_data(ttl=60)
def buscar_estoque_disponivel(data_festa):
    conn = conectar()
    cursor = conn.cursor(dictionary=True)

    inicio = datetime.combine(data_festa, time.min)
    fim = datetime.combine(data_festa, time.max)

    cursor.execute("""
        SELECT b.id, b.nome, b.quantidade_disponivel, b.preco_base,
        COALESCE((
            SELECT SUM(a.quantidade)
            FROM alugueis a
            WHERE a.brinquedo_id = b.id
            AND a.data_inicio BETWEEN %s AND %s
        ), 0) as ocupados
        FROM brinquedos b
    """, (inicio, fim))

    res = cursor.fetchall()
    conn.close()
    return res