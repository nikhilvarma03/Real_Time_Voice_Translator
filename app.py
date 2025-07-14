from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import speech_recognition as sr
import io
import wave
import threading
import queue
import time
from googletrans import Translator
import json
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize components
recognizer = sr.Recognizer()
translator = Translator()
audio_queue = queue.Queue()

# Global settings
current_language = 'en'
target_language = 'es'
is_recording = False


class VoiceProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.translator = Translator()
        self.is_processing = False

    def process_audio_chunk(self, audio_data):
        """Process a single audio chunk for speech recognition"""
        try:
            # Convert base64 to audio data
            audio_bytes = base64.b64decode(audio_data)

            # Create audio file in memory
            audio_io = io.BytesIO(audio_bytes)

            # Convert to wav format for speech recognition
            with wave.open(audio_io, 'rb') as wav_file:
                frames = wav_file.readframes(wav_file.getnframes())
                sample_rate = wav_file.getframerate()
                sample_width = wav_file.getsampwidth()

            # Create AudioData object
            audio_data_obj = sr.AudioData(frames, sample_rate, sample_width)

            # Perform speech recognition
            try:
                text = self.recognizer.recognize_google(
                    audio_data_obj, language=current_language)
                return text
            except sr.UnknownValueError:
                return ""
            except sr.RequestError as e:
                print(f"Speech recognition error: {e}")
                return ""

        except Exception as e:
            print(f"Audio processing error: {e}")
            return ""

    def translate_text(self, text):
        """Translate text to target language"""
        try:
            if text.strip():
                result = self.translator.translate(
                    text, src=current_language, dest=target_language)
                return result.text
            return ""
        except Exception as e:
            print(f"Translation error: {e}")
            return ""


# Initialize processor
processor = VoiceProcessor()


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('status', {'message': 'Connected to server'})


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


@socketio.on('start_recording')
def handle_start_recording():
    global is_recording
    is_recording = True
    emit('status', {'message': 'Recording started'})


@socketio.on('stop_recording')
def handle_stop_recording():
    global is_recording
    is_recording = False
    emit('status', {'message': 'Recording stopped'})


@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    if not is_recording:
        return

    def process_chunk():
        try:
            # Process audio for speech recognition
            text = processor.process_audio_chunk(data['audio'])

            if text:
                # Translate the text
                translated_text = processor.translate_text(text)

                # Send results back to client
                socketio.emit('transcription', {
                    'original': text,
                    'translated': translated_text,
                    'source_lang': current_language,
                    'target_lang': target_language,
                    'timestamp': time.time()
                })
        except Exception as e:
            print(f"Chunk processing error: {e}")

    # Process in separate thread to avoid blocking
    thread = threading.Thread(target=process_chunk)
    thread.daemon = True
    thread.start()


@socketio.on('change_language')
def handle_language_change(data):
    global current_language, target_language
    current_language = data.get('source', 'en')
    target_language = data.get('target', 'es')
    emit('status', {
         'message': f'Language changed to {current_language} -> {target_language}'})


@socketio.on('test_microphone')
def handle_test_microphone():
    """Test microphone functionality"""
    try:
        mic = sr.Microphone()
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
        emit('status', {'message': 'Microphone test successful'})
    except Exception as e:
        emit('status', {'message': f'Microphone test failed: {str(e)}'})


if __name__ == '__main__':
    print("Starting Voice Translator Application...")
    print("Access the application at: http://localhost:5000")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
