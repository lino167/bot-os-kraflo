import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configuração das Variáveis de Ambiente ---
# Pega as credenciais do arquivo .env
SUPABASE_URL: str = os.environ.get("SUPABASE_URL")
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY") # Lembre-se: esta deve ser a SERVICE_ROLE KEY
TELEGRAM_TOKEN: str = os.environ.get("TELEGRAM_TOKEN")

# --- Inicialização do Cliente Supabase ---
try:
    # Cria o cliente Supabase que será usado em todo o projeto
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logging.info("Conexão com o Supabase estabelecida com sucesso.")
except Exception as e:
    # Em caso de falha na conexão, registra um erro crítico
    logging.error(f"Falha ao conectar com o Supabase: {e}")
    supabase = None

