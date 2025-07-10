import logging
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Importa as configurações e os handlers de cada módulo
from config import TELEGRAM_TOKEN
from handlers import common, registration

# --- Configuração do Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    """
    Função principal. Inicia o bot, configura todos os handlers e começa a escutar
    por novas mensagens.
    """
    # Cria a aplicação do bot usando o token do arquivo de configuração
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- Conversa de Cadastro ---
    registration_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🆕 Abrir OS$"), registration.start_registration_or_os)],
        states={
            registration.NOME_EMPRESA: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_company_name)],
            registration.NOME_COMPLETO: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_full_name)],
            registration.FUNCAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_role)],
            registration.SETOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_sector_and_save)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel)],
    )

    # --- Adicionando todos os Handlers à Aplicação ---
    application.add_handler(CommandHandler("start", common.start))
    application.add_handler(registration_conv)

    # Placeholders para os outros botões
    application.add_handler(MessageHandler(filters.Regex("^✅ Fechar OS$"), lambda u, c: u.message.reply_text("Funcionalidade 'Fechar OS' em desenvolvimento.")))
    application.add_handler(MessageHandler(filters.Regex("^📋 Listar Abertas$"), lambda u, c: u.message.reply_text("Funcionalidade 'Listar Abertas' em desenvolvimento.")))
    application.add_handler(MessageHandler(filters.Regex("^📊 Relatórios$"), lambda u, c: u.message.reply_text("Funcionalidade 'Relatórios' em desenvolvimento.")))

    # --- Inicia o Bot ---
    # Imprime uma mensagem clara e visível no console
    print("="*50)
    print("🚀 BOT INICIADO COM SUCESSO! 🚀")
    print("O bot está online e aguardando por mensagens.")
    print("Pressione Ctrl+C para parar o bot.")
    print("="*50)
    
    # Coloca o bot para rodar
    application.run_polling()


# Garante que a função main() seja chamada apenas quando o script é executado diretamente
if __name__ == "__main__":
    main()
