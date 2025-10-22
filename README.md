# 🚀 Load Test Voyager API com Gemini

Sistema de teste de carga que simula conversas realistas entre usuários (via Gemini AI) e a API Voyager usando **Locust + Flask + ngrok**.

---

## 📋 O Que Este Sistema Faz

Este projeto simula usuários reais conversando com um assistente virtual (Voyager API) para comprar ingressos. Cada usuário virtual:

1. **Tem uma personalidade única** (uma das 3 personas definidas)
2. **Usa Gemini AI** para gerar respostas naturais em português
3. **Envia mensagens para Voyager API** que responde via webhook
4. **Mantém conversa completa** até receber link de pagamento (máximo 15 iterações)
5. **Registra todas as métricas** de tempo, custo e sucesso

```
┌──────────┐        ┌──────────┐        ┌──────────┐        ┌──────────┐
│  Locust  │───────>│  Gemini  │───────>│  Voyager │───────>│  Flask   │
│  Users   │ Persona│    AI    │ Message│   API    │ Webhook│ +ngrok   │
└──────────┘        └──────────┘        └──────────┘        └──────────┘
     │                    │                    │                   │
     └────────────────────┴────────────────────┴───────────────────┘
                    Conversa completa + métricas
```

---

## ⚡ Como Inicializar o Projeto

### 1. Clonar e Instalar Dependências

```bash
# Clone o repositório (se ainda não tiver)
cd /caminho/para/agents-load-test

# Crie e ative o ambiente virtual (recomendado)
python3 -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com sua chave da API Gemini:

```bash
# Opção 1: Criar manualmente
echo "GOOGLE_API_KEY=sua_chave_aqui" > .env

# Opção 2: Editar o arquivo
nano .env
```

Conteúdo do `.env`:
```
GOOGLE_API_KEY=sua_chave_da_api_gemini_aqui
```

**Como obter a chave da API Gemini:**
1. Acesse: https://ai.google.dev/
2. Clique em "Get API Key"
3. Crie ou selecione um projeto
4. Copie a chave gerada

### 3. Configurar ngrok (apenas primeira vez)

O ngrok é necessário para receber webhooks da Voyager API:

```bash
# Obtenha seu token em: https://dashboard.ngrok.com/get-started/your-authtoken
ngrok authtoken SEU_TOKEN_AQUI
```

### 4. Configurar Channel ID (se necessário)

Edite o arquivo `config.py` e atualize o `CHANNEL_ID` da sua API Voyager:

```python
# config.py
CHANNEL_ID = "seu_channel_id_aqui"
```

---

## 🚀 Como Executar os Testes

### Teste Simples (3 usuários)

Teste básico para validar o funcionamento do sistema com poucos usuários:

```bash
locust --headless -u 3 -r 1 -t 10m
```

Este teste é ideal para:
- Validação inicial do sistema
- Debug de problemas
- Testes de desenvolvimento
- Verificar fluxo completo da conversa

### Smoke Test (10 usuários)

Teste rápido para verificar a estabilidade do sistema:

```bash
locust --headless -u 10 -r 2 -t 10m
```

Este teste ajuda a:
- Validar a estabilidade do sistema
- Identificar problemas óbvios
- Verificar se o sistema aguenta carga básica
- Testar timeouts e recuperação de erros

### Load Test (100 usuários)

Teste de carga completo para simular uso real:

```bash
locust --headless -u 100 -r 5 -t 30m
```

Use este teste para:
- Simular carga real de produção
- Verificar limites do sistema
- Testar escalabilidade
- Identificar gargalos de performance

⚠️ **Importante:**
- Comece sempre pelo teste simples (3 usuários)
- Monitore os custos da API Gemini durante os testes
- Observe os logs para identificar problemas
- Ajuste os timeouts se necessário em `config.py`

### Com Interface Web

Se preferir controlar manualmente:

```bash
locust -f locustfile.py
# Depois acesse: http://localhost:8089
```

---

## 📝 Parâmetros Detalhados do Locust

### Parâmetros Principais

| Parâmetro | Descrição | Exemplo |
|-----------|-----------|---------|
| `-f` | **Arquivo do teste** - Especifica qual arquivo Locust usar | `-f locustfile.py` |
| `--headless` | **Modo sem interface** - Executa teste direto no terminal (sem UI web) | `--headless` |
| `-u` / `--users` | **Número de usuários** - Quantidade total de usuários simultâneos | `-u 10` |
| `-r` / `--spawn-rate` | **Taxa de criação** - Quantos usuários novos por segundo | `-r 2` |
| `--run-time` | **Duração do teste** - Tempo total de execução (s=segundos, m=minutos, h=horas) | `--run-time 5m` |

### Parâmetros de Relatório

| Parâmetro | Descrição | Exemplo |
|-----------|-----------|---------|
| `--html` | **Relatório HTML** - Gera relatório visual ao final do teste | `--html report.html` |
| `--csv` | **Relatórios CSV** - Gera 3 arquivos CSV com estatísticas | `--csv results` |
| `--csv-full-history` | **CSV completo** - Inclui histórico completo no CSV | `--csv-full-history` |

### Parâmetros de Log

| Parâmetro | Descrição | Exemplo |
|-----------|-----------|---------|
| `--loglevel` | **Nível de log** - Quantidade de informações no console (DEBUG, INFO, WARNING, ERROR) | `--loglevel INFO` |
| `--logfile` | **Arquivo de log** - Salva logs em arquivo | `--logfile test.log` |

### Parâmetros Avançados

| Parâmetro | Descrição | Exemplo |
|-----------|-----------|---------|
| `--host` | **URL base** - Sobrescreve o host definido no código | `--host https://api.example.com` |
| `-t` / `--run-time` | **Tempo de execução** - Igual a --run-time | `-t 30s` |
| `--stop-timeout` | **Timeout de parada** - Tempo máximo para usuários finalizarem | `--stop-timeout 60` |
| `--tags` | **Executar tags** - Executa apenas tasks com essas tags | `--tags tag1 tag2` |
| `--exclude-tags` | **Excluir tags** - Ignora tasks com essas tags | `--exclude-tags slow` |

### Exemplos Práticos Completos

**1. Teste rápido com relatório:**
```bash
locust -f locustfile.py --headless -u 5 -r 1 --run-time 3m --html report.html
```

**2. Teste longo com CSVs:**
```bash
locust -f locustfile.py --headless -u 20 -r 2 --run-time 30m --csv results --csv-full-history
```

**3. Debug detalhado:**
```bash
locust -f locustfile.py --headless -u 1 -r 1 --run-time 1m --loglevel DEBUG --logfile debug.log
```

**4. Teste com nome personalizado (timestamp):**
```bash
locust -f locustfile.py --headless -u 10 -r 2 --run-time 10m \
  --html report_$(date +%Y%m%d_%H%M%S).html \
  --csv results_$(date +%Y%m%d_%H%M%S)
```

### Entendendo os Parâmetros -u e -r

**Exemplo:** `-u 10 -r 2`

- Cria **10 usuários no total**
- Cria **2 usuários por segundo**
- Leva **5 segundos** para todos os usuários estarem ativos (10 ÷ 2 = 5s)

**Recomendações:**
- Para testes gradual: use `r` baixo (ex: `r 1` ou `r 2`)
- Para stress test: use `r` alto (ex: `r 10` ou `r 20`)
- **Atenção**: Este projeto simula conversas longas! Cada usuário pode levar 2-5 minutos por conversa completa

---

## 🎭 Personas - Simulação de Clientes Reais

O projeto inclui 3 personas diferentes que simulam clientes reais. Cada usuário virtual recebe **aleatoriamente** uma das personas:

### Persona 1 - Kataryna Smart
**Perfil:** Cliente interessada em comprar ingressos
- Aceita opt-in de mensagens promocionais
- Pede ingressos para 11/10/2026
- Quantidade: 2 adultos + 2 crianças
- **ACEITA** upselling (cabanas/experiências)
- Prossegue até finalizar pagamento via PIX

**Dados personalizados:** Cada teste gera telefone, email e CPF únicos

### Persona 2 - Talliz Smart
**Perfil:** Cliente curioso sobre o local
- Pergunta onde fica e o que tem para fazer
- Pede ingressos Arvorar para 20/11 (fechado)
- Aceita nova data: 21/11
- Quantidade: 4 adultos
- **RECUSA** upselling
- Finaliza no link de pagamento

**Dados personalizados:** Cada teste gera telefone, email e CPF únicos

### Persona 3 - Edman Smart
**Perfil:** Cliente focado em data específica
- Consulta disponibilidade
- Pede segunda semana de novembro
- Quantidade: 1 adulto, 1 gestante, 2 idosos
- **RECUSA** upselling
- Prossegue até pagamento via PIX

**Dados personalizados:** Cada teste gera telefone, email e CPF únicos

### Como as Personas São Usadas

1. Cada usuário virtual do Locust recebe **uma persona aleatória** no início
2. Os dados pessoais (telefone, email, CPF) são **gerados automaticamente** de forma única
3. O Gemini AI usa a persona para **conversar naturalmente** seguindo o roteiro
4. As conversas são **100% em português** com linguagem informal (estilo WhatsApp)

---

## 📁 Estrutura de Arquivos

```
agents-load-test/
├── locustfile.py          # Código principal do teste de carga
├── config.py              # Configurações (API URL, timeouts, etc)
├── requirements.txt       # Dependências Python
├── .env                   # Chaves de API (NÃO COMMITAR!)
├── .gitignore             # Arquivos ignorados pelo Git
├── personas/              # Definições das 3 personas
│   ├── persona_1.txt      # Kataryna Smart
│   ├── persona_2.txt      # Talliz Smart  
│   └── persona_3.txt      # Edman Smart
├── utils/                 # Utilitários
│   └── generate_user_data.py  # Gerador de dados de usuários
└── logs/                  # Logs e resultados (gerados automaticamente)
    ├── conversation_*.json      # Log de cada conversa individual
    └── load_test_results_*.json # Resumo agregado do teste
```

---

## ⚙️ Configuração Avançada

### Arquivo config.py

Principais configurações que você pode ajustar:

```python
# API Voyager
VOYAGER_API_URL = "https://voyager.g121.io"
CHANNEL_ID = "68e4464832ec9940d9993a12"  # ← ALTERE PARA SEU CHANNEL

# Servidor Flask (recebe webhooks)
FLASK_PORT = 5001  # Porta 5000 é usada pelo AirPlay no macOS

# Timeouts
WEBHOOK_TIMEOUT = 30  # segundos para aguardar webhook
POLLING_INTERVAL = 0.5  # intervalo de verificação

# Comportamento dos usuários
USER_WAIT_TIME = 1  # pausa entre ações do usuário (segundos)
```

---

## 📊 Analisando os Resultados

### Logs Durante a Execução

Durante o teste, você verá logs no console:

```
🚀 Iniciando sistema de teste de carga...
📡 Iniciando servidor Flask...
🔗 Iniciando túnel ngrok...
🌐 NGROK URL: https://abc123.ngrok-free.app
✅ Sistema pronto para receber requisições!
👤 User 1 created - Name: João Silva, Phone: 5511987654321...
🎬 Starting conversation - Base Session ID: abc-123-def...
🔄 Iteration 1/15 - Session: abc-123-def...
✅ Conversation complete - Iterations: 8 - Link found: true
```

### Arquivos de Log Gerados

Após cada teste, o sistema gera arquivos na pasta `logs/`:

1. **conversation_XXXXX_timestamp.json** - Log detalhado de cada conversa individual:
```json
{
  "summary": {
    "session_id": "abc-123-def",
    "user_id": 1,
    "iterations": 8,
    "found_link": true,
    "total_time_ms": 45230,
    "gemini_tokens": {...},
    "total_cost_usd": 0.003456
  },
  "messages": [...]
}
```

2. **load_test_results_timestamp.json** - Resumo agregado de todas as conversas:
```json
{
  "summary": {
    "total_conversations": 10,
    "successful_conversations": 8,
    "success_rate": "80.00%",
    "avg_iterations_per_conversation": 9.2,
    "total_cost_usd": 0.034560
  },
  "conversations": [...]
}
```

### Métricas do Locust

Ao final do teste, você verá estatísticas:

```
Type        Name                    # reqs  # fails  Avg    Min    Max    Median
----------- ----------------------- ------- -------- ------ ------ ------ ------
POST        Voyager Message         100     0(0%)    245ms  123ms  456ms  230ms
WEBHOOK     Voyager Webhook         100     0(0%)    4500ms 2000ms 8000ms 4200ms
GEMINI      Gemini Response         150     2(1.3%)  890ms  234ms  3400ms 780ms
CONVERSATION Complete Conversation  10      0(0%)    45230ms 30000ms 67000ms 43000ms
```

**O que observar:**
- ✅ **Taxa de falhas baixa** (< 5%)
- ✅ **Complete Conversation** sem falhas = conversas finalizaram com sucesso
- ⚠️ Falhas no Gemini são esperadas ocasionalmente (retry automático)
- ⚠️ Tempos altos são normais (conversas completas demoram 30s-2min)

---

## 🐛 Problemas Comuns e Soluções

### ❌ "Port 5001 already in use"

**Solução 1:** Liberar a porta
```bash
lsof -ti:5001 | xargs kill -9
```

**Solução 2:** Mudar a porta em `config.py`
```python
FLASK_PORT = 5002
```

### ❌ "ngrok authtoken not found"

```bash
# Configure o token do ngrok
ngrok authtoken SEU_TOKEN_AQUI
```

Obtenha o token em: https://dashboard.ngrok.com/get-started/your-authtoken

### ❌ "command not found: locust"

```bash
# Ative o ambiente virtual
source venv/bin/activate

# Se não resolver, reinstale
pip install -r requirements.txt
```

### ❌ "GOOGLE_API_KEY not found" ou erro do Gemini

**Causa:** Chave da API Gemini não configurada

**Solução:**
```bash
# Crie o arquivo .env
echo "GOOGLE_API_KEY=sua_chave_aqui" > .env

# Ou edite manualmente
nano .env
```

Obtenha a chave em: https://ai.google.dev/

### ❌ Muitos timeouts no webhook

**Possíveis causas:**
1. Channel ID incorreto em `config.py`
2. API Voyager lenta ou offline
3. Timeout muito curto
4. ngrok expirou ou não está conectado

**Soluções:**

**1. Verificar Channel ID:**
```python
# Em config.py
CHANNEL_ID = "seu_channel_id_correto_aqui"
```

**2. Aumentar timeout:**
```python
# Em config.py
WEBHOOK_TIMEOUT = 60  # 60 segundos
```

**3. Reduzir carga:**
```bash
locust -f locustfile.py --headless -u 5 -r 1 --run-time 2m
```

**4. Verificar ngrok:**
```bash
# Acesse a interface do ngrok para debug
open http://localhost:4040
```

### ❌ Gemini API Errors (429, 500, etc)

**Causa comum:** Limite de taxa da API Gemini

**Solução 1:** Reduzir número de usuários
```bash
# Use menos usuários simultâneos
locust -f locustfile.py --headless -u 3 -r 1 --run-time 5m
```

**Solução 2:** Aumentar wait time
```python
# Em config.py
USER_WAIT_TIME = 3  # Aumenta pausa entre ações
```

**Nota:** O código já tem retry automático (3 tentativas) para erros do Gemini

### ❌ "Persona file not found"

**Causa:** Arquivos de persona não encontrados

**Verificar:**
```bash
# Confirmar que as personas existem
ls -la personas/
# Deve mostrar: persona_1.txt, persona_2.txt, persona_3.txt
```

---

## 💡 Boas Práticas e Dicas

### 1. Sempre Comece Pequeno

**❌ NÃO faça isso primeiro:**
```bash
locust -f locustfile.py --headless -u 100 -r 50
```

**✅ FAÇA isso:**
```bash
# 1. Teste com 1 usuário primeiro
locust -f locustfile.py --headless -u 1 -r 1 --run-time 2m

# 2. Se funcionar, aumente gradualmente
locust -f locustfile.py --headless -u 5 -r 1 --run-time 5m
locust -f locustfile.py --headless -u 10 -r 2 --run-time 10m
```

### 2. Use Ambiente Virtual

```bash
# Sempre use venv para isolar dependências
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Monitore os Custos

Cada conversa usa tokens do Gemini:
- **Gemini 2.5 Flash:** $0.30 / 1M tokens (input), $2.50 / 1M tokens (output)
- **Custo médio por conversa:** ~$0.002 - $0.005 USD
- **Teste com 100 conversas:** ~$0.20 - $0.50 USD

**Dica:** Comece com poucos usuários e monitore o custo no arquivo `load_test_results_*.json`

### 4. Salve Resultados Importantes

```bash
# Use timestamp no nome dos relatórios
mkdir -p reports
locust -f locustfile.py --headless -u 10 -r 2 --run-time 10m \
  --html reports/test_$(date +%Y%m%d_%H%M%S).html \
  --csv reports/results_$(date +%Y%m%d_%H%M%S)
```

### 5. Entenda o Tempo de Execução

**⚠️ Importante:** Cada usuário completa UMA conversa completa que pode levar:
- Mínimo: 30 segundos (se tudo for rápido)
- Média: 1-2 minutos
- Máximo: 5 minutos (timeouts ou problemas)

**Exemplo real:**
```bash
# 10 usuários, 10 minutos
locust -f locustfile.py --headless -u 10 -r 2 --run-time 10m
```

Resultado esperado:
- 10 usuários completarão suas conversas
- Cada conversa demora ~2 minutos
- Total: ~10 conversas completas

### 6. Use Interface Web para Debug

```bash
# Inicie sem --headless
locust -f locustfile.py

# Acesse: http://localhost:8089
# Vantagens:
# - Visualizar métricas em tempo real
# - Ajustar número de usuários dinamicamente
# - Ver gráficos de performance
# - Parar teste quando quiser
```

---

## 🔍 Monitoramento Durante os Testes

### Interface Web do ngrok

O ngrok fornece uma interface web para debug dos webhooks:

```bash
# Acesse enquanto teste está rodando
open http://localhost:4040
```

Você pode ver:
- Todas as requisições HTTP recebidas
- Headers, body e timestamps
- Status codes e tempos de resposta
- Útil para debug de problemas com webhooks

### Logs em Tempo Real

Os logs aparecem automaticamente no console com emojis para fácil identificação:

```
📤 = Enviando requisição
✅ = Sucesso
⏳ = Aguardando
🎉 = Completo
❌ = Erro
⏰ = Timeout
🔄 = Iteração da conversa
💬 = Mensagem
```

### Interface Web do Locust

Para monitoramento visual em tempo real:

```bash
# Inicie sem --headless
locust -f locustfile.py

# Acesse: http://localhost:8089
```

Vantagens:
- Gráficos de performance ao vivo
- Número de usuários ativos
- Taxa de requisições/segundo
- Distribuição de tempos de resposta
- Pode pausar/parar/ajustar teste dinamicamente

---

## 🔧 Customização do Projeto

### Modificar Personas

Edite os arquivos em `personas/` para mudar comportamento:

```bash
nano personas/persona_1.txt
```

**Dicas:**
- Mantenha instruções claras e específicas
- Use linguagem natural
- Especifique quando aceitar/recusar ofertas
- Defina claramente dados pessoais a informar

### Criar Nova Persona

1. Crie novo arquivo: `personas/persona_4.txt`
2. Atualize o `locustfile.py` linha 269:
```python
# De:
self.persona_file = f'personas/persona_{random.randint(1,3)}.txt'

# Para:
self.persona_file = f'personas/persona_{random.randint(1,4)}.txt'
```

### Modificar Configurações

Todas em `config.py`:

```python
# Aumentar/diminuir tempo máximo de espera
WEBHOOK_TIMEOUT = 60  # segundos

# Mudar mensagem inicial (se necessário)
DEFAULT_MESSAGE = "Olá"

# Alterar intervalo de verificação de webhook
POLLING_INTERVAL = 0.5  # segundos

# Mudar porta do Flask
FLASK_PORT = 5002
```

### Ajustar Número Máximo de Iterações

Em `locustfile.py` linha 27:

```python
# Padrão: 15 iterações (30 mensagens total)
MAX_ITERATIONS = 15

# Para conversas mais curtas:
MAX_ITERATIONS = 10

# Para conversas mais longas:
MAX_ITERATIONS = 20
```

---

## 🎓 Arquitetura do Sistema

### Fluxo Completo de uma Conversa

```
1. Locust cria VoyagerUser
   ├── Atribui persona aleatória (1, 2 ou 3)
   ├── Gera dados de usuário únicos (nome, telefone, email, CPF)
   ├── Inicializa sessão Gemini com persona customizada
   └── Gera base_session_id (UUID)

2. Início da Conversa
   ├── Usuário envia mensagem inicial ("Olá")
   └── Sistema entra em loop (máx 15 iterações)

3. Iteração (repetido até encontrar link ou MAX_ITERATIONS)
   ├── a) Enviar mensagem para Voyager API
   │   ├── POST /v1/webhooks/widget
   │   ├── Body: {text, channelId, clientIdentifier, webhook}
   │   └── Webhook URL: ngrok/responses/{session_id}_{iteration}
   │
   ├── b) Voyager processa e responde via webhook
   │   ├── Voyager → ngrok → Flask
   │   └── Flask armazena em webhook_responses[session_id]
   │
   ├── c) Locust detecta resposta (polling)
   │   └── Verifica webhook_responses a cada 0.5s
   │
   ├── d) Verifica se resposta contém link HTTP
   │   ├── Se SIM: conversa completa ✅
   │   └── Se NÃO: continua para próxima iteração
   │
   └── e) Envia resposta para Gemini gerar próxima mensagem
       ├── Gemini recebe mensagem do assistente
       ├── Gemini gera resposta baseado na persona
       └── Retry automático (3x) se Gemini falhar

4. Fim da Conversa
   ├── Calcula métricas (tempo, tokens, custo)
   ├── Salva log individual: conversation_XXX.json
   └── Adiciona ao resumo agregado
```

### Componentes Principais

**locustfile.py:**
- `VoyagerUser`: Classe que simula cada usuário virtual
- `run_complete_conversation()`: Task principal (uma conversa completa)
- `send_to_voyager()`: Envia mensagem e aguarda webhook
- `flask_app`: Servidor para receber webhooks
- `save_test_results()`: Salva resumo agregado

**config.py:**
- Configurações centralizadas (URLs, timeouts, portas)

**utils/generate_user_data.py:**
- Gera dados de usuários únicos (nome, telefone, CPF, email)

**personas/**:
- Define comportamento de cada tipo de cliente

---

## 🔒 Segurança e Boas Práticas

### Não Commitar Informações Sensíveis

O `.gitignore` já está configurado para ignorar:
```
.env               # Chaves de API
*.log              # Logs
venv/              # Ambiente virtual
__pycache__/       # Cache Python
logs/              # Logs de conversas
reports/           # Relatórios
*.html             # Relatórios HTML
*.csv              # CSVs
```

### Gerenciar Chaves de API

```bash
# NUNCA faça commit do .env
echo ".env" >> .gitignore

# Use variáveis de ambiente
export GOOGLE_API_KEY="sua_chave"

# Ou arquivo .env (não commitado)
echo "GOOGLE_API_KEY=sua_chave" > .env
```

### Ambiente Virtual Isolado

Sempre use ambiente virtual para evitar conflitos:

```bash
# Criar
python3 -m venv venv

# Ativar (macOS/Linux)
source venv/bin/activate

# Ativar (Windows)
venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Desativar quando terminar
deactivate
```

---

## 📞 Suporte e Referências

### Documentação Oficial

- **Locust:** https://docs.locust.io/
- **Flask:** https://flask.palletsprojects.com/
- **ngrok:** https://ngrok.com/docs
- **Gemini API:** https://ai.google.dev/docs
- **Google Gen AI Python SDK:** https://github.com/googleapis/python-genai

### Recursos Úteis

- **Locust Parametros:** https://docs.locust.io/en/stable/configuration.html
- **ngrok Webhooks:** https://ngrok.com/docs/integrations/
- **Gemini Pricing:** https://ai.google.dev/pricing

---

## ✅ Checklist Antes de Executar

- [ ] Python 3.7+ instalado (`python3 --version`)
- [ ] Ambiente virtual criado e ativado
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] Arquivo `.env` criado com `GOOGLE_API_KEY`
- [ ] ngrok configurado (`ngrok authtoken ...`)
- [ ] Porta 5001 livre (ou outra em `config.py`)
- [ ] Channel ID correto em `config.py`
- [ ] Personas existem na pasta `personas/`
- [ ] Conexão de internet estável

---

## 🚀 Início Rápido - TL;DR

```bash
# 1. Setup inicial (primeira vez)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "GOOGLE_API_KEY=sua_chave" > .env
ngrok authtoken SEU_TOKEN

# 2. Configurar (se necessário)
nano config.py  # Ajuste CHANNEL_ID

# 3. Executar teste
locust -f locustfile.py --headless -u 5 -r 1 --run-time 5m --html report.html

# 4. Ver resultados
open report.html
cat logs/load_test_results_*.json
```

---

## 📄 Licença

Projeto para uso interno de testes de carga da API Voyager.

---

## 🤝 Contribuindo

Para adicionar melhorias:

1. Teste suas mudanças com 1 usuário primeiro
2. Documente novas configurações em `config.py`
3. Atualize o README se necessário
4. Valide que os logs estão sendo gerados corretamente

---

**Desenvolvido para testar conversas realistas com AI usando Locust + Gemini + Voyager API**

🚀 Boa sorte com os testes!
