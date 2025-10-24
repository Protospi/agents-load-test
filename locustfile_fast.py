import logging
import time
import uuid
import re
import os
import json
import random
import asyncio
from threading import Thread, Lock
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from locust import HttpUser, task, events, constant_pacing
from pyngrok import ngrok
from google import genai
from dotenv import load_dotenv
import requests as req
import uvicorn
from uvicorn import Config, Server
from config import (
    VOYAGER_API_URL, VOYAGER_ENDPOINT, CHANNEL_ID, CLIENT_DOMAIN,
    FLASK_PORT, FLASK_HOST, WEBHOOK_PATH, DEFAULT_MESSAGE, MESSAGE_TYPE,
    WEBHOOK_TIMEOUT, POLLING_INTERVAL, USER_WAIT_TIME,
    LOG_LEVEL, LOG_FORMAT, MAX_RESPONSE_CHARS, CLEAR_WEBHOOKS_AFTER_READ
)
from utils.generate_user_data import OptimizedUserData

# Load environment variables
load_dotenv()


# Configuration Constants
MAX_ITERATIONS = 20  # 15 iterations = 30 messages (15 user + 15 assistant)
INITIAL_MESSAGE = "Olá"

# Configuração de logging
# Create logs folder if it doesn't exist
logs_dir = "logs"
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Setup logging to both file and console
log_file = os.path.join(logs_dir, f"load_test_fast_{time.strftime('%d_%m_%y_%H_%M')}.log")

# Configure root logger
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(log_file),  # Log to file
        logging.StreamHandler()         # Log to console
    ]
)
logger = logging.getLogger(__name__)

# Armazenamento de respostas dos webhooks
webhook_responses = {}
responses_lock = Lock()

# Storage for conversation results
conversation_results = []
results_lock = Lock()

# User ID counter for generating unique user data
user_id_counter = 0
user_id_lock = Lock()

# FastAPI app para receber webhooks
fastapi_app = FastAPI()

# Variável global para armazenar a URL do ngrok
ngrok_url = None


@fastapi_app.post('/responses/{session_id}')
async def receive_webhook(session_id: str, request: Request):
    """Recebe webhook com a resposta da Voyager API"""
    try:
        payload = await request.json()
        
        with responses_lock:
            webhook_responses[session_id] = payload
        
        logger.info(f"✅ Webhook recebido para session_id: {session_id}")
        logger.debug(f"Payload: {payload}")
        print(f"✅ FastAPI: Webhook recebido para session_id: {session_id}")
        
        return JSONResponse(content={"status": "received"}, status_code=200)
    except Exception as e:
        logger.error(f"❌ Erro ao processar webhook: {e}")
        print(f"❌ FastAPI: Erro ao processar webhook: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@fastapi_app.get('/health')
async def health_check():
    """Health check endpoint"""
    return JSONResponse(content={"status": "ok", "responses_count": len(webhook_responses)}, status_code=200)


def start_fastapi():
    """Inicia o servidor FastAPI em uma thread separada"""
    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Configure uvicorn server
    config = Config(
        app=fastapi_app,
        host=FLASK_HOST,
        port=FLASK_PORT,
        log_level="error",
        loop="asyncio"
    )
    server = Server(config)
    
    # Run the server in this thread's event loop
    loop.run_until_complete(server.serve())


def start_ngrok():
    """Inicia o túnel ngrok e retorna a URL pública"""
    global ngrok_url
    
    try:
        # Encerra túneis existentes
        ngrok.kill()
    except:
        pass
    
    # Cria novo túnel
    tunnel = ngrok.connect(FLASK_PORT, bind_tls=True)
    ngrok_url = tunnel.public_url
    
    logger.info("=" * 80)
    logger.info(f"🌐 NGROK URL (FastAPI): {ngrok_url}")
    logger.info("=" * 80)
    print("=" * 80)
    print(f"🌐 NGROK URL (FastAPI): {ngrok_url}")
    print("=" * 80)
    
    return ngrok_url


def save_test_results():
    """Salva os resultados do teste em arquivo JSON"""
    with results_lock:
        if not conversation_results:
            logger.warning("⚠️  No conversation results to save")
            return
        
        # Calculate aggregated statistics
        total_conversations = len(conversation_results)
        successful_conversations = sum(1 for c in conversation_results if c['found_link'])
        total_iterations = sum(c['iterations'] for c in conversation_results)
        total_messages = sum(c['total_messages'] for c in conversation_results)
        total_time = sum(c['total_time_ms'] for c in conversation_results)
        total_cost = sum(c['cost'] for c in conversation_results)
        
        # Gemini token totals
        total_gemini_input = sum(c['gemini_input_tokens'] for c in conversation_results)
        total_gemini_output = sum(c['gemini_output_tokens'] for c in conversation_results)
        
        # Calculate averages
        avg_time = total_time / total_conversations if total_conversations > 0 else 0
        avg_iterations = total_iterations / total_conversations if total_conversations > 0 else 0
        avg_messages = total_messages / total_conversations if total_conversations > 0 else 0
        
        # Build summary
        summary = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_conversations': total_conversations,
            'successful_conversations': successful_conversations,
            'success_rate': f"{(successful_conversations/total_conversations*100):.2f}%" if total_conversations > 0 else "0%",
            'total_iterations': total_iterations,
            'avg_iterations_per_conversation': round(avg_iterations, 2),
            'total_messages': total_messages,
            'avg_messages_per_conversation': round(avg_messages, 2),
            'total_time_ms': round(total_time, 0),
            'avg_time_per_conversation_ms': round(avg_time, 0),
            'gemini_tokens': {
                'model': 'gemini-2.5-flash',
                'total_input_tokens': total_gemini_input,
                'total_output_tokens': total_gemini_output,
                'total_tokens': total_gemini_input + total_gemini_output,
                'cost_usd': round(total_cost, 6),
                'pricing': {
                    'input_per_1m_tokens': '$0.30',
                    'output_per_1m_tokens': '$2.50'
                }
            },
            'total_cost_usd': round(total_cost, 6)
        }
        
        # Create logs folder if it doesn't exist
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # Save to JSON file
        output_file = os.path.join(logs_dir, f"load_test_fast_results_{time.strftime('%d_%m_%y_%H_%M')}.json")
        
        # Create summary list without full message history (already saved in individual files)
        conversations_summary = []
        for conv in conversation_results:
            conv_summary = {
                'session_id': conv['session_id'],
                'timestamp': conv['timestamp'],
                'iterations': conv['iterations'],
                'total_messages': conv['total_messages'],
                'found_link': conv['found_link'],
                'total_time_ms': conv['total_time_ms'],
                'cost': conv['cost']
            }
            if 'error' in conv:
                conv_summary['error'] = conv['error']
            conversations_summary.append(conv_summary)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'summary': summary,
                    'conversations': conversations_summary
                }, f, indent=2, ensure_ascii=False)
            
            logger.info("=" * 80)
            logger.info("📊 TEST RESULTS SUMMARY (FASTAPI)")
            logger.info("=" * 80)
            logger.info(f"✅ Total conversations: {total_conversations}")
            logger.info(f"🎯 Successful (link found): {successful_conversations} ({summary['success_rate']})")
            logger.info(f"📈 Total iterations: {total_iterations} (avg: {summary['avg_iterations_per_conversation']})")
            logger.info(f"💬 Total messages: {total_messages} (avg: {summary['avg_messages_per_conversation']})")
            logger.info(f"⏱️  Total time: {total_time/1000:.1f}s (avg: {avg_time/1000:.1f}s per conversation)")
            logger.info(f"💰 Total cost: ${total_cost:.6f}")
            logger.info(f"💾 Results saved to: {output_file}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ Error saving results: {e}")


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Evento executado quando o Locust é iniciado"""
    logger.info("🚀 Iniciando sistema de teste de carga com FastAPI...")
    print("🚀 Iniciando sistema de teste de carga com FastAPI...")
    
    # Inicia FastAPI em thread separada
    logger.info("📡 Iniciando servidor FastAPI...")
    print("📡 Iniciando servidor FastAPI...")
    fastapi_thread = Thread(target=start_fastapi, daemon=True)
    fastapi_thread.start()
    
    # Aguarda FastAPI iniciar
    print("⏳ Aguardando FastAPI inicializar (2 segundos)...")
    time.sleep(2)
    
    # Inicia ngrok
    logger.info("🔗 Iniciando túnel ngrok...")
    print("🔗 Iniciando túnel ngrok...")
    start_ngrok()
    
    logger.info("✅ Sistema pronto para receber requisições!")
    print("✅ Sistema pronto para receber requisições!")


@events.quitting.add_listener
def on_locust_quit(environment, **kwargs):
    """Evento executado quando o Locust é encerrado"""
    logger.info("🛑 Encerrando ngrok...")
    try:
        ngrok.kill()
    except:
        pass
    
    # Save results to JSON
    save_test_results()


class VoyagerUser(HttpUser):
    """Usuário virtual que simula uma conversa completa com Voyager via Gemini"""
    
    # URL da API Voyager
    host = VOYAGER_API_URL
    
    # Tempo de espera entre conversas completas
    wait_time = constant_pacing(USER_WAIT_TIME)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_session_id = None
        self.gemini_client = None
        self.gemini_chat = None
        self.conversation_completed = False  # Flag to ensure only one conversation per user
        
        # Generate unique user ID and data
        global user_id_counter
        with user_id_lock:
            user_id_counter += 1
            self.user_id = user_id_counter
        
        # Generate randomized user data
        self.user_data = OptimizedUserData.generate_data(self.user_id)
        logger.info(f"👤 User {self.user_id} created - Name: {self.user_data['nome']}, Phone: {self.user_data['telefone']}, Email: {self.user_data['email']}, CPF: {self.user_data['cpf_formatted']}")
        
    def on_start(self):
        """Inicializa o cliente Gemini quando o usuário começa"""
        try:
            # Randomly select one of the three personas for this user
            self.persona_file = f'personas/persona_{random.randint(1,3)}.txt'
            
            # Load the selected persona
            try:
                with open(self.persona_file, 'r') as p:
                    persona_content = p.read()
            except FileNotFoundError:
                logger.error(f"❌ Persona file not found: {self.persona_file}")
                persona_content = ""
            
            # Print user data before replacement
            print(f"\n📋 User data for replacement - Phone: {self.user_data['telefone']}, Email: {self.user_data['email']}, CPF: {self.user_data['cpf_formatted']}")
            
            # Customize persona with generated user data based on persona file
            # Note: CPF in personas is unformatted (numbers only), but we replace with formatted version
            customized_persona = persona_content

            if self.persona_file == 'personas/persona_1.txt':
                customized_persona = customized_persona.replace("5531988776655", self.user_data['telefone'])
                customized_persona = customized_persona.replace("kataryna.smart@smarttalks.ai", self.user_data['email'])
                customized_persona = customized_persona.replace("87325940548", self.user_data['cpf_formatted'])
            elif self.persona_file == 'personas/persona_2.txt':
                customized_persona = customized_persona.replace("5521987654321", self.user_data['telefone'])
                customized_persona = customized_persona.replace("talliz.smart@smarttalks.ai", self.user_data['email'])
                customized_persona = customized_persona.replace("12345678901", self.user_data['cpf_formatted'])
            elif self.persona_file == 'personas/persona_3.txt':
                customized_persona = customized_persona.replace("5511976543210", self.user_data['telefone'])
                customized_persona = customized_persona.replace("edman.smart@smarttalks.ai", self.user_data['email'])
                customized_persona = customized_persona.replace("98765432100", self.user_data['cpf_formatted'])
            else:
                logger.error(f"❌ Unknown persona file: {self.persona_file}")
                return
            
            # Print the final customized persona for debugging
            print("=" * 80)
            print(f"🎭 FINAL CUSTOMIZED PERSONA for user {self.user_id}:")
            print("=" * 80)
            print(customized_persona)
            print("=" * 80)
            print()
            
            # Store client as instance variable to prevent it from being closed
            self.gemini_client = genai.Client(
                api_key=os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')
            )
            self.gemini_chat = self.gemini_client.chats.create(
                model="gemini-2.5-flash",
                config=genai.types.GenerateContentConfig(system_instruction=customized_persona)
            )
            logger.info(f"✅ Gemini chat session created for user {self.user_id} with persona: {self.persona_file} and customized data")
        except Exception as e:
            logger.error(f"❌ Error creating Gemini session: {e}")
            self.gemini_chat = None
            self.gemini_client = None
    
    def on_stop(self):
        """Clean up Gemini client when user stops"""
        try:
            if hasattr(self, 'gemini_client') and self.gemini_client:
                self.gemini_client.close()
                logger.info("✅ Gemini client closed")
        except Exception as e:
            logger.error(f"⚠️  Error closing Gemini client: {e}")
    
    def wait_for_webhook(self, session_id, timeout=WEBHOOK_TIMEOUT):
        """
        Aguarda a resposta do webhook por polling
        
        Args:
            session_id: ID da sessão para verificar
            timeout: Tempo máximo de espera em segundos
            
        Returns:
            dict: Payload recebido ou None se timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with responses_lock:
                if session_id in webhook_responses:
                    response = webhook_responses[session_id]
                    # Remove da memória após recuperar
                    if CLEAR_WEBHOOKS_AFTER_READ:
                        del webhook_responses[session_id]
                    return response
            
            # Aguarda antes de verificar novamente
            time.sleep(POLLING_INTERVAL)
        
        return None
    
    def extract_voyager_messages(self, webhook_response):
        """
        Extract messages from Voyager webhook response
        Returns list of messages with role and content
        Handles both text and image messages
        """
        messages = webhook_response.get('messages', [])
        extracted = []
        
        for msg in messages:
            role = msg.get('role', 'assistant')
            
            # Handle text messages
            if msg.get('type') == 'text' or msg.get('text'):
                text = msg.get('text', '')
                if text:
                    extracted.append({
                        'role': role,
                        'content': text
                    })
            
            # Handle image messages
            elif msg.get('type') == 'media' and msg.get('media', {}).get('type') == 'image':
                image_link = msg.get('media', {}).get('link', '')
                if image_link:
                    content = f"Estou enviando essa imagem como link para você ver link: {image_link}"
                    extracted.append({
                        'role': role,
                        'content': content
                    })
        
        return extracted
    
    def save_conversation_log(self, conversation_data, gemini_input_tokens, gemini_output_tokens, total_cost):
        """
        Save individual conversation to JSON file
        """
        # Create logs folder if it doesn't exist
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # Generate filename with timestamp and session_id (short version)
        short_session = conversation_data['session_id'][:8]
        timestamp = time.strftime('%d_%m_%y_%H_%M_%S')
        output_file = os.path.join(logs_dir, f"conversation_fast_{short_session}_{timestamp}.json")
        
        # Build conversation log similar to voyager_chat.py
        log_data = {
            'summary': {
                'session_id': conversation_data['session_id'],
                'user_id': conversation_data.get('user_id'),
                'user_data': conversation_data.get('user_data', {}),
                'iterations': conversation_data['iterations'],
                'found_link': conversation_data['found_link'],
                'total_messages': conversation_data['total_messages'],
                'timestamp': conversation_data['timestamp'],
                'total_time_ms': conversation_data['total_time_ms'],
                'voyager_tokens': {
                    'model': 'gpt-4 (assumed)',
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'total_tokens': 0,
                    'cost_usd': 0.0,
                    'pricing': {
                        'input_per_1m_tokens': '$2.00',
                        'output_per_1m_tokens': '$8.00'
                    }
                },
                'gemini_tokens': {
                    'model': 'gemini-2.5-flash',
                    'input_tokens': gemini_input_tokens,
                    'output_tokens': gemini_output_tokens,
                    'total_tokens': gemini_input_tokens + gemini_output_tokens,
                    'cost_usd': round(total_cost, 6),
                    'pricing': {
                        'input_per_1m_tokens': '$0.30',
                        'output_per_1m_tokens': '$2.50'
                    }
                },
                'total_cost_usd': round(total_cost, 6)
            },
            'messages': conversation_data['messages']
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Conversation saved to: {output_file}")
        except Exception as e:
            logger.error(f"❌ Error saving conversation log: {e}")
    
    def send_to_voyager(self, message_text, iteration_suffix):
        """
        Send message to Voyager and wait for response
        Uses same clientIdentifier for entire conversation
        Returns webhook response or None
        """
        # Unique webhook session ID for this specific request
        webhook_session_id = f"{self.base_session_id}_{iteration_suffix}"
        webhook_url = f"{ngrok_url}{WEBHOOK_PATH}/{webhook_session_id}"
        
        payload = {
            "type": "text",
            "text": message_text,
            "channelId": CHANNEL_ID,
            "clientIdentifier": f"{self.base_session_id}{CLIENT_DOMAIN}",  # Same for entire conversation
            "webhook": webhook_url
        }
        
        print(f"📤 FastAPI: Sending to Voyager with webhook URL: {webhook_url}")
        logger.info(f"📤 Sending to Voyager with webhook URL: {webhook_url}")
        
        start_time = time.time()
        
        try:
            response = self.client.post(
                VOYAGER_ENDPOINT,
                json=payload,
                headers={"Content-Type": "application/json"},
                name="Voyager Message"
            )
            
            if response.status_code not in [200, 201, 202]:
                logger.error(f"❌ Voyager API error - Status: {response.status_code}")
                print(f"❌ FastAPI: Voyager API error - Status: {response.status_code}")
                return None
            
            # Wait for webhook response
            logger.info(f"⏳ Waiting for webhook response (timeout: {WEBHOOK_TIMEOUT}s)")
            webhook_response = self.wait_for_webhook(webhook_session_id, timeout=WEBHOOK_TIMEOUT)
            
            # Log webhook response status
            if webhook_response:
                logger.info(f"✅ Got webhook response in {(time.time() - start_time):.1f}s")
                logger.debug(f"Webhook response: {json.dumps(webhook_response)[:500]}")
            else:
                logger.error(f"❌ Webhook timeout after {WEBHOOK_TIMEOUT}s")
            
            # Fire custom event for webhook
            total_time = (time.time() - start_time) * 1000
            if webhook_response:
                events.request.fire(
                    request_type="WEBHOOK",
                    name="Voyager Webhook",
                    response_time=total_time,
                    response_length=len(str(webhook_response)),
                    exception=None,
                    context={}
                )
            else:
                events.request.fire(
                    request_type="WEBHOOK",
                    name="Voyager Webhook",
                    response_time=total_time,
                    response_length=0,
                    exception=Exception("Webhook timeout"),
                    context={}
                )
            
            return webhook_response
            
        except Exception as e:
            logger.error(f"❌ Error sending to Voyager: {e}")
            return None
    
    @task
    def run_complete_conversation(self):
        """Runs a complete conversation between Gemini and Voyager"""
        
        # Only run one conversation per user
        if self.conversation_completed:
            # User already completed their conversation, just wait
            return
        
        if not self.gemini_chat:
            logger.error("❌ Gemini chat not initialized, skipping conversation")
            self.conversation_completed = True
            return
        
        # Generate base session ID for this conversation
        self.base_session_id = str(uuid.uuid4())
        
        # Initialize conversation tracking
        conversation_messages = []
        iteration_count = 0
        current_message = INITIAL_MESSAGE
        found_link = False
        
        # Token tracking
        gemini_input_tokens = 0
        gemini_output_tokens = 0
        
        conversation_start_time = time.time()
        
        print(f"\n{'='*80}")
        print(f"🎬 STARTING CONVERSATION (FastAPI) - Base Session ID: {self.base_session_id}")
        print(f"{'='*80}\n")
        logger.info(f"🎬 Starting conversation - Base Session ID: {self.base_session_id}")
        
        try:
            # Main conversation loop
            while iteration_count < MAX_ITERATIONS and not found_link:
                iteration_count += 1
                
                logger.info(f"🔄 Iteration {iteration_count}/{MAX_ITERATIONS} - Session: {self.base_session_id}")
                
                # A. Send message to Voyager
                logger.info(f"📤 Sending to Voyager (iteration {iteration_count}): {current_message[:100]}...")
                voyager_response = self.send_to_voyager(current_message, iteration_count)
                
                if not voyager_response:
                    print(f"❌ VOYAGER WEBHOOK TIMEOUT (iteration {iteration_count}) - Breaking conversation")
                    logger.error(f"❌ Failed to get response from Voyager (iteration {iteration_count}) - Ending conversation")
                    logger.error(f"   Message sent: {current_message[:200]}")
                    break
                
                # B. Extract messages from Voyager response
                voyager_messages = self.extract_voyager_messages(voyager_response)
                logger.info(f"📨 Received {len(voyager_messages)} message(s) from Voyager")
                
                if not voyager_messages:
                    print(f"❌ NO MESSAGES IN VOYAGER RESPONSE (iteration {iteration_count})")
                    print(f"   Full Voyager response: {json.dumps(voyager_response, indent=2)[:500]}")
                    logger.error(f"❌ No messages in Voyager response (iteration {iteration_count}) - Ending conversation")
                    logger.error(f"   Voyager response: {str(voyager_response)[:500]}")
                    
                    # Check if there's a 'text' field instead of 'messages'
                    if isinstance(voyager_response, dict):
                        # Try to extract text from different possible formats
                        text_content = voyager_response.get('text') or voyager_response.get('content') or voyager_response.get('message')
                        if text_content:
                            print(f"   Found text content in alternative field: {text_content[:200]}")
                            # Create a synthetic message from this text
                            voyager_messages = [{'role': 'assistant', 'content': text_content}]
                            logger.info(f"   ✅ Recovered message from alternative field")
                        else:
                            print(f"   Response keys: {list(voyager_response.keys())}")
                            break
                    else:
                        break
                
                # Add user message to conversation history
                conversation_messages.append({
                    'role': 'user',
                    'content': current_message
                })
                
                # Add Voyager assistant messages to conversation history
                for msg in voyager_messages:
                    conversation_messages.append(msg)
                
                # C. Check for HTTP link in Voyager response
                for msg in voyager_messages:
                    voyager_links = re.findall(r'https?://[^\s]+', msg['content'])
                    if voyager_links:
                        found_link = True
                        logger.info(f"🎉 HTTP link found in Voyager message: {voyager_links[0]}")
                        logger.debug(f"Full message with link: {msg['content']}")
                        break
                
                if found_link:
                    break
                
                # D. Get the last assistant message to send to Gemini
                last_voyager_message = voyager_messages[-1]['content'] if voyager_messages else ""
                
                if not last_voyager_message:
                    logger.error(f"❌ No assistant message to send to Gemini (iteration {iteration_count})")
                    break
                
                logger.info(f"🤖 Sending to Gemini (iteration {iteration_count}): {last_voyager_message[:100]}...")
                
                # E. Send to Gemini (with retry on failure)
                max_gemini_retries = 3
                gemini_success = False
                
                for retry_attempt in range(max_gemini_retries):
                    try:
                        gemini_start = time.time()
                        logger.info(f"⏳ Sending message to Gemini (attempt {retry_attempt + 1}/{max_gemini_retries})")
                        gemini_response = self.gemini_chat.send_message(last_voyager_message)
                        gemini_message = gemini_response.text
                        gemini_time = (time.time() - gemini_start) * 1000
                        logger.info(f"✅ Got Gemini response in {gemini_time/1000:.1f}s")
                        
                        # Extract Gemini token usage
                        if hasattr(gemini_response, 'usage_metadata') and gemini_response.usage_metadata:
                            gemini_input_tokens += getattr(gemini_response.usage_metadata, 'prompt_token_count', 0)
                            gemini_output_tokens += getattr(gemini_response.usage_metadata, 'candidates_token_count', 0)
                        
                        # Fire custom event for Gemini
                        events.request.fire(
                            request_type="GEMINI",
                            name="Gemini Response",
                            response_time=gemini_time,
                            response_length=len(gemini_message),
                            exception=None,
                            context={}
                        )
                        
                        logger.info(f"✅ Gemini responded (iteration {iteration_count}): {gemini_message[:100]}...")
                        gemini_success = True
                        break  # Success, exit retry loop
                        
                    except Exception as e:
                        if retry_attempt < max_gemini_retries - 1:
                            # Not the last attempt, wait and retry
                            logger.warning(f"⚠️  Gemini API error (attempt {retry_attempt + 1}/{max_gemini_retries}): {e}")
                            logger.info(f"   Waiting 1 second before retry...")
                            time.sleep(1)
                        else:
                            # Last attempt failed
                            logger.error(f"❌ Gemini API error (all {max_gemini_retries} attempts failed): {e}")
                            logger.error(f"   Iteration: {iteration_count}, Messages so far: {len(conversation_messages)}")
                            events.request.fire(
                                request_type="GEMINI",
                                name="Gemini Response",
                                response_time=0,
                                response_length=0,
                                exception=e,
                                context={}
                            )
                
                # End conversation if Gemini failed after all retries
                if not gemini_success:
                    print(f"❌ GEMINI FAILED AFTER RETRIES (iteration {iteration_count}) - Breaking conversation")
                    logger.error(f"❌ Gemini failed after {max_gemini_retries} retries (iteration {iteration_count}) - Ending conversation")
                    break
                
                # F. Check for HTTP link in Gemini response
                gemini_links = re.findall(r'https?://[^\s]+', gemini_message)
                if gemini_links:
                    found_link = True
                    logger.info(f"🎉 HTTP link found in Gemini message!")
                    break
                
                # G. Prepare next iteration
                current_message = gemini_message
                
                # Small delay between iterations
                time.sleep(0.5)
            
            # Log why conversation ended
            print(f"\n{'='*80}")
            if found_link:
                print(f"✅ CONVERSATION ENDED: Link found (iteration {iteration_count})")
                logger.info(f"✅ Conversation ended: Link found (iteration {iteration_count})")
            elif iteration_count >= MAX_ITERATIONS:
                print(f"⚠️  CONVERSATION ENDED: Max iterations reached ({iteration_count}/{MAX_ITERATIONS})")
                logger.warning(f"⚠️  Conversation ended: Max iterations reached ({iteration_count}/{MAX_ITERATIONS})")
            else:
                print(f"⚠️  CONVERSATION ENDED: Broke early at iteration {iteration_count}/{MAX_ITERATIONS}")
                logger.warning(f"⚠️  Conversation ended: Broke early at iteration {iteration_count}/{MAX_ITERATIONS}")
            print(f"{'='*80}\n")
            
            # Conversation complete
            total_conversation_time = (time.time() - conversation_start_time) * 1000
            
            # Calculate costs
            gemini_input_cost = (gemini_input_tokens / 1_000_000) * 0.30
            gemini_output_cost = (gemini_output_tokens / 1_000_000) * 2.50
            total_cost = gemini_input_cost + gemini_output_cost
            
            logger.info(
                f"✅ Conversation complete - Session: {self.base_session_id} - "
                f"Iterations: {iteration_count} - Messages: {len(conversation_messages)} - "
                f"Time: {total_conversation_time:.0f}ms - Cost: ${total_cost:.6f} - "
                f"Link found: {found_link}"
            )
            
            # Store conversation result
            conversation_data = {
                'session_id': self.base_session_id,
                'user_id': self.user_id,
                'user_data': {
                    'nome': self.user_data['nome'],
                    'telefone': self.user_data['telefone'],
                    'email': self.user_data['email'],
                    'cpf': self.user_data['cpf_formatted']
                },
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'iterations': iteration_count,
                'total_messages': len(conversation_messages),
                'found_link': found_link,
                'total_time_ms': round(total_conversation_time, 0),
                'gemini_input_tokens': gemini_input_tokens,
                'gemini_output_tokens': gemini_output_tokens,
                'cost': total_cost,
                'messages': conversation_messages
            }
            
            with results_lock:
                conversation_results.append(conversation_data)
            
            # Save individual conversation log
            self.save_conversation_log(conversation_data, gemini_input_tokens, gemini_output_tokens, total_cost)
            
            # Mark conversation as completed
            self.conversation_completed = True
            
            # Fire custom event for complete conversation
            events.request.fire(
                request_type="CONVERSATION",
                name="Complete Conversation",
                response_time=total_conversation_time,
                response_length=len(conversation_messages),
                exception=None if found_link else Exception("No link found"),
                context={}
            )
            
        except Exception as e:
            logger.error(f"💥 Unexpected error in conversation: {e}")
            import traceback
            traceback.print_exc()
            
            # Store failed conversation result
            total_conversation_time = (time.time() - conversation_start_time) * 1000
            error_cost = (gemini_input_tokens / 1_000_000) * 0.30 + (gemini_output_tokens / 1_000_000) * 2.50
            
            conversation_data = {
                'session_id': self.base_session_id,
                'user_id': self.user_id,
                'user_data': {
                    'nome': self.user_data['nome'],
                    'telefone': self.user_data['telefone'],
                    'email': self.user_data['email'],
                    'cpf': self.user_data['cpf_formatted']
                },
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'iterations': iteration_count,
                'total_messages': len(conversation_messages),
                'found_link': False,
                'total_time_ms': round(total_conversation_time, 0),
                'gemini_input_tokens': gemini_input_tokens,
                'gemini_output_tokens': gemini_output_tokens,
                'cost': error_cost,
                'error': str(e),
                'messages': conversation_messages
            }
            
            with results_lock:
                conversation_results.append(conversation_data)
            
            # Save individual conversation log even for failed conversations
            self.save_conversation_log(conversation_data, gemini_input_tokens, gemini_output_tokens, error_cost)
            
            # Mark conversation as completed even on error
            self.conversation_completed = True
            
            # Fire failure event
            events.request.fire(
                request_type="CONVERSATION",
                name="Complete Conversation",
                response_time=total_conversation_time,
                response_length=0,
                exception=e,
                context={}
            )

