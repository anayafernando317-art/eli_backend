from flask import Flask, request, jsonify
from flask_cors import CORS
import speech_recognition as sr
import random
import os
import traceback
from pydub import AudioSegment
import io
import tempfile
from googletrans import Translator

app = Flask(__name__)
CORS(app)

translator = Translator()
historial = []

print("✅ Eli - Tutor Conversacional de Pronunciación cargado")

# === SISTEMA CONVERSACIONAL ===
def es_solicitud_traduccion(texto):
    texto_lower = texto.lower()
    palabras_clave = [
        'translate', 'traduce', 'traducción', 'traduccion', 
        'how do you say', 'cómo se dice', 'what is in english',
        'en inglés', 'in english'
    ]
    return any(palabra in texto_lower for palabra in palabras_clave)

def extraer_palabra_traducir(texto):
    texto_lower = texto.lower()
    patrones = [
        'how do you say',
        'cómo se dice', 
        'what is',
        'traduce',
        'translate'
    ]
    
    for patron in patrones:
        if patron in texto_lower:
            inicio = texto_lower.find(patron) + len(patron)
            palabra = texto[inicio:].strip()
            palabra = palabra.rstrip('?').rstrip('.').rstrip('"').rstrip("'").strip()
            return palabra
    return None

def es_saludo(texto):
    saludos = [
        'hello', 'hi', 'hey', 'hola', 'good morning', 'good afternoon',
        'good evening', 'how are you', 'qué tal', 'cómo estás'
    ]
    texto_lower = texto.lower()
    return any(saludo in texto_lower for saludo in saludos)

def es_despedida(texto):
    despedidas = ['bye', 'goodbye', 'see you', 'adiós', 'chao', 'nos vemos']
    texto_lower = texto.lower()
    return any(despedida in texto_lower for despedida in despedidas)

def generar_respuesta_conversacional(texto_usuario):
    texto_lower = texto_usuario.lower()
    
    # Saludos
    if es_saludo(texto_usuario):
        saludos = [
            "¡Hello! I'm Eli, your English pronunciation coach. How can I help you practice today?",
            "Hi there! I'm here to help you improve your English pronunciation. What would you like to work on?",
            "Hey! I'm Eli, your pronunciation tutor. Ready to practice speaking English?"
        ]
        return random.choice(saludos), []
    
    # Despedidas
    if es_despedida(texto_usuario):
        despedidas = [
            "Goodbye! Great pronunciation practice today. See you next time!",
            "Bye! Keep practicing your English pronunciation every day.",
            "See you later! Don't forget to practice speaking regularly."
        ]
        return random.choice(despedidas), []
    
    # Preguntas sobre Eli
    if any(p in texto_lower for p in ['who are you', 'what are you', 'qué eres', 'cómo te llamas']):
        return "I'm Eli, your English pronunciation coach! I'm here to help you improve your speaking skills through conversation and pronunciation practice.", []
    
    # Estado de Eli
    if any(p in texto_lower for p in ['how are you', 'cómo estás', 'qué tal']):
        estados = [
            "I'm doing great! Ready to help you practice English pronunciation. How about you?",
            "I'm wonderful! Excited to practice English pronunciation with you today.",
            "I'm doing well, thank you for asking! How are you feeling about your English practice?"
        ]
        return random.choice(estados), []
    
    # Traducciones
    if es_solicitud_traduccion(texto_usuario):
        palabra = extraer_palabra_traducir(texto_usuario)
        if palabra:
            try:
                traduccion = translator.translate(palabra, dest='en')
                if traduccion.text.lower() != palabra.lower():
                    consejos = [f"Practice saying: '{traduccion.text}'", "Focus on the pronunciation of this new word"]
                    return f"✅ Translation: '{palabra}' → '{traduccion.text}'\n\nNow let's practice pronouncing it! Repeat after me: '{traduccion.text}'", consejos
                else:
                    return f"🤔 It seems '{palabra}' is already in English. Let's practice pronouncing it clearly!", [f"Practice saying '{palabra}' with clear pronunciation"]
            except:
                return "I'd be happy to help with translations! Let's focus on pronunciation practice.", []
        else:
            return "I'd be happy to help with translations! Please tell me what specific word you'd like to translate.", []
    
    # Respuesta conversacional normal con enfoque en pronunciación
    respuestas = [
        f"Great speaking practice! You said: '{texto_usuario}'. Let me give you some pronunciation tips.",
        f"Good effort! I heard: '{texto_usuario}'. Now let's work on your pronunciation.",
        f"Nice attempt! You mentioned: '{texto_usuario}'. Here are some tips to improve your speaking."
    ]
    return random.choice(respuestas), []

# === SISTEMA DE TUTOR DE PRONUNCIACIÓN ===
def analizar_pronunciacion(texto_transcrito, duracion_audio):
    """Analiza la pronunciación y devuelve consejos específicos"""
    consejos = []
    palabras = texto_transcrito.split()
    
    # Análisis básico de pronunciación
    if len(palabras) < 2:
        consejos.append("Try to speak in complete sentences (2-3 words minimum)")
    elif len(palabras) > 8:
        consejos.append("Great sentence length! You're speaking comfortably")
    
    if duracion_audio < 1.5:
        consejos.append("Speak for at least 2 seconds to practice flow and rhythm")
    elif duracion_audio > 5.0:
        consejos.append("Good speaking duration - you're practicing well!")
    
    # Detectar palabras comúnmente mal pronunciadas
    palabras_dificiles = {
        'the': 'Remember to use the "th" sound (tongue between teeth)',
        'very': 'Practice the "v" sound (upper teeth on lower lip)',
        'think': 'Focus on the "th" sound at the beginning',
        'world': 'Pronounce all three syllables clearly: wor-l-d',
        'water': 'Make the "t" sound clear and crisp',
        'right': 'Focus on the "r" sound at the beginning',
        'light': 'Clear "l" sound, not too soft',
        'this': 'Practice the "th" sound (voiced, tongue between teeth)',
        'that': 'Same as "this" - voiced "th" sound',
        'thanks': 'Unvoiced "th" at the beginning'
    }
    
    for palabra in palabras:
        if palabra.lower() in palabras_dificiles:
            consejos.append(f"Pronunciation tip for '{palabra}': {palabras_dificiles[palabra.lower()]}")
    
    # Consejos generales de pronunciación si no hay específicos
    if not consejos:
        consejos.extend([
            "Focus on speaking clearly and at a steady pace",
            "Practice difficult sounds like 'th', 'r', and 'v'",
            "Record yourself and compare with native speakers"
        ])
    
    return consejos[:3]  # Máximo 3 consejos

def necesita_correccion_pronunciacion(texto_usuario):
    """Determina si la respuesta merece corrección de pronunciación"""
    # No corregir saludos, despedidas o preguntas muy cortas
    if es_saludo(texto_usuario) or es_despedida(texto_usuario):
        return False
    
    palabras = texto_usuario.split()
    if len(palabras) < 2:
        return False
        
    return True

# === FUNCIONES DE AUDIO ===
def procesar_audio(audio_file):
    try:
        audio_bytes = audio_file.read()
        
        if audio_file.filename and audio_file.filename.lower().endswith('.m4a'):
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="m4a")
        elif audio_file.filename and audio_file.filename.lower().endswith('.mp3'):
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
        else:
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        
        audio = audio.set_channels(1).set_frame_rate(16000)
        duracion_audio = len(audio) / 1000.0
        
        wav_buffer = io.BytesIO()
        audio.export(wav_buffer, format="wav")
        wav_buffer.seek(0)
        
        return wav_buffer, duracion_audio
        
    except Exception as e:
        raise Exception(f"Error procesando audio: {str(e)}")

def transcribir_audio(wav_buffer):
    recognizer = sr.Recognizer()
    
    try:
        with sr.AudioFile(wav_buffer) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)
            texto = recognizer.recognize_google(audio_data, language='en-US')
            return texto.strip()
            
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        raise Exception(f"Error con el servicio de reconocimiento: {e}")

def generar_pregunta():
    preguntas = [
        "What do you like to do on weekends?",
        "Do you have any pets?",
        "What's your favorite food?",
        "Where would you like to travel?",
        "What do you usually eat for breakfast?",
        "What kind of music do you enjoy?",
        "Tell me about your family.",
        "What's your favorite season and why?",
        "Do you enjoy sports? Which ones?",
        "What was the last movie you watched?",
        "What's your favorite hobby?",
        "Do you prefer coffee or tea?",
        "What's the best book you've read recently?",
        "What do you do to relax?",
        "Do you like cooking? What's your specialty?",
        "What's your dream job?",
        "Do you prefer the city or the countryside?",
        "What's your favorite type of weather?",
        "Do you have any siblings?",
        "What's something you're learning right now?"
    ]
    return random.choice(preguntas)

# === ENDPOINT PRINCIPAL MEJORADO ===
@app.route("/conversar_audio", methods=["POST"])
def conversar_audio():
    if 'audio' not in request.files:
        return jsonify({"estado": "error", "respuesta": "No audio file"}), 400

    audio_file = request.files['audio']
    pregunta_actual = request.form.get('pregunta_actual', generar_pregunta())
    
    try:
        # Procesar audio
        wav_buffer, duracion_audio = procesar_audio(audio_file)

        # Transcribir audio
        texto_usuario = transcribir_audio(wav_buffer)
        
        print(f"🗣️ Usuario dijo: {texto_usuario}")
        print(f"⏱️ Duración: {duracion_audio} segundos")

        if not texto_usuario:
            return jsonify({
                "estado": "error", 
                "respuesta": "I couldn't hear any speech. Please try again and speak clearly."
            }), 400

        # ✅ SISTEMA HÍBRIDO: Conversación + Pronunciación
        respuesta, consejos_conversacion = generar_respuesta_conversacional(texto_usuario)
        
        # ✅ AGREGAR ANÁLISIS DE PRONUNCIACIÓN SI APLICA
        todos_consejos = consejos_conversacion
        if necesita_correccion_pronunciacion(texto_usuario):
            consejos_pronunciacion = analizar_pronunciacion(texto_usuario, duracion_audio)
            todos_consejos.extend(consejos_pronunciacion)

        # Determinar si cambiar la pregunta
        cambiar_pregunta = not es_saludo(texto_usuario) and not es_despedida(texto_usuario)
        nueva_pregunta = generar_pregunta() if cambiar_pregunta else pregunta_actual

        # Agregar al historial
        historial.append({
            "usuario": texto_usuario,
            "eli": respuesta,
            "duracion": duracion_audio,
            "consejos": todos_consejos,
            "pregunta": pregunta_actual
        })

        if len(historial) > 50:
            historial.pop(0)

        return jsonify({
            "estado": "exito",
            "respuesta": respuesta,
            "transcripcion": texto_usuario,
            "nueva_pregunta": nueva_pregunta,
            "dificultades_detectadas": [],
            "consejos": todos_consejos,
            "tipo_analisis": "pronunciacion_y_conversacion"
        })

    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return jsonify({
            "estado": "error",
            "respuesta": f"Error processing audio: {str(e)}"
        }), 500

@app.route("/obtener_pregunta", methods=["GET"])
def obtener_pregunta():
    return jsonify({"pregunta": generar_pregunta()})

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "estado": "online",
        "mensaje": "✅ Eli - Tutor Conversacional de Pronunciación",
        "funcionalidades": [
            "Conversaciones naturales en inglés",
            "Análisis de pronunciación en tiempo real", 
            "Traducciones integradas",
            "Consejos personalizados de pronunciación",
            "Práctica de speaking conversacional"
        ]
    })

@app.route("/")
def home():
    return "🎯 Eli Tutor - Conversación + Pronunciación | Usa /conversar_audio para practicar"

if __name__ == "__main__":
    print("🎯 Eli - Modo Tutor Conversacional activado")
    print("💡 Funcionalidades: Conversación + Pronunciación + Traducciones")
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=False)