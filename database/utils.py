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
        response = supabase.table('tecnicos').select('id_telegram, empresa_id').single().execute()
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
        new_os = response.data[0]
        logger.info(f"Nova OS #{new_os['id']} salva com sucesso.")
        return new_os
    except Exception as e:
        logger.error(f"Erro ao salvar nova OS: {e}")
        return None


async def get_open_os_by_user(user_id: int) -> list[dict] | None:
    """
    Busca todas as OS abertas para um determinado técnico com mais detalhes,
    ordenadas pela mais antiga primeiro.
    """
    try:
        # ALTERAÇÃO: Selecionamos mais colunas para a listagem.
        response = (
            supabase.table("ordens_de_servico")
            .select("id, equipamento_nome, equipamento_tag, prioridade, tipo_manutencao")
            .eq("tecnico_id", user_id)
            .eq("status_os", "Aberta")
            .order("id", desc=False) # Garante que as mais antigas apareçam primeiro
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar OS abertas para o usuário {user_id}: {e}")
        return None


async def close_os_in_db(os_id: int, close_data: dict, parts_data: list[dict]) -> bool:
    """Atualiza uma OS e, se houver, insere as peças utilizadas."""
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
async def get_all_os_for_report(user_id: int) -> list[dict] | None:
    """
    Busca todas as OS de uma empresa, com base no usuário que pediu,
    para a geração de relatórios. Junta os dados do técnico responsável.
    """
    try:
        # Primeiro, descobre a qual empresa o usuário pertence
        user_data = await get_user_data(user_id)
        if not user_data:
            return None
        
        empresa_id = user_data['empresa_id']

        # Agora, busca todas as OS daquela empresa, fazendo um join com a tabela de técnicos
        response = (
            supabase.table("ordens_de_servico")
            .select(
                "*, tecnicos(nome_completo)"
            )
            .eq("empresa_id", empresa_id)
            .order("id", desc=False)
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar dados para relatório da empresa do usuário {user_id}: {e}")
        return None
    
async def get_single_os_details(os_id: int) -> dict | None:
    """
    Busca todos os detalhes de uma única OS, incluindo o nome do técnico
    e a lista de peças utilizadas.

    Args:
        os_id: O ID da Ordem de Serviço a ser detalhada.

    Returns:
        Um dicionário com todos os dados da OS ou None em caso de erro.
    """
    try:
        # Busca a OS e faz um "join" para pegar o nome do técnico e a lista de peças
        response = (
            supabase.table("ordens_de_servico")
            .select(
                "*, tecnico:tecnicos(nome_completo, funcao), pecas:pecas_utilizadas(*)"
            )
            .eq("id", os_id)
            .single() # Esperamos apenas um resultado
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes da OS #{os_id}: {e}")
        return None