import pytest
from unittest.mock import AsyncMock, MagicMock

# Importando a função que queremos testar e a variável de estado
from handlers.service_order import get_equipment_name, ASK_TAG

@pytest.mark.asyncio
async def test_get_equipment_name():
    """
    Testa se a função get_equipment_name salva o nome do equipamento
    e retorna o estado correto.
    """
    # 1. Preparação (Arrange) - Criação dos Mocks
    
    # Mock do objeto Update: Simula uma atualização vinda do Telegram
    mock_update = MagicMock()
    mock_update.message = AsyncMock()
    mock_update.message.text = "Torno Mecânico 123" # O texto que o usuário enviou
    
    # Mock do objeto Context: Simula o contexto do bot
    mock_context = MagicMock()
    mock_context.user_data = {} # Começamos com user_data vazio

    # 2. Ação (Act) - Chamada da função a ser testada
    returned_state = await get_equipment_name(mock_update, mock_context)

    # 3. Verificação (Assert) - Checamos se tudo ocorreu como esperado
    
    # Verifica se a função de resposta foi chamada com o texto correto
    mock_update.message.reply_text.assert_awaited_once_with(
        "Entendido. Qual a TAG/identificador do equipamento?"
    )

    # Verifica se o user_data foi atualizado corretamente
    assert 'os_data' in mock_context.user_data
    assert mock_context.user_data['os_data']['equipamento_nome'] == "Torno Mecânico 123"

    # Verifica se a função retornou o estado correto para a ConversationHandler
    assert returned_state == ASK_TAG