import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram.ext import ConversationHandler

# Importa as funções que queremos testar
from handlers.common import start, cancel
# Importa o menu que esperamos que seja usado
from handlers.ui_components import MAIN_MENU_MARKUP

# Marca todos os testes neste ficheiro como assíncronos
pytestmark = pytest.mark.asyncio


async def test_start_command(mocker):
    """
    Testa se o comando /start envia a mensagem de boas-vindas correta
    com o menu principal para um utilizador registado.
    """
    # 1. PREPARAÇÃO
    mock_update = MagicMock()
    mock_update.effective_user.mention_html.return_value = "Test User"
    mock_update.message.reply_html = AsyncMock()
    mock_context = MagicMock()

    mocker.patch('handlers.common.is_user_registered', new_callable=AsyncMock, return_value=True)
    mocker.patch('handlers.common.get_user_data', new_callable=AsyncMock, return_value={'nome_completo': 'Utilizador Teste'})

    # 2. AÇÃO
    await start(mock_update, mock_context)

    # 3. VERIFICAÇÃO
    mock_update.message.reply_html.assert_awaited_with(
        "Olá, Utilizador Teste! Bem-vindo de volta.",
        reply_markup=MAIN_MENU_MARKUP,
    )


async def test_cancel_from_message(mocker):
    """
    Testa se a função cancel funciona corretamente quando chamada
    por uma mensagem de texto (update.message não é None).
    """
    # 1. PREPARAÇÃO
    mock_update = MagicMock()
    mock_update.callback_query = None # Garante que não há callback query
    mock_update.message.reply_text = AsyncMock()
    
    # Simula o user_data para testar se ele é limpo
    mock_context = MagicMock()
    mock_context.user_data = {'algum_dado': 'algum_valor'}

    # 2. AÇÃO
    resultado = await cancel(mock_update, mock_context)

    # 3. VERIFICAÇÃO
    # Verifica se a resposta de texto foi enviada
    mock_update.message.reply_text.assert_awaited_once_with(
        "Operação cancelada.", reply_markup=MAIN_MENU_MARKUP
    )
    # Verifica se o user_data foi limpo
    assert not mock_context.user_data 
    # Verifica se a função retornou o sinal para terminar a conversa
    assert resultado == ConversationHandler.END


async def test_cancel_from_callback_query(mocker):
    """
    Testa se a função cancel funciona corretamente quando chamada
    por um clique de botão (update.callback_query não é None).
    """
    # 1. PREPARAÇÃO
    mock_update = MagicMock()
    # Desta vez, simulamos um callback query
    mock_update.callback_query.answer = AsyncMock()
    mock_update.callback_query.edit_message_text = AsyncMock()
    
    mock_context = MagicMock()
    mock_context.user_data = {'algum_dado': 'algum_valor'}

    # 2. AÇÃO
    resultado = await cancel(mock_update, mock_context)

    # 3. VERIFICAÇÃO
    # Verifica se o callback foi respondido
    mock_update.callback_query.answer.assert_awaited_once()
    # Verifica se a mensagem original do botão foi editada
    mock_update.callback_query.edit_message_text.assert_awaited_once_with(
        text="Operação cancelada."
    )
    # Verifica se o user_data foi limpo
    assert not mock_context.user_data
    # Verifica se a função retornou o sinal para terminar a conversa
    assert resultado == ConversationHandler.END
