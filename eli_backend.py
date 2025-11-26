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
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

translator = Translator()
historial = []

print("✅ Eli - Tutor Conversacional MEJORADO cargado")

# === SISTEMA COACH CONVERSACIONAL MEJORADO ===
class SistemaCoach:
    def __init__(self):
        self.estado_conversacion = "inicio"
        self.ultimo_tema = ""
        self.historial = []
        self.nivel_usuario = "principiante"  # principiante, intermedio, avanzado
    
    def detectar_nivel_usuario(self, texto, duracion_audio):
        """Detecta el nivel del usuario basado en su respuesta"""
        palabras = texto.split()
        longitud_promedio = len(palabras)
        
        # Palabras complejas que indican nivel avanzado
        palabras_avanzadas = ['although', 'however', 'therefore', 'furthermore', 'meanwhile']
        palabras_complejas = sum(1 for palabra in palabras if palabra.lower() in palabras_avanzadas)
        
        if longitud_promedio > 10 or palabras_complejas > 1:
            return "avanzado"
        elif longitud_promedio > 5 or palabras_complejas > 0:
            return "intermedio"
        else:
            return "principiante"
    
    def analizar_pronunciacion_detallada(self, texto, audio_duration):
        """Análisis detallado de pronunciación con correcciones específicas"""
        analisis = {
            'puntuacion': 0,
            'correcciones': [],
            'consejos': [],
            'palabras_problematicas': [],
            'retroalimentacion_positiva': [],
            'nivel_detectado': 'principiante'
        }
        
        palabras = texto.lower().split()
        
        # Detectar nivel
        analisis['nivel_detectado'] = self.detectar_nivel_usuario(texto, audio_duration)
        
        # Diccionario expandido de palabras comúnmente mal pronunciadas
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
            'house': {'sonido_correcto': 'haʊs', 'explicacion': 'Sonido "ou" como en "now"'},
            'people': {'sonido_correcto': 'piːpəl', 'explicacion': 'Pronuncia ambas "p" claramente'},
            'because': {'sonido_correcto': 'bɪˈkɔz', 'explicacion': 'Énfasis en la segunda sílaba'},
            'friend': {'sonido_correcto': 'frɛnd', 'explicacion': 'Pronuncia la "r" y termina con "end"'},
        }
        
        # Detectar palabras problemáticas
        for palabra in palabras:
            palabra_limpia = re.sub(r'[^\w\s]', '', palabra.lower())
            if palabra_limpia in problemas_pronunciacion:
                correccion = problemas_pronunciacion[palabra_limpia]
                analisis['palabras_problematicas'].append({
                    'palabra': palabra_limpia,
                    'sonido_correcto': correccion['sonido_correcto'],
                    'explicacion': correccion['explicacion']
                })
        
        # Análisis de fluidez según nivel
        if analisis['nivel_detectado'] == "principiante":
            if len(palabras) < 3:
                analisis['consejos'].append("💡 Intenta formar oraciones más largas (mínimo 3 palabras)")
            if audio_duration < 1.5:
                analisis['consejos'].append("⏱️ Habla por al menos 2 segundos para practicar ritmo")
        elif analisis['nivel_detectado'] == "intermedio":
            if len(palabras) > 8:
                analisis['retroalimentacion_positiva'].append("¡Excelente! Estás usando oraciones complejas")
            if audio_duration > 3.0:
                analisis['retroalimentacion_positiva'].append("🎤 Buena duración y fluidez")
        
        return analisis

    def generar_respuesta_pedagogica(self, texto_usuario, duracion_audio=0):
        """Genera respuestas que enseñan y guían al estudiante"""
        texto_lower = texto_usuario.lower().strip()
        
        # Si el usuario no sabe qué decir
        if len(texto_usuario.split()) < 2 or texto_usuario.lower() in ['i dont know', 'no sé', 'no se', 'i dont know what to say']:
            return {
                "respuesta": "🤔 **No worries! Let me help you.**\n\n📝 **You can say something like:**\n• \"I'm not sure what to say, but I'm practicing my English\"\n• \"This is difficult for me, but I want to learn\"\n• \"Can you give me an example of what to say?\"\n\n💡 **Tip:** Don't be afraid to make mistakes! That's how we learn. Try recording one of these examples!",
                "tipo": "ayuda",
                "correcciones": [],
                "pregunta_seguimiento": True,
                "ejemplos_respuesta": [
                    "I'm not sure what to say, but I'm practicing my English",
                    "This is difficult for me, but I want to learn",
                    "Can you give me an example of what to say?"
                ]
            }
        
        # Si el usuario pide ayuda explícitamente
        if any(palabra in texto_lower for palabra in ['help', 'ayuda', 'how do i say', 'qué digo']):
            return {
                "respuesta": "🎯 **Of course! I'm here to help you.**\n\n💬 **For this question, you could talk about:**\n• Your daily routine\n• Your hobbies and interests\n• Your family or friends\n• Your goals or dreams\n\n📝 **Example response:** \"I usually wake up at 7 am, have breakfast, and then go to school. After school, I like to watch movies or play video games with my friends.\"\n\n🔁 **Now you try!** Record yourself saying something similar.",
                "tipo": "ayuda_explicita",
                "correcciones": [],
                "pregunta_seguimiento": True,
                "ejemplos_respuesta": [
                    "I usually wake up at 7 am and go to school",
                    "After school, I like to watch movies or play video games",
                    "On weekends, I spend time with my family and friends"
                ]
            }
        
        # Análisis normal con coaching mejorado
        analisis = self.analizar_pronunciacion_detallada(texto_usuario, duracion_audio)
        return self._construir_respuesta_educativa(analisis, texto_usuario)

    def _construir_respuesta_educativa(self, analisis, texto_usuario):
        """Construye una respuesta que realmente enseña"""
        partes_respuesta = []
        
        # 1. Saludo personalizado según nivel
        saludos_nivel = {
            "principiante": "🎉 **Great effort!** I can see you're starting your English journey!",
            "intermedio": "🌟 **Well done!** You're making good progress in English!",
            "avanzado": "💫 **Excellent!** Your English is becoming very fluent!"
        }
        partes_respuesta.append(saludos_nivel.get(analisis['nivel_detectado'], "🎉 Great job!"))
        
        # 2. Mostrar entendimiento
        partes_respuesta.append(f"🗣️ **You said:** \"{texto_usuario}\"")
        
        # 3. Correcciones específicas (máximo 2)
        if analisis['palabras_problematicas']:
            partes_respuesta.append("\n🎯 **Pronunciation Focus:**")
            for problema in analisis['palabras_problematicas'][:2]:
                partes_respuesta.append(
                    f"• **{problema['palabra']}**: {problema['explicacion']}\n"
                    f"  🔤 **Write it:** {problema['palabra']}\n"
                    f"  🔊 **Sound it:** /{problema['sonido_correcto']}/"
                )
        
        # 4. Consejos según nivel
        if analisis['consejos']:
            partes_respuesta.append("\n💡 **Practice Tips:**")
            for consejo in analisis['consejos'][:2]:
                partes_respuesta.append(f"• {consejo}")
        
        # 5. Retroalimentación positiva
        if analisis['retroalimentacion_positiva']:
            partes_respuesta.append("\n⭐ **What you're doing well:**")
            for positivo in analisis['retroalimentacion_positiva']:
                partes_respuesta.append(f"• {positivo}")
        
        # 6. Pregunta de seguimiento adaptada al nivel
        pregunta = self._generar_pregunta_nivel(analisis['nivel_detectado'])
        partes_respuesta.append(f"\n💬 **Let's continue:** {pregunta}")
        
        return {
            "respuesta": "\n".join(partes_respuesta),
            "tipo": "conversacion",
            "correcciones": analisis['palabras_problematicas'],
            "consejos": analisis['consejos'],
            "pregunta_seguimiento": True,
            "nivel_detectado": analisis['nivel_detectado']
        }
    
    def _generar_pregunta_nivel(self, nivel):
        """Genera preguntas adaptadas al nivel del usuario"""
        preguntas = {
            "principiante": [
                "What is your favorite color?",
                "Do you have any pets?",
                "What food do you like?",
                "How old are you?",
                "Where do you live?"
            ],
            "intermedio": [
                "What do you like to do on weekends?",
                "Can you describe your best friend?",
                "What's your favorite season and why?",
                "What are your plans for next weekend?",
                "Tell me about your family."
            ],
            "avanzado": [
                "What are your goals for the future?",
                "How do you think technology has changed education?",
                "What's your opinion on social media?",
                "Describe a challenge you've overcome recently.",
                "What does success mean to you?"
            ]
        }
        return random.choice(preguntas.get(nivel, preguntas["principiante"]))

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
        
        # 2. RESPUESTAS PEDAGÓGICAS PARA AYUDAR
        respuesta_pedagogica = self.generar_respuesta_pedagogica(texto_usuario, duracion_audio)
        if respuesta_pedagogica:
            return respuesta_pedagogica
        
        # 3. ANÁLISIS NORMAL
        analisis = self.analizar_pronunciacion_detallada(texto_usuario, duracion_audio)
        return self._construir_respuesta_educativa(analisis, texto_usuario)

# Instancia global del sistema coach mejorado
coach_mejorado = SistemaCoach()

# === VOCABULARIO MEJORADO PARA EL JUEGO ===
vocabulario = {
    "fácil": [
        "casa", "perro", "gato", "sol", "agua", "comida", "amigo", 
        "familia", "tiempo", "música", "libro", "escuela", "maestro",
        "estudiante", "ciudad", "país", "número", "color", "día", "noche"
    ],
    "normal": [
        "El gato está en la mesa",
        "Me gusta la música",
        "Tengo un perro grande", 
        "Hoy hace mucho sol",
        "Vamos a la escuela",
        "Mi familia es importante",
        "El libro es interesante",
        "Necesito beber agua",
        "Mi amigo viene hoy",
        "Qué tiempo hace hoy?"
    ],
    "difícil": [
        "The scientific research demonstrated significant improvements",
        "Global economic trends indicate substantial growth",
        "Environmental sustainability requires collaborative efforts",
        "Technological advancements continue to revolutionize",
        "Cognitive behavioral therapy has proven effective"
    ]
}

# === ENDPOINTS DEL JUEGO DE VOCABULARIO CORREGIDOS ===
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
        logger.error(f"❌ Error en /juego/palabra: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/juego/validar", methods=["POST"])
def validar_respuesta_juego():
    try:
        data = request.json
        palabra_original = data.get('palabra_original', '')
        respuesta_usuario = data.get('respuesta_usuario', '')
        dificultad = data.get('dificultad', 'fácil')
        
        print(f"🎯 Validando: '{palabra_original}' -> '{respuesta_usuario}' (Dificultad: {dificultad})")

        # ✅ DETECCIÓN DE IDIOMA MEJORADA
        # Primero verificamos si el usuario habló en inglés
        if respuesta_usuario.strip():
            try:
                deteccion = translator.detect(respuesta_usuario)
                idioma_detectado = deteccion.lang
                confianza = getattr(deteccion, 'confidence', 0.0)
                
                print(f"🌐 Idioma detectado: {idioma_detectado} (confianza: {confianza})")
                
                # Si detectamos español con alta confianza, es incorrecto
                if idioma_detectado == 'es' and confianza > 0.7:
                    return jsonify({
                        "es_correcta": False,
                        "respuesta_usuario": respuesta_usuario,
                        "traduccion_correcta": "",
                        "palabra_original": palabra_original,
                        "puntos_obtenidos": 0,
                        "mensaje": "Parece que hablaste en español. ¡Intenta decirlo en inglés! 🎯",
                        "consejo": "Recuerda: debes decir la palabra en inglés, no en español."
                    })
            except Exception as e:
                print(f"⚠️ Error en detección de idioma: {e}")

        # ✅ LÓGICA DE TRADUCCIÓN CORREGIDA
        if dificultad in ['fácil', 'normal']:
            # Para fácil y normal, traducir del español al inglés
            traduccion = translator.translate(palabra_original, src='es', dest='en')
            traduccion_correcta = traduccion.text.lower().strip()
            print(f"🔄 Traducción ES→EN: '{palabra_original}' -> '{traduccion_correcta}'")
        else:
            # En difícil, las frases YA están en inglés
            traduccion_correcta = palabra_original.lower().strip()
            print(f"🎓 Dificultad difícil - Usando original: '{traduccion_correcta}'")

        # Limpiar respuestas
        respuesta_limpia = respuesta_usuario.lower().strip()
        
        print(f"🔍 Comparando: '{respuesta_limpia}' vs '{traduccion_correcta}'")
        
        # ✅ COMPARACIÓN INTELIGENTE MEJORADA
        es_correcta = _es_respuesta_correcta_mejorada(respuesta_limpia, traduccion_correcta, dificultad)
        
        # Puntos basados en la dificultad
        puntos_obtenidos = {
            "fácil": 10,
            "normal": 25,
            "difícil": 50
        }[dificultad] if es_correcta else 0

        mensaje = "¡Correcto! 🎉" if es_correcta else "¡Casi! Sigue practicando 💪"
        
        print(f"✅ Validación: {es_correcta} - Puntos: {puntos_obtenidos}")
        
        return jsonify({
            "es_correcta": es_correcta,
            "respuesta_usuario": respuesta_usuario,
            "traduccion_correcta": traduccion_correcta,
            "palabra_original": palabra_original,
            "puntos_obtenidos": puntos_obtenidos,
            "mensaje": mensaje
        })
        
    except Exception as e:
        print(f"❌ Error en validación del juego: {e}")
        return jsonify({
            "error": f"Error en validación: {str(e)}",
            "es_correcta": False,
            "puntos_obtenidos": 0
        }), 500

def _es_respuesta_correcta_mejorada(respuesta, correcta, dificultad):
    """Comparación inteligente mejorada"""
    
    # Para dificultad fácil, ser más flexible
    if dificultad == 'fácil':
        # Eliminar artículos y puntuación
        articulos = ['the ', 'a ', 'an ']
        respuesta_limpia = respuesta
        correcta_limpia = correcta
        
        for articulo in articulos:
            respuesta_limpia = respuesta_limpia.replace(articulo, '')
            correcta_limpia = correcta_limpia.replace(articulo, '')
        
        # Comparar palabras clave
        palabras_respuesta = set(respuesta_limpia.split())
        palabras_correcta = set(correcta_limpia.split())
        
        return len(palabras_respuesta.intersection(palabras_correcta)) > 0
    
    # Para normal y difícil, comparación más precisa
    similitudes = [
        respuesta == correcta,
        respuesta in correcta,
        correcta in respuesta,
        respuesta.replace('the ', '').replace('a ', '').replace('an ', '') == 
        correcta.replace('the ', '').replace('a ', '').replace('an ', ''),
        respuesta.replace("'s", '').replace("'", '') == correcta.replace("'s", '').replace("'", ''),
        respuesta.replace('ing', 'in') == correcta.replace('ing', 'in')  # Flexibilidad en gerundios
    ]
    
    return any(similitudes)

# === FUNCIONES DE AUDIO MEJORADAS ===
def procesar_audio(audio_file):
    try:
        audio_bytes = audio_file.read()
        
        # Detectar formato y procesar
        if audio_file.filename and audio_file.filename.lower().endswith('.m4a'):
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="m4a")
        elif audio_file.filename and audio_file.filename.lower().endswith('.mp3'):
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
        else:
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        
        # Optimizar audio para reconocimiento
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

# === ENDPOINTS PRINCIPALES MEJORADOS ===
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
                "respuesta": "🎤 **I couldn't hear any speech.**\n\n💡 **Tips for better recording:**\n• Speak clearly for 2-3 seconds\n• Make sure you're in a quiet place\n• Hold the phone closer to your mouth\n• Try again with a complete sentence"
            }), 400

        # ✅ USAR EL SISTEMA COACH MEJORADO
        respuesta_coach = coach_mejorado.generar_respuesta_conversacional(texto_usuario, duracion_audio)
        
        # Guardar en historial
        historial.append({
            "usuario": texto_usuario,
            "eli": respuesta_coach["respuesta"],
            "duracion": duracion_audio,
            "tipo": respuesta_coach["tipo"],
            "correcciones": respuesta_coach.get("correcciones", []),
            "nivel": respuesta_coach.get("nivel_detectado", "principiante")
        })

        if len(historial) > 50:
            historial.pop(0)

        return jsonify({
            "estado": "exito",
            "respuesta": respuesta_coach["respuesta"],
            "transcripcion": texto_usuario,
            "nueva_pregunta": coach_mejorado._generar_pregunta_nivel(
                respuesta_coach.get("nivel_detectado", "principiante")
            ),
            "correcciones_pronunciacion": respuesta_coach.get("correcciones", []),
            "consejos": respuesta_coach.get("consejos", []),
            "nivel_detectado": respuesta_coach.get("nivel_detectado", "principiante"),
            "ejemplos_respuesta": respuesta_coach.get("ejemplos_respuesta", [])
        })

    except Exception as e:
        print(f"❌ Error en conversación: {e}")
        return jsonify({
            "estado": "error",
            "respuesta": f"❌ **Error processing audio:** {str(e)}\n\n💡 Please try recording again."
        }), 500

@app.route("/obtener_pregunta", methods=["GET"])
def obtener_pregunta():
    nivel = request.args.get('nivel', 'principiante')
    pregunta = coach_mejorado._generar_pregunta_nivel(nivel)
    return jsonify({"pregunta": pregunta})

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "estado": "online",
        "mensaje": "✅ Eli - Tutor Pedagógico Mejorado",
        "version": "4.0.0",
        "caracteristicas": [
            "Sistema coach pedagógico mejorado",
            "Detección de nivel automática", 
            "Correcciones de pronunciación específicas",
            "Juego de vocabulario con detección de idioma",
            "Respuestas educativas y guiadas"
        ]
    })

@app.route("/historial", methods=["GET"])
def obtener_historial():
    return jsonify({
        "total_conversaciones": len(historial),
        "historial": historial[-10:]  # Últimas 10 conversaciones
    })

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "mensaje": "🚀 Eli Backend Pedagógico funcionando correctamente",
        "version": "4.0.0",
        "endpoints": {
            "/conversar_audio": "Conversación con análisis de pronunciación",
            "/juego/palabra": "Obtener palabra para juego de traducción",
            "/juego/validar": "Validar respuesta del juego",
            "/obtener_pregunta": "Obtener pregunta conversacional",
            "/health": "Estado del sistema",
            "/historial": "Historial de conversaciones"
        }
    })

if __name__ == "__main__":
    print("🎯 Eli - Sistema Pedagógico Mejorado Activado")
    print("📚 Juego de Vocabulario con Detección de Idioma")
    print("💬 Sistema Coach con Niveles Automáticos")
    print("👨‍🏫 Respuestas Educativas y Guiadas")
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=False)