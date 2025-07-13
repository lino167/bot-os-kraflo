from telegram import ReplyKeyboardMarkup

# Teclado do menu principal atualizado com a nova opção de edição
REPLY_KEYBOARD = [
    ["🆕 Abrir OS", "✅ Fechar OS"],
    ["📋 Listar Abertas", "🗂️ Listar Fechadas"],
    ["📊 Relatórios", "✏️ Editar OS"],
]
MAIN_MENU_MARKUP = ReplyKeyboardMarkup(REPLY_KEYBOARD, resize_keyboard=True)