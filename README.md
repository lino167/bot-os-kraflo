<div align="center">
  <img src="./assets/Log redonda.png" alt="Kraflo Logo" width="150"/>
  <h1>Kraflo OS Bot - Gestor de Ordens de Serviço</h1>
  <p><strong>Automação industrial</strong></p>
  <p>
    Um bot de Telegram completo para a gestão de Ordens de Serviço (OS) industriais, construído com Python, Telegram Bot API e Supabase.
  </p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python" alt="Python Version">
    <img src="https://img.shields.io/badge/Supabase-PostgreSQL-green?style=for-the-badge&logo=supabase" alt="Supabase">
    <img src="https://img.shields.io/badge/Telegram-Bot%20API-blue?style=for-the-badge&logo=telegram" alt="Telegram">
  </p>
</div>

---

## 🎯 Sobre o Projeto

O **Kraflo OS Bot** foi desenvolvido como uma solução moderna e eficiente para otimizar o fluxo de trabalho de técnicos de manutenção no chão de fábrica. A aplicação permite a abertura e o fecho de Ordens de Serviço diretamente pelo telemóvel, utilizando uma interface de conversa totalmente guiada por botões, o que minimiza erros e agiliza o processo.

A arquitetura é **multi-empresa**, projetada para ser segura, escalável e de fácil manutenção, com dados de cada cliente isolados através de políticas de segurança a nível do banco de dados (RLS).

## ✨ Funcionalidades Principais

* **🤖 Interface Intuitiva:** Fluxos de conversa 100% guiados por botões, eliminando a necessidade de memorizar comandos.
* **🏢 Arquitetura Multi-Empresa:** Sistema de auto-registo para novos técnicos e empresas, com isolamento de dados garantido por RLS.
* **📋 Gestão Completa de OS:** Ciclo de vida completo, desde a abertura (com tipo, prioridade, detalhes do equipamento) até ao fecho.
* **🔩 Controlo de Peças:** Registo detalhado das peças utilizadas em cada manutenção, com nome, código e quantidade.
* **📸 Upload de Fotos:** Permite anexar uma imagem do problema diretamente na abertura da OS, utilizando o Supabase Storage.
* **📄 Relatórios Profissionais:** Geração interativa de relatórios em **PDF** (com branding da empresa) e **CSV** (para análise de dados).
* **📅 Filtros Avançados:** Sistema de relatórios com filtros por data ("Hoje", "Ontem") e um calendário interativo para seleção de períodos personalizados.
* **📖 Consultas Paginadas:** Listagens de OS abertas e fechadas com paginação para uma experiência de usuário limpa, mesmo com um grande volume de dados.

## 🛠️ Tecnologias e Arquitetura

Este projeto foi construído com uma stack de tecnologias modernas e uma arquitetura modular para garantir a manutenibilidade.

* **Linguagem:** Python
* **Framework do Bot:** `python-telegram-bot`
* **Backend & Banco de Dados:** Supabase (PostgreSQL)
* **Armazenamento de Ficheiros:** Supabase Storage
* **Geração de PDF:** `fpdf2`
* **Manipulação de Dados:** `pandas`
* **Controle de Versão:** Git & GitHub

A estrutura do projeto é dividida em responsabilidades claras:


/bot-os-kraflo
|-- /assets/          # Imagens e logos
|-- /database/        # Módulo de acesso ao banco de dados
|-- /handlers/        # Módulos com a lógica de cada fluxo do bot
|-- .env              # Ficheiro para as chaves de API
|-- main.py           # Orquestrador principal da aplicação
|-- requirements.txt  # Dependências do projeto


## 🚀 Como Executar o Projeto

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/lino167/bot-os-kraflo.git](https://github.com/lino167/bot-os-kraflo.git)
    cd bot-os-kraflo
    ```
2.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # No Linux/macOS
    # ou
    .\.venv\Scripts\Activate.ps1 # No Windows PowerShell
    ```
3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure as variáveis de ambiente:**
    * Crie um ficheiro chamado `.env` na raiz do projeto.
    * Preencha com as suas chaves:
        ```env
        TELEGRAM_TOKEN="SEU_TOKEN_DO_TELEGRAM"
        SUPABASE_URL="SUA_URL_DO_SUPABASE"
        SUPABASE_KEY="SUA_CHAVE_ANON_DO_SUPABASE"
        ```
5.  **Execute o bot:**
    ```bash
    python main.py
    ```

## 👤 Autor

**Zacarias Ramos**

* [LinkedIn](https://www.linkedin.com/in/zacarias-lino-ramos-filho-5203b61a2/)
* [GitHub](https://github.com/lino167)
