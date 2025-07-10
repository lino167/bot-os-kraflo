import logging
from config import supabase

# Configura o logger para este módulo
logger = logging.getLogger(__name__)


async def is_user_registered(user_id: int) -> bool:
    """Verifica no banco de dados se um usuário já está cadastrado."""
    if not supabase:
        logger.error("A conexão com o Supabase não está disponível.")
        return False
    try:
        response = supabase.table('tecnicos').select('id_telegram').eq('id_telegram', user_id).execute()
        return len(response.data) > 0
    except Exception as e:
        logger.error(f"Erro ao verificar o cadastro do usuário {user_id}: {e}")
        return False


async def get_user_data(user_id: int) -> dict | None:
    """Busca os dados de um técnico, incluindo o ID da empresa."""
    if not supabase:
        logger.error("A conexão com o Supabase não está disponível.")
        return None
    try:
        response = supabase.table('tecnicos').select('id_telegram, empresa_id').eq('id_telegram', user_id).single().execute()
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar dados do usuário {user_id}: {e}")
        return None


async def save_new_os(os_data: dict) -> dict | None:
    """Salva uma nova Ordem de Serviço no banco de dados."""
    if not supabase:
        logger.error("A conexão com o Supabase não está disponível.")
        return None
    try:
        response = supabase.table('ordens_de_servico').insert(os_data).execute()
        logger.info(f"Nova OS #{response.data[0]['id']} salva com sucesso.")
        return response.data[0]
    except Exception as e:
        logger.error(f"Erro ao salvar nova OS: {e}")
        return None


async def get_open_os_by_user(user_id: int) -> list[dict] | None:
    """
    Busca todas as OS com status 'Aberta' para um técnico.
    AGORA INCLUI A TAG DO EQUIPAMENTO.
    """
    try:
        # ALTERAÇÃO: Adicionado 'equipamento_tag' na seleção.
        response = supabase.table('ordens_de_servico').select('id, equipamento_nome, equipamento_tag').eq('tecnico_id', user_id).eq('status_os', 'Aberta').execute()
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar OS abertas para o usuário {user_id}: {e}")
        return None


async def close_os_in_db(os_id: int, close_data: dict, parts_data: list[dict]) -> bool:
    """Atualiza uma OS para 'Fechada' e, se houver, insere as peças utilizadas."""
    try:
        supabase.table('ordens_de_servico').update(close_data).eq('id', os_id).execute()
        logger.info(f"OS #{os_id} atualizada para o status '{close_data.get('status_os')}'.")

        if parts_data:
            for part in parts_data:
                part['ordem_id'] = os_id
            
            supabase.table('pecas_utilizadas').insert(parts_data).execute()
            logger.info(f"{len(parts_data)} peças adicionadas para a OS #{os_id}.")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao fechar a OS #{os_id} no banco de dados: {e}")
        return False
