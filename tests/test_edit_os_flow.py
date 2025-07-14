import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram.ext import ConversationHandler

# Importa as funções e estados da conversa que vamos testar
from handlers import os_edit

# Marca todos os testes neste ficheiro como assíncronos
pytestmark = pytest.mark.asyncio

# --- Mocks reutilizáveis para os testes ---
@pytest.fixture
def mock_update():
    """Cria um mock padrão para o objeto 'update'."""
    update = MagicMock()
    update.effective_user.id = 123456
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    update.message.reply_html = AsyncMock()
    update.message.reply_markdown = AsyncMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update

@pytest.fixture
def mock_context():
    """Cria um mock padrão para o objeto 'context'."""
    context = MagicMock()
    context.user_data = {}
    context.bot.delete_message = AsyncMock()
    return context

# --- Teste do Fluxo de Edição de OS ---

async def test_full_edit_os_flow_text_field(mocker, mock_update, mock_context):
    """
    Testa o fluxo completo de edição de um campo de texto numa OS.
    """
    # 1. PREPARAÇÃO
    # Simula as funções de base de dados que serão chamadas
    mocker.patch('handlers.os_edit.get_editable_os_count', new_callable=AsyncMock, return_value=1)
    mock_os_list = [{'id': 101, 'equipamento_nome': 'Tear Picanol', 'status_os': 'Aberta'}]
    mocker.patch('handlers.os_edit.get_editable_os_paginated', new_callable=AsyncMock, return_value=mock_os_list)
    
    mock_os_details = {'id': 101, 'equipamento_nome': 'Tear Picanol', 'status_os': 'Aberta', 'descricao_problema': 'Valor antigo'}
    mocker.patch('handlers.os_edit.get_single_os_details', new_callable=AsyncMock, return_value=mock_os_details)
    
    mock_update_field = mocker.patch('handlers.os_edit.update_os_field', new_callable=AsyncMock, return_value=True)

    # --- SIMULAÇÃO DA CONVERSA PASSO A PASSO ---

    # ETAPA 1: Utilizador clica em "Editar OS", a função 'start_edit_os' é chamada
    estado_seguinte = await os_edit.start_edit_os(mock_update, mock_context)
    assert estado_seguinte == os_edit.PAGINATING_EDIT_OS

    # ETAPA 2: Utilizador seleciona a OS para editar
    mock_update.callback_query.data = 'edit_select_os_101'
    estado_seguinte = await os_edit.show_edit_menu(mock_update, mock_context)
    assert estado_seguinte == os_edit.SELECT_FIELD

    # ETAPA 3: Utilizador seleciona o campo "Descrição do Problema"
    mock_update.callback_query.data = 'edit_field_descricao_problema'
    estado_seguinte = await os_edit.prompt_for_new_value(mock_update, mock_context)
    assert estado_seguinte == os_edit.GET_NEW_VALUE_TEXT

    # ETAPA 4: Utilizador envia o novo texto para a descrição
    mock_update.message.text = "Novo valor para a descrição"
    # Esta função irá atualizar o campo e depois chamar show_edit_menu novamente
    estado_final = await os_edit.update_field_from_text(mock_update, mock_context)

    # 3. VERIFICAÇÃO FINAL
    # Verifica se a função de atualização foi chamada com os dados corretos
    mock_update_field.assert_awaited_once_with(101, 'descricao_problema', 'Novo valor para a descrição')
    
    # Verifica se a mensagem de sucesso foi enviada
    mock_update.message.reply_text.assert_awaited_with("✅ Campo atualizado com sucesso!")
    
    # Verifica se a conversa retornou ao menu de seleção de campos
    assert estado_final == os_edit.SELECT_FIELD
