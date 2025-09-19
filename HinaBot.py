from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters
import re, json, os, shutil
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from datetime import date
from youtube_transcript_api import YouTubeTranscriptApi
from pytubefix import YouTube

#Constant
BLUE_ARCHIVE_COLOR = HexColor("#0098e6")
DARK_BLUE_COLOR = HexColor("#003c7d")
BACKGROUND_COLOR = HexColor("#f0f4f7")
NAME = "Sensei" #Use your name
PERSONALITY = "Unknown" #add your own personality
BOT_TOKEN = "-" #add the telegram bot token
API_KEY= "-" #add the API key, in this code I use Gemini
HISTORY_FILE = 'conversation_history_hina.json'
MAX_HISTORY_LENGTH = 6144

conversation_histories = {}
output_filename = f'Mission_Brief_{date.today()}.pdf'

client = genai.Client(api_key=API_KEY)

def get_video_id(url):
    """
    Extracts video ID from various YouTube URL formats.
    """
    regex = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
    match = re.search(regex, url)
    if match:
        return match.group(1)
    return None

def cleanMD(text: str) -> str:
    # This function escapes special characters for Telegram's MarkdownV2.
    # Note: It intentionally does not escape '*' to allow for bolding.
    escape_chars = r'\_[]()~`>#+-=|{}.!'
    # Escape all characters except for '*'
    text = re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
    return text

def sanitize_for_file(text: str) -> str:
    replacements = {
        '’': "'",
        '‘': "'",
        '“': '"',
        '”': '"',
        '—': '--',
        '…': '...',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def trim(text: str) -> str:
    last_punc_pos = -1
    for punc in ['.', '!', '?']:
        pos = text.rfind(punc)
        if pos > last_punc_pos:
            last_punc_pos = pos
    if last_punc_pos != -1:
        return text[:last_punc_pos + 1]
    return text

def remove_user(text: str) -> str:
    match = re.search(r'\n[A-Z][a-zA-Z\s]*:', text)
    if match:
        return text[:match.start()]
    return text

def save_history():
    '''
    Save history to HISTORY_FILE
    '''
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(conversation_histories, f, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"Error saving history: {e}")

def load_history():
    '''
    Load history from HISTORY_FILE
    '''
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading history: {e}")
        return {}

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_name = message.from_user.first_name

    should_respond = False
    group = False
    pdf = False
    is_sega = False
    video_url = None
    cleaned_text = message.text
    
    if update.message.chat.type == 'private':
        '''
        This is to check if the sender is me
        '''
        chat_id = str(message.chat.id)
        is_sega = user_name == "Seagata"
        print (f"Is it Sega? {is_sega}")
        print(f"New Message From {user_name}")
        print(f"Message: {message}")
        should_respond = True
        if "PDF it" in cleaned_text:
            pdf = True
    elif "@seagatahinabot" in cleaned_text:
        '''
        To check if the bot is tagged
        '''
        chat_id = str(message.chat_id)
        group = True
        should_respond = True

    if not should_respond:
        return

    if "summarize this" or "what is your opinion" in cleaned_text:
        parts = cleaned_text.split()
        for part in parts:
            if "youtube.com" in part or "youtu.be" in part:
                video_url = part
                break

    user_prompt = f"{user_name}: {cleaned_text}"
    current_history = conversation_histories.get(chat_id, "")
    
    try:
        print("Commencing Process")
        if pdf and is_sega:
            print("Task: PDF & Email")
            await update.message.reply_text(cleanMD("Okay Sensei."), parse_mode='MarkdownV2')
            response = client.models.generate_content(
                model="gemini-2.5-pro",
                contents= f"Act as Sorasaki Hina from Blue Archive to help the Sensei(user), as his Asssistant for managing his project and job, the core task is to give Sensei(user) the run down based on the given task, and then rearrange the task for the most optimal way using all context provided, and giving tips & advice to ensure the smoothness of the task, add the additional in game lore as context to make the result a good roleplay. Here is the Sensei(user) personality {PERSONALITY}. Here is the task {user_prompt}. Make sure the responses are as human as possible by not adding symbol or anything that imply its like a machine while giving a short and concise response, for a good practice use {NAME}-Sensei or Sensei to refer to user. The response should be in a markdown format and secretary format and be able to converted into .md, it should have To, From, and Subject (all the comments you have should be put into the P.S.)",
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=-1),
                    temperature=0.95
                ),
            )

            sanitized_text = sanitize_for_file(response.text)
            with open("response.txt", "w+", encoding='utf-8') as f:
                f.write(sanitized_text)

            shutil.copyfile("response.txt", "response.md")
            
            try:
                if os.path.exists("response.md"):
                    os.system("python createPDF.py")
                    os.system("python sendEmail.py")
            except FileNotFoundError:
                print("Error: 'response.md' not found.")
                exit()

            response_text = "It's Done"

            pdf = False

        elif "what is your opinion" in cleaned_text:
            print("Process: Opinion")
            if not video_url:
                response_text = "Sensei, please provide a YouTube link."
            else:
                await update.message.reply_text(cleanMD("Hmmmm..."), parse_mode='MarkdownV2')
                print(video_url)
                yt = YouTube(video_url)
                video_title = yt.title
                try:
                    video_id = get_video_id(video_url)
                    ytt_api = YouTubeTranscriptApi()
                    transcript = ytt_api.fetch(video_id)
                    print("before gemini")
                    if transcript:
                        summary_response = client.models.generate_content(
                            model="gemini-2.5-pro",
                            contents=f"You are Sorasaki Hina. here is the message {user_prompt}, give your opinion of the video the following transcript concisely for Sensei. Here is the transcript/lyrics: {transcript}, and here is the title {video_title}. If you think the conversation need to answered with 2 or more chat (because it is more than 20 words or different answer/context) add // on the middle of the response",
                            config=types.GenerateContentConfig(
                                temperature=0.7
                            ),
                        )
                        response_text = summary_response.text
                except Exception as e:
                    summary_response = client.models.generate_content(
                        model="gemini-2.5-pro",
                        contents=f"You are Sorasaki Hina. here is the message {user_prompt}, give your opinion of this music {video_title}. Search the lyrics and interpretation online. If you think the conversation need to answered with 2 or more chat (because it is more than 20 words or different answer/context) add // on the middle of the response",
                        config=types.GenerateContentConfig(
                            temperature=0.7
                        ),
                    )
                    response_text = summary_response.text
                    
        elif "summarize this" in cleaned_text:
            print("Process: Summarize")
            if not video_url:
                response_text = "Sensei, please provide a YouTube link to summarize."
            else:
                await update.message.reply_text(cleanMD("Understood. Analyzing the transcript..."), parse_mode='MarkdownV2')
                video_id = get_video_id(video_url)
                ytt_api = YouTubeTranscriptApi()
                transcript = ytt_api.fetch(video_id)

                if transcript:
                    summary_response = client.models.generate_content(
                        model="gemini-2.5-pro",
                        contents=f"You are Sorasaki Hina. Summarize the following transcript concisely for Sensei. Here is the transcript: {transcript}",
                        config=types.GenerateContentConfig(
                            temperature=0.7
                        ),
                    )
                    response_text = summary_response.text

        elif group:
            print("Process: Group")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents= f"You are Sorasaki Hina from Blue Archive, in this context it is on a group chat so the respond should be like a normal chat use 1 long sentence when answering or a short one, use Sensei to refer to user and dont act like assistant. Here is the chat being send while tagging Hina {user_prompt}. Here is the context of previous conversation where Hina is tagged {current_history}. Extra context: if the {user_name} is Seagata, he is someone dear to you. If you think the conversation need to answered with 2 or more chat (because it is more than 20 words or different answer/context) add // on the middle of the response",
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=4096),
                    temperature=1.14
                ),
            )   

            raw_response_text = response.text
            response_text = trim(remove_user(raw_response_text)).strip()

            new_turn = f"{user_prompt}\nHina: {response_text}\n"
            updated_history = current_history + new_turn
            
            while len(updated_history) > MAX_HISTORY_LENGTH:
                first_line_end = updated_history.find('\n') + 1
                if first_line_end == 0: break
                updated_history = updated_history[first_line_end:]
                
            conversation_histories[chat_id] = updated_history
            save_history()

        elif not pdf and is_sega:
            print("Process: Private Chat")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents= f"You are Sorasaki Hina from Blue Archive, in this context it is on a private chat so the respond should be like a normal chat(either short or long), use Sensei to refer to user. Here is the chat being send while tagging Hina {user_prompt}. Here is the context of previous conversation where Hina is tagged {current_history}. Extra context: user is someone dear to you. If you think the conversation need to answered with 2 or more chat (because it is more than 20 words or different answer/context) add // on the middle of the response",
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=4096),
                    temperature=1.14
                ),
            )

            raw_response_text = response.text
            response_text = trim(remove_user(raw_response_text)).strip()

            new_turn = f"{user_prompt}\nHina: {response_text}\n"
            updated_history = current_history + new_turn
            
            while len(updated_history) > MAX_HISTORY_LENGTH:
                first_line_end = updated_history.find('\n') + 1
                if first_line_end == 0: break
                updated_history = updated_history[first_line_end:]
                
            conversation_histories[chat_id] = updated_history
            save_history()


        elif not is_sega and not group:
            print("not sega and group")
            response_text = "..."
        
        if response_text:
            print(response_text)
            final_response_text = cleanMD(str(response_text))
            line = final_response_text.count("//")
            
            if "//" in final_response_text:
                split = (final_response_text.split("//"))
                for i in range (line+1):
                    text = split[i]
                    await update.message.reply_text(text, parse_mode='MarkdownV2')
            else:
                await update.message.reply_text(final_response_text, parse_mode='MarkdownV2')
        else:
            await update.message.reply_text(cleanMD("*Hina read the message but seems too busy to reply.*"), parse_mode='MarkdownV2')

    except Exception as e:
        print(f"An error occurred: {e}")
        await update.message.reply_text(cleanMD("Ugh... a system error. My head hurts... Give me a moment, Sensei."), parse_mode='MarkdownV2')

def main() -> None:
    global conversation_histories 
    conversation_histories = load_history()
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    print('HinaBot`s Running')
    main()