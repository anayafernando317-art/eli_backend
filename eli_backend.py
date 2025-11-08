from flask import Flask, request, jsonify
from flask_cors import CORS
import whisper
import random
import os
import traceback
import subprocess
import librosa
import numpy as np
import tempfile

app = Flask(__name__)
CORS(app)

historial = []

def generar_pregunta():
    preguntas = [
        "What do you like to do on weekends?",
        "Do you have any pets?",
        "What’s your favorite food?",
        "Where would you like to travel?",
        "What do you usually eat for breakfast?",
        "What kind of music do you enjoy?"
    ]
    return random.choice(preguntas)

def convertir_a_wav(input_path, output_path):
    comando = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ac", "1",
        "-ar", "16000",
        "-sample_fmt", "s16",
        output_path
    ]
    subprocess.run(comando, check=True)

def analizar_calidad_audio(audio_path):
    """Analiza la calidad del audio para evaluación de pronunciación"""
    try:
        # Cargar audio con librosa
        y, sr = librosa.load(audio_path, sr=16000)
        
        # Calcular métricas de calidad
        rms_energy = np.sqrt(np.mean(y**2))
        spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
        zero_crossing_rate = np.mean(librosa.feature.zero_crossing_rate(y))
        
        # Análisis de volumen y claridad
        volumen_score = min(rms_energy * 100, 1.0)
        claridad_score = min(spectral_centroid / 5000, 1.0)
        estabilidad_score = 1.0 - min(zero_crossing_rate * 10, 1.0)
        
        # Score general de calidad de audio
        calidad_audio = (volumen_score + claridad_score + estabilidad_score) / 3
        
        return {
            "calidad_audio_score": calidad_audio,
            "volumen_score": volumen_score,
            "claridad_score": claridad_score,
            "estabilidad_score": estabilidad_score
        }
    except Exception as e:
        print(f"Error en análisis de calidad: {e}")
        return {
            "calidad_audio_score": 0.5,
            "volumen_score": 0.5,
            "claridad_score": 0.5,
            "estabilidad_score": 0.5
        }

def evaluar_pronunciacion(texto_transcrito, audio_path):
    """Evalúa la pronunciación basado en diferentes criterios"""
    
    # Métricas simuladas (en un sistema real aquí iría un modelo de pronunciación)
    try:
        # 1. Análisis de longitud del texto
        palabras = texto_transcrito.split()
        longitud_score = min(len(palabras) / 10, 1.0)  # Máximo 10 palabras = score 1.0
        
        # 2. Análisis de calidad de audio
        calidad_audio = analizar_calidad_audio(audio_path)
        
        # 3. Análisis de fluidez (simulado)
        # En un sistema real, esto analizaría pausas, velocidad, etc.
        fluidez_score = calidad_audio["estabilidad_score"] * 0.7 + random.uniform(0.2, 0.3)
        
        # 4. Score de pronunciación general (simulado)
        pronunciacion_score = (
            longitud_score * 0.3 +
            calidad_audio["calidad_audio_score"] * 0.4 +
            fluidez_score * 0.3
        )
        
        # Generar retroalimentación basada en los scores
        comentarios = []
        
        if longitud_score < 0.3:
            comentarios.append("Try to speak a bit more. Say at least 3-4 words.")
        elif longitud_score > 0.8:
            comentarios.append("Great length! You're speaking in complete sentences.")
        
        if calidad_audio["volumen_score"] < 0.4:
            comentarios.append("Speak a bit louder for better analysis.")
        elif calidad_audio["volumen_score"] > 0.8:
            comentarios.append("Good volume level!")
            
        if calidad_audio["claridad_score"] < 0.4:
            comentarios.append("Try to speak more clearly and slowly.")
        elif calidad_audio["claridad_score"] > 0.8:
            comentarios.append("Very clear speech!")
            
        if fluidez_score < 0.5:
            comentarios.append("Practice speaking more smoothly without long pauses.")
        elif fluidez_score > 0.8:
            comentarios.append("Excellent fluency!")
        
        # Comentario general basado en el score de pronunciación
        if pronunciacion_score < 0.4:
            comentarios.append("Keep practicing! Focus on speaking clearly and at a steady pace.")
        elif pronunciacion_score < 0.7:
            comentarios.append("Good effort! With more practice you'll improve quickly.")
        else:
            comentarios.append("Excellent pronunciation! You're doing great!")
        
        return {
            "pronunciacion_score": round(pronunciacion_score, 2),
            "fluidez_score": round(fluidez_score, 2),
            "longitud_score": round(longitud_score, 2),
            "calidad_audio": calidad_audio,
            "comentarios": comentarios[:3]  # Máximo 3 comentarios
        }
        
    except Exception as e:
        print(f"Error en evaluación de pronunciación: {e}")
        return {
            "pronunciacion_score": 0.5,
            "fluidez_score": 0.5,
            "longitud_score": 0.5,
            "calidad_audio": {"calidad_audio_score": 0.5},
            "comentarios": ["We're analyzing your speech. Keep practicing!"]
        }

@app.route("/conversar_audio", methods=["POST"])
def conversar_audio():
    audio = request.files.get("audio")
    if not audio:
        return jsonify({"error": "No se recibió archivo de audio"}), 400

    original_path = "temp_original.aac"
    wav_path = "temp.wav"

    try:
        audio.save(original_path)

        if os.path.getsize(original_path) < 1000:
            raise ValueError("Archivo demasiado pequeño para transcribir")

        convertir_a_wav(original_path, wav_path)

        modelo_whisper = whisper.load_model("tiny")
        resultado = modelo_whisper.transcribe(wav_path)
        texto_usuario = resultado.get("text", "").strip().lower()
        print(f"🗣️ Transcripción: {texto_usuario}")

        if not texto_usuario:
            raise ValueError("Transcripción vacía")

        # Evaluar pronunciación
        evaluacion = evaluar_pronunciacion(texto_usuario, wav_path)

        respuesta = f"Thanks for sharing! {generar_pregunta()}"
        historial.append({
            "usuario": texto_usuario,
            "eli": respuesta,
            "evaluacion": evaluacion
        })

        return jsonify({
            "respuesta": respuesta,
            "retroalimentacion": "Análisis de pronunciación completado",
            "transcripcion": texto_usuario,
            "evaluacion": evaluacion,
            "historial": historial
        })

    except Exception as e:
        print(f"❌ Error al transcribir: {e}")
        traceback.print_exc()
        return jsonify({"error": "Error al procesar el audio"}), 500
    finally:
        for path in [original_path, wav_path]:
            if os.path.exists(path):
                os.remove(path)

@app.route("/conversar", methods=["POST"])
def conversar():
    data = request.get_json()
    frase_usuario = data.get('frase_usuario', '').strip()
    
    if not frase_usuario:
        return jsonify({"error": "No se recibió frase"}), 400

    respuesta = f"Thanks for sharing! {generar_pregunta()}"
    historial.append({
        "usuario": frase_usuario,
        "eli": respuesta,
        "retroalimentacion": None
    })

    return jsonify({
        "respuesta": respuesta,
        "retroalimentacion": None,
        "transcripcion": frase_usuario,
        "historial": historial
    })

@app.route("/")
def index():
    return "✅ Eli está vivo y escuchando 👂", 200

if __name__ == "__main__":
    print("✅ Eli backend cargado correctamente")
    app.run(host="0.0.0.0", port=5000)