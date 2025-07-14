from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from googletrans import Translator
import time
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize translator
translator = Translator()

# Global settings
current_source_language = 'en'
current_target_language = 'es'


class BrowserVoiceTranslator:
    def __init__(self):
        self.translator = Translator()

    def translate_text(self, text, source_lang, target_lang):
        """Translate text from source to target language"""
        try:
            if text.strip():
                result = self.translator.translate(
                    text, src=source_lang, dest=target_lang)
                return result.text
            return ""
        except Exception as e:
            print(f"Translation error: {e}")
            return f"Translation error: {str(e)}"


# Initialize processor
processor = BrowserVoiceTranslator()


@app.route('/')
def index():
    return render_template('index_browser.html')


@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('status', {'message': 'Connected to server', 'type': 'success'})


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


@socketio.on('translate_text')
def handle_translate_text(data):
    """Handle text translation from browser speech recognition"""
    def translate_async():
        try:
            original_text = data.get('text', '')
            source_lang = data.get('source_lang', 'en')
            target_lang = data.get('target_lang', 'es')

            if original_text.strip():
                # Translate the text
                translated_text = processor.translate_text(
                    original_text, source_lang, target_lang)

                # Send results back to client
                socketio.emit('translation_result', {
                    'original': original_text,
                    'translated': translated_text,
                    'source_lang': source_lang,
                    'target_lang': target_lang,
                    'timestamp': time.time()
                })

        except Exception as e:
            print(f"Translation error: {e}")
            socketio.emit('error', {'message': f'Translation error: {str(e)}'})

    # Process in separate thread
    thread = threading.Thread(target=translate_async)
    thread.daemon = True
    thread.start()


@socketio.on('update_languages')
def handle_update_languages(data):
    """Update source and target languages"""
    global current_source_language, current_target_language
    current_source_language = data.get('source', 'en')
    current_target_language = data.get('target', 'es')
    emit('status', {
        'message': f'Languages updated: {current_source_language} → {current_target_language}',
        'type': 'info'
    })


@socketio.on('test_speech')
def handle_test_speech():
    """Test speech recognition capability"""
    emit('status', {
        'message': 'Speech recognition test - please speak when prompted',
        'type': 'info'
    })


if __name__ == '__main__':
    print("🎤 Starting Browser-Based Voice Translator...")
    print("📱 This version uses browser speech recognition (no PyAudio needed)")
    print("🌐 Access at: http://localhost:5000")
    print("🔊 Make sure to allow microphone access in your browser")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
