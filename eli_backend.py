from flask import Flask, request, jsonify
from flask_cors import CORS
import speech_recognition as sr
import random
import os
import traceback
from pydub import AudioSegment
import io
import tempfile

app = Flask(__name__)
CORS(app)

historial = []

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

        # Evaluar pronunciación
        print("📊 Evaluando pronunciación...")
        evaluacion = evaluar_pronunciacion_simple(texto_usuario, duracion_audio)

        # Generar respuesta conversacional
        if texto_usuario:
            respuesta = f"Great! I heard you say: '{texto_usuario}'. {generar_pregunta()}"
        else:
            respuesta = f"Thanks for practicing! {generar_pregunta()}"

        # Agregar al historial
        historial.append({
            "usuario": texto_usuario,
            "eli": respuesta,
            "evaluacion": evaluacion
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
        
    respuesta = f"I understand you said: '{frase_usuario}'. {generar_pregunta()}"
    
    historial.append({
        "usuario": frase_usuario,
        "eli": respuesta,
        "evaluacion": None
    })
    
    return jsonify({
        "estado": "exito",
        "respuesta": respuesta,
        "retroalimentacion": "Conversación procesada"
    })

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint para verificar estado del servidor"""
    return jsonify({
        "estado": "online",
        "mensaje": "✅ Eli está vivo y escuchando 👂",
        "servicio_transcripcion": "Google Web Speech API"
    }), 200

@app.route("/")
def index():
    return "✅ Eli Pronunciation Analyzer is running! Use /conversar_audio for audio analysis.", 200

if __name__ == "__main__":
    print("✅ Eli backend cargado correctamente con SpeechRecognition")
    print("🎯 Endpoints disponibles:")
    print("   POST /conversar_audio - Para análisis de pronunciación por audio")
    print("   POST /conversar - Para conversación por texto")
    print("   GET  /health - Para verificar estado del servidor")
    
    # Configuración para Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=False)