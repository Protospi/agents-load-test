"""
Arquivo de configuração central para o teste de carga
Modifique aqui para alterar parâmetros do teste
"""

# ============================================================================
# CONFIGURAÇÕES DA API VOYAGER
# ============================================================================

# URL base da API Voyager
VOYAGER_API_URL = "https://voyager.g121.io"

# Endpoint para envio de mensagens
VOYAGER_ENDPOINT = "/v1/webhooks/widget"

# ID do canal (channel) a ser testado
CHANNEL_ID = "68e4464832ec9940d9993a12"

# Domínio do identificador do cliente
CLIENT_DOMAIN = "@stw.ai"

# ============================================================================
# CONFIGURAÇÕES DO SERVIDOR FLASK
# ============================================================================

# Porta do servidor Flask que receberá os webhooks
FLASK_PORT = 5001  # Mudado de 5000 para 5001 (macOS AirPlay usa 5000)

# Host do servidor Flask
FLASK_HOST = "0.0.0.0"

# Path base para webhooks
WEBHOOK_PATH = "/responses"

# ============================================================================
# CONFIGURAÇÕES DE TESTE
# ============================================================================

# Mensagem padrão enviada nos testes
DEFAULT_MESSAGE = "Olá"

# Tipo de mensagem
MESSAGE_TYPE = "text"

# Timeout para aguardar resposta do webhook (segundos)
WEBHOOK_TIMEOUT = 120

# Intervalo de polling para verificar webhook (segundos)
POLLING_INTERVAL = 0.5

# Tempo de espera entre requisições de um mesmo usuário (segundos)
USER_WAIT_TIME = 3

# ============================================================================
# CONFIGURAÇÕES DE LOG
# ============================================================================

# Nível de log (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL = "INFO"

# Formato do log
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# ============================================================================
# CONFIGURAÇÕES OPCIONAIS
# ============================================================================

# Mostrar payload completo nos logs (cuidado com dados sensíveis)
SHOW_FULL_PAYLOAD = False

# Limpar webhooks da memória após recuperar
CLEAR_WEBHOOKS_AFTER_READ = True

# Número máximo de caracteres da resposta a exibir no log
MAX_RESPONSE_CHARS = 100

