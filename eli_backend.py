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

# Inicializar el traductor
translator = Translator()

historial = []
contexto_conversacion = {
    "ultimo_tema": "",
    "preferencias_usuario": {},
    "historial_reciente": []
}

print("✅ Eli AI - Backend inteligente cargado con traducciones")

def traducir_texto(texto, destino='en'):
    """Traduce texto usando Google Translate"""
    try:
        traduccion = translator.translate(texto, dest=destino)
        return traduccion.text
    except Exception as e:
        print(f"❌ Error en traducción: {e}")
        return None

def analizar_intencion(texto_usuario):
    """Detecta qué tipo de respuesta necesita el usuario"""
    texto = texto_usuario.lower().strip()
    
    # Detectar solicitud de traducción
    palabras_traduccion = ['translate', 'traduce', 'traducción', 'traduccion', 'how do you say', 'what does mean', 'cómo se dice']
    if any(palabra in texto for palabra in palabras_traduccion):
        return "traduccion"
    
    # Detectar solicitud de significado
    palabras_significado = ['what does', 'what is', 'meaning', 'significado', 'qué significa']
    if any(palabra in texto for palabra in palabras_significado):
        return "significado"
    
    # Detectar saludos
    palabras_saludo = ['hello', 'hi', 'hey', 'hola', 'good morning', 'good afternoon', 'good evening']
    if any(palabra in texto for palabra in palabras_saludo):
        return "saludo"
    
    # Detectar preguntas sobre ELI
    palabras_sobre_eli = ['who are you', 'what are you', 'qué eres', 'cómo te llamas', 'what is your name']
    if any(palabra in texto for palabra in palabras_sobre_eli):
        return "sobre_eli"
    
    # Detectar despedidas
    palabras_despedida = ['bye', 'goodbye', 'see you', 'adiós', 'chao', 'nos vemos']
    if any(palabra in texto for palabra in palabras_despedida):
        return "despedida"
    
    # Detectar preguntas sobre ayuda
    palabras_ayuda = ['help', 'ayuda', 'what can you do', 'qué puedes hacer']
    if any(palabra in texto for palabra in palabras_ayuda):
        return "ayuda"
    
    # Detectar si el texto está en español
    if any(palabra in texto for palabra in ['hola', 'cómo', 'qué', 'dónde', 'cuándo', 'por qué', 'gracias']):
        return "espanol"
    
    # Por defecto, conversación normal
    return "conversacion"

def generar_respuesta_inteligente(texto_usuario, intencion):
    """Genera respuesta basada en la intención detectada"""
    
    if intencion == "traduccion":
        # Extraer la palabra/frase a traducir
        palabras = texto_usuario.lower().split()
        palabras_clave = ['translate', 'traduce', 'traducción', 'traduccion', 'cómo se dice']
        
        for palabra_clave in palabras_clave:
            if palabra_clave in palabras:
                idx = palabras.index(palabra_clave)
                if idx + 1 < len(palabras):
                    palabra_a_traducir = ' '.join(palabras[idx+1:])
                    
                    # ✅ TRADUCCIÓN REAL
                    traduccion = traducir_texto(palabra_a_traducir, 'en')
                    if traduccion:
                        return f"✅ Translation: '{palabra_a_traducir}' → '{traduccion}'\n\nNow let's practice pronouncing it! Repeat after me: '{traduccion}'"
                    else:
                        return f"I understand you want to translate: '{palabra_a_traducir}'. While I focus on pronunciation practice, you can use translation apps for accurate translations. Let's practice speaking instead! {generar_pregunta()}"
        
        return f"I'd be happy to help with translations! Please tell me what specific word or phrase you'd like to translate. {generar_pregunta()}"
    
    elif intencion == "significado":
        palabras = texto_usuario.lower().split()
        palabras_clave = ['what does', 'what is', 'meaning', 'significado', 'qué significa']
        
        for palabra_clave in palabras_clave:
            if palabra_clave in palabras:
                idx = palabras.index(palabra_clave)
                if idx + 1 < len(palabras):
                    palabra_significado = ' '.join(palabras[idx+1:])
                    
                    # Si la palabra parece estar en español, traducirla
                    if any(car in 'áéíóúñ' for car in palabra_significado):
                        traduccion = traducir_texto(palabra_significado, 'en')
                        if traduccion:
                            return f"📖 The word '{palabra_significado}' in Spanish means '{traduccion}' in English. Let's practice saying it: '{traduccion}'"
                    
                    return f"📖 You're asking about the meaning of '{palabra_significado}'. That's great for vocabulary! Try using this word in a sentence so we can practice pronunciation!"
        
        return f"That's a great question about meaning! While I specialize in pronunciation practice, understanding vocabulary is also important. Could you rephrase that as a speaking practice? {generar_pregunta()}"
    
    elif intencion == "saludo":
        saludos = [
            "Hello! I'm ELI, your English pronunciation assistant. Ready to practice speaking?",
            "Hi there! Let's work on your English pronunciation today.",
            "Greetings! I'm here to help you improve your English speaking skills.",
            "Welcome back! Ready for some English practice?"
        ]
        return f"{random.choice(saludos)} {generar_pregunta()}"
    
    elif intencion == "sobre_eli":
        respuestas = [
            "I'm ELI (English Language Instructor), an AI assistant designed to help you practice English pronunciation through conversation and audio analysis.",
            "I'm ELI, your personal English pronunciation coach! I listen to your speech and help you improve.",
            "I'm ELI - I specialize in helping students like you improve English pronunciation through interactive practice."
        ]
        return f"{random.choice(respuestas)} Now, let's practice speaking! {generar_pregunta()}"
    
    elif intencion == "despedida":
        despedidas = [
            "Goodbye! Great job practicing today. See you next time!",
            "Bye! Keep practicing your English every day.",
            "See you later! Don't forget to practice speaking regularly.",
            "Take care! I enjoyed our pronunciation practice session."
        ]
        return random.choice(despedidas)
    
    elif intencion == "ayuda":
        ayuda = [
            "I'm ELI, your English pronunciation assistant. I can help you: Analyze your pronunciation, Practice conversation, Improve your speaking skills. Just talk to me and I'll give you feedback!",
            "I'm here to help you practice English pronunciation! You can: Speak to me in English, Get feedback on your pronunciation, Practice conversation. Try saying something in English!"
        ]
        return f"{random.choice(ayuda)} {generar_pregunta()}"
    
    elif intencion == "espanol":
        # Si el usuario habla en español, traducir y animar a practicar en inglés
        traduccion = traducir_texto(texto_usuario, 'en')
        if traduccion:
            return f"🌎 I see you're speaking Spanish. In English, that would be: '{traduccion}'\n\nGreat job practicing! Now try saying it in English: '{traduccion}'"
        else:
            return f"🌎 I notice you're speaking Spanish. That's great! Let's practice the same phrase in English. Try saying: '{generar_pregunta()}'"
    
    else:
        # Conversación normal - responder contextualmente
        if texto_usuario:
            respuestas_contextuales = [
                f"Interesting! You said: '{texto_usuario}'. Let's continue practicing! {generar_pregunta()}",
                f"Thanks for sharing that! You mentioned: '{texto_usuario}'. {generar_pregunta()}",
                f"I understand you're saying: '{texto_usuario}'. Great practice! {generar_pregunta()}",
                f"That's great conversation practice! You told me: '{texto_usuario}'. {generar_pregunta()}"
            ]
            return random.choice(respuestas_contextuales)
        else:
            return f"Thanks for practicing! {generar_pregunta()}"

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

def mantener_contexto(texto_usuario, respuesta_eli):
    """Mantiene contexto de la conversación"""
    global contexto_conversacion
    
    # Limitar historial a 10 interacciones
    contexto_conversacion["historial_reciente"].append({
        "usuario": texto_usuario,
        "eli": respuesta_eli
    })
    
    if len(contexto_conversacion["historial_reciente"]) > 10:
        contexto_conversacion["historial_reciente"].pop(0)

def procesar_audio(audio_file):
    """Convierte cualquier formato de audio a WAV compatible usando pydub"""
    try:
        # Leer el archivo de audio
        audio_bytes = audio_file.read()
        
        # Determinar formato basado en extensión o contenido
        if audio_file.filename and audio_file.filename.lower().endswith('.m4a'):
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="m4a")
        elif audio_file.filename and audio_file.filename.lower().endswith('.mp3'):
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
        elif audio_file.filename and audio_file.filename.lower().endswith('.wav'):
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav")
        else:
            # Intentar detección automática
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        
        # Convertir a formato óptimo para reconocimiento de voz
        audio = audio.set_channels(1)  # Mono
        audio = audio.set_frame_rate(16000)  # 16kHz
        audio = audio.set_sample_width(2)  # 16-bit
        
        # Calcular duración
        duracion_audio = len(audio) / 1000.0  # pydub devuelve en milisegundos
        
        # Exportar a WAV en memoria
        wav_buffer = io.BytesIO()
        audio.export(wav_buffer, format="wav")
        wav_buffer.seek(0)
        
        return wav_buffer, duracion_audio
        
    except Exception as e:
        raise Exception(f"Error procesando audio: {str(e)}")

def transcribir_audio(wav_buffer):
    """Transcribe audio usando Google Web Speech API"""
    recognizer = sr.Recognizer()
    
    try:
        with sr.AudioFile(wav_buffer) as source:
            # Ajustar para ruido ambiental
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)
            
            # Usar Google Web Speech API (gratuita)
            texto = recognizer.recognize_google(audio_data, language='en-US')
            return texto.strip()
            
    except sr.UnknownValueError:
        return ""  # No se pudo entender el audio
    except sr.RequestError as e:
        raise Exception(f"Error con el servicio de reconocimiento: {e}")

def evaluar_pronunciacion_simple(texto_transcrito, audio_duration):
    """Evaluación simple de pronunciación"""
    try:
        # Métricas básicas
        palabras = texto_transcrito.split()
        total_palabras = len(palabras)
        
        # Score basado en longitud del texto
        if total_palabras == 0:
            longitud_score = 0
        else:
            longitud_score = min(total_palabras / 8.0, 1.0)
        
        # Score basado en duración del audio
        duracion_score = min(audio_duration / 3.0, 1.0)  # 3 segundos = score 1.0
        
        # Score de pronunciación general
        pronunciacion_score = (longitud_score + duracion_score) / 2.0
        
        # Generar retroalimentación
        comentarios = []
        
        if total_palabras < 2:
            comentarios.append("Try to speak a bit more. Say at least 2-3 words.")
        elif total_palabras > 5:
            comentarios.append("Great! You're speaking in complete sentences.")
        
        if audio_duration < 1.0:
            comentarios.append("Your recording is very short. Try to speak for 2-3 seconds.")
        elif audio_duration > 4.0:
            comentarios.append("Good recording length!")
            
        if pronunciacion_score < 0.4:
            comentarios.append("Keep practicing! Speak clearly and at a steady pace.")
        elif pronunciacion_score < 0.7:
            comentarios.append("Good effort! With practice you'll improve quickly.")
        else:
            comentarios.append("Excellent! Your pronunciation is getting better.")
        
        return {
            "pronunciacion_score": round(pronunciacion_score, 2),
            "fluidez_score": round(pronunciacion_score * 0.8, 2),
            "longitud_score": round(longitud_score, 2),
            "duracion_audio": round(audio_duration, 2),
            "total_palabras": total_palabras,
            "comentarios": comentarios[:2]
        }
        
    except Exception as e:
        print(f"Error en evaluación simple: {e}")
        return {
            "pronunciacion_score": 0.5,
            "fluidez_score": 0.5,
            "longitud_score": 0.5,
            "duracion_audio": audio_duration,
            "total_palabras": 0,
            "comentarios": ["We're analyzing your speech. Keep practicing!"]
        }

@app.route("/conversar_audio", methods=["POST"])
def conversar_audio():
    """Endpoint principal para análisis de pronunciación"""
    if 'audio' not in request.files:
        return jsonify({
            "estado": "error",
            "retroalimentacion": "No se recibió archivo de audio",
            "respuesta": "Please send an audio file."
        }), 400

    audio_file = request.files['audio']
    
    try:
        # Verificar tamaño del archivo
        audio_file.seek(0, 2)  # Ir al final
        file_size = audio_file.tell()
        audio_file.seek(0)  # Volver al inicio
        
        if file_size < 1000:
            return jsonify({
                "estado": "error",
                "retroalimentacion": "Archivo de audio demasiado pequeño",
                "respuesta": "The audio file is too short. Please record for at least 2-3 seconds."
            }), 400

        # Procesar audio (conversión y obtener duración)
        print("🔄 Procesando audio...")
        wav_buffer, duracion_audio = procesar_audio(audio_file)

        # Transcribir audio
        print("🎯 Transcribiendo audio...")
        texto_usuario = transcribir_audio(wav_buffer)
        
        print(f"🗣️ Transcripción: {texto_usuario}")

        if not texto_usuario:
            return jsonify({
                "estado": "error", 
                "retroalimentacion": "No se pudo transcribir el audio",
                "respuesta": "I couldn't hear any speech. Please try again and speak clearly."
            }), 400

        # ✅ ANÁLISIS DE INTENCIÓN MEJORADO
        print("🧠 Analizando intención del usuario...")
        intencion = analizar_intencion(texto_usuario)
        print(f"🎯 Intención detectada: {intencion}")
        
        respuesta = generar_respuesta_inteligente(texto_usuario, intencion)

        # Evaluar pronunciación
        print("📊 Evaluando pronunciación...")
        evaluacion = evaluar_pronunciacion_simple(texto_usuario, duracion_audio)

        # Mantener contexto de conversación
        mantener_contexto(texto_usuario, respuesta)

        # Agregar al historial
        historial.append({
            "usuario": texto_usuario,
            "eli": respuesta,
            "evaluacion": evaluacion,
            "intencion": intencion
        })

        # Limitar historial
        if len(historial) > 50:
            historial.pop(0)

        return jsonify({
            "estado": "exito",
            "respuesta": respuesta,
            "retroalimentacion": "Análisis de pronunciación completado",
            "transcripcion": texto_usuario,
            "evaluacion": evaluacion,
            "intencion": intencion,
            "historial": historial[-5:]
        })

    except Exception as e:
        print(f"❌ Error general: {e}")
        traceback.print_exc()
        return jsonify({
            "estado": "error",
            "retroalimentacion": f"Error procesando audio: {str(e)}",
            "respuesta": "Sorry, there was a technical issue. Please try again."
        }), 500

@app.route("/conversar", methods=["POST"])
def conversar():
    """Endpoint alternativo para conversación por texto"""
    data = request.get_json()
    frase_usuario = data.get('frase_usuario', '').strip()
    
    if not frase_usuario:
        return jsonify({
            "estado": "error",
            "respuesta": "Please provide some text."
        }), 400
    
    # ✅ USAR EL SISTEMA DE INTELIGENCIA MEJORADO
    intencion = analizar_intencion(frase_usuario)
    respuesta = generar_respuesta_inteligente(frase_usuario, intencion)
    mantener_contexto(frase_usuario, respuesta)
    
    historial.append({
        "usuario": frase_usuario,
        "eli": respuesta,
        "evaluacion": None,
        "intencion": intencion
    })
    
    return jsonify({
        "estado": "exito",
        "respuesta": respuesta,
        "retroalimentacion": "Conversación procesada",
        "intencion": intencion
    })

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint para verificar estado del servidor"""
    return jsonify({
        "estado": "online",
        "mensaje": "✅ Eli está vivo y escuchando 👂",
        "servicio_transcripcion": "Google Web Speech API",
        "caracteristicas": [
            "Análisis de pronunciación",
            "Detección de intenciones", 
            "Traducciones en tiempo real",
            "Respuestas contextuales",
            "Evaluación de fluidez"
        ],
        "historial_conversaciones": len(historial)
    }), 200

@app.route("/contexto", methods=["GET"])
def obtener_contexto():
    """Endpoint para ver el contexto actual (útil para debugging)"""
    return jsonify({
        "contexto_actual": contexto_conversacion,
        "ultimas_interacciones": historial[-3:] if historial else []
    }), 200

@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Eli Backend</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                text-align: center; 
                padding: 50px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                background: rgba(255,255,255,0.1);
                padding: 40px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
            }
            .success { 
                color: #4CAF50; 
                font-size: 28px;
                margin-bottom: 20px;
            }
            .info { 
                color: #FFD700; 
                margin: 15px 0;
                font-size: 18px;
            }
            a {
                color: #4FC3F7;
                text-decoration: none;
                font-weight: bold;
            }
            a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success">🚀 Eli Backend funcionando</div>
            <div class="info">✅ Con traducciones en tiempo real</div>
            <div class="info">🎯 Endpoint principal: <strong>/conversar_audio</strong></div>
            <div class="info">🔍 Health: <a href="/health">/health</a></div>
            <div class="info">💬 Texto: <a href="/conversar">/conversar</a></div>
            <div class="info">🧠 Contexto: <a href="/contexto">/contexto</a></div>
            <div class="info">🌎 Ahora con soporte para traducciones Español-Inglés</div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    print("✅ Eli backend inteligente cargado correctamente")
    print("🎯 Endpoints disponibles:")
    print("   POST /conversar_audio - Para análisis de pronunciación por audio")
    print("   POST /conversar - Para conversación por texto") 
    print("   GET  /health - Para verificar estado del servidor")
    print("   GET  /contexto - Para ver contexto de conversación")
    print("🧠 Características inteligentes:")
    print("   - Detección de intenciones (traducción, significado, saludos, etc.)")
    print("   - Traducciones en tiempo real Español-Inglés")
    print("   - Respuestas contextuales mejoradas")
    print("   - Memoria de conversación")
    
    # Configuración para Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=False)