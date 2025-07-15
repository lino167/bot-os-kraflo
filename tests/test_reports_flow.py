import pytest
from unittest.mock import AsyncMock, MagicMock, ANY
from handlers import reports
from handlers.reports import (
    CHOOSE_FILTER_TYPE,
    MANAGE_SELECTION,
)
from telegram.ext import ConversationHandler

# As fixtures continuam as mesmas
@pytest.fixture
def mock_update():
    """Fixture que cria um mock do objeto Update."""
    update = MagicMock()
    update.effective_user.id = 123456
    update.callback_query = AsyncMock()
    update.message = AsyncMock()
    return update

@pytest.fixture
def mock_context():
    """Fixture que cria um mock do objeto Context."""
    context = MagicMock()
    context.user_data = {}
    context.bot = AsyncMock()
    return context


@pytest.mark.asyncio
async def test_report_flow_today_to_csv(mocker, mock_update, mock_context):
    """
    Testa o fluxo completo de geração de um relatório CSV para as OS do dia.
    """
    # 1. PREPARAÇÃO
    mock_os_list = [
        {'id': 1, 'equipamento_nome': 'Torno CNC'},
        {'id': 2, 'equipamento_nome': 'Prensa Hidráulica'}
    ]
    mocker.patch('handlers.reports.get_all_os_for_report', return_value=mock_os_list)
    mock_generate_csv = mocker.patch('handlers.reports.generate_csv_report', new_callable=AsyncMock)

    # 2. AÇÃO e VERIFICAÇÃO - Passo a Passo

    # --- ETAPA 1: Usuário envia "Relatórios" (texto) ---
    mock_update.callback_query = None
    next_state = await reports.start_report_generation(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_with(mocker.ANY, reply_markup=mocker.ANY)
    assert next_state == CHOOSE_FILTER_TYPE

    # --- ETAPA 2: Usuário clica em "Relatório de Hoje" (botão) ---
    mock_update.callback_query = AsyncMock()
    mock_update.callback_query.data = 'report_today'
    next_state = await reports.handle_filter_choice(mock_update, mock_context)

    # --- CORREÇÃO FINAL AQUI ---
    # Verificamos que a função foi chamada uma vez.
    assert mock_update.callback_query.edit_message_text.await_count == 1
    
    # Pegamos os argumentos da chamada para inspecioná-los.
    call_args, call_kwargs = mock_update.callback_query.edit_message_text.await_args
    
    # Verificamos se o texto contém a frase que esperamos e se o reply_markup foi enviado.
    assert "Selecione as OS e escolha o formato:" in call_args[0]
    assert "reply_markup" in call_kwargs

    assert next_state == MANAGE_SELECTION
    assert mock_context.user_data['selected_os'] == [1, 2]

    # --- ETAPA 3: Usuário clica em "Gerar CSV" ---
    mock_update.callback_query.data = 'generate_csv'
    await reports.manage_selection(mock_update, mock_context)

    # 3. VERIFICAÇÃO FINAL
    mock_generate_csv.assert_awaited_once()


@pytest.mark.asyncio
async def test_report_flow_cancel(mocker, mock_update, mock_context):
    """Testa o cancelamento no menu de seleção de filtro de relatório."""
    mock_update.callback_query.data = 'cancel_report'
    next_state = await reports.handle_filter_choice(mock_update, mock_context)
    mock_update.callback_query.edit_message_text.assert_awaited_with("Geração de relatório cancelada.")
    assert next_state == ConversationHandler.END