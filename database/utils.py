import logging
from config import supabase

logger = logging.getLogger(__name__)

async def is_user_registered(user_id: int) -> bool:
    """Verifica no Supabase se o usuário já está cadastrado."""
    try:
        response = supabase.table('tecnicos').select('id_telegram', count='exact').eq('id_telegram', user_id).execute()
        return response.count > 0
    except Exception as e:
        logger.error(f"Erro ao verificar usuário {user_id}: {e}")
        return False

async def get_user_data(user_id: int) -> dict | None:
    """Busca os dados de um técnico, incluindo o ID da empresa."""
    try:
        response = supabase.table('tecnicos').select('id_telegram, empresa_id').eq('id_telegram', user_id).single().execute()
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar dados do usuário {user_id}: {e}")
        return None

async def save_new_os(os_data: dict) -> dict | None:
    """Salva uma nova Ordem de Serviço no banco de dados e retorna os dados da OS."""
    try:
        response = supabase.table('ordens_de_servico').insert(os_data).execute()
        if response.data:
            new_os = response.data[0]
            logger.info(f"Nova OS #{new_os['id']} salva com sucesso.")
            return new_os
        return None
    except Exception as e:
        logger.error(f"Erro ao salvar nova OS: {e}")
        return None

async def get_open_os_paginated(user_id: int, page: int, page_size: int) -> list | None:
    """Busca uma 'página' de OS abertas para um determinado técnico."""
    try:
        offset = page * page_size
        response = supabase.table('ordens_de_servico').select(
            'id, equipamento_nome, prioridade, tipo_manutencao, equipamento_tag'
        ).eq('tecnico_id', user_id).eq('status_os', 'Aberta').order('id', desc=False).range(offset, offset + page_size - 1).execute()
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar OS abertas paginada para o usuário {user_id}: {e}")
        return None

async def get_open_os_count(user_id: int) -> int:
    """Conta o número total de OS abertas para um usuário."""
    try:
        response = supabase.table('ordens_de_servico').select(
            'id', count='exact'
        ).eq('tecnico_id', user_id).eq('status_os', 'Aberta').execute()
        return response.count
    except Exception as e:
        logger.error(f"Erro ao contar OS abertas para o usuário {user_id}: {e}")
        return 0

async def get_closed_os_paginated(user_id: int, page: int, page_size: int) -> list | None:
    """Busca uma 'página' de OS fechadas ou pendentes para um determinado técnico."""
    try:
        offset = page * page_size
        response = supabase.table('ordens_de_servico').select(
            'id, equipamento_nome, status_os, data_fechamento'
        ).eq('tecnico_id', user_id).neq('status_os', 'Aberta').order('id', desc=True).range(offset, offset + page_size - 1).execute()
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar OS fechadas paginada para o usuário {user_id}: {e}")
        return None

async def get_closed_os_count(user_id: int) -> int:
    """Conta o número total de OS fechadas ou pendentes para um usuário."""
    try:
        response = supabase.table('ordens_de_servico').select(
            'id', count='exact'
        ).eq('tecnico_id', user_id).neq('status_os', 'Aberta').execute()
        return response.count
    except Exception as e:
        logger.error(f"Erro ao contar OS fechadas para o usuário {user_id}: {e}")
        return 0

async def close_os_in_db(os_id: int, close_data: dict, parts_data: list) -> bool:
    try:
        supabase.table('ordens_de_servico').update(close_data).eq('id', os_id).execute()
        logger.info(f"OS #{os_id} atualizada para status '{close_data.get('status_os')}'.")
        if parts_data:
            for part in parts_data:
                part['ordem_id'] = os_id
            supabase.table('pecas_utilizadas').insert(parts_data).execute()
            logger.info(f"{len(parts_data)} peças registradas para a OS #{os_id}.")
        return True
    except Exception as e:
        logger.error(f"Erro ao fechar OS #{os_id} no banco de dados: {e}")
        return False

async def get_all_os_for_report(user_id: int, start_date: str = None, end_date: str = None) -> list[dict] | None:
    """Busca todas as OS de uma empresa, com base no usuário, com filtro de data opcional."""
    try:
        user_data = await get_user_data(user_id)
        if not user_data:
            return None
        empresa_id = user_data['empresa_id']
        query = (
            supabase.table("ordens_de_servico")
            .select("*, tecnicos(nome_completo)")
            .eq("empresa_id", empresa_id)
        )
        if start_date:
            query = query.gte("data_abertura", start_date)
        if end_date:
            query = query.lte("data_abertura", end_date)
        response = query.order("id", desc=False).execute()
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar dados para relatório: {e}")
        return None

async def get_single_os_details(os_id: int) -> dict | None:
    """Busca todos os detalhes de uma única OS."""
    try:
        response = (
            supabase.table("ordens_de_servico")
            .select("*, tecnico:tecnicos(nome_completo, funcao), pecas:pecas_utilizadas(*)")
            .eq("id", os_id)
            .single()
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes da OS #{os_id}: {e}")
        return None

async def get_closed_os_paginated(user_id: int, page: int, page_size: int) -> list | None:
    """
    Busca uma 'página' de OS fechadas ou pendentes para um determinado técnico.
    """
    try:
        offset = page * page_size
        response = supabase.table('ordens_de_servico').select(
            'id, equipamento_nome, status_os, data_fechamento'
        ).eq('tecnico_id', user_id).neq('status_os', 'Aberta').order('id', desc=True).range(offset, offset + page_size - 1).execute()
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar OS fechadas paginada para o usuário {user_id}: {e}")
        return None

async def get_closed_os_count(user_id: int) -> int:
    """Conta o número total de OS fechadas ou pendentes para um usuário."""
    try:
        response = supabase.table('ordens_de_servico').select(
            'id', count='exact'
        ).eq('tecnico_id', user_id).neq('status_os', 'Aberta').execute()
        return response.count
    except Exception as e:
        logger.error(f"Erro ao contar OS fechadas para o usuário {user_id}: {e}")
        return 0