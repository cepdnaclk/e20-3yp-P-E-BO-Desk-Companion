from datetime import date
from io import BytesIO
import threading
import queue
import time
import os

# turn off the welcome message from pygame package
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "2"

import google.generativeai as genai
from gtts import gTTS
from gpiozero import LED
 
from pygame import mixer 
import speech_recognition as sr

import sounddevice 

# Using Raspberry Pi's 3.3v GPIO pins 24 and 25 for LEDs
gled = LED(5) 
rled = LED(6)

mixer.pre_init(frequency=24000, buffer=2048) 
mixer.init()

# add your Google Gemini API key here
my_api_key = "AIzaSyDjx04eYTq-09j7kzd24NeZfwYZ7eu3w9Q"

if len(my_api_key) < 5:
    print(f"Please add your Google Gemini API key in the program. \n " )
    quit() 

# set Google Gemini API key as a system environment variable or add it here
genai.configure(api_key= my_api_key)

# model of Google Gemini API
model = genai.GenerativeModel('gemini-1.5-flash',
    generation_config=genai.GenerationConfig(
        candidate_count=1,
        top_p = 0.95,
        top_k = 64,
        max_output_tokens=60, # 100 tokens correspond to roughly 60-80 words.
        temperature = 0.9,
    ))

# start the chat model 
chat = model.start_chat(history=[])


today = str(date.today())

# Initialize the counters  
numtext = 0 
numtts = 0 
numaudio = 0

# thread 1 for text generation 
def chatfun(request, text_queue, llm_done, stop_event):
    global numtext, chat
    
    response = chat.send_message(request, stream=True)
 
    # response.resolve() # waits for the completion of streaming response.
    
    shortstring = ''  
    ctext = ''
    
    for chunk in response:
        try:
            if chunk.candidates[0].content.parts:
                ctext = chunk.candidates[0].content.parts[0].text
                ctext = ctext.replace("*", "")
                
                if len(shortstring) > 10 or len(ctext) >10:
            
                    shortstring = "".join([shortstring, ctext])
                    
                    text_queue.put( shortstring )
            
                    print(shortstring, end='') #, flush=True)
                    shortstring = ''
                    ctext = ''
                    # time.sleep(0.2)
                    numtext += 1
            
                else:
                    shortstring = "".join([shortstring, ctext])
                    ctext = ''
                
        except Exception as e:
            continue 

    if len(ctext) > 0: 
        shortstring = "".join([shortstring, ctext])
        
    if len(shortstring) > 0: 
        print(shortstring, end='') 
                
        text_queue.put(shortstring)                         

        numtext += 1
        
    if numtext > 0: 
        append2log(f"AI: {response.candidates[0].content.parts[0].text } \n")
        
    else:
        llm_done.set()
        stop_event.set()
    
    llm_done.set()  # Signal completion after the loop

    
# convert "text" to audio file and play back 
def speak_text(text):
    global slang, rled
           
    mp3file = BytesIO()
    tts = gTTS(text, lang = "en", tld = 'us') 
    tts.write_to_fp(mp3file)

    mp3file.seek(0)
    rled.on()
    print("AI: ", text)
    
    try:
        mixer.music.load(mp3file, "mp3")
        mixer.music.play()

        while mixer.music.get_busy():
            time.sleep(0.2)   

    except KeyboardInterrupt:
        mixer.music.stop()
        mp3file = None
        rled.off() 

    mp3file = None

    rled.off() 
  
# thread 2 for tts    
def text2speech(text_queue, tts_done, llm_done, audio_queue, stop_event):

    global numtext, numtts
        
    time.sleep(1.0)  
    
    while not stop_event.is_set():  # Keep running until stop_event is set
  
        if not text_queue.empty():

            text = text_queue.get(timeout = 1)  # Wait for 1 second for an item
             
            if len(text) > 0:
                # print(text)
                try:
                    mp3file1 = BytesIO()
                    tts = gTTS(text, lang = "en", tld = 'us') 
                    tts.write_to_fp(mp3file1)
                except Exception as e:
                    continue
                
                audio_queue.put(mp3file1)
                numtts += 1  
                text_queue.task_done()
                
        #print("\n numtts, numtext : ", numtts , numtext)
        
        if llm_done.is_set() and numtts == numtext:             
            #time.sleep(0.3) 
            tts_done.set()
            mp3file1 = None
            #print("\n break from the text queue" )

            break
            


# thread 3 for audio playback 
def play_audio(audio_queue,tts_done, stop_event):
 
    global numtts, numaudio, rled 
        
    #print("start play_audio()")
    while not stop_event.is_set():  # Keep running until stop_event is set

        mp3audio1 = BytesIO() 
        mp3audio1 = audio_queue.get()  
        mp3audio1.seek(0)          
        rled.on()
        
        mixer.music.load(mp3audio1, "mp3")
        mixer.music.play()

        #print("Numaudio: ", numaudio )  

        while mixer.music.get_busy():
            time.sleep(0.2) 
        
        numaudio += 1 
        audio_queue.task_done()
        
        #print("\n numtts, numaudio : ", numtts , numaudio)
            
        rled.off()
 
        if tts_done.is_set() and numtts  == numaudio: 
            mp3audio1 = None
            #print("\n no more audio/text data, breaking from audio thread")
            break  # Exit loop      
 
# save conversation to a log file 
def append2log(text):
    global today
    fname = 'chatlog-' + today + '.txt'
    with open(fname, "a", encoding='utf-8') as f:
        f.write(text + "\n")
        f.close 
      
# define default language to work with the AI model 
slang = "en-EN"
# Define a list to store the conversation history
conversation_history = []

def main():
    global today, slang, numtext, numtts, numaudio, messages, rled, gled
    
    rec = sr.Recognizer()
    mic = sr.Microphone()
    
    rec.dynamic_energy_threshold = False
    rec.energy_threshold = 400   
  
    sleeping = True 
    # while loop for conversation 
    while True:     
        
        with mic as source:            
            rec.adjust_for_ambient_noise(source, duration=0.5)

            try: 
                gled.on()
                print("Listening ...")                
                audio = rec.listen(source, timeout=10) 
                text = rec.recognize_google(audio, language=slang)
                
                if len(text) > 0:
                    print(f"You: {text}\n")
                else:
                    continue  
                
                gled.off()                 
                
                # AI is in sleeping mode
                if sleeping:
                    if "Pebo" in text.lower():
                        request = text.lower().split("Pebo")[1]
                        
                        # Wake AI
                        sleeping = False
                        chat = model.start_chat(history=[])
                        append2log(f"_" * 40)                    
                        today = str(date.today())  
                        messages = []  

                        if len(request) < 2:
                            speak_text("Hi there, how can I help?")
                            continue   
                    else:
                        continue
                else: 
                    request = text.lower()

                    if "that's all" in request:
                        append2log(f"You: {request}\n")
                        speak_text("Bye now")
                        append2log(f"AI: Bye now.\n")                        
                        sleeping = True
                        continue
                    
                    if "Pebo" in request:
                        request = request.split("Pebo")[1]
                        
                if len(request) == 0:
                    continue                

                # 🆕 Add conversation history before calling AI
                conversation_history.append({"role": "user", "parts": ["Answer briefly with max two sentences: " + request]})

                append2log(f"You: {request}\n")

                # Initialize the counters before each reply from AI 
                numtext = 0 
                numtts = 0 
                numaudio = 0
                
                # Define text and audio queues for data storage 
                text_queue = queue.Queue()
                audio_queue = queue.Queue()
                
                # Define events
                llm_done = threading.Event()                
                tts_done = threading.Event() 
                stop_event = threading.Event()                
     
                # Thread 1 for handling the LLM responses 
                llm_thread = threading.Thread(target=chatfun, args=(request, text_queue, llm_done, stop_event,))

                # Thread 2 for text-to-speech 
                tts_thread = threading.Thread(target=text2speech, args=(text_queue, tts_done, llm_done, audio_queue, stop_event,))
                
                # Thread 3 for audio playback 
                play_thread = threading.Thread(target=play_audio, args=(audio_queue, tts_done, stop_event,))
 
                llm_thread.start()
                tts_thread.start()
                play_thread.start()
                
                # wait for LLM to finish responding
                llm_done.wait()
                llm_thread.join() 
                
                tts_done.wait()
                audio_queue.join()
 
                stop_event.set()  
                tts_thread.join()
                play_thread.join()  
 
                print('\n')
 
            except Exception as e:
                continue 
 
 
if __name__ == "__main__":
    main()
