import pytest
from unittest.mock import MagicMock, AsyncMock
from types import SimpleNamespace

# Importa a função que queremos testar
from database.utils import is_user_registered

# Marca todos os testes neste ficheiro como assíncronos
pytestmark = pytest.mark.asyncio


async def test_is_user_registered_quando_usuario_existe(mocker):
    """
    Testa o caso em que o usuário JÁ está registado.
    Verifica se a função retorna True.
    """
    # 1. PREPARAÇÃO (Arrange)
    # Criamos um objeto de resposta simulado e preciso.
    mock_response = SimpleNamespace(count=1)

    # Cria uma simulação do cliente Supabase
    mock_supabase_client = MagicMock()
    
    # A função .execute() é síncrona.
    # Simulamos que ela retorna diretamente o nosso objeto de resposta.
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

    # Substitui o cliente 'supabase' real pelo nosso simulado
    mocker.patch('database.utils.supabase', mock_supabase_client)

    # 2. AÇÃO (Act)
    # A função is_user_registered é async, então a chamamos com await.
    resultado = await is_user_registered(user_id=12345)

    # 3. VERIFICAÇÃO (Assert)
    assert resultado is True


async def test_is_user_registered_quando_usuario_nao_existe(mocker):
    """
    Testa o caso em que o usuário NÃO está registado.
    Verifica se a função retorna False.
    """
    # 1. PREPARAÇÃO (Arrange)
    mock_response = SimpleNamespace(count=0)

    mock_supabase_client = MagicMock()
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
    
    mocker.patch('database.utils.supabase', mock_supabase_client)

    # 2. AÇÃO (Act)
    resultado = await is_user_registered(user_id=99999)

    # 3. VERIFICAÇÃO (Assert)
    assert resultado is False


async def test_is_user_registered_em_caso_de_excecao(mocker):
    """
    Testa o que acontece se o Supabase der um erro.
    Verifica se a função retorna False de forma segura.
    """
    # 1. PREPARAÇÃO (Arrange)
    mock_supabase_client = MagicMock()
    # A função síncrona .execute() pode levantar uma exceção.
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("Erro de conexão simulado")

    mocker.patch('database.utils.supabase', mock_supabase_client)

    # 2. AÇÃO (Act)
    resultado = await is_user_registered(user_id=12345)

    # 3. VERIFICAÇÃO (Assert)
    assert resultado is False
