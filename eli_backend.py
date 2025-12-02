# app.py - Versión mejorada completa
from flask import Flask, request, jsonify, g
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
import uuid
import jwt
import time
from datetime import datetime, timedelta
from functools import wraps
import json
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from dataclasses import dataclass, asdict
from enum import Enum

# ============================================
# CONFIGURACIÓN
# ============================================
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-me')
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hora
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    AUDIO_FILE_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Niveles de XP
    XP_PER_CORRECT_ANSWER = 10
    XP_PER_MINUTE_CONVERSATION = 5
    DAILY_STREAK_BONUS = [50, 100, 200, 500]

# Configurar logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('eli_tutor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

translator = Translator()

print("🚀 Eli - Tutor Conversacional MEJORADO v5.0 cargado")

# ============================================
# MODELOS DE DATOS
# ============================================
@dataclass
class UserSession:
    """Modelo para sesión de usuario"""
    user_id: str
    session_id: str
    current_level: str = "principiante"
    conversation_history: List[Dict] = None
    game_stats: Dict[str, Any] = None
    pronunciation_weaknesses: List[str] = None
    strengths: List[str] = None
    created_at: datetime = None
    last_interaction: datetime = None
    xp: int = 0
    level: int = 1
    daily_streak: int = 0
    last_login_date: str = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.game_stats is None:
            self.game_stats = {
                "total_points": 0, 
                "games_played": 0,
                "correct_answers": 0,
                "total_attempts": 0
            }
        if self.pronunciation_weaknesses is None:
            self.pronunciation_weaknesses = []
        if self.strengths is None:
            self.strengths = []
        if self.created_at is None:
            self.created_at = datetime.now()
        self.last_interaction = datetime.now()
    
    def to_dict(self):
        return asdict(self)

@dataclass
class PronunciationAnalysis:
    """Modelo para análisis de pronunciación"""
    score: float
    corrections: List[Dict]
    tips: List[str]
    problem_words: List[Dict]
    positive_feedback: List[str]
    detected_level: str
    rhythm_score: float = 0.0
    intonation_pattern: str = "neutral"

@dataclass
class GameResult:
    """Modelo para resultados del juego"""
    is_correct: bool
    user_answer: str
    correct_translation: str
    original_word: str
    points_earned: int
    message: str
    xp_earned: int = 0
    accuracy: float = 0.0

class DifficultyLevel(Enum):
    EASY = "fácil"
    MEDIUM = "normal"
    HARD = "difícil"

# ============================================
# GESTIÓN DE SESIONES
# ============================================
class SessionManager:
    """Manejador de sesiones de usuario"""
    
    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}
        self.user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_ids]
    
    def create_session(self, user_id: str) -> UserSession:
        """Crea una nueva sesión para el usuario"""
        session_id = str(uuid.uuid4())
        
        # Verificar racha diaria
        today = datetime.now().strftime("%Y-%m-%d")
        session = UserSession(
            user_id=user_id,
            session_id=session_id,
            created_at=datetime.now()
        )
        
        self.sessions[session_id] = session
        
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        self.user_sessions[user_id].append(session_id)
        
        logger.info(f"Nueva sesión creada: {session_id} para usuario {user_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Obtiene una sesión por ID"""
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, **kwargs):
        """Actualiza los datos de una sesión"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            session.last_interaction = datetime.now()
    
    def cleanup_old_sessions(self, hours_old: int = 24):
        """Limpia sesiones antiguas"""
        cutoff = datetime.now() - timedelta(hours=hours_old)
        to_remove = []
        
        for session_id, session in self.sessions.items():
            if session.last_interaction < cutoff:
                to_remove.append(session_id)
        
        for session_id in to_remove:
            del self.sessions[session_id]
            logger.info(f"Sesión {session_id} removida por inactividad")

session_manager = SessionManager()

# ============================================
# SISTEMA COACH CONVERSACIONAL MEJORADO
# ============================================
class SistemaCoach:
    def __init__(self):
        self.estado_conversacion = "inicio"
        self.ultimo_tema = ""
        self.nivel_usuario = "principiante"
        
        # Temas de conversación por nivel
        self.topics = {
            "principiante": [
                "daily_routine", "family", "hobbies", "food", "weather"
            ],
            "intermedio": [
                "travel", "work", "education", "technology", "sports"
            ],
            "avanzado": [
                "environment", "politics", "culture", "science", "future_plans"
            ]
        }
    
    def detectar_nivel_usuario(self, texto: str, duracion_audio: float) -> str:
        """Detecta el nivel del usuario basado en múltiples factores"""
        
        if not texto:
            return "principiante"
        
        palabras = texto.split()
        longitud_promedio = len(palabras)
        
        # Palabras complejas que indican nivel avanzado
        palabras_avanzadas = {
            'although', 'however', 'therefore', 'furthermore', 'meanwhile',
            'consequently', 'nevertheless', 'moreover', 'otherwise'
        }
        
        # Estructuras gramaticales complejas
        estructuras_complejas = [
            r'if I were', r'I wish I had', r'should have', 
            r'not only.*but also', r'despite the fact'
        ]
        
        palabras_complejas = sum(1 for palabra in palabras 
                                if palabra.lower() in palabras_avanzadas)
        
        estructuras_count = sum(1 for estructura in estructuras_complejas 
                               if re.search(estructura, texto, re.IGNORECASE))
        
        # Puntuación basada en múltiples factores
        score = 0
        
        # Longitud del texto
        if longitud_promedio > 15:
            score += 3
        elif longitud_promedio > 8:
            score += 2
        elif longitud_promedio > 4:
            score += 1
        
        # Vocabulario complejo
        score += palabras_complejas * 2
        
        # Estructuras gramaticales
        score += estructuras_count * 3
        
        # Duración del audio (fluidez)
        if duracion_audio > 5:
            score += 2
        elif duracion_audio > 3:
            score += 1
        
        # Determinar nivel basado en score
        if score >= 8:
            return "avanzado"
        elif score >= 4:
            return "intermedio"
        else:
            return "principiante"
    
    def analizar_pronunciacion_detallada(self, texto: str, 
                                        audio_duration: float) -> PronunciationAnalysis:
        """Análisis detallado de pronunciación"""
        
        palabras = texto.lower().split()
        nivel_detectado = self.detectar_nivel_usuario(texto, audio_duration)
        
        # Diccionario expandido de problemas de pronunciación
        problemas_pronunciacion = {
            'the': {'sonido_correcto': 'ðə', 'explicacion': 'Coloca la lengua entre los dientes'},
            'think': {'sonido_correcto': 'θɪŋk', 'explicacion': 'Sonido "th" suave'},
            'this': {'sonido_correcto': 'ðɪs', 'explicacion': 'Sonido "th" vibrante'},
            'very': {'sonido_correcto': 'vɛri', 'explicacion': 'Labio inferior con dientes superiores'},
            'water': {'sonido_correcto': 'wɔːtər', 'explicacion': 'Pronuncia claramente la "t"'},
            'world': {'sonido_correcto': 'wɜːrld', 'explicacion': 'Tres sílabas: wor-l-d'},
            'right': {'sonido_correcto': 'raɪt', 'explicacion': 'Sonido "r" fuerte'},
            'light': {'sonido_correcto': 'laɪt', 'explicacion': 'Sonido "l" claro'},
            'thanks': {'sonido_correcto': 'θæŋks', 'explicacion': 'Sonido "th" al inicio'},
            'she': {'sonido_correcto': 'ʃi', 'explicacion': 'Sonido "sh" redondeando labios'},
            'usually': {'sonido_correcto': 'juːʒuəli', 'explicacion': 'Sonido "zh" como en "vision"'},
        }
        
        # Detectar palabras problemáticas
        palabras_problematicas = []
        for palabra in palabras:
            palabra_limpia = re.sub(r'[^\w\s]', '', palabra.lower())
            if palabra_limpia in problemas_pronunciacion:
                correccion = problemas_pronunciacion[palabra_limpia]
                palabras_problematicas.append({
                    'palabra': palabra_limpia,
                    'sonido_correcto': correccion['sonido_correcto'],
                    'explicacion': correccion['explicacion'],
                    'ejemplo': f"Escucha: /{correccion['sonido_correcto']}/"
                })
        
        # Calcular score de pronunciación
        score_base = 70.0  # Puntuación base
        
        # Ajustar score basado en factores
        if len(palabras_problematicas) == 0:
            score_base += 20
        elif len(palabras_problematicas) <= 2:
            score_base += 10
        
        if audio_duration > 2.0:
            score_base += 5
        
        # Limitar score a 100
        score = min(100.0, score_base)
        
        # Generar consejos según nivel
        consejos = []
        retroalimentacion_positiva = []
        
        if nivel_detectado == "principiante":
            if len(palabras) < 3:
                consejos.append("💡 Intenta formar oraciones más largas (mínimo 3 palabras)")
            if audio_duration < 1.5:
                consejos.append("⏱️ Habla por al menos 2 segundos para practicar ritmo")
            retroalimentacion_positiva.append("¡Bienvenido! Estás empezando un gran viaje de aprendizaje")
        
        elif nivel_detectado == "intermedio":
            if len(palabras) > 8:
                retroalimentacion_positiva.append("¡Excelente! Estás usando oraciones complejas")
            if audio_duration > 3.0:
                retroalimentacion_positiva.append("🎤 Buena duración y fluidez")
            consejos.append("💪 Intenta usar conectores como 'however' o 'therefore'")
        
        else:  # Avanzado
            if len(palabras) > 15:
                retroalimentacion_positiva.append("👏 Fluidez excepcional y vocabulario extenso")
            consejos.append("🎯 Enfócate en entonación y acento natural")
        
        return PronunciationAnalysis(
            score=score,
            corrections=[],
            tips=consejos,
            problem_words=palabras_problematicas,
            positive_feedback=retroalimentacion_positiva,
            detected_level=nivel_detectado,
            rhythm_score=audio_duration / len(palabras) if palabras else 0,
            intonation_pattern="neutral"
        )
    
    def generar_respuesta_pedagogica(self, texto_usuario: str, 
                                   duracion_audio: float = 0) -> Dict[str, Any]:
        """Genera respuestas que enseñan y guían al estudiante"""
        
        texto_lower = texto_usuario.lower().strip()
        
        # Si el usuario no sabe qué decir
        if len(texto_usuario.split()) < 2 or texto_usuario.lower() in [
            'i dont know', 'no sé', 'no se', 'i dont know what to say',
            'i don\'t know', 'no lo sé'
        ]:
            return {
                "respuesta": self._generar_respuesta_ayuda(),
                "tipo": "ayuda",
                "correcciones": [],
                "pregunta_seguimiento": True,
                "ejemplos_respuesta": [
                    "I'm not sure what to say, but I'm practicing my English",
                    "This is difficult for me, but I want to learn",
                    "Can you give me an example of what to say?"
                ],
                "nivel_detectado": "principiante"
            }
        
        # Si el usuario pide ayuda explícitamente
        if any(palabra in texto_lower for palabra in [
            'help', 'ayuda', 'how do i say', 'qué digo', 'what should i say'
        ]):
            return {
                "respuesta": self._generar_respuesta_ayuda_explicita(),
                "tipo": "ayuda_explicita",
                "correcciones": [],
                "pregunta_seguimiento": True,
                "ejemplos_respuesta": [
                    "I usually wake up at 7 am and go to school",
                    "After school, I like to watch movies or play video games",
                    "On weekends, I spend time with my family and friends"
                ],
                "nivel_detectado": self.detectar_nivel_usuario(texto_usuario, duracion_audio)
            }
        
        # Análisis normal con coaching mejorado
        analisis = self.analizar_pronunciacion_detallada(texto_usuario, duracion_audio)
        return self._construir_respuesta_educativa(analisis, texto_usuario)
    
    def _generar_respuesta_ayuda(self) -> str:
        """Genera respuesta de ayuda para usuarios que no saben qué decir"""
        return """🤔 **No worries! Let me help you.**

📝 **You can say something like:**
• "I'm not sure what to say, but I'm practicing my English"
• "This is difficult for me, but I want to learn"
• "Can you give me an example of what to say?"

💡 **Tip:** Don't be afraid to make mistakes! That's how we learn. 
Try recording one of these examples!

🎯 **Practice Tip:** Start with simple sentences about your daily life."""
    
    def _generar_respuesta_ayuda_explicita(self) -> str:
        """Genera respuesta cuando el usuario pide ayuda explícitamente"""
        return """🎯 **Of course! I'm here to help you.**

💬 **For this question, you could talk about:**
• Your daily routine
• Your hobbies and interests  
• Your family or friends
• Your goals or dreams

📝 **Example response:** "I usually wake up at 7 am, have breakfast, and then go to school. 
After school, I like to watch movies or play video games with my friends."

🔁 **Now you try!** Record yourself saying something similar.

💪 **Remember:** Focus on clear pronunciation, not perfection!"""
    
    def _construir_respuesta_educativa(self, analisis: PronunciationAnalysis, 
                                     texto_usuario: str) -> Dict[str, Any]:
        """Construye una respuesta que realmente enseña"""
        
        partes_respuesta = []
        
        # 1. Saludo personalizado según nivel
        saludos_nivel = {
            "principiante": "🎉 **Great effort!** I can see you're starting your English journey!",
            "intermedio": "🌟 **Well done!** You're making good progress in English!",
            "avanzado": "💫 **Excellent!** Your English is becoming very fluent!"
        }
        partes_respuesta.append(
            saludos_nivel.get(analisis.detected_level, "🎉 Great job!")
        )
        
        # 2. Mostrar entendimiento
        partes_respuesta.append(f"🗣️ **You said:** \"{texto_usuario}\"")
        
        # 3. Puntuación de pronunciación
        partes_respuesta.append(
            f"📊 **Pronunciation Score:** {analisis.score:.1f}/100"
        )
        
        # 4. Correcciones específicas
        if analisis.problem_words:
            partes_respuesta.append("\n🎯 **Pronunciation Focus:**")
            for problema in analisis.problem_words[:3]:  # Máximo 3 correcciones
                partes_respuesta.append(
                    f"• **{problema['palabra']}**: {problema['explicacion']}\n"
                    f"  🔤 **Write it:** {problema['palabra']}\n"
                    f"  🔊 **Sound it:** {problema['ejemplo']}"
                )
        
        # 5. Consejos según nivel
        if analisis.tips:
            partes_respuesta.append("\n💡 **Practice Tips:**")
            for consejo in analisis.tips[:2]:
                partes_respuesta.append(f"• {consejo}")
        
        # 6. Retroalimentación positiva
        if analisis.positive_feedback:
            partes_respuesta.append("\n⭐ **What you're doing well:**")
            for positivo in analisis.positive_feedback:
                partes_respuesta.append(f"• {positivo}")
        
        # 7. Pregunta de seguimiento adaptada
        pregunta = self._generar_pregunta_nivel(analisis.detected_level)
        partes_respuesta.append(f"\n💬 **Let's continue:** {pregunta}")
        
        # 8. Sugerencia de práctica adicional
        if analisis.score < 70:
            partes_respuesta.append(
                "\n🔁 **Try repeating:** Say it again, focusing on the corrections above."
            )
        
        return {
            "respuesta": "\n".join(partes_respuesta),
            "tipo": "conversacion",
            "correcciones": analisis.problem_words,
            "consejos": analisis.tips,
            "pregunta_seguimiento": True,
            "nivel_detectado": analisis.detected_level,
            "pronunciation_score": analisis.score,
            "next_question": pregunta
        }
    
    def _generar_pregunta_nivel(self, nivel: str) -> str:
        """Genera preguntas adaptadas al nivel del usuario"""
        
        preguntas = {
            "principiante": [
                "What is your favorite color?",
                "Do you have any pets?",
                "What food do you like?",
                "How old are you?",
                "Where do you live?",
                "What's your favorite animal?",
                "Do you like sports?",
                "What time do you wake up?",
                "How many people are in your family?",
                "What's your favorite day of the week?"
            ],
            "intermedio": [
                "What do you like to do on weekends?",
                "Can you describe your best friend?",
                "What's your favorite season and why?",
                "What are your plans for next weekend?",
                "Tell me about your family.",
                "What was the last movie you watched?",
                "What's your favorite type of music?",
                "Describe your ideal vacation.",
                "What's the most interesting place you've visited?",
                "What are your hobbies?"
            ],
            "avanzado": [
                "What are your goals for the future?",
                "How do you think technology has changed education?",
                "What's your opinion on social media?",
                "Describe a challenge you've overcome recently.",
                "What does success mean to you?",
                "How has your culture influenced your personality?",
                "What global issue concerns you the most?",
                "Describe a book that changed your perspective.",
                "What skills do you think will be important in 10 years?",
                "How do you balance work and personal life?"
            ]
        }
        
        return random.choice(preguntas.get(nivel, preguntas["principiante"]))
    
    def generar_respuesta_conversacional(self, texto_usuario: str, 
                                       duracion_audio: float = 0) -> Dict[str, Any]:
        """Genera respuestas naturales y mantiene la conversación"""
        
        texto_lower = texto_usuario.lower().strip()
        
        # 1. Detección de saludos
        saludos = ['hello', 'hi', 'hey', 'hola', 'good morning', 
                  'good afternoon', 'good evening', 'good night']
        
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
                "pregunta_seguimiento": True,
                "nivel_detectado": "principiante"
            }
        
        # 2. Respuestas pedagógicas para ayudar
        respuesta_pedagogica = self.generar_respuesta_pedagogica(
            texto_usuario, duracion_audio
        )
        
        if respuesta_pedagogica:
            return respuesta_pedagogica
        
        # 3. Análisis normal
        analisis = self.analizar_pronunciacion_detallada(texto_usuario, duracion_audio)
        return self._construir_respuesta_educativa(analisis, texto_usuario)

# Instancia global del sistema coach
coach_mejorado = SistemaCoach()

# ============================================
# SISTEMA DE JUEGO MEJORADO
# ============================================
class VocabularyGame:
    """Sistema de juego de vocabulario mejorado"""
    
    def __init__(self):
        self.vocabulario = self._cargar_vocabulario()
        self.user_stats = {}
    
    def _cargar_vocabulario(self) -> Dict[str, List[str]]:
        """Carga el vocabulario desde una fuente (podría ser una base de datos)"""
        return {
            "fácil": [
                "casa", "perro", "gato", "sol", "agua", "comida", "amigo", 
                "familia", "tiempo", "música", "libro", "escuela", "maestro",
                "estudiante", "ciudad", "país", "número", "color", "día", "noche",
                "coche", "mesa", "silla", "puerta", "ventana", "manzana", "naranja",
                "leche", "pan", "arroz", "playa", "montaña", "río", "bosque"
            ],
            "normal": [
                "El gato está en la mesa",
                "Me gusta la música rock",
                "Tengo un perro grande y juguetón", 
                "Hoy hace mucho sol y calor",
                "Vamos a la escuela todos los días",
                "Mi familia es muy importante para mí",
                "El libro es interesante y educativo",
                "Necesito beber agua fresca",
                "Mi amigo viene hoy a visitarme",
                "Qué tiempo hace hoy en tu ciudad?",
                "La comida está muy deliciosa",
                "Estoy aprendiendo inglés rápido",
                "La ciudad es grande y moderna",
                "Me encanta la playa en verano",
                "El estudiante estudia mucho"
            ],
            "difícil": [
                "The scientific research demonstrated significant improvements",
                "Global economic trends indicate substantial growth potential",
                "Environmental sustainability requires collaborative efforts worldwide",
                "Technological advancements continue to revolutionize industries",
                "Cognitive behavioral therapy has proven effective for many",
                "The entrepreneur developed an innovative business strategy",
                "Artificial intelligence is transforming various sectors globally",
                "Renewable energy sources are essential for sustainable development",
                "The researcher conducted a comprehensive literature review",
                "International collaboration fosters scientific breakthroughs"
            ]
        }
    
    def obtener_palabra_aleatoria(self, dificultad: str) -> Dict[str, Any]:
        """Obtiene una palabra aleatoria según la dificultad"""
        
        if dificultad not in self.vocabulario:
            dificultad = "fácil"
        
        palabra = random.choice(self.vocabulario[dificultad])
        
        # Puntos base según dificultad
        puntos_base = {
            "fácil": 10,
            "normal": 25, 
            "difícil": 50
        }[dificultad]
        
        # Tiempo sugerido según dificultad
        tiempo_sugerido = {
            "fácil": 15,
            "normal": 30,
            "difícil": 45
        }[dificultad]
        
        # Pista según dificultad
        pista = self._generar_pista(palabra, dificultad)
        
        return {
            "palabra": palabra,
            "dificultad": dificultad,
            "puntos_base": puntos_base,
            "tiempo_sugerido": tiempo_sugerido,
            "pista": pista,
            "id": str(uuid.uuid4())[:8]
        }
    
    def _generar_pista(self, palabra: str, dificultad: str) -> str:
        """Genera una pista para la palabra"""
        
        if dificultad == "fácil":
            # Para palabras simples, dar la primera letra
            return f"Starts with: '{palabra[0].upper()}'"
        
        elif dificultad == "normal":
            # Para frases, dar la traducción palabra por palabra
            try:
                traduccion = translator.translate(palabra, src='es', dest='en')
                palabras_traduccion = traduccion.text.split()
                
                if len(palabras_traduccion) > 2:
                    return f"Translates to: '{' '.join(palabras_traduccion[:2])}...'"
                else:
                    return f"Translates to: '{traduccion.text}'"
            except:
                return "Try to pronounce each word clearly"
        
        else:  # difícil
            # Para frases complejas, dar una palabra clave
            palabras_clave = palabra.split()[:2]
            return f"Keywords: {', '.join(palabras_clave)}"
    
    def validar_respuesta(self, palabra_original: str, respuesta_usuario: str,
                         dificultad: str) -> GameResult:
        """Valida la respuesta del usuario"""
        
        try:
            # Limpiar respuestas
            respuesta_limpia = respuesta_usuario.strip().lower()
            
            # Detectar idioma
            idioma_info = self._detectar_idioma(respuesta_limpia)
            
            # Validar según dificultad
            es_correcta = False
            mensaje = ""
            traduccion_correcta = ""
            
            if dificultad in ['fácil', 'normal']:
                # Traducir del español al inglés
                traduccion = translator.translate(
                    palabra_original, 
                    src='es', 
                    dest='en'
                )
                traduccion_correcta = traduccion.text.lower().strip()
                
                # Verificar si habló en español
                if idioma_info['idioma'] == 'es' and idioma_info['confianza'] > 0.6:
                    mensaje = "¡Hablaste en español! Debes decirlo en inglés. 🎯"
                else:
                    es_correcta = self._comparar_respuestas(
                        respuesta_limpia, 
                        traduccion_correcta, 
                        dificultad
                    )
                    
                    if es_correcta:
                        mensaje = "¡Perfecto! 🎉 Pronunciación correcta."
                    else:
                        mensaje = "¡Casi! Escucha la pronunciación correcta. 💪"
            
            else:  # difícil
                # Las frases ya están en inglés
                traduccion_correcta = palabra_original.lower().strip()
                es_correcta = self._comparar_respuestas(
                    respuesta_limpia,
                    traduccion_correcta,
                    dificultad
                )
                
                if es_correcta:
                    mensaje = "¡Excelente! 👏 Pronunciación avanzada correcta."
                else:
                    mensaje = "Buena intento. Practica la pronunciación. 📚"
            
            # Calcular puntos
            puntos_base = {
                "fácil": 10,
                "normal": 25,
                "difícil": 50
            }[dificultad]
            
            puntos_obtenidos = puntos_base if es_correcta else max(1, puntos_base // 5)
            
            # Calcular XP adicional
            xp_extra = self._calcular_xp_extra(respuesta_limpia, es_correcta)
            
            return GameResult(
                is_correct=es_correcta,
                user_answer=respuesta_usuario,
                correct_translation=traduccion_correcta,
                original_word=palabra_original,
                points_earned=puntos_obtenidos,
                message=mensaje,
                xp_earned=xp_extra,
                accuracy=100.0 if es_correcta else 50.0
            )
            
        except Exception as e:
            logger.error(f"Error validando respuesta: {e}")
            
            return GameResult(
                is_correct=False,
                user_answer=respuesta_usuario,
                correct_translation="",
                original_word=palabra_original,
                points_earned=0,
                message=f"Error en validación: {str(e)[:50]}",
                xp_earned=0,
                accuracy=0.0
            )
    
    def _detectar_idioma(self, texto: str) -> Dict[str, Any]:
        """Detecta el idioma del texto"""
        try:
            if not texto:
                return {"idioma": "unknown", "confianza": 0.0}
            
            deteccion = translator.detect(texto)
            return {
                "idioma": deteccion.lang,
                "confianza": getattr(deteccion, 'confidence', 0.0)
            }
        except:
            return {"idioma": "unknown", "confianza": 0.0}
    
    def _comparar_respuestas(self, respuesta: str, correcta: str, 
                           dificultad: str) -> bool:
        """Comparación inteligente de respuestas"""
        
        # Normalizar texto
        respuesta_norm = self._normalizar_texto(respuesta)
        correcta_norm = self._normalizar_texto(correcta)
        
        # Comparación exacta
        if respuesta_norm == correcta_norm:
            return True
        
        # Para dificultad fácil, ser más flexible
        if dificultad == "fácil":
            # Verificar si contiene la palabra clave
            palabras_clave = correcta_norm.split()
            for palabra in palabras_clave:
                if len(palabra) > 3 and palabra in respuesta_norm:
                    return True
        
        # Para dificultad normal, permitir pequeños errores
        elif dificultad == "normal":
            # Usar similitud de Jaccard
            palabras_respuesta = set(respuesta_norm.split())
            palabras_correcta = set(correcta_norm.split())
            
            if len(palabras_correcta) == 0:
                return False
            
            interseccion = palabras_respuesta.intersection(palabras_correcta)
            similitud = len(interseccion) / len(palabras_correcta)
            
            return similitud >= 0.7
        
        # Para dificultad difícil, requerir mayor precisión
        else:
            # Comparación de secuencia
            from difflib import SequenceMatcher
            similitud = SequenceMatcher(None, respuesta_norm, correcta_norm).ratio()
            return similitud >= 0.8
        
        return False
    
    def _normalizar_texto(self, texto: str) -> str:
        """Normaliza el texto para comparación"""
        texto = texto.lower().strip()
        
        # Remover artículos comunes
        articulos = ['the ', 'a ', 'an ', 'el ', 'la ', 'los ', 'las ', 'un ', 'una ']
        for articulo in articulos:
            texto = texto.replace(articulo, ' ')
        
        # Remover puntuación
        texto = re.sub(r'[^\w\s]', '', texto)
        
        # Remover espacios extras
        texto = ' '.join(texto.split())
        
        return texto
    
    def _calcular_xp_extra(self, respuesta: str, es_correcta: bool) -> int:
        """Calcula XP extra basado en la respuesta"""
        
        if not es_correcta:
            return 1  # XP mínimo por intentar
        
        # XP basado en longitud de respuesta
        xp_longitud = min(len(respuesta.split()) * 2, 10)
        
        # XP por complejidad
        palabras_complejas = ['although', 'however', 'therefore', 'furthermore']
        xp_complejidad = sum(2 for palabra in palabras_complejas 
                           if palabra in respuesta.lower())
        
        return 5 + xp_longitud + xp_complejidad

# Instancia del juego
vocabulary_game = VocabularyGame()

# ============================================
# UTILIDADES DE AUDIO MEJORADAS
# ============================================
class AudioProcessor:
    """Procesador de audio mejorado"""
    
    def __init__(self):
        self.supported_formats = ['.wav', '.mp3', '.m4a', '.ogg', '.flac']
    
    def procesar_audio(self, audio_file) -> Tuple[io.BytesIO, float]:
        """Procesa el archivo de audio"""
        try:
            audio_bytes = audio_file.read()
            
            if len(audio_bytes) > Config.AUDIO_FILE_MAX_SIZE:
                raise ValueError(f"Audio file too large. Max size: {Config.AUDIO_FILE_MAX_SIZE/1024/1024}MB")
            
            # Detectar formato
            formato = self._detectar_formato(audio_file)
            
            # Convertir a WAV
            if formato in ['m4a', 'mp3', 'ogg', 'flac']:
                audio = AudioSegment.from_file(
                    io.BytesIO(audio_bytes), 
                    format=formato.replace('.', '')
                )
            else:
                # Asumir WAV por defecto
                audio = AudioSegment.from_file(
                    io.BytesIO(audio_bytes), 
                    format="wav"
                )
            
            # Optimizar para reconocimiento de voz
            audio = self._optimizar_audio(audio)
            duracion_audio = len(audio) / 1000.0
            
            # Exportar a buffer WAV
            wav_buffer = io.BytesIO()
            audio.export(wav_buffer, format="wav")
            wav_buffer.seek(0)
            
            logger.info(f"Audio procesado: {duracion_audio:.2f}s, formato: {formato}")
            
            return wav_buffer, duracion_audio
            
        except Exception as e:
            logger.error(f"Error procesando audio: {e}")
            raise Exception(f"Error procesando audio: {str(e)}")
    
    def _detectar_formato(self, audio_file) -> str:
        """Detecta el formato del archivo de audio"""
        if audio_file.filename:
            # Basado en extensión
            extension = os.path.splitext(audio_file.filename.lower())[1]
            if extension in self.supported_formats:
                return extension.replace('.', '')
        
        # Intento de detección por contenido
        try:
            audio_bytes = audio_file.read(1024)
            audio_file.seek(0)
            
            # Detección simple basada en magic numbers
            if audio_bytes[:4] == b'RIFF':
                return 'wav'
            elif audio_bytes[:3] == b'ID3':
                return 'mp3'
            elif audio_bytes[:4] == b'ftyp':
                return 'm4a'
        except:
            pass
        
        # Por defecto, asumir wav
        return 'wav'
    
    def _optimizar_audio(self, audio: AudioSegment) -> AudioSegment:
        """Optimiza el audio para reconocimiento de voz"""
        # Convertir a mono
        audio = audio.set_channels(1)
        
        # Establecer sample rate a 16kHz (óptimo para reconocimiento)
        audio = audio.set_frame_rate(16000)
        
        # Normalizar volumen
        audio = audio.normalize()
        
        # Reducir ruido básico (esto es una simplificación)
        # En producción, usaría una librería más avanzada como noisereduce
        
        return audio
    
    def transcribir_audio(self, wav_buffer: io.BytesIO) -> str:
        """Transcribe audio a texto usando Google Speech Recognition"""
        recognizer = sr.Recognizer()
        
        try:
            with sr.AudioFile(wav_buffer) as source:
                # Ajustar para ruido ambiental
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Grabar audio
                audio_data = recognizer.record(source)
                
                # Intentar reconocimiento con configuración mejorada
                texto = recognizer.recognize_google(
                    audio_data, 
                    language='en-US',
                    show_all=False
                )
                
                texto_limpio = texto.strip()
                logger.info(f"Audio transcrito: '{texto_limpio}'")
                
                return texto_limpio
                
        except sr.UnknownValueError:
            logger.warning("No se pudo entender el audio")
            return ""
        except sr.RequestError as e:
            logger.error(f"Error en servicio de reconocimiento: {e}")
            raise Exception(f"Error en servicio de reconocimiento: {e}")
        except Exception as e:
            logger.error(f"Error transcribiendo audio: {e}")
            return ""

# Instancia del procesador de audio
audio_processor = AudioProcessor()

# ============================================
# SISTEMA DE GAMIFICACIÓN
# ============================================
class GamificationSystem:
    """Sistema de gamificación para motivar al usuario"""
    
    def __init__(self):
        self.achievements = self._cargar_logros()
        self.user_progress = {}
    
    def _cargar_logros(self) -> List[Dict]:
        """Carga la lista de logros disponibles"""
        return [
            {
                "id": "first_steps",
                "title": "👣 Primeros Pasos",
                "description": "Completa tu primera conversación",
                "xp_reward": 50,
                "condition": lambda stats: stats.get("conversations_completed", 0) >= 1,
                "icon": "👣"
            },
            {
                "id": "chat_master",
                "title": "💬 Maestro del Chat",
                "description": "Completa 10 conversaciones",
                "xp_reward": 200,
                "condition": lambda stats: stats.get("conversations_completed", 0) >= 10,
                "icon": "💬"
            },
            {
                "id": "pronunciation_pro",
                "title": "🎤 Pro de la Pronunciación",
                "description": "Alcanza 90% en pronunciación",
                "xp_reward": 150,
                "condition": lambda stats: stats.get("pronunciation_avg", 0) >= 90,
                "icon": "🎤"
            },
            {
                "id": "vocabulary_expert",
                "title": "📚 Experto en Vocabulario",
                "description": "Gana 1000 puntos en el juego",
                "xp_reward": 300,
                "condition": lambda stats: stats.get("game_points", 0) >= 1000,
                "icon": "📚"
            },
            {
                "id": "daily_streak_3",
                "title": "🔥 Racha de 3 Días",
                "description": "Practica 3 días seguidos",
                "xp_reward": 100,
                "condition": lambda stats: stats.get("daily_streak", 0) >= 3,
                "icon": "🔥"
            },
            {
                "id": "daily_streak_7",
                "title": "🏆 Racha de 7 Días",
                "description": "Practica 7 días seguidos",
                "xp_reward": 500,
                "condition": lambda stats: stats.get("daily_streak", 0) >= 7,
                "icon": "🏆"
            },
            {
                "id": "level_up_5",
                "title": "⭐ Nivel 5 Alcanzado",
                "description": "Alcanza el nivel 5",
                "xp_reward": 250,
                "condition": lambda stats: stats.get("level", 0) >= 5,
                "icon": "⭐"
            },
            {
                "id": "perfect_score",
                "title": "💯 Puntuación Perfecta",
                "description": "Obtén 100% en pronunciación",
                "xp_reward": 100,
                "condition": lambda stats: stats.get("pronunciation_max", 0) >= 100,
                "icon": "💯"
            }
        ]
    
    def update_user_progress(self, user_id: str, stats_update: Dict):
        """Actualiza el progreso del usuario"""
        if user_id not in self.user_progress:
            self.user_progress[user_id] = {
                "total_xp": 0,
                "level": 1,
                "conversations_completed": 0,
                "game_points": 0,
                "pronunciation_avg": 0,
                "pronunciation_max": 0,
                "daily_streak": 0,
                "last_login": None,
                "achievements": []
            }
        
        user_stats = self.user_progress[user_id]
        
        # Actualizar estadísticas
        for key, value in stats_update.items():
            if key in user_stats:
                if key in ["total_xp", "game_points"]:
                    user_stats[key] += value
                elif key == "pronunciation_avg":
                    # Promedio móvil
                    current_count = user_stats.get("pronunciation_count", 0)
                    current_avg = user_stats.get("pronunciation_avg", 0)
                    new_avg = (current_avg * current_count + value) / (current_count + 1)
                    user_stats[key] = new_avg
                    user_stats["pronunciation_count"] = current_count + 1
                elif key == "pronunciation_max":
                    user_stats[key] = max(user_stats.get(key, 0), value)
                else:
                    user_stats[key] = value
        
        # Actualizar racha diaria
        today = datetime.now().strftime("%Y-%m-%d")
        if user_stats["last_login"] != today:
            if user_stats["last_login"]:
                # Verificar si fue ayer
                last_date = datetime.strptime(user_stats["last_login"], "%Y-%m-%d")
                yesterday = datetime.now() - timedelta(days=1)
                if last_date.strftime("%Y-%m-%d") == yesterday.strftime("%Y-%m-%d"):
                    user_stats["daily_streak"] += 1
                else:
                    user_stats["daily_streak"] = 1
            else:
                user_stats["daily_streak"] = 1
            
            user_stats["last_login"] = today
        
        # Calcular nivel basado en XP
        user_stats["level"] = self._calculate_level(user_stats["total_xp"])
        
        # Verificar logros desbloqueados
        new_achievements = self._check_achievements(user_id, user_stats)
        
        return {
            "stats": user_stats,
            "new_achievements": new_achievements
        }
    
    def _calculate_level(self, xp: int) -> int:
        """Calcula el nivel basado en XP"""
        # Fórmula: nivel = floor(sqrt(xp/100)) + 1
        return int((xp / 100) ** 0.5) + 1
    
    def _check_achievements(self, user_id: str, stats: Dict) -> List[Dict]:
        """Verifica qué logros ha desbloqueado el usuario"""
        unlocked = []
        
        for achievement in self.achievements:
            achievement_id = achievement["id"]
            
            # Verificar si ya está desbloqueado
            if achievement_id in stats.get("achievements", []):
                continue
            
            # Verificar condición
            if achievement["condition"](stats):
                unlocked.append(achievement)
                stats.setdefault("achievements", []).append(achievement_id)
                
                # Agregar XP del logro
                stats["total_xp"] += achievement["xp_reward"]
        
        return unlocked
    
    def get_user_stats(self, user_id: str) -> Dict:
        """Obtiene estadísticas del usuario"""
        if user_id in self.user_progress:
            stats = self.user_progress[user_id].copy()
            
            # Calcular XP para próximo nivel
            current_level = stats["level"]
            xp_for_current = (current_level - 1) ** 2 * 100
            xp_for_next = current_level ** 2 * 100
            xp_needed = xp_for_next - stats["total_xp"]
            
            stats["xp_for_next_level"] = xp_needed
            stats["progress_to_next"] = (
                (stats["total_xp"] - xp_for_current) / 
                (xp_for_next - xp_for_current)
            ) * 100
            
            return stats
        else:
            return {
                "total_xp": 0,
                "level": 1,
                "conversations_completed": 0,
                "game_points": 0,
                "pronunciation_avg": 0,
                "daily_streak": 0,
                "achievements": [],
                "xp_for_next_level": 100,
                "progress_to_next": 0
            }

# Instancia del sistema de gamificación
gamification = GamificationSystem()

# Historial global (temporal, en producción usar base de datos)
historial_conversaciones = []

# ============================================
# ENDPOINTS DE LA API
# ============================================

# Middleware para autenticación básica (simplificado)
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # En producción, usar JWT tokens
        user_id = request.headers.get('X-User-ID')
        session_id = request.headers.get('X-Session-ID')
        
        if not user_id:
            user_id = "guest_" + str(uuid.uuid4())[:8]
        
        g.user_id = user_id
        g.session_id = session_id
        
        return f(*args, **kwargs)
    return decorated_function

@app.route("/api/conversar_audio", methods=["POST"])
@require_auth
def conversar_audio():
    """Endpoint principal para conversación con audio"""
    
    if 'audio' not in request.files:
        return jsonify({
            "estado": "error", 
            "respuesta": "No audio file provided"
        }), 400
    
    audio_file = request.files['audio']
    pregunta_actual = request.form.get('pregunta_actual', "")
    
    try:
        # Procesar audio
        wav_buffer, duracion_audio = audio_processor.procesar_audio(audio_file)
        
        # Transcribir
        texto_usuario = audio_processor.transcribir_audio(wav_buffer)
        
        logger.info(f"Usuario {g.user_id} dijo: '{texto_usuario}' ({duracion_audio:.2f}s)")
        
        if not texto_usuario:
            return jsonify({
                "estado": "error", 
                "respuesta": """🎤 **I couldn't hear any speech.**

💡 **Tips for better recording:**
• Speak clearly for 2-3 seconds
• Make sure you're in a quiet place
• Hold the phone closer to your mouth
• Try again with a complete sentence

🔊 **Example:** "Hello, how are you today?"""
            }), 400
        
        # Obtener respuesta del coach
        respuesta_coach = coach_mejorado.generar_respuesta_conversacional(
            texto_usuario, 
            duracion_audio
        )
        
        # Crear o actualizar sesión
        if g.session_id and session_manager.get_session(g.session_id):
            session = session_manager.get_session(g.session_id)
            session_manager.update_session(
                g.session_id,
                conversation_history=session.conversation_history + [{
                    "timestamp": datetime.now().isoformat(),
                    "user": texto_usuario,
                    "eli": respuesta_coach["respuesta"],
                    "duration": duracion_audio,
                    "pronunciation_score": respuesta_coach.get("pronunciation_score", 0)
                }]
            )
        else:
            session = session_manager.create_session(g.user_id)
            g.session_id = session.session_id
        
        # Actualizar gamificación
        gamification.update_user_progress(g.user_id, {
            "conversations_completed": 1,
            "pronunciation_avg": respuesta_coach.get("pronunciation_score", 0),
            "pronunciation_max": respuesta_coach.get("pronunciation_score", 0)
        })
        
        # Guardar en historial global
        historial_item = {
            "user_id": g.user_id,
            "session_id": g.session_id,
            "timestamp": datetime.now().isoformat(),
            "user_input": texto_usuario,
            "eli_response": respuesta_coach["respuesta"],
            "duration": duracion_audio,
            "pronunciation_score": respuesta_coach.get("pronunciation_score", 0),
            "detected_level": respuesta_coach.get("nivel_detectado", "principiante")
        }
        historial_conversaciones.append(historial_item)
        
        # Limitar historial
        if len(historial_conversaciones) > 1000:
            historial_conversaciones.pop(0)
        
        return jsonify({
            "estado": "exito",
            "respuesta": respuesta_coach["respuesta"],
            "transcripcion": texto_usuario,
            "nueva_pregunta": respuesta_coach.get("next_question", ""),
            "correcciones_pronunciacion": respuesta_coach.get("correcciones", []),
            "consejos": respuesta_coach.get("consejos", []),
            "nivel_detectado": respuesta_coach.get("nivel_detectado", "principiante"),
            "ejemplos_respuesta": respuesta_coach.get("ejemplos_respuesta", []),
            "pronunciation_score": respuesta_coach.get("pronunciation_score", 0),
            "session_id": g.session_id,
            "xp_earned": 10  # XP base por conversación
        })
        
    except Exception as e:
        logger.error(f"Error en conversación: {traceback.format_exc()}")
        return jsonify({
            "estado": "error",
            "respuesta": f"""❌ **Error processing audio**

🔧 **Technical details:** {str(e)[:100]}

💡 **Please try:**
1. Recording again
2. Speaking more clearly
3. Using a different microphone

If the problem persists, contact support."""
        }), 500

@app.route("/api/juego/palabra", methods=["GET"])
@require_auth
def obtener_palabra_juego():
    """Obtiene una palabra para el juego de vocabulario"""
    try:
        dificultad = request.args.get('dificultad', 'fácil')
        
        # Validar dificultad
        if dificultad not in ['fácil', 'normal', 'difícil']:
            dificultad = 'fácil'
        
        # Obtener palabra aleatoria
        palabra_data = vocabulary_game.obtener_palabra_aleatoria(dificultad)
        
        # Registrar en sesión
        if g.session_id:
            session_manager.update_session(
                g.session_id,
                game_stats={
                    "last_game_word": palabra_data["palabra"],
                    "last_game_difficulty": dificultad
                }
            )
        
        return jsonify({
            "estado": "exito",
            **palabra_data
        })
        
    except Exception as e:
        logger.error(f"Error en /juego/palabra: {e}")
        return jsonify({
            "estado": "error",
            "mensaje": f"Error obteniendo palabra: {str(e)}"
        }), 500

@app.route("/api/juego/validar", methods=["POST"])
@require_auth
def validar_respuesta_juego():
    """Valida la respuesta del juego de vocabulario"""
    try:
        data = request.json
        palabra_original = data.get('palabra_original', '')
        respuesta_usuario = data.get('respuesta_usuario', '')
        dificultad = data.get('dificultad', 'fácil')
        session_id = data.get('session_id', g.session_id)
        
        logger.info(f"Validando juego: {palabra_original[:20]}... -> {respuesta_usuario[:20]}...")
        
        # Validar respuesta
        resultado = vocabulary_game.validar_respuesta(
            palabra_original, 
            respuesta_usuario, 
            dificultad
        )
        
        # Actualizar gamificación
        gamification.update_user_progress(g.user_id, {
            "game_points": resultado.points_earned
        })
        
        # Actualizar sesión
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                session.game_stats["total_points"] += resultado.points_earned
                session.game_stats["games_played"] += 1
                if resultado.is_correct:
                    session.game_stats["correct_answers"] += 1
                session.game_stats["total_attempts"] += 1
        
        return jsonify({
            "estado": "exito",
            **asdict(resultado)
        })
        
    except Exception as e:
        logger.error(f"Error en validación del juego: {e}")
        return jsonify({
            "estado": "error",
            "mensaje": f"Error en validación: {str(e)}",
            "is_correct": False,
            "points_earned": 0
        }), 500

@app.route("/api/obtener_pregunta", methods=["GET"])
@require_auth
def obtener_pregunta():
    """Obtiene una pregunta conversacional"""
    try:
        nivel = request.args.get('nivel', 'principiante')
        pregunta = coach_mejorado._generar_pregunta_nivel(nivel)
        
        return jsonify({
            "estado": "exito",
            "pregunta": pregunta,
            "nivel": nivel,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo pregunta: {e}")
        return jsonify({
            "estado": "error",
            "mensaje": str(e)
        }), 500

@app.route("/api/estadisticas", methods=["GET"])
@require_auth
def obtener_estadisticas():
    """Obtiene estadísticas del usuario"""
    try:
        stats = gamification.get_user_stats(g.user_id)
        
        # Obtener sesión actual si existe
        session_data = None
        if g.session_id:
            session = session_manager.get_session(g.session_id)
            if session:
                session_data = session.to_dict()
        
        return jsonify({
            "estado": "exito",
            "user_id": g.user_id,
            "stats": stats,
            "session": session_data,
            "total_conversations": len([h for h in historial_conversaciones 
                                       if h["user_id"] == g.user_id])
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return jsonify({
            "estado": "error",
            "mensaje": str(e)
        }), 500

@app.route("/api/historial", methods=["GET"])
@require_auth
def obtener_historial():
    """Obtiene el historial de conversaciones del usuario"""
    try:
        limite = int(request.args.get('limite', 10))
        
        # Filtrar historial por usuario
        user_historial = [
            h for h in historial_conversaciones 
            if h["user_id"] == g.user_id
        ][-limite:]
        
        return jsonify({
            "estado": "exito",
            "total": len(user_historial),
            "historial": user_historial
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        return jsonify({
            "estado": "error",
            "mensaje": str(e)
        }), 500

@app.route("/api/sesion/iniciar", methods=["POST"])
def iniciar_sesion():
    """Inicia una nueva sesión para el usuario"""
    try:
        data = request.json
        user_id = data.get('user_id', f"user_{str(uuid.uuid4())[:8]}")
        
        # Crear sesión
        session = session_manager.create_session(user_id)
        
        # Generar token JWT simple (en producción usar librería JWT completa)
        token = jwt.encode(
            {
                'user_id': user_id,
                'session_id': session.session_id,
                'exp': datetime.utcnow() + timedelta(days=7)
            },
            Config.JWT_SECRET_KEY,
            algorithm='HS256'
        )
        
        return jsonify({
            "estado": "exito",
            "user_id": user_id,
            "session_id": session.session_id,
            "token": token,
            "level": session.current_level,
            "welcome_message": "¡Bienvenido a Eli Tutor! Ready to practice your English? 🎯"
        })
        
    except Exception as e:
        logger.error(f"Error iniciando sesión: {e}")
        return jsonify({
            "estado": "error",
            "mensaje": str(e)
        }), 500

@app.route("/api/sesion/cerrar", methods=["POST"])
@require_auth
def cerrar_sesion():
    """Cierra la sesión del usuario"""
    try:
        if g.session_id and g.session_id in session_manager.sessions:
            # En producción, invalidar token
            del session_manager.sessions[g.session_id]
            
            if g.user_id in session_manager.user_sessions:
                session_manager.user_sessions[g.user_id] = [
                    sid for sid in session_manager.user_sessions[g.user_id]
                    if sid != g.session_id
                ]
        
        return jsonify({
            "estado": "exito",
            "mensaje": "Sesión cerrada correctamente"
        })
        
    except Exception as e:
        logger.error(f"Error cerrando sesión: {e}")
        return jsonify({
            "estado": "error",
            "mensaje": str(e)
        }), 500

@app.route("/api/salud", methods=["GET"])
def health_check():
    """Endpoint de salud del sistema"""
    return jsonify({
        "estado": "online",
        "servicio": "Eli - Tutor Pedagógico Mejorado",
        "version": "5.0.0",
        "timestamp": datetime.now().isoformat(),
        "estadisticas": {
            "sesiones_activas": len(session_manager.sessions),
            "conversaciones_totales": len(historial_conversaciones),
            "usuarios_unicos": len(session_manager.user_sessions)
        },
        "caracteristicas": [
            "Sistema coach pedagógico con detección de nivel",
            "Análisis de pronunciación detallado",
            "Juego de vocabulario con gamificación",
            "Sistema de logros y progresión",
            "Procesamiento de audio mejorado",
            "Gestión de sesiones de usuario"
        ]
    })

@app.route("/", methods=["GET"])
def home():
    """Página principal de la API"""
    return jsonify({
        "mensaje": "🚀 Eli Backend Pedagógico - API v5.0",
        "version": "5.0.0",
        "documentacion": {
            "endpoints_principales": {
                "POST /api/conversar_audio": "Conversación con análisis de pronunciación",
                "GET /api/juego/palabra": "Obtener palabra para juego de traducción",
                "POST /api/juego/validar": "Validar respuesta del juego",
                "GET /api/obtener_pregunta": "Obtener pregunta conversacional",
                "GET /api/estadisticas": "Obtener estadísticas del usuario",
                "GET /api/historial": "Historial de conversaciones",
                "POST /api/sesion/iniciar": "Iniciar sesión",
                "POST /api/sesion/cerrar": "Cerrar sesión",
                "GET /api/salud": "Estado del sistema"
            },
            "autenticacion": "Incluir X-User-ID y X-Session-ID en headers",
            "formatos_audio": "WAV, MP3, M4A, OGG, FLAC (máx 10MB)"
        }
    })

# ============================================
# TAREAS PROGRAMADAS (simplificadas)
# ============================================
def tareas_automaticas():
    """Ejecuta tareas automáticas de mantenimiento"""
    try:
        # Limpiar sesiones antiguas cada hora
        session_manager.cleanup_old_sessions(hours_old=24)
        
        # Limpiar historial antiguo (mantener solo 1000 registros)
        global historial_conversaciones
        if len(historial_conversaciones) > 1000:
            historial_conversaciones = historial_conversaciones[-1000:]
        
        logger.info("Tareas automáticas ejecutadas")
    except Exception as e:
        logger.error(f"Error en tareas automáticas: {e}")

# ============================================
# INICIALIZACIÓN
# ============================================
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ELI - TUTOR CONVERSACIONAL MEJORADO v5.0")
    print("=" * 60)
    print("📚 Características principales:")
    print("   • Sistema coach con detección de nivel automática")
    print("   • Análisis de pronunciación detallado")
    print("   • Juego de vocabulario con gamificación")
    print("   • Sistema de logros y progresión")
    print("   • Gestión de sesiones de usuario")
    print("   • Procesamiento de audio optimizado")
    print("=" * 60)
    print("🌐 Endpoints disponibles en http://localhost:5000")
    print("🔧 Modo: Producción" if not app.debug else "🔧 Modo: Desarrollo")
    print("=" * 60)
    
    # Configurar puerto
    port = int(os.environ.get('PORT', 5000))
    
    # Ejecutar aplicación
    app.run(
        host="0.0.0.0", 
        port=port, 
        debug=False,
        threaded=True  # Para manejar múltiples conexiones
    )