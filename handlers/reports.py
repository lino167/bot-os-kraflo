import logging
import os
import pytz
import pandas as pd
from fpdf import FPDF
from datetime import date, timedelta, datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.utils import get_all_os_for_report, get_single_os_details
from handlers.common import cancel
from handlers.calendar_helper import create_calendar

logger = logging.getLogger(__name__)

# Estados simplificados
SELECT_START_DATE, SELECT_END_DATE, MANAGE_SELECTION = range(25, 28)

class PDF(FPDF):
    """Classe personalizada para ter um cabeçalho profissional com logo e slogan."""
    def header(self):
        self.set_draw_color(45, 52, 54)
        self.set_text_color(45, 52, 54)
        try:
            self.image('assets/Logo sem background.png', x=10, y=12, w=40)
        except FileNotFoundError:
            self.set_xy(10, 12)
            self.set_font('Arial', 'B', 12)
            self.cell(40, 25, 'KRAFLO', 0, 0, 'C')
        self.set_xy(55, 22)
        self.set_font('Arial', 'B', 16)
        self.cell(0, 8, 'Kraflo - Bot de Ordens de Serviço', 0, 1, 'L')
        self.set_x(55)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(108, 122, 137)
        self.cell(0, 6, 'Automação industrial', 0, 1, 'L')
        self.set_xy(10, 40) 
        self.set_font('Arial', 'B', 12)
        self.set_text_color(45, 52, 54)
        self.cell(0, 10, 'Relatório Detalhado de Ordem de Serviço', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_draw_color(189, 195, 199)
        self.line(10, self.get_y() - 5, 200, self.get_y() - 5)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

async def start_report_generation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de relatórios diretamente com o calendário."""
    await update.message.reply_text(
        "📊 **Gerador de Relatórios**\n\n"
        "Para começar, selecione a **DATA DE INÍCIO** do período desejado:", 
        reply_markup=create_calendar()
    )
    return SELECT_START_DATE

async def process_calendar_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, date_stage: int) -> int:
    query = update.callback_query
    await query.answer()
    parts = query.data.split('_')
    action, prefix = parts[0], parts[1]
    if action == "calendar":
        if prefix == "ignore": return date_stage
        if prefix in ["prev", "next"]:
            year, month = map(int, parts[2].split('-'))
            prompt = "Selecione a DATA DE INÍCIO:" if date_stage == SELECT_START_DATE else "Selecione a DATA FINAL:"
            await query.edit_message_text(prompt, reply_markup=create_calendar(year, month))
            return date_stage
        if prefix == "day":
            date_value = parts[2]
            if date_stage == SELECT_START_DATE:
                context.user_data['start_date'] = date_value
                await query.edit_message_text(f"Data de início: {pd.to_datetime(date_value).strftime('%d/%m/%Y')}\n\nAgora, selecione a **DATA FINAL**:", reply_markup=create_calendar())
                return SELECT_END_DATE
            elif date_stage == SELECT_END_DATE:
                start_date_str = context.user_data.get('start_date')
                if not start_date_str:
                    await query.edit_message_text("Erro: data de início não encontrada. Comece novamente.")
                    return await start_report_generation(update, context)
                end_date_str = date_value
                if pd.to_datetime(end_date_str) < pd.to_datetime(start_date_str):
                    await context.bot.answer_callback_query(query.id, "A data final não pode ser anterior à inicial!", show_alert=True)
                    return SELECT_END_DATE
                start_date_q = pd.to_datetime(start_date_str).strftime("%Y-%m-%d 00:00:00")
                end_date_q = pd.to_datetime(end_date_str).strftime("%Y-%m-%d 23:59:59")
                context.user_data['filter_title'] = f"de {pd.to_datetime(start_date_str).strftime('%d/%m/%Y')} a {pd.to_datetime(end_date_str).strftime('%d/%m/%Y')}"
                return await fetch_and_list_os(update, context, start_date_q, end_date_q)
    return date_stage

async def handle_start_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await process_calendar_selection(update, context, SELECT_START_DATE)
async def handle_end_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await process_calendar_selection(update, context, SELECT_END_DATE)
async def fetch_and_list_os(update: Update, context: ContextTypes.DEFAULT_TYPE, start_date: str | None, end_date: str | None) -> int:
    query = update.callback_query
    user_id = update.effective_user.id
    await query.edit_message_text("Buscando dados, por favor aguarde...")
    os_list = await get_all_os_for_report(user_id, start_date, end_date)
    if not os_list:
        await query.edit_message_text("Nenhuma OS encontrada para o filtro selecionado.")
        context.user_data.clear()
        return ConversationHandler.END
    context.user_data['all_os_list'] = os_list
    context.user_data['selected_os'] = [os['id'] for os in os_list]
    return await list_os_for_selection(update, context)
async def list_os_for_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    all_os_list = context.user_data['all_os_list']
    selected_os = context.user_data.get('selected_os', [])
    filter_title = context.user_data.get('filter_title', '')
    keyboard = [[InlineKeyboardButton(f"{'✅' if os['id'] in selected_os else '☑️'} OS #{os['id']} - {os['equipamento_nome']}", callback_data=f"toggle_{os['id']}")] for os in all_os_list]
    keyboard.extend([
        [InlineKeyboardButton("➡️ Marcar Todos", callback_data="select_all"), InlineKeyboardButton("⬅️ Desmarcar Todos", callback_data="select_none")],
        [InlineKeyboardButton("📄 Gerar PDF", callback_data="generate_pdf"), InlineKeyboardButton("📈 Gerar CSV", callback_data="generate_csv")],
        [InlineKeyboardButton("↩️ Voltar", callback_data="report_back")],
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = f"Relatório {filter_title}\n\nSelecione as OS e escolha o formato:"
    if query:
        await query.edit_message_text(message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    return MANAGE_SELECTION
async def manage_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action, _, value = query.data.partition('_')
    if action == "toggle":
        os_id = int(value)
        selected_os = context.user_data.get('selected_os', [])
        if os_id in selected_os: selected_os.remove(os_id)
        else: selected_os.append(os_id)
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
        file_path = f"relatorio_detalhado_{user_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
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
        report_data = [item for item in all_os_list if item['id'] in selected_ids]
        processed_data = []
        for service_order in report_data:
            os_copy = service_order.copy()
            tecnico_info = os_copy.pop('tecnicos', {}) or {} 
            os_copy['tecnico_nome'] = tecnico_info.get('nome_completo', 'N/A')
            os_copy['tecnico_codigo'] = tecnico_info.get('codigo_empresa', '')
            processed_data.append(os_copy)
        df = pd.DataFrame(processed_data)
        df.rename(columns={
            'id': 'OS', 'equipamento_nome': 'Equipamento', 'equipamento_tag': 'TAG', 
            'tipo_manutencao': 'Tipo', 'prioridade': 'Prioridade', 'status_os': 'Status', 
            'data_abertura': 'Abertura', 'data_fechamento': 'Fechamento', 
            'descricao_problema': 'Problema', 'diagnostico_solucao': 'Solução', 
            'notas_finais': 'Notas', 'tecnico_nome': 'Técnico', 'tecnico_codigo': 'Código Técnico',
            'url_foto': 'Link Foto Abertura', 
            'url_arquivo_fechamento': 'Link Anexo Fechamento'
        }, inplace=True)
        local_tz = pytz.timezone("America/Sao_Paulo")
        for col in ['Abertura', 'Fechamento']:
            if col in df.columns and not df[col].isnull().all():
                df[col] = pd.to_datetime(df[col]).dt.tz_convert(local_tz).dt.strftime('%d/%m/%Y %H:%M')
        colunas_finais = [
            'OS', 'Status', 'Prioridade', 'Tipo', 'Equipamento', 'TAG', 'Técnico', 'Código Técnico',
            'Abertura', 'Fechamento', 'Problema', 'Solução', 'Notas', 
            'Link Foto Abertura', 'Link Anexo Fechamento'
        ]
        colunas_existentes = [col for col in colunas_finais if col in df.columns]
        df_final = df[colunas_existentes]
        file_path = f"relatorio_selecao_{user_id}_{datetime.now().strftime('%Y%m%d')}.csv"
        df_final.to_csv(file_path, index=False, sep=';', encoding='utf-8-sig')
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
            local_tz = pytz.timezone("America/Sao_Paulo")
            utc_date = pd.to_datetime(date_str)
            local_date = utc_date.tz_convert(local_tz)
            return local_date.strftime('%d/%m/%Y às %H:%M')
        except (ValueError, TypeError): 
            return str(date_str)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, sanitize_text('1. Detalhes do Profissional'), ln=True, border='B')
    pdf.ln(4)

    #--- SEÇÃO DE INFORMAÇÕES DO TÉCNICO ---
    pdf.set_font('Arial', '', 10)
    tecnico_info = data.get('tecnico', {}) or {}
    pdf.cell(0, 6, sanitize_text(f"Nome: {tecnico_info.get('nome_completo', 'N/A')}"), ln=True)
    codigo_empresa = tecnico_info.get('codigo_empresa')
    if codigo_empresa:
        pdf.cell(0, 6, sanitize_text(f"Código/Matrícula: {codigo_empresa}"), ln=True)
    pdf.cell(0, 6, sanitize_text(f"Função: {tecnico_info.get('funcao', 'N/A')}"), ln=True)
    pdf.ln(8)
    def add_field(title, value):
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 7, sanitize_text(title), ln=True)
        pdf.set_font('Arial', '', 11)
        pdf.multi_cell(0, 7, sanitize_text(f"  {value if value else 'Não preenchido'}"))
        pdf.ln(1)
        
    # --- SEÇÃO DE DETALHES DA ORDEM DE SERVIÇO ---
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

    # --- SEÇÃO DE ANEXOS ---
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 7, "Anexos", ln=True)
    pdf.ln(1) # Adiciona um pequeno espaço após o título da seção

    pdf.set_font('Arial', '', 10)
    
    url_foto_abertura = data.get('url_foto')
    if url_foto_abertura:
        # Escreve o label e quebra a linha
        pdf.cell(0, 6, "Anexo Abertura:", ln=True) 
        pdf.set_text_color(0, 0, 255) # Cor azul para o link
        # Adiciona um recuo e escreve o texto do link clicável em uma nova linha
        pdf.cell(0, 6, "   Clique aqui para ver o anexo", ln=True, link=url_foto_abertura) 
        pdf.set_text_color(45, 52, 54) # Volta para a cor de texto padrão
        pdf.ln(2) # Adiciona um espaço extra após o link

    url_arquivo_fechamento = data.get('url_arquivo_fechamento')
    if url_arquivo_fechamento:
        # Escreve o label e quebra a linha
        pdf.cell(0, 6, "Anexo Fechamento:", ln=True) 
        pdf.set_text_color(0, 0, 255)
        # Adiciona um recuo e escreve o texto do link clicável em uma nova linha
        pdf.cell(0, 6, "   Clique aqui para ver o anexo", ln=True, link=url_arquivo_fechamento)
        pdf.set_text_color(45, 52, 54)
        pdf.ln(2)
    
    # Mensagem caso não existam anexos
    if not url_foto_abertura and not url_arquivo_fechamento:
        pdf.cell(0, 6, "  Nenhum anexo encontrado.", ln=True)
        
    pdf.ln(4) # Espaço antes da próxima seção

    # --- SEÇÃO DE PEÇAS UTILIZADAS ---
    pecas = data.get('pecas_utilizadas', [])
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
