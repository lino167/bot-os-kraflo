import calendar
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def create_calendar(year: int = None, month: int = None) -> InlineKeyboardMarkup:
    """Cria um teclado de calendário interativo para um mês e ano específicos."""
    now = datetime.now()
    if year is None: year = now.year
    if month is None: month = now.month

    data_ignore = "calendar_ignore"
    keyboard = []
    keyboard.append([InlineKeyboardButton(f"{calendar.month_name[month]} {year}", callback_data=data_ignore)])
    keyboard.append([InlineKeyboardButton(day, callback_data=data_ignore) for day in ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]])

    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        row = [InlineKeyboardButton(str(day) if day != 0 else " ", callback_data=f"calendar_day_{year}-{month:02d}-{day:02d}" if day != 0 else data_ignore) for day in week]
        keyboard.append(row)

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