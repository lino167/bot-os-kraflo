from itertools import count

# Usamos um contador para garantir que todos os estados tenham um ID único em todo o bot.
_state_counter = count()

# --- Estados de Registro (registration.py) ---
ASK_COMPANY_NAME = next(_state_counter)
ASK_IF_COMPANY_CODE = next(_state_counter)
GET_COMPANY_CODE = next(_state_counter)
GET_FULL_NAME = next(_state_counter)
GET_ROLE = next(_state_counter)
GET_SECTOR = next(_state_counter)

# --- Estados de Ordem de Serviço (service_order.py) ---
# Abertura
CONFIRM_SAVE = next(_state_counter)
ASK_EQUIPMENT = next(_state_counter)
ASK_TAG = next(_state_counter)
ASK_LOCATION = next(_state_counter)
ASK_MAINT_TYPE = next(_state_counter)
ASK_PRIORITY = next(_state_counter)
ASK_PROBLEM_DESC = next(_state_counter)
ASK_IF_PHOTO = next(_state_counter)
GET_PHOTO = next(_state_counter)
HANDLE_UPLOAD_ERROR = next(_state_counter)
# Fechamento
SELECT_OS_TO_CLOSE = next(_state_counter)
ASK_SOLUTION = next(_state_counter)
ASK_IF_PARTS = next(_state_counter)
ASK_PART_NAME = next(_state_counter)
ASK_PART_TAG = next(_state_counter)
ASK_PART_QTY = next(_state_counter)
ASK_MORE_PARTS = next(_state_counter)
ASK_FINAL_STATUS = next(_state_counter)
ASK_IF_ATTACHMENT = next(_state_counter)
GET_ATTACHMENT = next(_state_counter)
HANDLE_ATTACHMENT_UPLOAD_ERROR = next(_state_counter)
ASK_IF_NOTES = next(_state_counter)
GET_FINAL_NOTES = next(_state_counter)
# Paginação
PAGINATING_OS = next(_state_counter)
PAGINATING_CLOSED_OS = next(_state_counter)

# --- Estados de Relatórios (reports.py) ---
SELECT_START_DATE = next(_state_counter)
SELECT_END_DATE = next(_state_counter)
MANAGE_SELECTION = next(_state_counter)

# --- Estados de Edição de OS (os_edit.py) ---
PAGINATING_EDIT_OS = next(_state_counter)
SELECT_FIELD = next(_state_counter)
GET_NEW_VALUE_TEXT = next(_state_counter)
GET_NEW_VALUE_BUTTON = next(_state_counter)

# --- Estados de Deleção de OS (os_delete.py) ---
CHOOSE_STATUS = next(_state_counter)
SELECT_DATE = next(_state_counter)
LIST_OS_FOR_DELETION = next(_state_counter)
CONFIRM_DELETE = next(_state_counter)

# --- Estados do Gerenciador de Peças (parts_manager.py) ---
ASK_SEARCH_TERM = next(_state_counter)
SHOW_RESULTS = next(_state_counter)
