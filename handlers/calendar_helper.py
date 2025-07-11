import calendar
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def create_calendar(year: int = None, month: int = None) -> InlineKeyboardMarkup:
    """
    Cria um teclado de calendário interativo para um mês e ano específicos.
    """
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    data_ignore = "calendar_ignore"
    keyboard = []

    # Linha 1: Mês e Ano
    keyboard.append([InlineKeyboardButton(f"{calendar.month_name[month]} {year}", callback_data=data_ignore)])

    # Linha 2: Dias da semana
    week_days = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
    keyboard.append([InlineKeyboardButton(day, callback_data=data_ignore) for day in week_days])

    # Linhas do calendário com os dias
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data=data_ignore))
            else:
                # O callback_data contém o dia selecionado no formato AAAA-MM-DD
                row.append(InlineKeyboardButton(str(day), callback_data=f"calendar_day_{year}-{month:02d}-{day:02d}"))
        keyboard.append(row)

    # Linha final: Navegação
    # Correção para cálculo de mês/ano
    if month == 1:
        prev_month_date = datetime(year - 1, 12, 1)
    else:
        prev_month_date = datetime(year, month - 1, 1)

    if month == 12:
        next_month_date = datetime(year + 1, 1, 1)
    else:
        next_month_date = datetime(year, month + 1, 1)
    
    keyboard.append([
        InlineKeyboardButton("<", callback_data=f"calendar_prev_{prev_month_date.year}-{prev_month_date.month}"),
        InlineKeyboardButton("Hoje", callback_data=f"calendar_day_{now.year}-{now.month:02d}-{now.day:02d}"),
        InlineKeyboardButton(">", callback_data=f"calendar_next_{next_month_date.year}-{next_month_date.month}")
    ])

    return InlineKeyboardMarkup(keyboard)