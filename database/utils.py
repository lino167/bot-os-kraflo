import logging
from config import supabase

logger = logging.getLogger(__name__)

async def is_user_registered(user_id: int) -> bool:
    """Verifica no Supabase se o usuário já está cadastrado."""
    try:
        response = supabase.table('tecnicos').select('id_telegram').eq('id_telegram', user_id).execute()
        return len(response.data) > 0
    except Exception as e:
        logger.error(f"Erro ao verificar usuário {user_id}: {e}")
        return False

async def get_user_data(user_id: int) -> dict | None:
    """Busca os dados de um técnico, incluindo o ID da empresa."""
    try:
        response = supabase.table('tecnicos').select('id_telegram, empresa_id').eq('id_telegram', user_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar dados do usuário {user_id}: {e}")
        return None

async def save_new_os(os_data: dict) -> int | None:
    """Salva uma nova Ordem de Serviço no banco de dados."""
    try:
        response = supabase.table('ordens_de_servico').insert(os_data).execute()
        if response.data:
            new_os_id = response.data[0]['id']
            logger.info(f"Nova OS #{new_os_id} salva com sucesso.")
            return new_os_id
        return None
    except Exception as e:
        logger.error(f"Erro ao salvar nova OS: {e}")
        return None