from telegram import ReplyKeyboardMarkup, InlineKeyboardButton

# Teclado principal com botões de texto
REPLY_KEYBOARD = [
    ["🆕 Abrir OS", "✅ Fechar OS"],
    ["📋 Listar Abertas", "🗂️ Listar Fechadas"],
    ["📊 Relatórios", "✏️ Editar OS"],
]
MAIN_MENU_MARKUP = ReplyKeyboardMarkup(REPLY_KEYBOARD, resize_keyboard=True)

# --- Teclados de Botões Inline (para edição e outras conversas) ---

# Teclado para selecionar o Tipo de Manutenção
TIPO_MANUTENCAO_KEYBOARD = [
    [InlineKeyboardButton("🔧 Corretiva", callback_data="Corretiva")],
    [InlineKeyboardButton("📈 Preditiva", callback_data="Preditiva")],
    [InlineKeyboardButton("🗓️ Preventiva", callback_data="Preventiva")]
]

# Teclado para selecionar a Prioridade
PRIORIDADE_KEYBOARD = [
    [InlineKeyboardButton("🚨 Urgente", callback_data="Urgente")],
    [InlineKeyboardButton("⚠️ Alta", callback_data="Alta")],
    [InlineKeyboardButton("🔷 Média", callback_data="Média")],
    [InlineKeyboardButton("⚪ Baixa", callback_data="Baixa")]
]

# Teclado para selecionar o Status da OS
STATUS_OS_KEYBOARD = [
    [InlineKeyboardButton("✅ Concluída", callback_data="Concluída")],
    [InlineKeyboardButton("⏳ Pendente", callback_data="Pendente")],
    [InlineKeyboardButton("🔴 Aberta", callback_data="Aberta")]
]
