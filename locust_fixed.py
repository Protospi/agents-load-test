import logging
import time
import uuid
import re
import os
import json
import random
from threading import Thread, Lock
from flask import Flask, request, jsonify
from locust import HttpUser, task, events, constant_pacing
from pyngrok import ngrok
from dotenv import load_dotenv
import requests as req
from config import (
    VOYAGER_API_URL, VOYAGER_ENDPOINT, CHANNEL_ID, CLIENT_DOMAIN,
    FLASK_PORT, FLASK_HOST, WEBHOOK_PATH, DEFAULT_MESSAGE, MESSAGE_TYPE,
    WEBHOOK_TIMEOUT, POLLING_INTERVAL, USER_WAIT_TIME,
    LOG_LEVEL, LOG_FORMAT, MAX_RESPONSE_CHARS, CLEAR_WEBHOOKS_AFTER_READ
)
from utils.generate_user_data import OptimizedUserData

# Load environment variables
load_dotenv()

# Load fixed user messages from file
FIXED_USER_MESSAGES = []
try:
    with open('fixed_conversation/user_messages.txt', 'r', encoding='utf-8') as f:
        FIXED_USER_MESSAGES = json.load(f)
    print(f"✅ Loaded {len(FIXED_USER_MESSAGES)} fixed user messages")
except FileNotFoundError:
    print("❌ Error: fixed_conversation/user_messages.txt not found!")
    FIXED_USER_MESSAGES = ["Olá"]  # Fallback
except json.JSONDecodeError as e:
    print(f"❌ Error parsing user_messages.txt: {e}")
    FIXED_USER_MESSAGES = ["Olá"]  # Fallback

# Configuration Constants
MAX_ITERATIONS = len(FIXED_USER_MESSAGES) if FIXED_USER_MESSAGES else 20

# Configuração de logging
# Create logs folder if it doesn't exist
logs_dir = "logs"
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Setup logging to both file and console
log_file = os.path.join(logs_dir, f"load_test_{time.strftime('%d_%m_%y_%H_%M')}.log")

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

# Personas will be loaded randomly for each user in on_start method

# Armazenamento de respostas dos webhooks
webhook_responses = {}
responses_lock = Lock()

# Storage for conversation results
conversation_results = []
results_lock = Lock()

# User ID counter for generating unique user data
user_id_counter = 0
user_id_lock = Lock()

# Flask app para receber webhooks
flask_app = Flask(__name__)
flask_app.logger.setLevel(logging.WARNING)

# Variável global para armazenar a URL do ngrok
ngrok_url = None


@flask_app.route('/responses/<session_id>', methods=['POST'])
def receive_webhook(session_id):
    """Recebe webhook com a resposta da Voyager API"""
    try:
        payload = request.get_json()
        
        with responses_lock:
            webhook_responses[session_id] = payload
        
        logger.info(f"✅ Webhook recebido para session_id: {session_id}")
        logger.debug(f"Payload: {payload}")
        
        return jsonify({"status": "received"}), 200
    except Exception as e:
        logger.error(f"❌ Erro ao processar webhook: {e}")
        return jsonify({"error": str(e)}), 500


@flask_app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "responses_count": len(webhook_responses)}), 200


def start_flask():
    """Inicia o servidor Flask em uma thread separada"""
    flask_app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False, use_reloader=False)


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
    logger.info(f"🌐 NGROK URL: {ngrok_url}")
    logger.info("=" * 80)
    
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
            'mode': 'fixed_messages',
            'fixed_messages_count': len(FIXED_USER_MESSAGES)
        }
        
        # Create logs folder if it doesn't exist
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # Save to JSON file
        output_file = os.path.join(logs_dir, f"load_test_results_{time.strftime('%d_%m_%y_%H_%M')}.json")
        
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
            logger.info("📊 TEST RESULTS SUMMARY")
            logger.info("=" * 80)
            logger.info(f"✅ Total conversations: {total_conversations}")
            logger.info(f"🎯 Successful (link found): {successful_conversations} ({summary['success_rate']})")
            logger.info(f"📈 Total iterations: {total_iterations} (avg: {summary['avg_iterations_per_conversation']})")
            logger.info(f"💬 Total messages: {total_messages} (avg: {summary['avg_messages_per_conversation']})")
            logger.info(f"⏱️  Total time: {total_time/1000:.1f}s (avg: {avg_time/1000:.1f}s per conversation)")
            logger.info(f"📝 Mode: Fixed messages ({len(FIXED_USER_MESSAGES)} messages)")
            logger.info(f"💾 Results saved to: {output_file}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ Error saving results: {e}")


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Evento executado quando o Locust é iniciado"""
    logger.info("🚀 Iniciando sistema de teste de carga...")
    
    # Inicia Flask em thread separada
    logger.info("📡 Iniciando servidor Flask...")
    flask_thread = Thread(target=start_flask, daemon=True)
    flask_thread.start()
    
    # Aguarda Flask iniciar
    time.sleep(2)
    
    # Inicia ngrok
    logger.info("🔗 Iniciando túnel ngrok...")
    start_ngrok()
    
    logger.info("✅ Sistema pronto para receber requisições!")


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
    """Usuário virtual que simula uma conversa completa com Voyager usando mensagens fixas"""
    
    # URL da API Voyager
    host = VOYAGER_API_URL
    
    # Tempo de espera entre conversas completas
    wait_time = constant_pacing(USER_WAIT_TIME)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_session_id = None
        self.conversation_completed = False  # Flag to ensure only one conversation per user
        self.message_index = 0  # Track current position in fixed messages
        
        # Generate unique user ID and data
        global user_id_counter
        with user_id_lock:
            user_id_counter += 1
            self.user_id = user_id_counter
        
        # Generate randomized user data
        self.user_data = OptimizedUserData.generate_data(self.user_id)
        logger.info(f"👤 User {self.user_id} created - Name: {self.user_data['nome']}, Phone: {self.user_data['telefone']}, Email: {self.user_data['email']}, CPF: {self.user_data['cpf_formatted']}")
        
    def on_start(self):
        """Initialize user session"""
        logger.info(f"🚀 User {self.user_id} starting with {len(FIXED_USER_MESSAGES)} fixed messages")
        logger.info(f"📋 User data - Phone: {self.user_data['telefone']}, Email: {self.user_data['email']}, CPF: {self.user_data['cpf_formatted']}")
    
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
    
    def save_conversation_log(self, conversation_data):
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
        output_file = os.path.join(logs_dir, f"conversation_{short_session}_{timestamp}.json")
        
        # Build conversation log
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
                'mode': 'fixed_messages',
                'fixed_messages_used': len(FIXED_USER_MESSAGES)
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
        """Runs a complete conversation using fixed messages"""
        
        # Only run one conversation per user
        if self.conversation_completed:
            # User already completed their conversation, just wait
            return
        
        if not FIXED_USER_MESSAGES:
            logger.error("❌ No fixed messages loaded, skipping conversation")
            self.conversation_completed = True
            return
        
        # Generate base session ID for this conversation
        self.base_session_id = str(uuid.uuid4())
        
        # Initialize conversation tracking
        conversation_messages = []
        iteration_count = 0
        found_link = False
        
        conversation_start_time = time.time()
        
        print(f"\n{'='*80}")
        print(f"🎬 STARTING CONVERSATION - Base Session ID: {self.base_session_id}")
        print(f"{'='*80}\n")
        logger.info(f"🎬 Starting conversation - Base Session ID: {self.base_session_id}")
        
        try:
            # Main conversation loop - iterate through fixed messages
            while self.message_index < len(FIXED_USER_MESSAGES) and not found_link:
                iteration_count += 1
                
                # Get current message from fixed list
                current_message = FIXED_USER_MESSAGES[self.message_index]
                self.message_index += 1
                
                logger.info(f"🔄 Iteration {iteration_count}/{len(FIXED_USER_MESSAGES)} - Session: {self.base_session_id}")
                
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
                
                # C. Check for payment link in Voyager response
                for msg in voyager_messages:
                    voyager_links = re.findall(r'https?://[^\s]+', msg['content'])
                    for link in voyager_links:
                        if link.startswith('https://pay.smarttalks.ai'):
                            found_link = True
                            logger.info(f"🎉 Payment link found in Voyager message: {link}")
                            logger.debug(f"Full message with link: {msg['content']}")
                            break
                    if found_link:
                        break
                
                if found_link:
                    break
                
                # Small delay between iterations
                time.sleep(0.5)
            
            # Log why conversation ended
            print(f"\n{'='*80}")
            if found_link:
                print(f"✅ CONVERSATION ENDED: Link found (iteration {iteration_count})")
                logger.info(f"✅ Conversation ended: Link found (iteration {iteration_count})")
            elif self.message_index >= len(FIXED_USER_MESSAGES):
                print(f"⚠️  CONVERSATION ENDED: All messages sent ({iteration_count}/{len(FIXED_USER_MESSAGES)})")
                logger.warning(f"⚠️  Conversation ended: All messages sent ({iteration_count}/{len(FIXED_USER_MESSAGES)})")
            else:
                print(f"⚠️  CONVERSATION ENDED: Broke early at iteration {iteration_count}/{len(FIXED_USER_MESSAGES)}")
                logger.warning(f"⚠️  Conversation ended: Broke early at iteration {iteration_count}/{len(FIXED_USER_MESSAGES)}")
            print(f"{'='*80}\n")
            
            # Conversation complete
            total_conversation_time = (time.time() - conversation_start_time) * 1000
            
            logger.info(
                f"✅ Conversation complete - Session: {self.base_session_id} - "
                f"Iterations: {iteration_count} - Messages: {len(conversation_messages)} - "
                f"Time: {total_conversation_time:.0f}ms - "
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
                'messages': conversation_messages
            }
            
            with results_lock:
                conversation_results.append(conversation_data)
            
            # Save individual conversation log
            self.save_conversation_log(conversation_data)
            
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
                'error': str(e),
                'messages': conversation_messages
            }
            
            with results_lock:
                conversation_results.append(conversation_data)
            
            # Save individual conversation log even for failed conversations
            self.save_conversation_log(conversation_data)
            
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

