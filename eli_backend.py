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
import re  # ✅ Para expresiones regulares

app = Flask(__name__)
CORS(app)

translator = Translator()
historial = []

print("✅ Eli - Tutor Conversacional de Pronunciación cargado")

# === VOCABULARIO PARA EL JUEGO ===
vocabulario = {
    "fácil": [
        "casa", "perro", "gato", "sol", "agua", "comida", "amigo", 
        "familia", "tiempo", "música", "libro", "escuela", "maestro",
        "estudiante", "ciudad", "país", "número", "color", "día", "noche",
        "mesa", "silla", "ventana", "puerta", "coche", "flor", "árbol",
        "playa", "mar", "cielo", "luna", "estrella", "montaña", "río",
        "pan", "leche", "fruta", "verdura", "carne", "pescado", "huevo",
        "cuchara", "tenedor", "cuchillo", "plato", "vaso", "cama", "sofá",
        "zapato", "ropa", "camisa", "pantalón", "vestido", "calcetín"
    ],
    "normal": [
        "El gato está en la mesa",
        "Me gusta la música",
        "Tengo un perro grande",
        "Hoy hace mucho sol",
        "Vamos a la escuela",
        "Mi familia es muy importante",
        "El libro es interesante",
        "Necesito beber agua",
        "Mi amigo viene hoy",
        "Qué tiempo hace hoy?",
        "Me encanta comer pizza",
        "Los niños juegan en el parque",
        "Estudio inglés todos los días",
        "La película fue muy divertida",
        "Quiero viajar a otro país",
        "Mi color favorito es el azul",
        "La comida está deliciosa",
        "Trabajo en una oficina",
        "Leo un libro antes de dormir",
        "La casa es grande y bonita",
        "El coche necesita gasolina",
        "Mañana es mi cumpleaños",
        "Los estudiantes aprenden rápido",
        "El restaurante está lleno",
        "Necesito comprar comida"
    ],
    "difícil": [
        "I would have gone to the university if I had known about the scholarship opportunities",
        "The scientific research demonstrated significant improvements in renewable energy efficiency",
        "Global economic trends indicate substantial growth in emerging markets this quarter",
        "Environmental sustainability requires collaborative efforts from multiple stakeholders",
        "Technological advancements continue to revolutionize modern communication systems",
        "The interdisciplinary approach to problem-solving yields innovative solutions across various sectors",
        "Comprehensive analysis of macroeconomic indicators reveals potential shifts in fiscal policy",
        "Cognitive behavioral therapy has proven effective in treating anxiety disorders",
        "Renewable energy sources are becoming increasingly cost-competitive with traditional fossil fuels",
        "Artificial intelligence algorithms can process vast amounts of data in real-time",
        "Climate change mitigation strategies require international cooperation and commitment",
        "The pharmaceutical company developed a groundbreaking treatment for rare diseases",
        "Sustainable urban planning incorporates green spaces and efficient public transportation",
        "Quantum computing represents the next frontier in computational technology",
        "Biomedical engineering combines principles of medicine and engineering"
    ]
}

# === ENDPOINTS DEL JUEGO ===
@app.route("/juego/palabra", methods=["GET"])
def obtener_palabra_juego():
    try:
        dificultad = request.args.get('dificultad', 'fácil')
        
        if dificultad not in vocabulario:
            return jsonify({"error": "Dificultad no válida"}), 400
        
        palabra = random.choice(vocabulario[dificultad])
        
        return jsonify({
            "palabra": palabra,
            "dificultad": dificultad,
            "puntos_base": {
                "fácil": 10,
                "normal": 25, 
                "difícil": 50
            }[dificultad]
        })
    except Exception as e:
        print(f"❌ Error en /juego/palabra: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/juego/validar", methods=["POST"])
def validar_respuesta_juego():
    try:
        data = request.json
        palabra_original = data.get('palabra_original', '')
        respuesta_usuario = data.get('respuesta_usuario', '')
        dificultad = data.get('dificultad', 'fácil')
        
        print(f"🎯 Validando: '{palabra_original}' -> '{respuesta_usuario}' (Dificultad: {dificultad})")

        # Traducir la palabra original al inglés para comparar
        if any(c.isalpha() for c in palabra_original) and not palabra_original.strip().isascii():
            # Si contiene caracteres no ASCII, asumimos que es español y traducimos
            traduccion = translator.translate(palabra_original, src='es', dest='en')
            traduccion_correcta = traduccion.text
        else:
            # Si ya está en inglés, usamos la palabra original
            traduccion_correcta = palabra_original
        
        # Limpiar ambas respuestas para comparación
        respuesta_limpia = respuesta_usuario.lower().strip()
        correcta_limpia = traduccion_correcta.lower().strip()
        
        # Comparación más flexible para el juego
        es_correcta = (
            respuesta_limpia == correcta_limpia or
            respuesta_limpia in correcta_limpia or
            correcta_limpia in respuesta_limpia or
            respuesta_limpia.replace("the ", "") == correcta_limpia.replace("the ", "") or
            respuesta_limpia.replace("a ", "") == correcta_limpia.replace("a ", "")
        )
        
        # Puntos basados en la dificultad
        puntos_obtenidos = {
            "fácil": 10,
            "normal": 25,
            "difícil": 50
        }[dificultad] if es_correcta else 0

        print(f"✅ Validación: {es_correcta} - Puntos: {puntos_obtenidos}")
        
        return jsonify({
            "es_correcta": es_correcta,
            "respuesta_usuario": respuesta_usuario,
            "traduccion_correcta": traduccion_correcta,
            "palabra_original": palabra_original,
            "puntos_obtenidos": puntos_obtenidos
        })
        
    except Exception as e:
        print(f"❌ Error en validación del juego: {e}")
        return jsonify({
            "error": f"Error en validación: {str(e)}",
            "es_correcta": False,
            "puntos_obtenidos": 0
        }), 500

# === SISTEMA CONVERSACIONAL MEJORADO ===
def es_solicitud_traduccion(texto):
    """Detección MÁS PRECISA de solicitudes de traducción"""
    texto_lower = texto.lower().strip()
    
    patrones_traduccion = [
        r'.*how do you say.*',
        r'.*cómo se dice.*', 
        r'.*traduce.*',
        r'.*translate.*',
        r'.*what is.*in english.*',
        r'.*qué es.*en inglés.*',
        r'.*como se dice.*',  # Sin acento
        r'.*how to say.*'
    ]
    
    return any(re.search(patron, texto_lower) for patron in patrones_traduccion)

def extraer_palabra_traducir(texto):
    """Extracción MEJORADA de la palabra a traducir"""
    texto_lower = texto.lower().strip()
    
    # ✅ PATRONES MÁS ESPECÍFICOS CON EXPRESIONES REGULARES
    patrones = [
        r'how do you say (.+?) (?:in english|please|por favor|\?|$)',
        r'cómo se dice (.+?) (?:en inglés|por favor|\?|$)',
        r'traduce (.+?) (?:a inglés|por favor|\?|$)',
        r'translate (.+?) (?:to english|please|\?|$)',
        r'what is (.+?) in english',
        r'qué es (.+?) en inglés'
    ]
    
    for patron in patrones:
        match = re.search(patron, texto_lower)
        if match:
            palabra = match.group(1).strip()
            # Limpiar la palabra
            palabra = re.sub(r'[?.,!¿¡]', '', palabra)  # Remover puntuación
            return palabra
    
    # ✅ MÉTODO DE RESPUESTA: Buscar después de palabras clave
    palabras_clave = ['say', 'dice', 'traduce', 'translate', 'what is', 'qué es']
    palabras = texto_lower.split()
    
    for i, palabra in enumerate(palabras):
        if palabra in palabras_clave and i + 1 < len(palabras):
            # Tomar la siguiente palabra como candidata
            candidata = palabras[i + 1]
            # Limpiar y devolver
            candidata = re.sub(r'[?.,!¿¡]', '', candidata)
            return candidata
    
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
    
    # ✅ TRADUCCIONES MEJORADAS
    if es_solicitud_traduccion(texto_usuario):
        palabra = extraer_palabra_traducir(texto_usuario)
        print(f"🔍 Palabra a traducir detectada: '{palabra}'")  # Debug
        
        if palabra and len(palabra) > 1:  # Asegurar que no sea una letra sola
            try:
                # ✅ DETECCIÓN MEJORADA DEL IDIOMA ORIGINAL
                deteccion_idioma = translator.detect(palabra)
                idioma_original = deteccion_idioma.lang
                confianza = deteccion_idioma.confidence
                
                print(f"🌐 Idioma detectado: {idioma_original} (confianza: {confianza})")
                
                # Solo traducir si parece español o tiene baja confianza de ser inglés
                if idioma_original == 'es' or confianza < 0.8:
                    traduccion = translator.translate(palabra, src='es', dest='en')
                    texto_traducido = traduccion.text
                    
                    # Verificar que la traducción sea diferente
                    if texto_traducido.lower() != palabra.lower():
                        consejos = [
                            f"Practice saying: '{texto_traducido}'", 
                            f"Repeat the word 3 times: '{texto_traducido}'",
                            "Focus on the pronunciation of this new word"
                        ]
                        return f"✅ **Translation**: '{palabra}' → '{texto_traducido}'\n\n🎯 **Now let's practice pronouncing it!** Repeat after me: '{texto_traducido}'", consejos
                    else:
                        return f"🤔 It seems '{palabra}' doesn't need translation. Let's practice pronouncing it clearly!", [f"Practice saying '{palabra}' with clear pronunciation"]
                else:
                    return f"🔍 I detected that '{palabra}' might already be in English. Let's practice its pronunciation!", [f"Focus on pronouncing '{palabra}' clearly"]
                    
            except Exception as e:
                print(f"❌ Error en traducción: {e}")
                return f"🔄 Let's practice the pronunciation of '{palabra}'! Say it clearly.", [f"Practice saying '{palabra}'"]
        else:
            return "I'd be happy to help with translations! Please tell me what specific word you'd like to translate. For example: 'How do you say casa in English?'", []
    
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
    
    return consejos[:3]

def necesita_correccion_pronunciacion(texto_usuario):
    """Determina si la respuesta merece corrección de pronunciación"""
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
        "What was the last movie you watched?"
    ]
    return random.choice(preguntas)

# === ENDPOINTS PRINCIPALES ===
@app.route("/conversar_audio", methods=["POST"])
def conversar_audio():
    if 'audio' not in request.files:
        return jsonify({"estado": "error", "respuesta": "No audio file"}), 400

    audio_file = request.files['audio']
    pregunta_actual = request.form.get('pregunta_actual', generar_pregunta())
    
    try:
        wav_buffer, duracion_audio = procesar_audio(audio_file)
        texto_usuario = transcribir_audio(wav_buffer)
        
        print(f"🗣️ Usuario dijo: {texto_usuario}")

        if not texto_usuario:
            return jsonify({
                "estado": "error", 
                "respuesta": "I couldn't hear any speech. Please try again and speak clearly."
            }), 400

        # ✅ SISTEMA HÍBRIDO MEJORADO
        respuesta, consejos_conversacion = generar_respuesta_conversacional(texto_usuario)
        
        todos_consejos = consejos_conversacion
        if necesita_correccion_pronunciacion(texto_usuario):
            consejos_pronunciacion = analizar_pronunciacion(texto_usuario, duracion_audio)
            todos_consejos.extend(consejos_pronunciacion)

        cambiar_pregunta = not es_saludo(texto_usuario) and not es_despedida(texto_usuario)
        nueva_pregunta = generar_pregunta() if cambiar_pregunta else pregunta_actual

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
            "consejos": todos_consejos
        })

    except Exception as e:
        print(f"❌ Error: {e}")
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
        "mensaje": "✅ Eli - Tutor con Traducciones Mejoradas y Juego de Vocabulario"
    })

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "mensaje": "🚀 Eli Backend funcionando correctamente",
        "version": "2.0.0",
        "caracteristicas": [
            "Tutor conversacional de pronunciación",
            "Sistema de traducciones mejorado", 
            "Juego de vocabulario integrado",
            "Análisis de pronunciación en tiempo real"
        ]
    })

if __name__ == "__main__":
    print("🎯 Eli - Sistema Completo Activado")
    print("📚 Juego de Vocabulario Integrado")
    print("🔊 Sistema de Pronunciación Mejorado")
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=False)