import logging
import os
import pandas as pd
from fpdf import FPDF
from datetime import date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.utils import get_all_os_for_report, get_single_os_details
from handlers.common import cancel
from handlers.calendar_helper import create_calendar

logger = logging.getLogger(__name__)

# --- Definição dos Estados da Conversa ---
CHOOSE_FILTER_TYPE, SELECT_START_DATE, SELECT_END_DATE, MANAGE_SELECTION = range(24, 28)

# --- Classe PDF (sem alterações) ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'Relatório de Ordens de Serviço - Kraflo', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

# --- Funções do Novo Fluxo de Relatórios ---

async def start_report_generation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Apresenta as opções de filtro de data."""
    keyboard = [
        [InlineKeyboardButton("🗓️ Relatório de Hoje", callback_data="report_today")],
        [InlineKeyboardButton("🗓️ Relatório de Ontem", callback_data="report_yesterday")],
        [InlineKeyboardButton("📅 Selecionar Período", callback_data="report_period")],
        [InlineKeyboardButton("📋 Listar Todas as OS", callback_data="report_all")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_report")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "📊 Gerador de Relatórios\n\nEscolha o tipo de filtro que deseja aplicar:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "📊 Gerador de Relatórios\n\nEscolha o tipo de filtro que deseja aplicar:",
            reply_markup=reply_markup
        )
    return CHOOSE_FILTER_TYPE

async def handle_filter_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa a escolha do filtro de data e busca os dados."""
    query = update.callback_query
    await query.answer()
    
    filter_type = query.data

    if filter_type == "report_today":
        today = date.today()
        start_date = today.strftime("%Y-%m-%d 00:00:00")
        end_date = today.strftime("%Y-%m-%d 23:59:59")
        context.user_data['filter_title'] = f"do dia {today.strftime('%d/%m/%Y')}"
        return await fetch_and_list_os(update, context, start_date, end_date)

    elif filter_type == "report_yesterday":
        yesterday = date.today() - timedelta(days=1)
        start_date = yesterday.strftime("%Y-%m-%d 00:00:00")
        end_date = yesterday.strftime("%Y-%m-%d 23:59:59")
        context.user_data['filter_title'] = f"do dia {yesterday.strftime('%d/%m/%Y')}"
        return await fetch_and_list_os(update, context, start_date, end_date)

    elif filter_type == "report_all":
        context.user_data['filter_title'] = "de todas as Ordens de Serviço"
        return await fetch_and_list_os(update, context, None, None)

    elif filter_type == "report_period":
        await query.edit_message_text(
            "Selecione a DATA DE INÍCIO no calendário:",
            reply_markup=create_calendar()
        )
        return SELECT_START_DATE
        
    elif filter_type == "cancel_report":
        await query.edit_message_text("Geração de relatório cancelada.")
        return ConversationHandler.END

async def process_calendar_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, date_stage: str) -> int:
    """Função genérica para processar cliques no calendário."""
    query = update.callback_query
    await query.answer()
    
    action, _, value = query.data.partition('_')

    if action == "calendar":
        if value == "ignore":
            return date_stage 
        
        # Lida com a navegação de mês
        if value.startswith("prev") or value.startswith("next"):
            year, month = map(int, query.data.split('_')[2].split('-'))
            prompt_text = "Selecione a DATA DE INÍCIO:" if date_stage == SELECT_START_DATE else "Selecione a DATA FINAL:"
            await query.edit_message_text(prompt_text, reply_markup=create_calendar(year, month))
            return date_stage

        # Lida com a seleção de um dia
        if date_stage == SELECT_START_DATE:
            context.user_data['start_date'] = value
            await query.edit_message_text(
                f"Data de início: {pd.to_datetime(value).strftime('%d/%m/%Y')}\n\nAgora, selecione a DATA FINAL:",
                reply_markup=create_calendar()
            )
            return SELECT_END_DATE
        
        elif date_stage == SELECT_END_DATE:
            start_date_str = context.user_data.get('start_date')
            if not start_date_str:
                await query.edit_message_text("Erro: data de início não encontrada. Por favor, comece novamente.")
                return await start_report_generation(query.message, context)

            end_date_str = value
            start_date_dt = pd.to_datetime(start_date_str)
            end_date_dt = pd.to_datetime(end_date_str)

            if end_date_dt < start_date_dt:
                await context.bot.answer_callback_query(query.id, "A data final não pode ser anterior à data inicial!", show_alert=True)
                return SELECT_END_DATE

            start_date_query = start_date_dt.strftime("%Y-%m-%d 00:00:00")
            end_date_query = end_date_dt.strftime("%Y-%m-%d 23:59:59")
            
            context.user_data['filter_title'] = f"do período de {start_date_dt.strftime('%d/%m/%Y')} a {end_date_dt.strftime('%d/%m/%Y')}"
            return await fetch_and_list_os(update, context, start_date_query, end_date_query)

    return date_stage 

async def handle_start_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await process_calendar_selection(update, context, SELECT_START_DATE)

async def handle_end_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await process_calendar_selection(update, context, SELECT_END_DATE)


async def fetch_and_list_os(update: Update, context: ContextTypes.DEFAULT_TYPE, start_date: str | None, end_date: str | None) -> int:
    """Função central para buscar dados com base no filtro e iniciar a tela de seleção."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    await query.edit_message_text("Buscando dados, por favor aguarde...")
    
    os_list = await get_all_os_for_report(user_id, start_date, end_date)
    
    if not os_list:
        await query.edit_message_text("Nenhuma OS encontrada para o filtro selecionado.")
        context.user_data.clear()
        return ConversationHandler.END
        
    context.user_data['all_os_list'] = os_list
    context.user_data['selected_os'] = [os['id'] for os in os_list] # Pré-seleciona todos
    
    return await list_os_for_selection(update, context)

async def list_os_for_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Monta e exibe a lista interativa de seleção de OS."""
    query = update.callback_query
    
    all_os_list = context.user_data['all_os_list']
    selected_os = context.user_data.get('selected_os', [])
    filter_title = context.user_data.get('filter_title', '')

    keyboard = []
    for os in all_os_list:
        marker = "✅" if os['id'] in selected_os else "☑️"
        keyboard.append([InlineKeyboardButton(f"{marker} OS #{os['id']} - {os['equipamento_nome']}", callback_data=f"toggle_{os['id']}")])
    
    keyboard.extend([
        [InlineKeyboardButton("➡️ Marcar Todos", callback_data="select_all"), InlineKeyboardButton("⬅️ Desmarcar Todos", callback_data="select_none")],
        [InlineKeyboardButton("📄 Gerar PDF", callback_data="generate_pdf"), InlineKeyboardButton("📈 Gerar CSV", callback_data="generate_csv")],
        [InlineKeyboardButton("↩️ Voltar aos Filtros", callback_data="report_back")],
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = f"Relatório {filter_title}\n\nSelecione as OS e escolha o formato:"
    
    if query:
        await query.edit_message_text(message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    
    return MANAGE_SELECTION

async def manage_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gerencia a seleção de OS e aciona a geração do relatório."""
    query = update.callback_query
    await query.answer()
    
    # Usamos partição para lidar com callbacks como "toggle_123"
    action, _, value = query.data.partition('_')
    
    if action == "toggle":
        os_id = int(value)
        selected_os = context.user_data.get('selected_os', [])
        if os_id in selected_os: selected_os.remove(os_id)
        else: selected_os.append(os_id)
        context.user_data['selected_os'] = selected_os
        return await list_os_for_selection(update, context)

    elif action == "select":
        all_os_ids = [os['id'] for os in context.user_data.get('all_os_list', [])]
        context.user_data['selected_os'] = all_os_ids if value == "all" else []
        return await list_os_for_selection(update, context)

    elif action == "generate":
        if not context.user_data.get('selected_os', []):
            await context.bot.answer_callback_query(query.id, "Nenhuma OS selecionada!", show_alert=True)
            return MANAGE_SELECTION
        if value == "pdf": return await generate_pdf_report(update, context)
        elif value == "csv": return await generate_csv_report(update, context)

    elif action == "report" and value == "back":
        # Limpa os dados da lista para recomeçar
        context.user_data.pop('all_os_list', None)
        context.user_data.pop('selected_os', None)
        return await start_report_generation(update, context)

    return MANAGE_SELECTION

async def generate_pdf_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = update.effective_user.id
    selected_ids = context.user_data.get('selected_os', [])
    await query.edit_message_text(f"Gerando o PDF com {len(selected_ids)} OS selecionada(s)...")

    file_path = ""
    try:
        pdf = PDF(orientation='P', unit='mm', format='A4')
        
        for os_id in selected_ids:
            os_details = await get_single_os_details(os_id)
            if os_details:
                _create_detailed_pdf_page(pdf, os_details)

        file_path = f"relatorio_detalhado_{user_id}.pdf"
        pdf.output(file_path)

        with open(file_path, "rb") as document:
            await context.bot.send_document(chat_id=user_id, document=document)
            
    except Exception as e:
        logger.error(f"Erro ao gerar PDF múltiplo para o usuário {user_id}: {e}")
        await context.bot.send_message(chat_id=user_id, text="Ocorreu um erro ao gerar o PDF.")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        context.user_data.clear()
    return ConversationHandler.END

async def generate_csv_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = update.effective_user.id
    selected_ids = context.user_data.get('selected_os', [])
    await query.edit_message_text(f"Gerando o CSV com {len(selected_ids)} OS selecionada(s)...")

    file_path = ""
    try:
        all_os_list = context.user_data.get('all_os_list', [])
        report_data = [os for os in all_os_list if os['id'] in selected_ids]

        df = pd.DataFrame(report_data)
        df.rename(columns={'id': 'OS', 'equipamento_nome': 'Equipamento', 'equipamento_tag': 'TAG', 'tipo_manutencao': 'Tipo', 'prioridade': 'Prioridade', 'status_os': 'Status', 'data_abertura': 'Abertura', 'data_fechamento': 'Fechamento', 'descricao_problema': 'Problema', 'diagnostico_solucao': 'Solução', 'notas_finais': 'Notas', 'tecnicos': 'Técnico'}, inplace=True)
        df['Técnico'] = df['Técnico'].apply(lambda x: x['nome_completo'] if isinstance(x, dict) else 'N/A')

        file_path = f"relatorio_selecao_{user_id}.csv"
        df.to_csv(file_path, index=False, sep=';', encoding='utf-8-sig')

        with open(file_path, "rb") as document:
            await context.bot.send_document(chat_id=user_id, document=document)
    except Exception as e:
        logger.error(f"Erro ao gerar relatório CSV para o usuário {user_id}: {e}")
        await context.bot.send_message(chat_id=user_id, text="Ocorreu um erro ao gerar seu relatório CSV.")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        context.user_data.clear()
    return ConversationHandler.END

def _create_detailed_pdf_page(pdf: PDF, data: dict):
    pdf.add_page()
    pdf.set_font('Arial', '', 11)

    def sanitize_text(text):
        if not text: return ""
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    def format_date(date_str):
        if not date_str: return "Não preenchido"
        try:
            return pd.to_datetime(date_str).strftime('%d/%m/%Y às %H:%M')
        except (ValueError, TypeError):
            return str(date_str)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, sanitize_text('1. Detalhes do Profissional'), ln=True, border='B')
    pdf.ln(4)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, sanitize_text(f"Nome: {data.get('tecnico', {}).get('nome_completo', 'N/A')}"), ln=True)
    pdf.cell(0, 6, sanitize_text(f"Função: {data.get('tecnico', {}).get('funcao', 'N/A')}"), ln=True)
    pdf.ln(8)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, sanitize_text(f"2. Detalhes da OS ID: {data.get('id')}"), ln=True, border='B')
    pdf.ln(4)
    
    def add_field(title, value):
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 7, sanitize_text(title), ln=True)
        pdf.set_font('Arial', '', 11)
        pdf.multi_cell(0, 7, sanitize_text(f"  {value if value else 'Não preenchido'}"))
        pdf.ln(1)

    add_field("Máquina", f"{data.get('equipamento_nome', 'N/A')} ({data.get('equipamento_tag', 'N/A')})")
    add_field("Tipo de Manutenção", data.get('tipo_manutencao'))
    add_field("Problema Apresentado", data.get('descricao_problema'))
    add_field("Solução Aplicada", data.get('diagnostico_solucao'))
    add_field("Notas Finais", data.get('notas_finais'))
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 7, "Datas", ln=True)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 7, sanitize_text(f"  Abertura: {format_date(data.get('data_abertura'))}"), ln=True)
    pdf.cell(0, 7, sanitize_text(f"  Fechamento: {format_date(data.get('data_fechamento'))}"), ln=True)
    pdf.ln(4)

    pecas = data.get('pecas', [])
    if pecas:
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 7, "Peças Utilizadas", ln=True)
        pdf.set_font('Arial', '', 11)
        for peca in pecas:
            pdf.cell(0, 7, sanitize_text(f"  - Descrição: {peca.get('nome_peca', 'N/A')}"), ln=True)
            pdf.cell(0, 7, sanitize_text(f"    TAG/Código: {peca.get('tag_peca', 'N/A')}"), ln=True)
            pdf.cell(0, 7, sanitize_text(f"    Quantidade: {peca.get('quantidade', 'N/A')}"), ln=True)
            pdf.ln(2)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 7, "Status Final do Serviço", ln=True)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 7, sanitize_text(f"  {data.get('status_os', 'N/A')}"), ln=True)