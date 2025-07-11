import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configuração das Variáveis de Ambiente ---
SUPABASE_URL: str = os.environ.get("SUPABASE_URL")
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY")
TELEGRAM_TOKEN: str = os.environ.get("TELEGRAM_TOKEN")

# --- Inicialização do Cliente Supabase ---
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logging.info("Conexão com o Supabase estabelecida com sucesso.")
except Exception as e:
    logging.error(f"Falha ao conectar com o Supabase: {e}")
    supabase = None