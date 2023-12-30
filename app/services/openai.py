import os
import re
import time
import difflib
from anyio import Path
from openai import OpenAI
import app.db.firebase_storage as storage
from dotenv import load_dotenv

# Initiate the path of our current directory using 'pathlib' module
load_dotenv()
KEY = os.getenv("OPENAI_API_KEY")
# Load the environment variables containing in the .env file
# load_dotenv(os.path.join(basedir, '.env'))
class OpenAIService():

    def __init__(self):

        self.client = OpenAI(api_key=KEY)

        # Define the directory where we want to save audio request files
        self.AUDIO_DIRECTORY = "./local/audios/"

        # Define the audio file extension
        self.AUDIO_FILE_EXTENSION = '.mp3'

        self.messages = [{"role": "system", "content": 'You are an AI assistant. Respond to all input.'}]
    
    def text_completion(self, prompt: str, template_type: int = None):
        # 0: Create English pronunciation lesson
        # 1: Create quiz-based lesson
        if template_type == 1:
            prompt += ". Give an explanation as well. Every quiz includes: question, options, answer, explanation and should have 4 options. Wrap quiz list in a json array."
        print(prompt)
        
        response = self.client.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=3500,
            temperature=0, 
        )

        response = response.choices[0].text
        print(response)

        # if template_type == 1:
        #     print("Load error!!!")
        #     return json.loads(response)
        
        return response
    
    def generate_audio(self, text: str):
        timestamp = int(time.time()) 
        audio_name = f"speech_{timestamp}"
        full_path = os.path.join(self.AUDIO_DIRECTORY, audio_name + self.AUDIO_FILE_EXTENSION)
        
        try:
            response = self.client.audio.speech.create(
                input=text,
                model="tts-1",
                voice="alloy",
                speed=1.0
            )
            response.stream_to_file(full_path)
        except Exception as error:
            print(str(error))

        print(full_path)

        # Upload audio
        try:
            storage.upload_audio(full_path)
        except Exception as error:
            print(str(error))

        return str(full_path)

    def transcribe(self, file):
        
        transcript = ""
        
        # Create a directory for files
        if not os.path.exists(self.AUDIO_DIRECTORY):
            os.makedirs(self.AUDIO_DIRECTORY)

        timestamp = int(time.time()) 
        audio_name = f"speech_{timestamp}"
        # Combine the directory, filename, timestamp, and extension to create the full path
        full_path = os.path.join(self.AUDIO_DIRECTORY, audio_name + self.AUDIO_FILE_EXTENSION)

        # Save audio file to disk temporarily
        try:
            contents = file.file.read()
            with open(full_path, 'wb') as f:
                f.write(contents)
        except Exception:
            return "There was an error uploading the file"
        finally:
            file.file.close()

        # Save the audio file information to the storage
        try:
            storage.upload_audio(full_path)
        except Exception as error:
            print(str(error))
        
        # Transcribe audio using OpenAI API
        with open(full_path, 'rb') as f:
            transcript = self.client.audio.transcriptions.create(model="whisper-1", file=f, language="en", temperature=0.7)
        

        return str(transcript.text).lower(), full_path
    
    def pronunciation_score(self, original_script, file):

        user_script, full_path = self.transcribe(file)
        
        if not original_script or not user_script:
            return None
        
        html_output, percent_diff = self.highlight_script_differrences(original_script, user_script)
      
        return original_script, user_script, percent_diff, html_output
        
    def get_score(self, original_split, user_script_split):
        matcher = difflib.SequenceMatcher(None, original_split, user_script_split)
        ops = matcher.get_opcodes()
        percent_diff = 100 - round(((sum(original_end - original_start for op, original_start, original_end, user_start, user_end in ops if op != 'equal') / max(len(original_split), len(user_script_split))) * 100), 2)
        return round(percent_diff, 2)

    def get_html(self, original_split, user_script_split, raw_user_script_split):
        matcher = difflib.SequenceMatcher(None, original_split, user_script_split)
        ops = matcher.get_opcodes()
        # Create a list to hold the HTML-formatted words
        highlighted_words = []
        for op, original_start, original_end, user_start, user_end in ops:
            if op == 'equal':
                # If the words are equal, add a green span tag around the word
                for i in range(original_start, original_end):
                    if i < len(user_script_split):
                        highlighted_words.append(f'<span className="green">{raw_user_script_split[i]}</span>')

            elif op == 'replace':
                # If the words are different, add a red span tag around the word
                for i in range(original_start, original_end):
                    if i < len(user_script_split):
                        if original_split[i] == user_script_split[i]:
                            # If the capitalization is different, keep the original capitalization
                            highlighted_words.append(f'<span className="red">{raw_user_script_split[i]}</span>')
                        else:
                            # Otherwise, add the user's word with red highlighting
                            highlighted_words.append(f'<span className="red">{raw_user_script_split[i]}</span>')
            elif op == 'delete':
                    # If the word is missing from the user's script, add a red span tag around the original word
                    for i in range(original_start, original_end):
                        if i < len(user_script_split):
                            highlighted_words.append(f'<span className="red">{raw_user_script_split[i]}</span>')
            elif op == 'insert':
                # If there is an extra word in the user's script, add a red span tag around the user's word
                for i in range(user_start, user_end):
                    if i < len(user_script_split):
                        highlighted_words.append(f'<span className="red">{raw_user_script_split[i]}</span>')
        
        # highlight the remaining word with red if the user script is longer than the original script             
        if len(raw_user_script_split) > len(highlighted_words):
            for i in range(len(highlighted_words), len(raw_user_script_split)):
                highlighted_words.append(f'<span className="red">{raw_user_script_split[i]}</span>')
            
        # Join the list of highlighted words into a single string
        highlighted_script = ' '.join(highlighted_words)

        # Wrap the highlighted script in a div tag with a class for styling
        return f'<div className="highlighted-script">{highlighted_script}</div>'
        

    def highlight_script_differrences(self, original_script, user_script):

        user_script_cleaned = re.sub(r"[^a-zA-Z\s]", "", user_script).lower()
        original_script_cleaned = re.sub(r"[^a-zA-Z\s]", "", original_script).lower()

        raw_user_script_split = user_script.split()
        user_script_split = user_script_cleaned.split()
        original_split = original_script_cleaned.split()
        
        percent_diff = self.get_score(original_split, user_script_split)
        html_output = self.get_html(original_split, user_script_split, raw_user_script_split)

        return html_output, percent_diff
    


# @app.post("/transcribe", tags=["Convert audio to text"], description="Transcribes audio into the input language.")
# async def transcribe(file: UploadFile = File(...)):
        
#     transcript = ""
#     directory = "./audio_files/"

#     # Create a directory for files
#     if not os.path.exists(directory):
#         os.makedirs(directory)

#     # Combine the directory, filename to create the full path
#     full_path = os.path.join(directory, file.filename)
#     print(full_path)
#     # Save audio file to disk temporarily
#     try:
#         contents = file.file.read()
#         with open(full_path, 'wb') as f:
#             f.write(contents)
#     except Exception:
#         return "There was an error uploading the file"
#     finally:
#         file.file.close()
    
#     # Transcribe audio using OpenAI API
#     with open(full_path, 'rb') as f:
#         transcript = client.audio.transcriptions.create(model="whisper-1", file=f, language="en", temperature=0.7)
        
#     return str(transcript.text).lower()
    
# @app.post("/generate_audio", tags=["Generate audio"], description="Convert text to speech.")
# async def textToSpeech(text: Annotated[str, Form()]):
#     speech_file_path = Path("./audio_files") / "speech.mp3"

#     try:
#         response = client.audio.speech.create(
#             input=text,
#             model="tts-1",
#             voice="alloy",
#             speed=1.0
#         )
#     except Exception as error:
#         print(str(error))

#     response.stream_to_file(speech_file_path)
#     print(speech_file_path)
#     # https://github.com/tiangolo/fastapi/discussions/6284
#     return speech_file_path
    
# @app.post("/pronunciation_score", tags=["Pronunciation Score"], description="Pronunciation Score")
# async def pronunciation_score(original_script: Annotated[str, Form()], audio_file: UploadFile = File(...)):

#     user_script = await transcribe(audio_file)
    
#     if not original_script or not user_script:
#         return None
    
#     html_output, percent_diff = highlight_script_differrences(original_script, user_script)
    
#     return original_script, user_script, percent_diff, html_output

# def get_score(original_split, user_script_split):
#     matcher = difflib.SequenceMatcher(None, original_split, user_script_split)
#     ops = matcher.get_opcodes()
#     percent_diff = 100 - round(((sum(original_end - original_start for op, original_start, original_end, user_start, user_end in ops if op != 'equal') / max(len(original_split), len(user_script_split))) * 100), 2)
#     return round(percent_diff, 2)

# def get_html(original_split, user_script_split, raw_user_script_split):
#     matcher = difflib.SequenceMatcher(None, original_split, user_script_split)
#     ops = matcher.get_opcodes()
#     # Create a list to hold the HTML-formatted words
#     highlighted_words = []
#     for op, original_start, original_end, user_start, user_end in ops:
#         if op == 'equal':
#             # If the words are equal, add a green span tag around the word
#             for i in range(original_start, original_end):
#                 if i < len(user_script_split):
#                     highlighted_words.append(f'<span className="green">{raw_user_script_split[i]}</span>')

#         elif op == 'replace':
#             # If the words are different, add a red span tag around the word
#             for i in range(original_start, original_end):
#                 if i < len(user_script_split):
#                     if original_split[i] == user_script_split[i]:
#                         # If the capitalization is different, keep the original capitalization
#                         highlighted_words.append(f'<span className="red">{raw_user_script_split[i]}</span>')
#         elif op == 'delete':
#                 # If the word is missing from the user's script, add a red span tag around the original word
#                 for i in range(original_start, original_end):
#                     if i < len(user_script_split):
#                         highlighted_words.append(f'<span className="red">{raw_user_script_split[i]}</span>')
#         elif op == 'insert':
#             # If there is an extra word in the user's script, add a red span tag around the user's word
#             for i in range(user_start, user_end):
#                 if i < len(user_script_split):
#                     highlighted_words.append(f'<span className="red">{raw_user_script_split[i]}</span>')
    
#     # highlight the remaining word with red if the user script is longer than the original script             
#     if len(raw_user_script_split) > len(highlighted_words):
#         for i in range(len(highlighted_words), len(raw_user_script_split)):
#             highlighted_words.append(f'<span className="red">{raw_user_script_split[i]}</span>')
        
#     # Join the list of highlighted words into a single string
#     highlighted_script = ' '.join(highlighted_words)


#     # Wrap the highlighted script in a div tag with a class for styling
#     return f'<div className="highlighted-script">{highlighted_script}</div>'
    

# def highlight_script_differrences(original_script, user_script):
#     user_script_cleaned = re.sub(r"[^a-zA-Z\s]", "", user_script).lower()
#     original_script_cleaned = re.sub(r"[^a-zA-Z\s]", "", original_script).lower()

#     raw_user_script_split = user_script.split()
#     user_script_split = user_script_cleaned.split()
#     original_split = original_script_cleaned.split()
    
#     percent_diff = get_score(original_split, user_script_split)
#     html_output = get_html(original_split, user_script_split, raw_user_script_split)

#     return html_output, percent_diff