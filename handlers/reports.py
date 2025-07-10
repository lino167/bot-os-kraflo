import logging
import os
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

# Importações dos nossos próprios módulos
from database.utils import get_all_os_for_report, get_single_os_details
from handlers.common import cancel

# Configura o logger para este módulo
logger = logging.getLogger(__name__)

# --- Definição dos Estados da Conversa ---
MANAGE_SELECTION = range(24, 25)


# --- Classe PDF Personalizada (Inspirada no seu exemplo) ---
class PDF(FPDF):
    """Classe personalizada para ter cabeçalho e rodapé no PDF."""
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'Relatório de Atividades - Kraflo', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')


# --- Funções do Fluxo de Geração de Relatórios ---

async def start_report_generation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ponto de entrada único. Inicia a tela de seleção de OS."""
    context.user_data['selected_os'] = []
    return await list_os_for_selection(update, context)

async def list_os_for_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Monta e exibe a lista interativa de seleção de OS."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if 'all_os_list' not in context.user_data:
        context.user_data['all_os_list'] = await get_all_os_for_report(user_id)

    all_os_list = context.user_data['all_os_list']
    selected_os = context.user_data.get('selected_os', [])

    if not all_os_list:
        message_text = "Nenhuma Ordem de Serviço encontrada para gerar relatórios."
        if query:
            await query.edit_message_text(message_text)
        else:
            await update.message.reply_text(message_text)
        return ConversationHandler.END

    keyboard = []
    for os in all_os_list:
        marker = "✅" if os['id'] in selected_os else "🔲"
        keyboard.append([InlineKeyboardButton(f"{marker} OS #{os['id']} - {os['equipamento_nome']}", callback_data=f"toggle_{os['id']}")])
    
    keyboard.append([
        InlineKeyboardButton("✅ Marcar Todos", callback_data="select_all"),
        InlineKeyboardButton("🗑️ Limpar Seleção", callback_data="select_none"),
    ])
    keyboard.append([
        InlineKeyboardButton("📄 Gerar PDF", callback_data="generate_pdf"),
        InlineKeyboardButton("📈 Gerar CSV", callback_data="generate_csv"),
    ])
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="cancel_report")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = "Selecione as OS e escolha o formato do relatório:"
    
    if query:
        await query.edit_message_text(message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    
    return MANAGE_SELECTION

async def manage_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gerencia a seleção de OS e aciona a geração do relatório escolhido."""
    query = update.callback_query
    await query.answer()
    
    action, _, value = query.data.partition('_')
    
    selected_os = context.user_data.get('selected_os', [])
    all_os_ids = [os['id'] for os in context.user_data.get('all_os_list', [])]

    if action == "toggle":
        os_id = int(value)
        if os_id in selected_os:
            selected_os.remove(os_id)
        else:
            selected_os.append(os_id)
        context.user_data['selected_os'] = selected_os
        return await list_os_for_selection(update, context)

    elif action == "select":
        context.user_data['selected_os'] = all_os_ids if value == "all" else []
        return await list_os_for_selection(update, context)

    elif action == "generate":
        if not selected_os:
            await context.bot.answer_callback_query(query.id, "Nenhuma OS selecionada!", show_alert=True)
            return MANAGE_SELECTION
        
        if value == "pdf":
            return await generate_pdf_report(update, context)
        elif value == "csv":
            return await generate_csv_report(update, context)

    elif action == "cancel":
        await query.edit_message_text("Geração de relatório cancelada.")
        context.user_data.clear()
        return await cancel(update, context)

    return MANAGE_SELECTION

async def generate_pdf_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gera um único PDF com várias páginas, uma para cada OS selecionada."""
    query = update.callback_query
    user_id = update.effective_user.id
    selected_ids = context.user_data.get('selected_os', [])
    await query.edit_message_text(f"Gerando o PDF com {len(selected_ids)} OS selecionada(s)...")

    file_path = ""
    try:
        pdf = PDF(orientation='P', unit='mm', format='A4') # Usa a classe personalizada
        
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
    """Gera um relatório CSV contendo apenas as OS selecionadas."""
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
    """
    Adiciona uma página ao PDF com os detalhes de uma OS, usando um layout robusto.
    """
    pdf.add_page()
    pdf.set_font('Arial', '', 11)

    def sanitize_text(text):
        if not text:
            return ""
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    def format_date(date_str):
        if not date_str: return "Não preenchido"
        try:
            return pd.to_datetime(date_str).strftime('%d/%m/%Y às %H:%M')
        except (ValueError, TypeError):
            return str(date_str)

    # --- Seção 1: Detalhes do Profissional ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, sanitize_text('1. Detalhes do Profissional'), ln=True, border='B')
    pdf.ln(4)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, sanitize_text(f"Nome: {data.get('tecnico', {}).get('nome_completo', 'N/A')}"), ln=True)
    pdf.cell(0, 6, sanitize_text(f"Função: {data.get('tecnico', {}).get('funcao', 'N/A')}"), ln=True)
    pdf.ln(8)

    # --- Seção 2: Detalhes da Ordem de Serviço ---
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
    
    # --- Seção 3: Datas ---
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 7, "Datas", ln=True)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 7, sanitize_text(f"  Abertura: {format_date(data.get('data_abertura'))}"), ln=True)
    pdf.cell(0, 7, sanitize_text(f"  Fechamento: {format_date(data.get('data_fechamento'))}"), ln=True)
    pdf.ln(4)

    # --- Seção 4: Peças Utilizadas ---
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
    
    # --- Seção 5: Status Final ---
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 7, "Status Final do Serviço", ln=True)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 7, sanitize_text(f"  {data.get('status_os', 'N/A')}"), ln=True)
