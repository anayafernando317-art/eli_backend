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

# === SISTEMA COACH CONVERSACIONAL MEJORADO ===
class SistemaCoach:
    def __init__(self):
        self.estado_conversacion = "inicio"
        self.ultimo_tema = ""
        self.historial = []
    
    def analizar_pronunciacion_detallada(self, texto, audio_duration):
        """Análisis detallado de pronunciación con correcciones específicas"""
        analisis = {
            'puntuacion': 0,
            'correcciones': [],
            'consejos': [],
            'palabras_problematicas': [],
            'retroalimentacion_positiva': []
        }
        
        palabras = texto.lower().split()
        
        # Diccionario de palabras comúnmente mal pronunciadas con correcciones
        problemas_pronunciacion = {
            'the': {'sonido_correcto': 'ðə', 'explicacion': 'Coloca la lengua entre los dientes para el sonido "th"'},
            'think': {'sonido_correcto': 'θɪŋk', 'explicacion': 'Sonido "th" suave, sin vibrar cuerdas vocales'},
            'this': {'sonido_correcto': 'ðɪs', 'explicacion': 'Sonido "th" vibrante, con vibración en garganta'},
            'very': {'sonido_correcto': 'vɛri', 'explicacion': 'Muerde suavemente el labio inferior con dientes superiores para la "v"'},
            'water': {'sonido_correcto': 'wɔːtər', 'explicacion': 'Pronuncia claramente la "t" en el medio'},
            'world': {'sonido_correcto': 'wɜːrld', 'explicacion': 'Tres sílabas: wor-l-d'},
            'right': {'sonido_correcto': 'raɪt', 'explicacion': 'Sonido "r" fuerte al inicio'},
            'light': {'sonido_correcto': 'laɪt', 'explicacion': 'Sonido "l" claro, lengua en paladar'},
            'thanks': {'sonido_correcto': 'θæŋks', 'explicacion': 'Sonido "th" al inicio, luego "anks"'},
            'she': {'sonido_correcto': 'ʃi', 'explicacion': 'Sonido "sh" redondeando los labios'},
            'usually': {'sonido_correcto': 'juːʒuəli', 'explicacion': 'Sonido "zh" en el medio como en "vision"'},
        }
        
        # Detectar palabras problemáticas
        for palabra in palabras:
            palabra_limpia = palabra.strip('.,!?')
            if palabra_limpia in problemas_pronunciacion:
                correccion = problemas_pronunciacion[palabra_limpia]
                analisis['palabras_problematicas'].append({
                    'palabra': palabra_limpia,
                    'sonido_correcto': correccion['sonido_correcto'],
                    'explicacion': correccion['explicacion']
                })
        
        # Análisis de fluidez
        if len(palabras) < 3:
            analisis['consejos'].append("💡 Intenta formar oraciones más largas (mínimo 3 palabras)")
        elif len(palabras) > 8:
            analisis['retroalimentacion_positiva'].append("¡Excelente! Estás usando oraciones complejas")
        
        if audio_duration < 1.5:
            analisis['consejos'].append("⏱️ Habla por al menos 2 segundos para practicar ritmo")
        elif audio_duration > 4.0:
            analisis['retroalimentacion_positiva'].append("🎤 Buena duración de habla")
        
        return analisis

    def generar_respuesta_conversacional(self, texto_usuario, duracion_audio=0):
        """Genera respuestas naturales y mantiene la conversación"""
        texto_lower = texto_usuario.lower().strip()
        
        # 1. DETECCIÓN DE SALUDOS
        saludos = ['hello', 'hi', 'hey', 'hola', 'good morning', 'good afternoon', 'good evening']
        if any(saludo in texto_lower for saludo in saludos):
            self.estado_conversacion = "conversando"
            respuestas_saludo = [
                "Hello! It's great to hear from you! How are you doing today?",
                "Hi there! I'm excited to practice English with you. How's your day going?",
                "Hey! Wonderful to talk with you. What would you like to practice today?",
                "Hello! I'm here to help you improve your English. How are you feeling about your practice?"
            ]
            return {
                "respuesta": random.choice(respuestas_saludo),
                "tipo": "saludo",
                "correcciones": [],
                "pregunta_seguimiento": True
            }
        
        # 2. DETECCIÓN DE ESTADO/EMOCIONES
        if any(p in texto_lower for p in ['how are you', 'cómo estás', 'qué tal']):
            respuestas_estado = [
                "I'm doing wonderful! Ready to help you practice English. Thank you for asking!",
                "I'm great! So excited to be your English practice partner today.",
                "I'm doing well! Always happy when we get to practice together."
            ]
            return {
                "respuesta": f"{random.choice(respuestas_estado)} How about you? How are you feeling?",
                "tipo": "estado",
                "correcciones": [],
                "pregunta_seguimiento": True
            }
        
        # 3. DETECCIÓN DE DESPEDIDAS
        despedidas = ['bye', 'goodbye', 'see you', 'adiós', 'chao', 'nos vemos']
        if any(despedida in texto_lower for despedida in despedidas):
            self.estado_conversacion = "despedida"
            respuestas_despedida = [
                "Goodbye! It was wonderful practicing with you. See you next time! 🎉",
                "Bye! Keep practicing every day - you're making great progress! 👋",
                "See you later! Don't forget to practice your pronunciation daily. 📚"
            ]
            return {
                "respuesta": random.choice(respuestas_despedida),
                "tipo": "despedida",
                "correcciones": [],
                "pregunta_seguimiento": False
            }
        
        # 4. ANÁLISIS DE PRONUNCIACIÓN PARA RESPUESTAS NORMALES
        analisis = self.analizar_pronunciacion_detallada(texto_usuario, duracion_audio)
        
        # Construir respuesta conversacional
        respuesta = self._construir_respuesta_con_retroalimentacion(analisis, texto_usuario)
        
        return {
            "respuesta": respuesta,
            "tipo": "conversacion",
            "correcciones": analisis['palabras_problematicas'],
            "consejos": analisis['consejos'],
            "pregunta_seguimiento": True
        }
    
    def _construir_respuesta_con_retroalimentacion(self, analisis, texto_usuario):
        """Construye una respuesta con retroalimentación balanceada"""
        partes_respuesta = []
        
        # 1. Retroalimentación positiva
        if analisis['retroalimentacion_positiva']:
            partes_respuesta.append(f"🎉 {random.choice(analisis['retroalimentacion_positiva'])}")
        else:
            elogios = [
                "Good effort! I understood what you said.",
                "Nice job expressing yourself!",
                "Great attempt at conversation!",
                "Well done! Your message came through clearly."
            ]
            partes_respuesta.append(random.choice(elogios))
        
        # 2. Mostrar entendimiento de lo que dijo el usuario
        partes_respuesta.append(f"🗣️ You said: \"{texto_usuario}\"")
        
        # 3. Correcciones específicas de pronunciación
        if analisis['palabras_problematicas']:
            partes_respuesta.append("\n🎯 **Pronunciation tips:**")
            for problema in analisis['palabras_problematicas'][:2]:  # Máximo 2 correcciones
                partes_respuesta.append(
                    f"• For '{problema['palabra']}': {problema['explicacion']}\n"
                    f"  📝 Write it like: {problema['palabra']}\n"
                    f"  🔊 Sound like: /{problema['sonido_correcto']}/"
                )
        
        # 4. Consejos generales
        if analisis['consejos']:
            partes_respuesta.append("\n💡 **Practice tips:**")
            for consejo in analisis['consejos'][:2]:  # Máximo 2 consejos
                partes_respuesta.append(f"• {consejo}")
        
        # 5. Pregunta de seguimiento para continuar la conversación
        preguntas_seguimiento = [
            "What do you think about that?",
            "Can you tell me more about your day?",
            "How does that make you feel?",
            "What would you like to practice next?",
            "Can you give me another example?",
            "What are your plans for the rest of the day?",
            "Why do you think that is important?",
            "How was your experience with that?",
            "What would you do differently next time?"
        ]
        
        partes_respuesta.append(f"\n💬 **Let's continue our conversation:** {random.choice(preguntas_seguimiento)}")
        
        return "\n".join(partes_respuesta)

# Instancia global del sistema coach mejorado
coach_mejorado = SistemaCoach()

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

        # ✅ CORRECCIÓN DEFINITIVA - SIEMPRE TRADUCIR DESDE ESPAÑOL EN FÁCIL Y NORMAL
        if dificultad in ['fácil', 'normal']:
            # Para fácil y normal, SIEMPRE traducir del español al inglés
            traduccion = translator.translate(palabra_original, src='es', dest='en')
            traduccion_correcta = traduccion.text
            print(f"🔄 Traducción ES→EN: '{palabra_original}' -> '{traduccion_correcta}'")
        else:
            # En difícil, las frases YA están en inglés
            traduccion_correcta = palabra_original
            print(f"🎓 Dificultad difícil - Usando original: '{traduccion_correcta}'")

        # Limpiar respuestas
        respuesta_limpia = respuesta_usuario.lower().strip()
        correcta_limpia = traduccion_correcta.lower().strip()
        
        print(f"🔍 Comparando: '{respuesta_limpia}' vs '{correcta_limpia}'")
        
        # ✅ COMPARACIÓN MÁS FLEXIBLE PERO PRECISA
        es_correcta = _es_respuesta_correcta(respuesta_limpia, correcta_limpia, dificultad)
        
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

def _es_respuesta_correcta(respuesta, correcta, dificultad):
    """Comparación inteligente según dificultad"""
    
    # Para dificultad fácil, ser más flexible
    if dificultad == 'fácil':
        # Solo comparar palabras clave (sin artículos, sin puntuación)
        articulos = ['the ', 'a ', 'an ']
        respuesta_limpia = respuesta
        correcta_limpia = correcta
        
        for articulo in articulos:
            respuesta_limpia = respuesta_limpia.replace(articulo, '')
            correcta_limpia = correcta_limpia.replace(articulo, '')
        
        palabras_respuesta = set(respuesta_limpia.split())
        palabras_correcta = set(correcta_limpia.split())
        
        # Si hay al menos una palabra en común, es correcto
        return len(palabras_respuesta.intersection(palabras_correcta)) > 0
    
    # Para normal y difícil, comparación más estricta pero inteligente
    similitudes = [
        respuesta == correcta,
        respuesta in correcta,
        correcta in respuesta,
        respuesta.replace('the ', '').replace('a ', '').replace('an ', '') == correcta.replace('the ', '').replace('a ', '').replace('an ', ''),
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
    """Genera preguntas conversacionales más naturales"""
    preguntas = [
        "What do you enjoy doing in your free time?",
        "Can you describe your favorite place to relax?",
        "What's something you're looking forward to this week?",
        "Tell me about a book or movie you recently enjoyed.",
        "What kind of music do you like to listen to?",
        "How do you usually spend your weekends?",
        "What's your favorite season and why?",
        "Can you describe your ideal vacation?",
        "What's a skill you'd like to learn in the future?",
        "Tell me about someone who inspires you."
    ]
    return random.choice(preguntas)

# === ENDPOINTS PRINCIPALES ===
@app.route("/conversar_audio", methods=["POST"])
def conversar_audio():
    if 'audio' not in request.files:
        return jsonify({"estado": "error", "respuesta": "No audio file"}), 400

    audio_file = request.files['audio']
    pregunta_actual = request.form.get('pregunta_actual', "")
    
    try:
        wav_buffer, duracion_audio = procesar_audio(audio_file)
        texto_usuario = transcribir_audio(wav_buffer)
        
        print(f"🗣️ Usuario dijo: '{texto_usuario}' (Duración: {duracion_audio:.2f}s)")

        if not texto_usuario:
            return jsonify({
                "estado": "error", 
                "respuesta": "I couldn't hear any speech. Please try again and speak clearly for 2-3 seconds."
            }), 400

        # ✅ USAR EL SISTEMA COACH MEJORADO
        respuesta_coach = coach_mejorado.generar_respuesta_conversacional(texto_usuario, duracion_audio)
        
        # Determinar si cambiar la pregunta
        cambiar_pregunta = respuesta_coach["pregunta_seguimiento"] and len(texto_usuario.split()) > 2
        
        # Guardar en historial
        historial.append({
            "usuario": texto_usuario,
            "eli": respuesta_coach["respuesta"],
            "duracion": duracion_audio,
            "tipo": respuesta_coach["tipo"],
            "correcciones": respuesta_coach.get("correcciones", [])
        })

        if len(historial) > 50:
            historial.pop(0)

        return jsonify({
            "estado": "exito",
            "respuesta": respuesta_coach["respuesta"],
            "transcripcion": texto_usuario,
            "nueva_pregunta": generar_pregunta() if cambiar_pregunta else pregunta_actual,
            "correcciones_pronunciacion": respuesta_coach.get("correcciones", []),
            "consejos": respuesta_coach.get("consejos", [])
        })

    except Exception as e:
        print(f"❌ Error en conversación: {e}")
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