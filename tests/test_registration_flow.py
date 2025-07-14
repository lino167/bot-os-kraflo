import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram.ext import ConversationHandler

# Importa as funções e estados da conversa que vamos testar
from handlers import registration
from handlers.common import start
from handlers.ui_components import MAIN_MENU_MARKUP

# Marca todos os testes neste ficheiro como assíncronos
pytestmark = pytest.mark.asyncio

# --- Mocks reutilizáveis para os testes ---
@pytest.fixture
def mock_update():
    """Cria um mock padrão para o objeto 'update'."""
    update = MagicMock()
    update.effective_user.id = 123456
    update.message.reply_text = AsyncMock()
    update.message.reply_html = AsyncMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update

@pytest.fixture
def mock_context():
    """Cria um mock padrão para o objeto 'context'."""
    context = MagicMock()
    context.user_data = {} # Simula o dicionário para guardar dados da conversa
    return context

# --- Testes do Fluxo de Registo ---

async def test_start_para_novo_utilizador_inicia_registo(mocker, mock_update, mock_context):
    """
    Testa se o comando /start para um novo utilizador inicia corretamente
    a conversa de registo.
    """
    # 1. PREPARAÇÃO
    mocker.patch('handlers.common.is_user_registered', new_callable=AsyncMock, return_value=False)
    
    # 2. AÇÃO
    resultado_estado = await start(mock_update, mock_context)

    # 3. VERIFICAÇÃO
    mock_update.message.reply_text.assert_awaited_once_with(
        "Bem-vindo ao Bot de OS da Kraflo! Vejo que é o seu primeiro acesso.\n\n"
        "Vamos criar o seu cadastro. Para começar, qual o nome da sua EMPRESA?",
        reply_markup=mocker.ANY
    )
    assert resultado_estado == registration.ASK_COMPANY_NAME


async def test_fluxo_completo_de_registo_sem_codigo(mocker, mock_update, mock_context):
    """
    Testa toda a sequência de registo para um utilizador que não tem código de empresa.
    """
    # 1. PREPARAÇÃO
    # --- Mock da tabela 'empresas' ---
    mock_empresas_table = MagicMock()
    # Simula que a empresa ainda não existe
    mock_empresas_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    # Simula a resposta ao inserir a nova empresa
    mock_empresas_table.insert.return_value.execute.return_value = MagicMock(data=[{'id': 'uuid-da-empresa'}])

    # --- Mock da tabela 'tecnicos' ---
    mock_tecnicos_table = MagicMock()
    # Para o teste, a inserção do técnico não precisa de retornar nada especial
    mock_tecnicos_table.insert.return_value.execute.return_value = MagicMock(data=[])

    # --- Função de 'side_effect' para o .table() ---
    # Esta função irá retornar o mock correto dependendo do nome da tabela chamada
    def table_side_effect(table_name):
        if table_name == 'empresas':
            return mock_empresas_table
        elif table_name == 'tecnicos':
            return mock_tecnicos_table
        return MagicMock() # Retorna um mock genérico para segurança

    # --- Mock principal do cliente supabase ---
    mock_supabase_client = MagicMock()
    # Atribuímos a nossa função de side_effect ao método .table()
    mock_supabase_client.table.side_effect = table_side_effect
    mocker.patch('handlers.registration.supabase', mock_supabase_client)

    # --- SIMULAÇÃO DA CONVERSA PASSO A PASSO ---

    # ETAPA 1: Utilizador envia o nome da empresa
    mock_update.message.text = "Empresa Teste"
    await registration.ask_if_company_code(mock_update, mock_context)

    # ETAPA 2: Utilizador clica em "Não tenho código"
    mock_update.callback_query.data = 'code_no'
    await registration.ask_name_directly(mock_update, mock_context)

    # ETAPA 3: Utilizador envia o nome completo
    mock_update.message.text = "Utilizador de Teste"
    await registration.get_full_name_and_ask_role(mock_update, mock_context)

    # ETAPA 4: Utilizador envia a função
    mock_update.message.text = "Tester"
    await registration.get_role_and_ask_sector(mock_update, mock_context)

    # ETAPA 5: Utilizador envia o setor e finaliza
    mock_update.message.text = "QA"
    estado_final = await registration.get_sector_and_save(mock_update, mock_context)

    # 3. VERIFICAÇÃO FINAL
    # Agora verificamos cada mock de tabela individualmente
    mock_empresas_table.insert.assert_called_once_with({'nome_empresa': 'Empresa Teste'})

    dados_esperados = {
        "id_telegram": 123456,
        "nome_completo": "Utilizador de Teste",
        "funcao": "Tester",
        "setor": "QA",
        "codigo_empresa": None,
        "empresa_id": "uuid-da-empresa",
    }
    mock_tecnicos_table.insert.assert_called_once_with(dados_esperados)
    
    mock_update.message.reply_text.assert_awaited_with(
        "✅ Cadastro realizado com sucesso!\n\nAgora você tem acesso a todas as funcionalidades.",
        reply_markup=MAIN_MENU_MARKUP
    )
    assert estado_final == ConversationHandler.END

