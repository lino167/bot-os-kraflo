import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram.ext import ConversationHandler

# Importa as funções e estados da conversa que vamos testar
from handlers import service_order

# Marca todos os testes neste ficheiro como assíncronos
pytestmark = pytest.mark.asyncio

# --- Mocks reutilizáveis para os testes ---
@pytest.fixture
def mock_update():
    """Cria um mock padrão para o objeto 'update'."""
    update = MagicMock()
    update.effective_user.id = 123456
    update.message.reply_text = AsyncMock()
    # Adicionamos o reply_html para ser consistente com outros handlers
    update.message.reply_html = AsyncMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update

@pytest.fixture
def mock_context():
    """Cria um mock padrão para o objeto 'context'."""
    context = MagicMock()
    context.user_data = {} # Simula o dicionário para guardar dados da conversa
    context.bot.send_message = AsyncMock() # Mock para o envio de mensagens finais
    return context

# --- Teste do Fluxo de Abertura de OS ---

async def test_full_open_os_flow_no_photo(mocker, mock_update, mock_context):
    """
    Testa a conversa completa de abertura de OS, para o caso em que o utilizador
    decide não anexar uma foto.
    """
    # 1. PREPARAÇÃO
    # Simulamos as funções de base de dados que são chamadas no final
    mocker.patch('handlers.service_order.get_user_data', new_callable=AsyncMock, return_value={'empresa_id': 'uuid-da-empresa'})
    mock_save_new_os = mocker.patch('handlers.service_order.save_new_os', new_callable=AsyncMock, return_value={'id': 99})

    # --- SIMULAÇÃO DA CONVERSA PASSO A PASSO ---

    # ETAPA 1: Utilizador clica em "Abrir OS", a função 'start_open_os' é chamada
    estado_seguinte = await service_order.start_open_os(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_with(
        "Você selecionou 'Abrir OS'. Deseja iniciar o processo?",
        reply_markup=mocker.ANY
    )
    assert estado_seguinte == service_order.CONFIRM_SAVE

    # ETAPA 2: Utilizador clica "Sim, começar"
    mock_update.callback_query.data = 'start_os'
    estado_seguinte = await service_order.ask_for_equipment(mock_update, mock_context)
    mock_update.callback_query.edit_message_text.assert_awaited_with(text="Ótimo! Qual equipamento ou ativo precisa de manutenção?")
    assert estado_seguinte == service_order.ASK_EQUIPMENT

    # ETAPA 3: Utilizador envia o nome do equipamento
    mock_update.message.text = "Tear Picanol"
    estado_seguinte = await service_order.get_equipment_name(mock_update, mock_context)
    assert estado_seguinte == service_order.ASK_TAG

    # ETAPA 4: Utilizador envia a TAG
    mock_update.message.text = "PC-05"
    estado_seguinte = await service_order.get_equipment_tag(mock_update, mock_context)
    assert estado_seguinte == service_order.ASK_LOCATION

    # ETAPA 5: Utilizador envia a Localização
    mock_update.message.text = "Corredor B"
    estado_seguinte = await service_order.get_location(mock_update, mock_context)
    assert estado_seguinte == service_order.ASK_MAINT_TYPE

    # ETAPA 6: Utilizador clica no tipo de manutenção
    mock_update.callback_query.data = 'Corretiva'
    estado_seguinte = await service_order.get_maintenance_type(mock_update, mock_context)
    assert estado_seguinte == service_order.ASK_PRIORITY
    
    # ETAPA 7: Utilizador clica na prioridade
    mock_update.callback_query.data = 'Alta'
    estado_seguinte = await service_order.get_priority(mock_update, mock_context)
    assert estado_seguinte == service_order.ASK_PROBLEM_DESC
    
    # ETAPA 8: Utilizador descreve o problema
    mock_update.message.text = "Máquina parada, não liga."
    estado_seguinte = await service_order.get_problem_description_and_ask_photo(mock_update, mock_context)
    assert estado_seguinte == service_order.ASK_IF_PHOTO

    # ETAPA 9: Utilizador clica em "Não, pular" a foto
    mock_update.callback_query.data = 'photo_no'
    estado_final = await service_order.save_os_and_finish(mock_update, mock_context)

    # 3. VERIFICAÇÃO FINAL
    # Verifica se a função para guardar a OS foi chamada com os dados corretos
    dados_esperados = {
        'equipamento_nome': 'Tear Picanol',
        'equipamento_tag': 'PC-05',
        'localizacao': 'Corredor B',
        'tipo_manutencao': 'Corretiva',
        'prioridade': 'Alta',
        'descricao_problema': 'Máquina parada, não liga.',
        'status_os': 'Aberta',
        'tecnico_id': 123456,
        'empresa_id': 'uuid-da-empresa'
    }
    mock_save_new_os.assert_awaited_once_with(dados_esperados)

    # Verifica se a mensagem final de sucesso foi enviada
    mock_context.bot.send_message.assert_awaited_once_with(
        chat_id=123456,
        text="✅ Ordem de Serviço #99 aberta com sucesso!",
        reply_markup=mocker.ANY
    )

    # Verifica se a conversa terminou
    assert estado_final == ConversationHandler.END

