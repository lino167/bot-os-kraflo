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
    # CORREÇÃO: Definimos o user.id e o chat.id para serem o mesmo valor.
    # Isto garante que a verificação do chat_id no final do teste funcione.
    update.effective_user.id = 123456
    update.effective_chat.id = 123456
    
    update.message.reply_text = AsyncMock()
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

# --- Teste do Fluxo de Fechamento de OS ---

async def test_full_close_os_flow_with_parts(mocker, mock_update, mock_context):
    """
    Testa a conversa completa de fechamento de OS, incluindo a adição de uma peça.
    """
    # 1. PREPARAÇÃO
    mock_open_os = [{'id': 101, 'equipamento_nome': 'Tear Picanol', 'equipamento_tag': 'PC-05'}]
    mocker.patch('handlers.service_order.get_open_os_paginated', new_callable=AsyncMock, return_value=mock_open_os)
    mock_close_os = mocker.patch('handlers.service_order.close_os_in_db', new_callable=AsyncMock, return_value=True)

    # --- SIMULAÇÃO DA CONVERSA PASSO A PASSO ---

    # ETAPA 1: Utilizador clica em "Fechar OS"
    estado_seguinte = await service_order.start_close_os(mock_update, mock_context)
    assert estado_seguinte == service_order.SELECT_OS_TO_CLOSE

    # ETAPA 2: Utilizador seleciona a OS
    mock_update.callback_query.data = 'close_101'
    estado_seguinte = await service_order.ask_for_solution(mock_update, mock_context)
    assert estado_seguinte == service_order.ASK_SOLUTION

    # ETAPA 3: Utilizador descreve a solução
    mock_update.message.text = "Correia principal substituída."
    estado_seguinte = await service_order.get_solution_and_ask_parts(mock_update, mock_context)
    assert estado_seguinte == service_order.ASK_IF_PARTS

    # ETAPA 4: Utilizador clica em "Sim" para adicionar peças
    mock_update.callback_query.data = 'parts_yes'
    estado_seguinte = await service_order.ask_part_name(mock_update, mock_context)
    assert estado_seguinte == service_order.ASK_PART_NAME

    # ETAPA 5: Utilizador envia o nome da peça
    mock_update.message.text = "Correia Dentada 50T"
    estado_seguinte = await service_order.get_part_name(mock_update, mock_context)
    assert estado_seguinte == service_order.ASK_PART_TAG

    # ETAPA 6: Utilizador envia a TAG da peça
    mock_update.message.text = "PN-12345-C"
    estado_seguinte = await service_order.get_part_tag(mock_update, mock_context)
    assert estado_seguinte == service_order.ASK_PART_QTY

    # ETAPA 7: Utilizador envia a quantidade
    mock_update.message.text = "1"
    estado_seguinte = await service_order.get_part_qty_and_ask_more(mock_update, mock_context)
    assert estado_seguinte == service_order.ASK_MORE_PARTS

    # ETAPA 8: Utilizador clica em "Não" para adicionar mais peças
    mock_update.callback_query.data = 'parts_no'
    estado_seguinte = await service_order.ask_for_final_status(mock_update, mock_context)
    assert estado_seguinte == service_order.ASK_FINAL_STATUS

    # ETAPA 9: Utilizador define o status final
    mock_update.callback_query.data = 'Concluída'
    estado_seguinte = await service_order.get_final_status_and_ask_if_notes(mock_update, mock_context)
    assert estado_seguinte == service_order.ASK_IF_NOTES

    # ETAPA 10: Utilizador opta por não adicionar notas
    mock_update.callback_query.data = 'notes_no'
    estado_final = await service_order.finalize_without_notes(mock_update, mock_context)

    # 3. VERIFICAÇÃO FINAL
    close_data_esperado = {
        "diagnostico_solucao": "Correia principal substituída.",
        "status_os": "Concluída",
        "notas_finais": '',
        "data_fechamento": "now()"
    }
    parts_data_esperado = [{
        "nome_peca": "Correia Dentada 50T",
        "tag_peca": "PN-12345-C",
        "quantidade": 1,
    }]
    
    mock_close_os.assert_awaited_once_with(101, close_data_esperado, parts_data_esperado)

    # Agora a verificação do chat_id vai funcionar corretamente
    mock_context.bot.send_message.assert_awaited_once_with(
        chat_id=123456,
        text="✅ Ordem de Serviço #101 fechada com sucesso!",
        reply_markup=mocker.ANY
    )
    assert estado_final == ConversationHandler.END
