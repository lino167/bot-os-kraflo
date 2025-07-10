import logging
from config import supabase # Importa a instância do Supabase do nosso arquivo de configuração

# Configura o logger para este módulo
logger = logging.getLogger(__name__)

async def is_user_registered(user_id: int) -> bool:
    """
    Verifica no banco de dados Supabase se um usuário, com base no seu ID do Telegram,
    já possui um cadastro na tabela 'tecnicos'.

    Args:
        user_id: O ID do usuário do Telegram.

    Returns:
        True se o usuário estiver cadastrado, False caso contrário.
    """
    if not supabase:
        logger.error("A conexão com o Supabase não está disponível.")
        return False
        
    try:
        # Executa a consulta para encontrar um técnico com o ID fornecido
        response = supabase.table('tecnicos').select('id_telegram').eq('id_telegram', user_id).execute()
        
        # Retorna True se a lista de dados não estiver vazia (ou seja, encontrou o usuário)
        return len(response.data) > 0
    except Exception as e:
        logger.error(f"Erro ao verificar o cadastro do usuário {user_id}: {e}")
        return False

# No futuro, outras funções de banco de dados como:
# - save_work_order
# - get_open_work_orders
# - get_company_by_user
# ...serão adicionadas aqui.
