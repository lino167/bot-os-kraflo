import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ConversationHandler, 
    MessageHandler, filters, CallbackQueryHandler, ContextTypes
)

from config import TELEGRAM_TOKEN
from handlers import common, registration, service_order, reports, os_edit # Importa o novo módulo
from database.utils import is_user_registered

# Configuração do logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# =============================================================================
# FUNÇÃO DE GUARDA (HELPER)
# Definida aqui, no topo, para estar disponível para todos os handlers.
# =============================================================================
async def check_registration_and_start(update: Update, context: ContextTypes.DEFAULT_TYPE, start_function):
    """
    Função de guarda: verifica se o usuário está cadastrado antes de executar
    uma ação protegida (abrir OS, relatórios, etc.).
    """
    user = update.effective_user
    if not user:
        logger.warning("Não foi possível identificar o usuário na mensagem.")
        return ConversationHandler.END

    logger.info(f"User {user.id} a tentar aceder à função protegida: {start_function.__name__}")
    
    if await is_user_registered(user.id):
        logger.info(f"User {user.id} está registado. A prosseguir com a ação.")
        # Passa o objeto 'update' original para que a próxima função tenha o contexto completo
        return await start_function(update, context)
    else:
        logger.warning(f"User {user.id} não está registado. Acesso negado. A instruí-lo para se registar.")
        # Usa o update.message para garantir que podemos sempre enviar uma resposta de texto.
        await update.message.reply_text("Você precisa de se registar primeiro. Use o comando /start para começar.")
        return ConversationHandler.END


# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================
def main() -> None:
    """Inicia o bot e configura todos os handlers."""
    logger.info("A iniciar a configuração do bot...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- DEFINIÇÃO DOS HANDLERS DE CONVERSA ---
    logger.info("A configurar os handlers de conversa...")

    # 1. Handler de Cadastro e Menu Principal (Gatilho: /start)
    registration_conv = ConversationHandler(
        entry_points=[CommandHandler("start", common.start)],
        states={
            registration.ASK_COMPANY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.ask_if_company_code)],
            registration.ASK_IF_COMPANY_CODE: [
                CallbackQueryHandler(registration.prompt_for_company_code, pattern='^code_yes$'),
                CallbackQueryHandler(registration.ask_name_directly, pattern='^code_no$')
            ],
            registration.GET_COMPANY_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_company_code_and_ask_name)],
            registration.GET_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_full_name_and_ask_role)],
            registration.GET_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_role_and_ask_sector)],
            registration.GET_SECTOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_sector_and_save)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel)],
        per_user=True, per_chat=True,
    )

    # 2. Handler de Abertura de OS (Gatilho: botão do menu)
    open_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🆕 Abrir OS$"), lambda u, c: check_registration_and_start(u, c, service_order.start_open_os))],
        states={
            service_order.CONFIRM_SAVE: [CallbackQueryHandler(service_order.ask_for_equipment, pattern='^start_os$|^cancel_os$')],
            service_order.ASK_EQUIPMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_equipment_name)],
            service_order.ASK_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_equipment_tag)],
            service_order.ASK_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_location)],
            service_order.ASK_MAINT_TYPE: [CallbackQueryHandler(service_order.get_maintenance_type)],
            service_order.ASK_PRIORITY: [CallbackQueryHandler(service_order.get_priority)],
            service_order.ASK_PROBLEM_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_problem_description_and_ask_photo)],
            service_order.ASK_IF_PHOTO: [
                CallbackQueryHandler(service_order.prompt_for_photo, pattern='^photo_yes$'),
                CallbackQueryHandler(service_order.save_os_and_finish, pattern='^photo_no$')
            ],
            service_order.GET_PHOTO: [MessageHandler(filters.PHOTO, service_order.get_photo_and_save)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel)],
        per_user=True, per_chat=True,
    )
    
    # 3. Handler de Fechamento de OS
    close_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^✅ Fechar OS$"), lambda u, c: check_registration_and_start(u, c, service_order.start_close_os))],
        states={
            service_order.SELECT_OS_TO_CLOSE: [CallbackQueryHandler(service_order.ask_for_solution, pattern="^close_")],
            service_order.ASK_SOLUTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_solution_and_ask_parts)],
            service_order.ASK_IF_PARTS: [CallbackQueryHandler(service_order.ask_part_name, pattern='^parts_yes$'), CallbackQueryHandler(service_order.ask_for_final_status, pattern='^parts_no$')],
            service_order.ASK_PART_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_part_name)],
            service_order.ASK_PART_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_part_tag)],
            service_order.ASK_PART_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_part_qty_and_ask_more)],
            service_order.ASK_MORE_PARTS: [CallbackQueryHandler(service_order.ask_part_name, pattern='^parts_yes$'), CallbackQueryHandler(service_order.ask_for_final_status, pattern='^parts_no$')],
            service_order.ASK_FINAL_STATUS: [CallbackQueryHandler(service_order.get_final_status_and_ask_if_notes)],
            service_order.ASK_IF_NOTES: [CallbackQueryHandler(service_order.prompt_for_final_notes, pattern='^notes_yes$'), CallbackQueryHandler(service_order.finalize_without_notes, pattern='^notes_no$')],
            service_order.GET_FINAL_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_final_notes_and_save)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel), CallbackQueryHandler(common.cancel, pattern='^cancel_close$')],
        per_user=True, per_chat=True,
    )

    # 4. Handler de Relatórios
    report_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📊 Relatórios$"), lambda u, c: check_registration_and_start(u, c, reports.start_report_generation))],
        states={
            reports.CHOOSE_FILTER_TYPE: [CallbackQueryHandler(reports.handle_filter_choice)],
            reports.SELECT_START_DATE: [CallbackQueryHandler(reports.handle_start_date_selection)],
            reports.SELECT_END_DATE: [CallbackQueryHandler(reports.handle_end_date_selection)],
            reports.MANAGE_SELECTION: [CallbackQueryHandler(reports.manage_selection)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel), CallbackQueryHandler(common.cancel, pattern='^cancel_report$')],
        per_user=True, per_chat=True,
    )

    # 5. Handler de Listagem de OS Abertas
    list_open_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Listar Abertas$"), lambda u, c: check_registration_and_start(u, c, service_order.start_list_open_os))],
        states={
            service_order.PAGINATING_OS: [CallbackQueryHandler(service_order.navigate_os_page, pattern="^list_open")],
        },
        fallbacks=[CallbackQueryHandler(service_order.cancel_pagination, pattern="^list_open_cancel$")],
        per_user=True, per_chat=True,
    )

    # 6. Handler de Listagem de OS Fechadas
    list_closed_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🗂️ Listar Fechadas$"), lambda u, c: check_registration_and_start(u, c, service_order.start_list_closed_os))],
        states={
            service_order.PAGINATING_CLOSED_OS: [CallbackQueryHandler(service_order.navigate_closed_os_page, pattern="^list_closed")],
        },
        fallbacks=[CallbackQueryHandler(service_order.cancel_pagination, pattern="^list_closed_cancel$")],
        per_user=True, per_chat=True,
    )

    # 7. Handler de Edição de OS
    edit_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^✏️ Editar OS$"), lambda u, c: check_registration_and_start(u, c, os_edit.start_edit_os))],
        states={
            os_edit.PAGINATING_EDIT_OS: [
                CallbackQueryHandler(os_edit.navigate_editable_os_page, pattern="^edit_nav_"),
                CallbackQueryHandler(os_edit.show_edit_menu, pattern="^edit_select_os_"),
            ],
            os_edit.SELECT_FIELD: [
                CallbackQueryHandler(os_edit.prompt_for_new_value, pattern="^edit_field_"),
                CallbackQueryHandler(common.cancel, pattern="^edit_finish$"),
            ],
            os_edit.GET_NEW_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, os_edit.update_field_and_return_to_menu)],
        },
        fallbacks=[CallbackQueryHandler(common.cancel, pattern="^edit_cancel$"), CommandHandler("cancelar", common.cancel)],
        per_user=True, per_chat=True,
    )
    
    # --- REGISTO DE TODOS OS HANDLERS NA APLICAÇÃO ---
    logger.info("A adicionar handlers à aplicação...")
    
    # O handler de cadastro é o mais importante e deve vir primeiro para lidar com o /start
    application.add_handler(registration_conv)
    
    # Adicionamos os outros handlers de conversa
    application.add_handler(open_os_conv)
    application.add_handler(close_os_conv)
    application.add_handler(report_conv)
    application.add_handler(list_open_os_conv)
    application.add_handler(list_closed_os_conv)
    application.add_handler(edit_os_conv)
    
    logger.info("Todos os handlers foram adicionados.")
    
    # Mensagem de sucesso no console
    print("="*50)
    print("🚀 BOT INICIADO COM SUCESSO! 🚀")
    print("="*50)
    
    # Inicia o bot
    logger.info("Bot pronto e a iniciar o polling.")
    application.run_polling()


if __name__ == "__main__":
    main()
