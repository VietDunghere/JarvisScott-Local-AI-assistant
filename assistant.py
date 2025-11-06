import os
import psutil
import datetime
import pyttsx3
import schedule
import time
import speech_recognition as sr
import threading

# --- Cấu hình giọng nói ---
import pyttsx3
import threading
import queue
import time

# --- Speech queue & worker (1 engine, 1 worker thread) ---
speech_queue = queue.Queue()
speech_stop_event = threading.Event()

engine = pyttsx3.init()
engine.setProperty('rate', 175)

# Optionally choose an English voice (keep default if not found)
voices = engine.getProperty('voices')
for v in voices:
    if "english" in v.name.lower():
        engine.setProperty('voice', v.id)
        break

def speech_worker():
    """Worker lấy text từ queue và gọi engine.runAndWait() chỉ trong worker này."""
    while not speech_stop_event.is_set():
        try:
            text = speech_queue.get(timeout=0.2)  # đợi item tới
        except queue.Empty:
            continue

        try:
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            # nếu có lỗi, in ra để debug nhưng không crash worker
            print("Speech worker error:", e)
        finally:
            speech_queue.task_done()

# Start worker thread (call once at program start)
speech_thread = threading.Thread(target=speech_worker, daemon=True)
speech_thread.start()

def speak(text):
    """Gọi để nói: in ra console và đưa vào queue để worker xử lý."""
    print(f"🤖 {text}")
    # put text vào queue để worker đọc
    speech_queue.put(text)

def stop_speech_worker(wait_for_queue=True, timeout=5):
    """Dừng worker an toàn khi chương trình kết thúc."""
    if wait_for_queue:
        # đợi mọi item trong queue được xử lý (tối đa timeout giây)
        try:
            speech_queue.join()
        except Exception:
            pass
    speech_stop_event.set()
    # cho worker 1 nhịp để thoát
    speech_thread.join(timeout)


# --- Các chức năng cơ bản ---
def check_system_info():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    speak(f"CPU: {cpu}%, RAM: {ram}%, Disk: {disk}%")

def open_folder(path):
    if os.path.exists(path):
        os.startfile(path)
        speak(f"Opened folder: {path}")
    else:
        speak("Cannot find this folder, Sir.")

def daily_reminder():
    speak("Good morning Sir.")
    today = datetime.datetime.now().strftime("%d/%m/%Y")
    speak(f"Today is {today}. You don't have any class today, Sir.")

# --- CLI chính ---
def main():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    speak("Good morning Sir, what do you want to do today?")
    schedule.every().day.at("08:00").do(daily_reminder)

    while True:
        with mic as source:
            print("🎙️ Listening...")
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)

        try:
            cmd = recognizer.recognize_google(audio, language="en-US").lower()
            print(f">> {cmd}")
        except sr.UnknownValueError:
            speak("Sorry Sir, I didn’t catch that.")
            continue
        except sr.RequestError:
            speak("Connection error with Google Speech API.")
            continue

        # --- Xử lý lệnh ---
        if any(word in cmd for word in ["exit", "goodbye", "stop"]):
            speak("Good night Sir.")
            stop_speech_worker(wait_for_queue=True)
            break

        elif any(word in cmd for word in ["ram", "system", "cpu"]):
            check_system_info()

        elif "open" in cmd:
            if "download" in cmd:
                path = os.path.join(os.path.expanduser("~"), "Downloads")
            elif "document" in cmd:
                path = os.path.join(os.path.expanduser("~"), "Documents")
            elif "desktop" in cmd:
                path = os.path.join(os.path.expanduser("~"), "Desktop")
            else:
                speak("Please specify which folder to open, Sir.")
                continue
            open_folder(path)

        elif "time" in cmd:
            now = datetime.datetime.now().strftime("%H:%M")
            speak(f"The current time is {now}.")

        elif "date" in cmd or "today" in cmd:
            today = datetime.datetime.now().strftime("%A, %d %B %Y")
            speak(f"Today is {today}.")

        elif "hello" in cmd or "hi" in cmd:
            speak("Hello Sir, how are you today?")

        elif "how are you" in cmd:
            speak("I'm always great when I'm with you, Sir.")

        elif "your name" in cmd:
            speak("I'm Jarvis, your AI assistant.")

        else:
            speak("Sorry Sir, I don't understand that yet.")

        # --- Duy trì lịch trình ---
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    speak("Welcome Sir, I'm Jarvis, your assistant. What can I help you with?")
    main()
    stop_speech_worker(wait_for_queue=True)