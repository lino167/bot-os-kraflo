from telegram.ext.filters import MessageFilter

from handlers.ui_components import REPLY_KEYBOARD

class _FreeTextFilter(MessageFilter):
    """
    Filtro customizado que só permite mensagens de texto que NÃO SÃO
    um dos botões do menu principal.
    """
    def filter(self, message):
        button_texts = [item for sublist in REPLY_KEYBOARD for item in sublist]
        return message.text is not None and message.text not in button_texts

class _MenuButtonFilter(MessageFilter):
    """
    Corresponde a qualquer texto que seja um botão do menu principal,
    EXCETO o botão de cancelar, que é tratado nos fallbacks.
    """
    def filter(self, message):
        button_texts = [item for sublist in REPLY_KEYBOARD for item in sublist]
        cancel_button_text = "❌ Cancelar"
        
        return message.text is not None and message.text in button_texts and message.text != cancel_button_text

# Instâncias que vamos usar no main.py
free_text_filter = _FreeTextFilter()
menu_button_filter = _MenuButtonFilter()
