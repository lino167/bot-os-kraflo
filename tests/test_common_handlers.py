import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Funções e Handlers a serem testados ou mockados
from handlers.common import start
from handlers.registration import ASK_COMPANY_NAME
from telegram.ext import ConversationHandler

@pytest.mark.asyncio
# Usamos @patch para interceptar as chamadas às funções do banco de dados
@patch('handlers.common.ask_company_name', new_callable=AsyncMock)
@patch('handlers.common.get_user_data', new_callable=AsyncMock)
@patch('handlers.common.is_user_registered', new_callable=AsyncMock)
async def test_start_for_registered_user(
    mock_is_registered, mock_get_data, mock_ask_name
):
    """Testa o fluxo da função start para um usuário já cadastrado."""
    
    # 1. Preparação (Arrange)
    # Forçamos o retorno das funções mockadas
    mock_is_registered.return_value = True # Simula que o usuário está no DB
    mock_get_data.return_value = {'nome_completo': 'Usuário Teste'} # Simula os dados do usuário

    mock_update = MagicMock()
    mock_update.effective_user = MagicMock()
    mock_update.effective_user.mention_html.return_value = "Usuário Teste" # Para a mensagem de olá
    mock_update.message = AsyncMock()

    # 2. Ação (Act)
    returned_state = await start(mock_update, MagicMock())

    # 3. Verificação (Assert)
    # Verifica se a verificação de usuário foi chamada
    mock_is_registered.assert_awaited_once()

    # Verifica se a mensagem de boas-vindas foi enviada
    mock_update.message.reply_html.assert_awaited_once()
    # Pega o primeiro argumento da chamada para verificar o texto
    call_args = mock_update.message.reply_html.call_args[0]
    assert "Olá, Usuário Teste! Bem-vindo de volta." in call_args[0]

    # Verifica que o fluxo de cadastro NÃO foi iniciado
    mock_ask_name.assert_not_called()

    # Verifica que a conversa terminou (não iniciou um novo fluxo)
    assert returned_state == ConversationHandler.END


@pytest.mark.asyncio
@patch('handlers.common.ask_company_name', new_callable=AsyncMock, return_value=ASK_COMPANY_NAME)
@patch('handlers.common.is_user_registered', new_callable=AsyncMock)
async def test_start_for_new_user(mock_is_registered, mock_ask_name):
    """Testa o fluxo da função start para um novo usuário."""

    # 1. Preparação (Arrange)
    mock_is_registered.return_value = False # Simula que o usuário NÃO está no DB
    
    mock_update = MagicMock()
    mock_update.effective_user = MagicMock()
    mock_update.message = AsyncMock()

    # 2. Ação (Act)
    returned_state = await start(mock_update, MagicMock())

    # 3. Verificação (Assert)
    mock_is_registered.assert_awaited_once()
    
    # Verifica que a mensagem de boas-vindas NÃO foi enviada
    mock_update.message.reply_html.assert_not_called()
    
    # Verifica que o fluxo de cadastro FOI iniciado
    mock_ask_name.assert_awaited_once()

    # Verifica que o estado retornado é o de início do cadastro
    assert returned_state == ASK_COMPANY_NAME