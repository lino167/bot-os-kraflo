import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

# Importações dos nossos próprios módulos
from handlers.common import cancel, MAIN_MENU_MARKUP
from database.utils import get_user_data, save_new_os, get_open_os_by_user, close_os_in_db, is_user_registered

# Configura o logger para este módulo
logger = logging.getLogger(__name__)

# --- Definição dos Estados da Conversa ---
# Estados para ABERTURA de OS
(ASK_EQUIPMENT, ASK_TAG, ASK_LOCATION, ASK_MAINT_TYPE, 
 ASK_PRIORITY, ASK_PROBLEM_DESC, CONFIRM_SAVE) = range(7, 14)

# Estados para FECHAMENTO de OS (com a nova etapa de decisão)
(SELECT_OS_TO_CLOSE, ASK_SOLUTION, ASK_IF_PARTS, ASK_PART_NAME, 
 ASK_PART_TAG, ASK_PART_QTY, ASK_MORE_PARTS, ASK_FINAL_STATUS, 
 ASK_IF_NOTES, GET_FINAL_NOTES) = range(14, 24) # Numeração estendida

# --- FLUXO DE ABERTURA DE OS (Sem alterações) ---
# (O código de abertura de OS permanece o mesmo)
async def start_open_os(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [[InlineKeyboardButton("Sim, começar", callback_data="start_os")], [InlineKeyboardButton("Não, voltar", callback_data="cancel_os")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Você selecionou 'Abrir OS'. Deseja iniciar o processo?", reply_markup=reply_markup)
    return CONFIRM_SAVE

async def ask_for_equipment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == 'start_os':
        await query.edit_message_text(text="Ótimo! Qual equipamento ou ativo precisa de manutenção?")
        return ASK_EQUIPMENT
    else:
        await query.edit_message_text(text="Abertura de OS cancelada.")
        return await cancel(update, context)

async def get_equipment_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['os_data'] = {'equipamento_nome': update.message.text}
    await update.message.reply_text("Entendido. Qual a TAG/identificador do equipamento?")
    return ASK_TAG

async def get_equipment_tag(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['os_data']['equipamento_tag'] = update.message.text
    await update.message.reply_text("Qual o setor ou linha de produção onde o equipamento está localizado?")
    return ASK_LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['os_data']['localizacao'] = update.message.text
    keyboard = [[InlineKeyboardButton("🔧 Corretiva", callback_data="Corretiva")], [InlineKeyboardButton("📈 Preditiva", callback_data="Preditiva")], [InlineKeyboardButton("🗓️ Preventiva", callback_data="Preventiva")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Qual o tipo de manutenção a ser realizada?", reply_markup=reply_markup)
    return ASK_MAINT_TYPE

async def get_maintenance_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['os_data']['tipo_manutencao'] = query.data
    keyboard = [[InlineKeyboardButton("🚨 Urgente", callback_data="Urgente")], [InlineKeyboardButton("⚠️ Alta", callback_data="Alta")], [InlineKeyboardButton("🔷 Média", callback_data="Média")], [InlineKeyboardButton("⚪ Baixa", callback_data="Baixa")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"Tipo: {query.data}. Agora, qual o nível de prioridade?", reply_markup=reply_markup)
    return ASK_PRIORITY

async def get_priority(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['os_data']['prioridade'] = query.data
    await query.edit_message_text(text=f"Prioridade: {query.data}. Por favor, descreva o problema observado ou o plano de serviço.")
    return ASK_PROBLEM_DESC

async def get_problem_description_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['os_data']['descricao_problema'] = update.message.text
    user_id = update.effective_user.id
    user_db_data = await get_user_data(user_id)
    if not user_db_data:
        await update.message.reply_text("Erro: não foi possível encontrar seus dados. Tente /start.", reply_markup=MAIN_MENU_MARKUP)
        return ConversationHandler.END
    
    os_data = context.user_data['os_data']
    os_data.update({"status_os": "Aberta", "tecnico_id": user_id, "empresa_id": user_db_data['empresa_id']})
    
    new_os = await save_new_os(os_data)
    if new_os:
        await update.message.reply_text(f"✅ Ordem de Serviço #{new_os['id']} aberta com sucesso!", reply_markup=MAIN_MENU_MARKUP)
    else:
        await update.message.reply_text("❌ Ocorreu um erro ao salvar a OS.", reply_markup=MAIN_MENU_MARKUP)
    context.user_data.clear()
    return ConversationHandler.END


# --- FLUXO DE FECHAMENTO DE OS (Atualizado com Notas Opcionais) ---

async def start_close_os(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    open_os_list = await get_open_os_by_user(user_id)
    if not open_os_list:
        await update.message.reply_text("Você não possui nenhuma Ordem de Serviço aberta.", reply_markup=MAIN_MENU_MARKUP)
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(f"#{os['id']} - {os['equipamento_nome']} ({os['equipamento_tag']})", callback_data=f"close_{os['id']}")] for os in open_os_list]
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="cancel_close")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecione a Ordem de Serviço que deseja fechar:", reply_markup=reply_markup)
    return SELECT_OS_TO_CLOSE

async def ask_for_solution(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == 'cancel_close':
        await query.edit_message_text(text="Fechamento de OS cancelado.")
        return await cancel(update, context)
    os_id = int(query.data.split('_')[1])
    context.user_data['os_id_to_close'] = os_id
    await query.edit_message_text(text=f"Fechando OS #{os_id}.\n\nDescreva o diagnóstico final e a solução aplicada.")
    return ASK_SOLUTION

async def get_solution_and_ask_parts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['close_solution'] = update.message.text
    context.user_data['parts_list'] = []
    keyboard = [[InlineKeyboardButton("✅ Sim", callback_data="parts_yes")], [InlineKeyboardButton("❌ Não", callback_data="parts_no")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Houve troca de peças nesta manutenção?", reply_markup=reply_markup)
    return ASK_IF_PARTS

async def ask_part_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    num_peca = len(context.user_data.get('parts_list', [])) + 1
    await query.edit_message_text(text=f"Ok, vamos adicionar as peças trocadas.\n\nPara a Peça {num_peca}, qual o nome dela?")
    return ASK_PART_NAME

async def get_part_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['current_part_name'] = update.message.text
    await update.message.reply_text("Qual o TAG/Código (Part Number) dessa peça?")
    return ASK_PART_TAG

async def get_part_tag(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['current_part_tag'] = update.message.text
    await update.message.reply_text("Qual a quantidade utilizada desta peça?")
    return ASK_PART_QTY

async def get_part_qty_and_ask_more(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        qty = int(update.message.text)
        part = {"nome_peca": context.user_data['current_part_name'], "tag_peca": context.user_data['current_part_tag'], "quantidade": qty}
        context.user_data['parts_list'].append(part)
        keyboard = [[InlineKeyboardButton("➕ Sim", callback_data="parts_yes")], [InlineKeyboardButton("👍 Não, continuar", callback_data="parts_no")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"✅ Peça '{part['nome_peca']}' adicionada.\nDeseja adicionar outra peça?", reply_markup=reply_markup)
        return ASK_MORE_PARTS
    except ValueError:
        await update.message.reply_text("Quantidade inválida. Por favor, digite apenas números.")
        return ASK_PART_QTY

async def ask_for_final_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("✅ Concluída", callback_data="Concluída")], [InlineKeyboardButton("⏳ Pendente", callback_data="Pendente")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Entendido. Qual o status final desta Ordem de Serviço?", reply_markup=reply_markup)
    return ASK_FINAL_STATUS

async def get_final_status_and_ask_if_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """NOVA ETAPA: Salva o status e pergunta se o usuário quer adicionar notas."""
    query = update.callback_query
    await query.answer()
    context.user_data['final_status'] = query.data
    
    keyboard = [
        [InlineKeyboardButton("✍️ Sim, adicionar", callback_data="notes_yes")],
        [InlineKeyboardButton("👍 Não, finalizar", callback_data="notes_no")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"Status definido como '{query.data}'.\n\nDeseja adicionar notas finais?", reply_markup=reply_markup)
    return ASK_IF_NOTES

async def prompt_for_final_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """NOVA ETAPA: Pede para o usuário digitar as notas."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Ok. Por favor, adicione as notas finais, observações ou recomendações.")
    return GET_FINAL_NOTES

async def _save_and_end_closing_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Função auxiliar para salvar os dados e finalizar a conversa, evitando repetição de código."""
    os_id = context.user_data['os_id_to_close']
    
    close_data = {
        "diagnostico_solucao": context.user_data.get('close_solution', 'N/A'),
        "status_os": context.user_data.get('final_status', 'Fechada'),
        "notas_finais": context.user_data.get('final_notes', ''), # Pega a nota se existir
        "data_fechamento": "now()"
    }
    
    parts_data = context.user_data.get('parts_list', [])
    success = await close_os_in_db(os_id, close_data, parts_data)

    chat_id = update.effective_chat.id
    if success:
        await context.bot.send_message(chat_id=chat_id, text=f"✅ Ordem de Serviço #{os_id} fechada com sucesso!", reply_markup=MAIN_MENU_MARKUP)
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ Ocorreu um erro ao fechar a OS.", reply_markup=MAIN_MENU_MARKUP)

    context.user_data.clear()
    return ConversationHandler.END

async def get_final_notes_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva as notas finais digitadas e finaliza o fechamento."""
    context.user_data['final_notes'] = update.message.text
    return await _save_and_end_closing_conversation(update, context)

async def finalize_without_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finaliza o fechamento sem adicionar notas."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Ok, finalizando o fechamento...")
    context.user_data['final_notes'] = '' # Garante que as notas fiquem vazias
    return await _save_and_end_closing_conversation(update, context)

async def list_open_os(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Verifica o cadastro do usuário, busca no banco e lista todas as
    suas Ordens de Serviço com status 'Aberta'.
    """
    user_id = update.effective_user.id

    # Passo 1: Verificar se o usuário está cadastrado antes de prosseguir.
    # (É uma boa prática garantir isso, mesmo que o acesso seja por um botão)
    if not await is_user_registered(user_id):
        await update.message.reply_text(
            "Você precisa estar cadastrado para ver suas Ordens de Serviço. "
            "Por favor, inicie o cadastro clicando em '🆕 Abrir OS'."
        )
        return

    # Passo 2: Buscar as OS abertas no banco de dados.
    open_os_list = await get_open_os_by_user(user_id)

    # Se a lista estiver vazia, avisa o usuário.
    if not open_os_list:
        await update.message.reply_text(
            "Você não possui nenhuma Ordem de Serviço aberta.",
            reply_markup=MAIN_MENU_MARKUP
        )
        return

    # Passo 3: Formatar a mensagem com a lista de OS.
    message = "<b>Suas Ordens de Serviço Abertas:</b>\n\n"
    for os in open_os_list:
        message += (
            f"<b>OS #{os['id']}</b>\n"
            f"  <b>Equipamento:</b> {os['equipamento_nome']} ({os['equipamento_tag']})\n"
            f"  <b>Tipo:</b> {os['tipo_manutencao']}\n"
            f"  <b>Prioridade:</b> {os['prioridade']}\n"
            f"--------------------\n"
        )

    # Envia a mensagem formatada para o usuário.
    # Usamos reply_html para que a formatação em negrito (<b>) funcione.
    await update.message.reply_html(message)