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
    "dificultades_detectadas": [],
    "progreso_semanal": {}
}

print("✅ Eli Coach - Tutor de pronunciación cargado")

def analizar_dificultades(texto_transcrito, audio_duration):
    """Analiza posibles dificultades del estudiante"""
    dificultades = []
    palabras = texto_transcrito.lower().split()
    
    # Análisis de longitud
    if len(palabras) < 2:
        dificultades.append("hablar_mas")
    elif len(palabras) > 8:
        dificultades.append("hablar_demasiado")
    
    # Análisis de duración
    if audio_duration < 1.5:
        dificultades.append("audio_corto")
    elif audio_duration > 6.0:
        dificultades.append("audio_largo")
    
    # Análisis de contenido (detección simple de errores comunes)
    if any(word in texto_transcrito.lower() for word in ['umm', 'ahh', 'ehh']):
        dificultades.append("muletillas")
    
    if texto_transcrito.strip() and len(texto_transcrito.split()) > 0:
        # Verificar si la respuesta es muy genérica
        respuestas_genericas = ['i dont know', "i don't know", 'no se', 'no sé', 'nothing', 'nada']
        if any(resp in texto_transcrito.lower() for resp in respuestas_genericas):
            dificultades.append("respuesta_generica")
    
    return dificultades

def generar_retroalimentacion_util(texto_transcrito, audio_duration, dificultades):
    """Genera retroalimentación útil para mejorar"""
    
    consejos = []
    palabras = texto_transcrito.split()
    total_palabras = len(palabras)
    
    # Consejos basados en dificultades detectadas
    if "hablar_mas" in dificultades:
        consejos.append("💡 **Try to speak a bit more**. Aim for 2-3 complete sentences.")
        consejos.append("🎯 **Practice tip**: Think of your answer before speaking, then say it clearly.")
    
    if "audio_corto" in dificultades:
        consejos.append("⏱️ **Speak for 2-3 seconds** minimum. This gives me enough to analyze.")
    
    if "muletillas" in dificultades:
        consejos.append("🗣️ **Reduce filler words** like 'umm', 'ahh'. Pause briefly instead.")
        consejos.append("🎯 **Practice**: Record yourself and notice when you use filler words.")
    
    if "respuesta_generica" in dificultades:
        consejos.append("🤔 **Elaborate more** - instead of 'I don't know', try 'I'm not sure about that because...'")
        consejos.append("💭 **Think about**: What would you say if a friend asked you this?")
    
    # Consejos generales de pronunciación
    if total_palabras >= 3:
        if audio_duration / total_palabras < 0.4:
            consejos.append("🐢 **Slow down a bit** - speaking clearly is more important than speed.")
        elif audio_duration / total_palabras > 0.8:
            consejos.append("🚀 **Good pacing**! You're speaking at a comfortable speed.")
    
    # Consejos positivos de refuerzo
    if total_palabras >= 4 and "respuesta_generica" not in dificultades:
        consejos.append("⭐ **Great job elaborating**! You're providing good details.")
    
    if not consejos:
        consejos.append("🎉 **Excellent effort**! Keep practicing regularly.")
        consejos.append("📚 **Tip**: Practice 10 minutes every day for best results.")
    
    return consejos[:3]  # Máximo 3 consejos

def proporcionar_ejemplo_respuesta(pregunta_actual):
    """Proporciona ejemplos de cómo responder"""
    
    ejemplos = {
        "what do you like to do on weekends?": [
            "On weekends, I usually go to the park with my friends and sometimes we play soccer.",
            "I enjoy watching movies and spending time with my family on weekends.",
            "My weekend routine includes studying in the morning and relaxing in the afternoon."
        ],
        "do you have any pets?": [
            "Yes, I have a dog named Max. He's very friendly and loves to play.",
            "No, I don't have any pets right now, but I'd like to get a cat someday.",
            "I have two cats and they're both very playful and cute."
        ],
        "what's your favorite food?": [
            "My favorite food is pizza because you can put many different toppings on it.",
            "I really enjoy eating tacos, especially with chicken and avocado.",
            "I love pasta dishes, particularly spaghetti with tomato sauce."
        ],
        "where would you like to travel?": [
            "I'd love to visit Japan to see the cherry blossoms and experience the culture.",
            "My dream destination is Italy because I love history and Italian food.",
            "I want to travel to Canada to see the beautiful mountains and lakes."
        ]
    }
    
    for key, examples in ejemplos.items():
        if key in pregunta_actual.lower():
            return random.choice(examples)
    
    # Ejemplo genérico si no hay coincidencia específica
    ejemplos_genericos = [
        "That's an interesting question. I think that...",
        "In my opinion, this is important because...",
        "From my experience, I would say that...",
        "I believe that... for several reasons. First...",
        "Well, there are a few things to consider. For example..."
    ]
    return random.choice(ejemplos_genericos)

def corregir_pronunciacion_palabras(texto_transcrito):
    """Detecta palabras que podrían tener problemas de pronunciación"""
    
    # Palabras comúnmente mal pronunciadas por hispanohablantes
    palabras_dificiles = {
        'the': 'th-e (pon la lengua entre los dientes)',
        'think': 'th-ink (lengua entre dientes para el "th")',
        'very': 've-ry (la "v" es con dientes en labio inferior)',
        'beach': 'bea-ch (cuidado con no decir "bitch")',
        'sheet': 'shee-t (cuidado con no decir "shit")',
        'work': 'w-ork (la "r" es suave)',
        'walk': 'w-alk (la "l" es suave)',
        'world': 'w-or-ld (pronuncia las tres sílabas)'
    }
    
    palabras_usuario = texto_transcrito.lower().split()
    correcciones = []
    
    for palabra in palabras_usuario:
        if palabra in palabras_dificiles:
            correcciones.append(f"**{palabra}**: {palabras_dificiles[palabra]}")
    
    return correcciones

def generar_respuesta_coach(texto_transcrito, audio_duration, pregunta_actual):
    """Genera respuesta como un coach de pronunciación"""
    
    # Analizar dificultades
    dificultades = analizar_dificultades(texto_transcrito, audio_duration)
    retroalimentacion = generar_retroalimentacion_util(texto_transcrito, audio_duration, dificultades)
    correcciones = corregir_pronunciacion_palabras(texto_transcrito)
    
    # Construir respuesta
    respuesta = ""
    
    # Reconocimiento positivo
    if texto_transcrito.strip():
        respuesta += f"🎯 **Good attempt!** You said: \"{texto_transcrito}\"\n\n"
    else:
        respuesta += "🎤 **I couldn't hear you clearly.** Let's try again!\n\n"
    
    # Agregar retroalimentación específica
    if retroalimentacion:
        respuesta += "💡 **Tips to improve**:\n"
        for tip in retroalimentacion:
            respuesta += f"• {tip}\n"
        respuesta += "\n"
    
    # Agregar correcciones de pronunciación si hay
    if correcciones:
        respuesta += "🗣️ **Pronunciation focus**:\n"
        for correccion in correcciones:
            respuesta += f"• {correccion}\n"
        respuesta += "\n"
    
    # Ofrecer ejemplo si hay dificultades
    if "respuesta_generica" in dificultades or not texto_transcrito.strip():
        ejemplo = proporcionar_ejemplo_respuesta(pregunta_actual)
        respuesta += f"📝 **Here's an example response**: \"{ejemplo}\"\n\n"
        respuesta += "🔁 **Now you try**! Record yourself saying a similar response.\n\n"
    else:
        # Continuar con nueva pregunta
        nueva_pregunta = generar_pregunta()
        respuesta += f"🔜 **Next practice**: {nueva_pregunta}"
    
    return respuesta, dificultades, retroalimentacion

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

# ... (las funciones procesar_audio, transcribir_audio se mantienen igual)

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

@app.route("/conversar_audio", methods=["POST"])
def conversar_audio():
    """Endpoint principal para práctica de pronunciación"""
    if 'audio' not in request.files:
        return jsonify({
            "estado": "error",
            "respuesta": "Please send an audio file."
        }), 400

    audio_file = request.files['audio']
    pregunta_actual = request.form.get('pregunta_actual', generar_pregunta())
    
    try:
        # Verificar tamaño del archivo
        audio_file.seek(0, 2)
        file_size = audio_file.tell()
        audio_file.seek(0)
        
        if file_size < 1000:
            return jsonify({
                "estado": "error",
                "respuesta": "The audio file is too short. Please record for at least 2-3 seconds."
            }), 400

        # Procesar audio
        print("🔄 Procesando audio...")
        wav_buffer, duracion_audio = procesar_audio(audio_file)

        # Transcribir audio
        print("🎯 Transcribiendo audio...")
        texto_usuario = transcribir_audio(wav_buffer)
        
        print(f"🗣️ Estudiante dijo: {texto_usuario}")

        # ✅ NUEVO ENFOQUE: COACHING EN LUGAR DE EVALUACIÓN
        print("👨‍🏫 Analizando como coach...")
        respuesta, dificultades, consejos = generar_respuesta_coach(
            texto_usuario, 
            duracion_audio, 
            pregunta_actual
        )

        # Actualizar contexto con dificultades detectadas
        for dificultad in dificultades:
            if dificultad not in contexto_conversacion["dificultades_detectadas"]:
                contexto_conversacion["dificultades_detectadas"].append(dificultad)

        # Agregar al historial
        historial.append({
            "usuario": texto_usuario,
            "eli": respuesta,
            "duracion": duracion_audio,
            "dificultades": dificultades,
            "consejos": consejos,
            "pregunta": pregunta_actual
        })

        # Limitar historial
        if len(historial) > 50:
            historial.pop(0)

        return jsonify({
            "estado": "exito",
            "respuesta": respuesta,
            "transcripcion": texto_usuario,
            "dificultades_detectadas": dificultades,
            "consejos": consejos,
            "nueva_pregunta": generar_pregunta() if "Next practice" in respuesta else pregunta_actual,
            "progreso": {
                "sesiones_hoy": len([h for h in historial if "pregunta" in h]),
                "dificultades_comunes": contexto_conversacion["dificultades_detectadas"][-5:] if contexto_conversacion["dificultades_detectadas"] else []
            }
        })

    except Exception as e:
        print(f"❌ Error general: {e}")
        traceback.print_exc()
        return jsonify({
            "estado": "error",
            "respuesta": f"Sorry, there was a technical issue. Please try again. Error: {str(e)}"
        }), 500

@app.route("/obtener_pregunta", methods=["GET"])
def obtener_pregunta():
    """Endpoint para obtener una nueva pregunta"""
    return jsonify({
        "pregunta": generar_pregunta(),
        "tipo": "conversacion"
    })

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint para verificar estado del servidor"""
    return jsonify({
        "estado": "online",
        "mensaje": "✅ Eli Coach activo - Enfoque en mejora, no en calificación",
        "estadisticas": {
            "sesiones_totales": len(historial),
            "dificultades_comunes": contexto_conversacion["dificultades_detectadas"][-5:] if contexto_conversacion["dificultades_detectadas"] else [],
            "estudiantes_activos": "preparatoria"
        }
    }), 200

@app.route("/progreso", methods=["GET"])
def obtener_progreso():
    """Endpoint para ver el progreso del estudiante"""
    return jsonify({
        "sesiones_totales": len(historial),
        "dificultades_detectadas": contexto_conversacion["dificultades_detectadas"],
        "ultimas_practicas": historial[-5:] if historial else [],
        "recomendaciones": [
            "Practice 10 minutes daily",
            "Focus on one difficulty at a time", 
            "Record yourself and compare"
        ]
    })

@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Eli Coach</title>
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
            .coach {
                color: #4FC3F7;
                font-size: 24px;
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success">👨‍🏫 Eli Coach</div>
            <div class="coach">Tutor de Pronunciación en Inglés</div>
            <div class="info">✅ Enfoque en MEJORA continua</div>
            <div class="info">🎯 Ayuda cuando no sabes responder</div>
            <div class="info">💡 Consejos prácticos personalizados</div>
            <div class="info">🚀 Para estudiantes de preparatoria</div>
            <div class="info">🔗 Usa /conversar_audio para practicar</div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    print("👨‍🏫 Eli Coach - Tutor de pronunciación cargado")
    print("🎯 Enfoque: Ayudar a mejorar, no calificar")
    print("🚀 Endpoints:")
    print("   POST /conversar_audio - Práctica principal con coaching")
    print("   GET  /obtener_pregunta - Obtener nueva pregunta")
    print("   GET  /progreso - Ver progreso del estudiante")
    print("   GET  /health - Estado del servidor")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=False)