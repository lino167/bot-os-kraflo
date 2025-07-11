from telegram import ReplyKeyboardMarkup

# Teclado do menu principal, agora num local centralizado.
REPLY_KEYBOARD = [
    ["🆕 Abrir OS", "✅ Fechar OS"],
    ["📋 Listar Abertas", "🗂️ Listar Fechadas"],
    ["📊 Relatórios"],
]
MAIN_MENU_MARKUP = ReplyKeyboardMarkup(REPLY_KEYBOARD, resize_keyboard=True)