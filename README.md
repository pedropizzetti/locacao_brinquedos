# Sistema de Gestão: Mais Brinquedos

Este projeto é uma solução completa para o gerenciamento de locação de brinquedos. Desenvolvido para transformar o controle manual (planilhas/papel) em um sistema digital ágil, seguro e acessível de qualquer lugar.

---

## Sistema Online

O projeto está hospedado e pronto para uso:
[Acesse aqui](https://maisbrinquedos.streamlit.app/)

---

## O que o sistema faz?

* **Agenda Inteligente:** Controle total das entregas e coletas organizadas por data.
* **CRM de Clientes:** Cadastro rápido com histórico e link direto para conversa no WhatsApp.
* **Inventário Real:** Gestão de disponibilidade de infláveis, camas elásticas e mesas.
* **Segurança:** Painel administrativo restrito para proteção dos dados da empresa.

---

## Arquitetura do Sistema

Diferente de sistemas que rodam apenas no computador, este projeto utiliza tecnologias modernas de nuvem:

* **Frontend/Dashboard:** Python com Streamlit
* **Banco de Dados:** TiDB Cloud (Arquitetura MySQL distribuída)
* **Hospedagem:** Streamlit Community Cloud

---

## ⚙️ Como rodar este projeto

### 1. Clone o repositório

```bash
git clone https://github.com/pedropizzetti/locacao_brinquedos.git
```

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Configure as credenciais

Configure as *secrets* do Streamlit com as credenciais do seu TiDB Cloud para permitir a conexão com o banco de dados.

### 4. Execute o projeto

```bash
streamlit run app.py
```

---

## Observações

* Certifique-se de estar com o ambiente Python configurado corretamente
* É necessário acesso ao TiDB Cloud para funcionamento completo do sistema

---
