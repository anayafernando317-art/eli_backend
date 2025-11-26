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
import re

app = Flask(__name__)
CORS(app)

translator = Translator()
historial = []

print("✅ Eli - Tutor Conversacional de Pronunciación cargado")

# === SISTEMA COACH MEJORADO ===
class SistemaCoach:
    def __init__(self):
        self.historial_conversacion = []
        self.estadisticas = {
            'total_palabras': 0,
            'sesiones_hoy': 0,
            'dificultades_detectadas': set(),
            'progreso_fluidez': 0
        }
    
    def analizar_calidad_respuesta(self, texto, duracion_audio):
        """Análisis profundo de la respuesta del estudiante"""
        analisis = {
            'puntuacion_fluidez': 0,
            'consejos': [],
            'elogios': [],
            'areas_mejora': []
        }
        
        palabras = texto.split()
        total_palabras = len(palabras)
        
        # Análisis de longitud
        if total_palabras < 3:
            analisis['areas_mejora'].append("Try to use longer sentences (3+ words)")
            analisis['puntuacion_fluidez'] -= 1
        elif total_palabras > 8:
            analisis['elogios'].append("Great! You're using complex sentences")
            analisis['puntuacion_fluidez'] += 2
        else:
            analisis['puntuacion_fluidez'] += 1
        
        # Análisis de duración
        if duracion_audio < 2.0:
            analisis['areas_mejora'].append("Speak for at least 2-3 seconds to practice rhythm")
        elif duracion_audio > 4.0:
            analisis['elogios'].append("Excellent speaking duration!")
            analisis['puntuacion_fluidez'] += 1
        
        # Análisis de estructura
        if any(p in texto.lower() for p in ['and', 'but', 'because', 'so']):
            analisis['elogios'].append("Good use of connecting words!")
            analisis['puntuacion_fluidez'] += 1
        
        # Consejos específicos de pronunciación
        consejos_pronunciacion = self._generar_consejos_pronunciacion(texto)
        analisis['consejos'].extend(consejos_pronunciacion)
        
        return analisis
    
    def _generar_consejos_pronunciacion(self, texto):
        """Genera consejos específicos basados en palabras comunes"""
        consejos = []
        palabras = texto.lower().split()
        
        # Palabras comúnmente problemáticas con consejos específicos
        dificultades = {
            'the': 'Practice the "th" sound: place tongue between teeth',
            'very': 'For "v", gently bite your lower lip with upper teeth',
            'think': 'Focus on the soft "th" at the beginning',
            'world': 'Pronounce all three syllables: wor-l-d',
            'water': 'Make the "t" sound clear and crisp',
            'right': 'Roll your "r" slightly at the beginning',
            'this': 'Voiced "th" - vibrate your vocal cords',
            'that': 'Same as "this" - voiced "th" sound',
            'thanks': 'Unvoiced "th" - no vibration',
            'she': 'For "sh", round your lips and push air out',
            'usually': 'Focus on the "zh" sound in the middle',
            'picture': 'Pronounce both "c" and "t" sounds clearly'
        }
        
        for palabra in palabras:
            if palabra in dificultades:
                consejos.append(f"💡 For '{palabra}': {dificultades[palabra]}")
        
        # Consejos generales si no hay específicos
        if not consejos:
            consejos.extend([
                "🎯 Try to speak at a steady pace - not too fast or slow",
                "🔊 Practice difficult sounds like 'th', 'r', and 'v' daily",
                "👂 Record yourself and compare with native speakers"
            ])
        
        return consejos[:3]
    
    def generar_respuesta_motivacional(self, analisis, texto_usuario):
        """Genera respuestas motivacionales y de coaching"""
        
        # Elogios basados en el análisis
        if analisis['elogios']:
            elogio = random.choice(analisis['elogios'])
        else:
            elogios_generales = [
                "Good effort! Keep practicing!",
                "You're making progress!",
                "I can see your improvement!",
                "Great attempt! Every practice counts!"
            ]
            elogio = random.choice(elogios_generales)
        
        # Construir respuesta completa
        respuesta = f"{elogio}\n\n"
        
        if analisis['areas_mejora']:
            respuesta += "📈 **Areas to improve:**\n"
            for area in analisis['areas_mejora'][:2]:
                respuesta += f"• {area}\n"
            respuesta += "\n"
        
        if analisis['consejos']:
            respuesta += "🎯 **Pronunciation tips:**\n"
            for consejo in analisis['consejos']:
                respuesta += f"• {consejo}\n"
            respuesta += "\n"
        
        # Pregunta de seguimiento para mantener conversación
        preguntas_seguimiento = [
            "Can you tell me more about that?",
            "How did that make you feel?",
            "What happened next?",
            "Why do you think that?",
            "Can you give me an example?",
            "What's your opinion on this?"
        ]
        
        respuesta += f"💬 **Let's continue:** {random.choice(preguntas_seguimiento)}"
        
        return respuesta

# Instancia global del sistema coach
coach = SistemaCoach()

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

# === ENDPOINTS DEL JUEGO DE VOCABULARIO ===
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

        # ✅ DETECCIÓN INTELIGENTE POR DIFICULTAD
        if dificultad == 'difícil':
            # En difícil, las frases YA están en inglés - NO traducir
            traduccion_correcta = palabra_original
            print(f"🎓 Dificultad difícil - Usando original: '{traduccion_correcta}'")
        else:
            # Para fácil y normal, detectar idioma y traducir si es español
            try:
                deteccion = translator.detect(palabra_original)
                idioma_original = deteccion.lang
                confianza = deteccion.confidence
                
                if idioma_original == 'es' or confianza < 0.6:
                    traduccion = translator.translate(palabra_original, src='es', dest='en')
                    traduccion_correcta = traduccion.text
                    print(f"🔄 Traducción: '{palabra_original}' -> '{traduccion_correcta}'")
                else:
                    traduccion_correcta = palabra_original
                    print(f"✅ Ya en inglés: '{traduccion_correcta}'")
                    
            except Exception as e:
                print(f"❌ Error en detección: {e}")
                # Fallback: traducir asumiendo español
                traduccion = translator.translate(palabra_original, src='es', dest='en')
                traduccion_correcta = traduccion.text

        # Limpiar respuestas
        respuesta_limpia = respuesta_usuario.lower().strip()
        correcta_limpia = traduccion_correcta.lower().strip()
        
        # ✅ COMPARACIÓN MÁS INTELIGENTE
        es_correcta = _es_respuesta_correcta(respuesta_limpia, correcta_limpia, dificultad)
        
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

def _es_respuesta_correcta(respuesta, correcta, dificultad):
    """Comparación inteligente según dificultad"""
    
    # Para dificultad fácil, ser más flexible
    if dificultad == 'fácil':
        # Solo comparar palabras clave
        palabras_respuesta = set(respuesta.split())
        palabras_correcta = set(correcta.split())
        return len(palabras_respuesta.intersection(palabras_correcta)) > 0
    
    # Para normal y difícil, comparación más estricta pero inteligente
    similitudes = [
        respuesta == correcta,
        respuesta in correcta,
        correcta in respuesta,
        respuesta.replace('the ', '').replace('a ', '') == correcta.replace('the ', '').replace('a ', ''),
        respuesta.replace("'s", '').replace("'", '') == correcta.replace("'s", '').replace("'", '')
    ]
    
    return any(similitudes)

# === ENDPOINTS SPEAKING CHALLENGE ===
@app.route("/challenge/tema", methods=["GET"])
def obtener_tema_challenge():
    """Obtiene un tema conversacional aleatorio"""
    temas = [
        "Describe your favorite holiday tradition",
        "What would you do if you won the lottery?",
        "Talk about your dream vacation destination",
        "Describe your perfect day from morning to night",
        "What's your opinion on social media?",
        "Talk about a book or movie that changed your perspective",
        "Describe your favorite season and why you love it",
        "What are your goals for the next year?",
        "Talk about a person who inspires you",
        "Describe your favorite type of music and why",
        "What does success mean to you?",
        "Talk about a challenge you overcame",
        "Describe your ideal job or career",
        "What are you most grateful for in your life?",
        "Talk about a skill you'd like to learn"
    ]
    return jsonify({"tema": random.choice(temas)})

@app.route("/challenge/analizar", methods=["POST"])
def analizar_fluidez():
    """Analiza fluidez y da puntuación"""
    data = request.json
    texto = data.get('texto', '')
    duracion = data.get('duracion', 0)
    pausas = data.get('pausas_largas', 0)
    
    # Cálculo de puntuación
    palabras_por_minuto = (len(texto.split()) / duracion) * 60 if duracion > 0 else 0
    puntuacion_fluidez = min(100, palabras_por_minuto * 2)  # Base: 50 WPM = 100 puntos
    puntuacion_fluidez -= pausas * 10  # Penalizar pausas largas
    
    consejos = []
    if palabras_por_minuto < 30:
        consejos.append("Try to speak a bit faster - aim for 30-50 words per minute")
    elif palabras_por_minuto > 80:
        consejos.append("Great speed! You're speaking very fluently")
    
    if pausas > 2:
        consejos.append("Try to reduce long pauses between sentences")
    
    return jsonify({
        "puntuacion_fluidez": max(0, puntuacion_fluidez),
        "palabras_por_minuto": palabras_por_minuto,
        "consejos_fluidez": consejos,
        "duracion_efectiva": duracion
    })

# === SISTEMA CONVERSACIONAL MEJORADO ===
def es_solicitud_traduccion(texto):
    texto_lower = texto.lower().strip()
    
    patrones_traduccion = [
        r'.*how do you say.*',
        r'.*cómo se dice.*', 
        r'.*traduce.*',
        r'.*translate.*',
        r'.*what is.*in english.*',
        r'.*qué es.*en inglés.*',
        r'.*como se dice.*',
        r'.*how to say.*'
    ]
    
    return any(re.search(patron, texto_lower) for patron in patrones_traduccion)

def extraer_palabra_traducir(texto):
    texto_lower = texto.lower().strip()
    
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
            palabra = re.sub(r'[?.,!¿¡]', '', palabra)
            return palabra
    
    palabras_clave = ['say', 'dice', 'traduce', 'translate', 'what is', 'qué es']
    palabras = texto_lower.split()
    
    for i, palabra in enumerate(palabras):
        if palabra in palabras_clave and i + 1 < len(palabras):
            candidata = palabras[i + 1]
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
    
    if es_saludo(texto_usuario):
        saludos = [
            "¡Hello! I'm Eli, your English pronunciation coach. How can I help you practice today?",
            "Hi there! I'm here to help you improve your English pronunciation. What would you like to work on?",
            "Hey! I'm Eli, your pronunciation tutor. Ready to practice speaking English?"
        ]
        return random.choice(saludos), []
    
    if es_despedida(texto_usuario):
        despedidas = [
            "Goodbye! Great pronunciation practice today. See you next time!",
            "Bye! Keep practicing your English pronunciation every day.",
            "See you later! Don't forget to practice speaking regularly."
        ]
        return random.choice(despedidas), []
    
    if any(p in texto_lower for p in ['who are you', 'what are you', 'qué eres', 'cómo te llamas']):
        return "I'm Eli, your English pronunciation coach! I'm here to help you improve your speaking skills through conversation and pronunciation practice.", []
    
    if any(p in texto_lower for p in ['how are you', 'cómo estás', 'qué tal']):
        estados = [
            "I'm doing great! Ready to help you practice English pronunciation. How about you?",
            "I'm wonderful! Excited to practice English pronunciation with you today.",
            "I'm doing well, thank you for asking! How are you feeling about your English practice?"
        ]
        return random.choice(estados), []
    
    if es_solicitud_traduccion(texto_usuario):
        palabra = extraer_palabra_traducir(texto_usuario)
        print(f"🔍 Palabra a traducir detectada: '{palabra}'")
        
        if palabra and len(palabra) > 1:
            try:
                deteccion_idioma = translator.detect(palabra)
                idioma_original = deteccion_idioma.lang
                confianza = deteccion_idioma.confidence
                
                print(f"🌐 Idioma detectado: {idioma_original} (confianza: {confianza})")
                
                if idioma_original == 'es' or confianza < 0.8:
                    traduccion = translator.translate(palabra, src='es', dest='en')
                    texto_traducido = traduccion.text
                    
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
    
    respuestas = [
        f"Great speaking practice! You said: '{texto_usuario}'. Let me give you some pronunciation tips.",
        f"Good effort! I heard: '{texto_usuario}'. Now let's work on your pronunciation.",
        f"Nice attempt! You mentioned: '{texto_usuario}'. Here are some tips to improve your speaking."
    ]
    return random.choice(respuestas), []

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
        
        print(f"🗣️ Usuario dijo: {texto_usuario} (Duración: {duracion_audio}s)")

        if not texto_usuario:
            return jsonify({
                "estado": "error", 
                "respuesta": "I couldn't hear any speech. Please try again and speak clearly for 2-3 seconds."
            }), 400

        # ✅ ANÁLISIS COMPLETO CON EL SISTEMA COACH
        analisis = coach.analizar_calidad_respuesta(texto_usuario, duracion_audio)
        respuesta = coach.generar_respuesta_motivacional(analisis, texto_usuario)

        # Actualizar estadísticas
        coach.estadisticas['total_palabras'] += len(texto_usuario.split())
        coach.estadisticas['sesiones_hoy'] += 1

        # Generar nueva pregunta si es apropiado
        cambiar_pregunta = len(texto_usuario.split()) > 2
        nueva_pregunta = generar_pregunta() if cambiar_pregunta else pregunta_actual

        # Guardar en historial
        historial.append({
            "usuario": texto_usuario,
            "eli": respuesta,
            "duracion": duracion_audio,
            "analisis": analisis,
            "pregunta": pregunta_actual
        })

        if len(historial) > 50:
            historial.pop(0)

        return jsonify({
            "estado": "exito",
            "respuesta": respuesta,
            "transcripcion": texto_usuario,
            "nueva_pregunta": nueva_pregunta,
            "puntuacion_fluidez": analisis['puntuacion_fluidez'],
            "consejos": analisis['consejos'],
            "elogios": analisis['elogios']
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
        "mensaje": "✅ Eli - Tutor con Sistema Coach Mejorado y Juegos Integrados"
    })

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "mensaje": "🚀 Eli Backend funcionando correctamente",
        "version": "3.0.0",
        "caracteristicas": [
            "Tutor conversacional de pronunciación mejorado",
            "Sistema coach con análisis de fluidez", 
            "Juego de vocabulario corregido",
            "Speaking Challenge integrado",
            "Análisis de pronunciación en tiempo real"
        ]
    })

if __name__ == "__main__":
    print("🎯 Eli - Sistema Completo Activado")
    print("📚 Juego de Vocabulario Corregido")
    print("💬 Speaking Challenge Integrado")
    print("👨‍🏫 Sistema Coach Mejorado")
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=False)