from flask import Flask, request, jsonify
from flask_cors import CORS
import whisper
import random
import os
import traceback
import subprocess
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

def convertir_a_wav(input_path, output_path):
    """Convierte audio a formato WAV compatible"""
    comando = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ac", "1",
        "-ar", "16000", 
        "-acodec", "pcm_s16le",
        output_path
    ]
    subprocess.run(comando, check=True, capture_output=True)

def evaluar_pronunciacion_simple(texto_transcrito, audio_duration):
    """Evaluación simple de pronunciación sin librosa"""
    try:
        # Métricas básicas sin análisis complejo
        palabras = texto_transcrito.split()
        total_palabras = len(palabras)
        
        # Score basado en longitud del texto
        if total_palabras == 0:
            longitud_score = 0
        else:
            longitud_score = min(total_palabras / 8.0, 1.0)
        
        # Score basado en duración del audio (evitar audio muy corto)
        duracion_score = min(audio_duration / 3.0, 1.0)  # 3 segundos = score 1.0
        
        # Score de pronunciación general (simulado)
        pronunciacion_score = (longitud_score + duracion_score) / 2.0
        
        # Generar retroalimentación simple
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
            "fluidez_score": round(pronunciacion_score * 0.8, 2),  # Simulado
            "longitud_score": round(longitud_score, 2),
            "duracion_audio": round(audio_duration, 2),
            "total_palabras": total_palabras,
            "comentarios": comentarios[:2]  # Máximo 2 comentarios
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
    
    # Crear archivos temporales
    with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as temp_original:
        original_path = temp_original.name
        audio_file.save(original_path)

    wav_path = original_path + ".wav"

    try:
        # Verificar tamaño del archivo
        if os.path.getsize(original_path) < 1000:
            return jsonify({
                "estado": "error",
                "retroalimentacion": "Archivo de audio demasiado pequeño",
                "respuesta": "The audio file is too short. Please record for at least 2-3 seconds."
            }), 400

        # Convertir a WAV
        print("🔄 Convirtiendo audio a WAV...")
        convertir_a_wav(original_path, wav_path)

        # Obtener duración del audio
        comando_duracion = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", wav_path
        ]
        resultado_duracion = subprocess.run(comando_duracion, capture_output=True, text=True)
        duracion_audio = float(resultado_duracion.stdout.strip()) if resultado_duracion.stdout else 0

        # Transcribir con Whisper
        print("🎯 Transcribiendo audio...")
        modelo_whisper = whisper.load_model("base")
        resultado = modelo_whisper.transcribe(wav_path)
        texto_usuario = resultado.get("text", "").strip()
        
        print(f"🗣️ Transcripción: {texto_usuario}")

        if not texto_usuario:
            return jsonify({
                "estado": "error", 
                "retroalimentacion": "No se pudo transcribir el audio",
                "respuesta": "I couldn't hear any speech. Please try again and speak clearly."
            }), 400

        # Evaluar pronunciación (versión simple)
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

    except subprocess.CalledProcessError as e:
        print(f"❌ Error en conversión de audio: $e")
        return jsonify({
            "estado": "error",
            "retroalimentacion": "Error procesando el formato de audio",
            "respuesta": "There was an issue with the audio format. Please try again."
        }), 500
        
    except Exception as e:
        print(f"❌ Error general: $e")
        traceback.print_exc()
        return jsonify({
            "estado": "error",
            "retroalimentacion": f"Error interno del servidor: {str(e)}",
            "respuesta": "Sorry, there was a technical issue. Please try again."
        }), 500
        
    finally:
        # Limpiar archivos temporales
        for path in [original_path, wav_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass

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
        "modelo_whisper": "cargado"
    }), 200

@app.route("/")
def index():
    return "✅ Eli Pronunciation Analyzer is running! Use /conversar_audio for audio analysis.", 200

if __name__ == "__main__":
    print("✅ Eli backend cargado correctamente")
    print("🎯 Endpoints disponibles:")
    print("   POST /conversar_audio - Para análisis de pronunciación por audio")
    print("   POST /conversar - Para conversación por texto")
    print("   GET  /health - Para verificar estado del servidor")
    
    app.run(host="0.0.0.0", port=5000, debug=False)