import os
import sys
import logging
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import speech_recognition as sr
import random
import traceback
from pydub import AudioSegment
import io
import uuid
import time
from datetime import datetime, timedelta
from functools import wraps
import json
from typing import Dict, List, Optional, Tuple, Any
import re

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

print("🚀 Eli - Tutor Conversacional MEJORADO v5.0")

# ============================================
# CONFIGURACIÓN
# ============================================
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'eli-secret-key-render-2024')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    AUDIO_FILE_MAX_SIZE = 10 * 1024 * 1024
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

app = Flask(__name__)
app.config.from_object(Config)

# CORS para desarrollo y producción
CORS(app, resources={
    r"/api/*": {
        "origins": ["*", "http://localhost:*", "https://*.onrender.com"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-User-ID", "X-Session-ID"],
        "supports_credentials": True
    }
})

# ============================================
# GOOGLETRANS CON RETRY MECANISM
# ============================================
class RobustTranslator:
    def __init__(self):
        self.translator = None
        self._initialize_translator()
    
    def _initialize_translator(self):
        """Inicializar googletrans con manejo de errores"""
        try:
            from googletrans import Translator
            self.translator = Translator()
            logger.info("✅ googletrans initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize googletrans: {e}")
            self.translator = None
    
    def translate_with_retry(self, text, src='auto', dest='en', retries=3):
        """Traducir con reintentos"""
        if not self.translator:
            self._initialize_translator()
            if not self.translator:
                return self._fallback_translate(text, dest)
        
        for attempt in range(retries):
            try:
                result = self.translator.translate(text, src=src, dest=dest)
                return result.text
            except Exception as e:
                logger.warning(f"Translation attempt {attempt + 1} failed: {e}")
                time.sleep(0.5)
                if attempt == retries - 1:
                    return self._fallback_translate(text, dest)
    
    def detect_language(self, text, retries=2):
        """Detectar idioma con reintentos"""
        if not self.translator:
            return 'en', 0.8
        
        for attempt in range(retries):
            try:
                detection = self.translator.detect(text)
                return detection.lang, getattr(detection, 'confidence', 0.7)
            except:
                time.sleep(0.3)
        
        return 'en', 0.5
    
    def _fallback_translate(self, text, dest='en'):
        """Traducción de respaldo cuando googletrans falla"""
        # Diccionario básico para palabras comunes
        basic_dict = {
            # Español -> Inglés
            'casa': 'house', 'perro': 'dog', 'gato': 'cat', 'sol': 'sun',
            'agua': 'water', 'comida': 'food', 'amigo': 'friend', 
            'familia': 'family', 'tiempo': 'time', 'música': 'music',
            'libro': 'book', 'escuela': 'school', 'maestro': 'teacher',
            'estudiante': 'student', 'ciudad': 'city', 'país': 'country',
            'número': 'number', 'color': 'color', 'día': 'day', 'noche': 'night',
            
            # Frases comunes
            'El gato está en la mesa': 'The cat is on the table',
            'Me gusta la música': 'I like music',
            'Tengo un perro grande': 'I have a big dog',
            'Hoy hace mucho sol': 'Today is very sunny',
            'Vamos a la escuela': 'We go to school',
            'Mi familia es importante': 'My family is important',
            'El libro es interesante': 'The book is interesting',
            'Necesito beber agua': 'I need to drink water',
            'Mi amigo viene hoy': 'My friend is coming today',
            'Qué tiempo hace hoy?': 'What is the weather like today?'
        }
        
        text_lower = text.lower().strip()
        
        # Buscar coincidencia exacta
        if text_lower in basic_dict:
            return basic_dict[text_lower]
        
        # Para frases en inglés (hard), devolver tal cual
        if dest == 'en' and any(word in text_lower for word in 
                              ['the', 'and', 'but', 'because', 'however']):
            return text
        
        # Intentar traducir palabra por palabra
        words = text_lower.split()
        translated_words = []
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word in basic_dict:
                translated_words.append(basic_dict[clean_word])
            else:
                translated_words.append(word)
        
        return ' '.join(translated_words)

# Instancia global del traductor
translator = RobustTranslator()

# ============================================
# MODELOS DE DATOS
# ============================================
class UserSession:
    def __init__(self, user_id: str, session_id: str):
        self.user_id = user_id
        self.session_id = session_id
        self.current_level = "beginner"
        self.conversation_history = []
        self.game_stats = {
            "total_points": 0,
            "games_played": 0,
            "correct_answers": 0,
            "total_attempts": 0
        }
        self.xp = 0
        self.level = 1
        self.daily_streak = 0
        self.created_at = datetime.now()
        self.last_interaction = datetime.now()
        self.pronunciation_scores = []
    
    def add_conversation(self, user_text: str, eli_response: str, score: float):
        self.conversation_history.append({
            "user": user_text,
            "eli": eli_response,
            "score": score,
            "timestamp": datetime.now().isoformat()
        })
        self.pronunciation_scores.append(score)
        
        # Limitar historial
        if len(self.conversation_history) > 50:
            self.conversation_history.pop(0)
        if len(self.pronunciation_scores) > 20:
            self.pronunciation_scores.pop(0)
    
    def update_level(self):
        if not self.pronunciation_scores:
            return
        
        avg_score = sum(self.pronunciation_scores) / len(self.pronunciation_scores)
        
        if avg_score >= 85 and self.current_level != "advanced":
            self.current_level = "advanced"
        elif avg_score >= 70 and self.current_level == "beginner":
            self.current_level = "intermediate"
    
    def to_dict(self):
        avg_score = sum(self.pronunciation_scores) / len(self.pronunciation_scores) if self.pronunciation_scores else 0
        
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "current_level": self.current_level,
            "xp": self.xp,
            "level": self.level,
            "game_stats": self.game_stats,
            "conversation_count": len(self.conversation_history),
            "avg_pronunciation_score": round(avg_score, 1),
            "daily_streak": self.daily_streak
        }

# ============================================
# GESTIÓN DE SESIONES
# ============================================
class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}
    
    def create_session(self, user_id: str) -> UserSession:
        session_id = str(uuid.uuid4())
        session = UserSession(user_id, session_id)
        self.sessions[session_id] = session
        logger.info(f"New session: {session_id} for user {user_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, **kwargs):
        if session_id in self.sessions:
            session = self.sessions[session_id]
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            session.last_interaction = datetime.now()

session_manager = SessionManager()

# ============================================
# SISTEMA COACH CONVERSACIONAL
# ============================================
class SistemaCoach:
    def __init__(self):
        self.topics = [
            "daily routine", "family", "hobbies", "food", "weather",
            "travel", "work", "school", "sports", "music",
            "movies", "technology", "future plans", "memories", "dreams",
            "culture", "environment", "health", "relationships", "books"
        ]
    
    def detectar_nivel_usuario(self, texto: str, duracion_audio: float) -> str:
        if not texto:
            return "beginner"
        
        palabras = texto.split()
        word_count = len(palabras)
        
        advanced_words = {'although', 'however', 'therefore', 'furthermore', 
                         'meanwhile', 'consequently', 'nevertheless'}
        
        advanced_count = sum(1 for word in palabras if word.lower() in advanced_words)
        complex_structures = any(pattern in texto.lower() for pattern in 
                               ['if i were', 'i wish i had', 'should have'])
        
        score = 0
        if word_count > 12: score += 3
        elif word_count > 7: score += 2
        elif word_count > 3: score += 1
        
        score += advanced_count * 2
        if complex_structures: score += 3
        if duracion_audio > 4: score += 2
        elif duracion_audio > 2: score += 1
        
        if score >= 8: return "advanced"
        elif score >= 4: return "intermediate"
        return "beginner"
    
    def analizar_pronunciacion(self, texto: str, audio_duration: float) -> Dict[str, Any]:
        palabras = texto.lower().split()
        nivel = self.detectar_nivel_usuario(texto, audio_duration)
        
        # Palabras problemáticas comunes
        problem_patterns = {
            'the': 'ðə (tongue between teeth for "th")',
            'think': 'θɪŋk (soft "th", no vibration)',
            'this': 'ðɪs (vibrating "th")',
            'very': 'vɛri (bite lower lip for "v")',
            'water': 'wɔːtər (pronounce the "t")',
            'world': 'wɜːrld (three syllables: wor-l-d)',
            'right': 'raɪt (strong "r" sound)',
            'light': 'laɪt (clear "l" sound)',
            'she': 'ʃi (rounded lips for "sh")',
            'usually': 'juːʒuəli ("zh" sound like in "vision")'
        }
        
        problem_words = []
        for palabra in palabras:
            clean = re.sub(r'[^\w]', '', palabra)
            if clean in problem_patterns:
                problem_words.append({
                    'word': clean,
                    'explanation': problem_patterns[clean],
                    'phonetic': problem_patterns[clean].split(' ')[0]
                })
        
        # Calcular score
        score = 65.0  # Base
        
        # Bonus por buen audio
        if audio_duration >= 2.0:
            score += 10
        if audio_duration >= 3.0:
            score += 5
        
        # Penalización por problemas
        if problem_words:
            score -= len(problem_words) * 5
        
        # Bonus por fluidez
        if len(palabras) >= 5:
            score += 5
        if len(palabras) >= 10:
            score += 5
        
        # Bonus por nivel
        if nivel == "intermediate":
            score += 5
        elif nivel == "advanced":
            score += 10
        
        # Asegurar rango 0-100
        score = max(30.0, min(100.0, score))
        
        # Generar consejos
        tips = []
        if nivel == "beginner":
            if len(palabras) < 3:
                tips.append("Try to form longer sentences (minimum 3 words)")
            tips.append("Speak slowly and clearly")
            if audio_duration < 1.5:
                tips.append("Speak for at least 2 seconds to practice rhythm")
        
        elif nivel == "intermediate":
            tips.append("Focus on natural intonation and stress patterns")
            tips.append("Try using connecting words like 'however' or 'therefore'")
            if not problem_words:
                tips.append("Great! Now work on speaking more naturally")
        
        else:  # advanced
            tips.append("Work on natural rhythm and speaking rate")
            tips.append("Practice using idiomatic expressions")
            if score < 85:
                tips.append("Aim for more natural, native-like pronunciation")
        
        if problem_words:
            tips.append(f"Practice the word(s): {', '.join(pw['word'] for pw in problem_words[:2])}")
        
        return {
            'score': round(score, 1),
            'problem_words': problem_words[:3],
            'tips': tips[:3],
            'detected_level': nivel,
            'word_count': len(palabras),
            'duration': round(audio_duration, 1)
        }
    
    def generar_respuesta(self, texto_usuario: str, duracion_audio: float = 0) -> Dict[str, Any]:
        texto_lower = texto_usuario.lower().strip()
        
        # Respuestas especiales
        if not texto_usuario or len(texto_usuario.strip()) < 2:
            return self._respuesta_sin_audio()
        
        if any(word in texto_lower for word in ['help', 'ayuda', 'i dont know', 'no sé', 'what should i say']):
            return self._respuesta_ayuda(texto_usuario, duracion_audio)
        
        # Verificar si habló en español
        lang, confidence = translator.detect_language(texto_usuario)
        if lang == 'es' and confidence > 0.6:
            return self._respuesta_en_espanol(texto_usuario)
        
        # Análisis normal
        analisis = self.analizar_pronunciacion(texto_usuario, duracion_audio)
        
        # Construir respuesta
        response_parts = []
        
        # Encabezado según nivel
        level_headers = {
            "beginner": "🎉 **Great effort!** You're starting strong!",
            "intermediate": "🌟 **Well done!** Your English is improving nicely!",
            "advanced": "💫 **Excellent!** Very impressive English!"
        }
        response_parts.append(level_headers.get(analisis['detected_level'], "🎉 Good job!"))
        
        # Mostrar lo que dijo el usuario
        response_parts.append(f"🗣️ **You said:** \"{texto_usuario}\"")
        
        # Puntuación
        response_parts.append(f"📊 **Pronunciation Score:** {analisis['score']}/100")
        
        # Correcciones específicas
        if analisis['problem_words']:
            response_parts.append("\n🎯 **Pronunciation Focus:**")
            for pw in analisis['problem_words']:
                response_parts.append(f"• **{pw['word']}**: {pw['explanation']}")
                response_parts.append(f"  🔤 **Write it:** {pw['word']}")
                response_parts.append(f"  🔊 **Sound it:** /{pw['phonetic']}/")
        
        # Consejos
        if analisis['tips']:
            response_parts.append("\n💡 **Practice Tips:**")
            for tip in analisis['tips']:
                response_parts.append(f"• {tip}")
        
        # Retroalimentación positiva
        if analisis['score'] >= 80:
            response_parts.append("\n⭐ **Great work on:**")
            if analisis['duration'] >= 2.0:
                response_parts.append("• Good speaking duration")
            if analisis['word_count'] >= 5:
                response_parts.append("• Forming complete sentences")
            if not analisis['problem_words']:
                response_parts.append("• Clear pronunciation")
        
        # Siguiente pregunta
        next_q = self._generar_pregunta(analisis['detected_level'])
        response_parts.append(f"\n💬 **Let's continue:** {next_q}")
        
        # Si el score es bajo, sugerir repetir
        if analisis['score'] < 70:
            response_parts.append("\n🔁 **Try repeating:** Say it again, focusing on the corrections above.")
        
        return {
            "respuesta": "\n".join(response_parts),
            "tipo": "conversacion",
            "correcciones": analisis['problem_words'],
            "consejos": analisis['tips'],
            "pregunta_seguimiento": True,
            "nivel_detectado": analisis['detected_level'],
            "pronunciation_score": analisis['score'],
            "next_question": next_q,
            "ejemplos_respuesta": self._generar_ejemplos(analisis['detected_level'])
        }
    
    def _respuesta_sin_audio(self) -> Dict[str, Any]:
        return {
            "respuesta": """🤔 **I didn't hear any speech.**

💡 **Tips for better recording:**
• Speak clearly for 2-3 seconds
• Make sure you're in a quiet place
• Hold the microphone closer
• Try saying: "Hello, my name is..." or "I like to..." 

🎤 **Ready when you are!**""",
            "tipo": "ayuda",
            "pregunta_seguimiento": True,
            "nivel_detectado": "beginner",
            "pronunciation_score": 0,
            "ejemplos_respuesta": [
                "Hello, my name is...",
                "I like to listen to music",
                "Today is a beautiful day"
            ]
        }
    
    def _respuesta_ayuda(self, texto_usuario: str, duracion_audio: float) -> Dict[str, Any]:
        nivel = self.detectar_nivel_usuario(texto_usuario, duracion_audio)
        
        ejemplos = {
            "beginner": [
                "I like to eat pizza",
                "My favorite color is blue",
                "I have two sisters",
                "I live in a big city",
                "I wake up at 7 o'clock"
            ],
            "intermediate": [
                "On weekends, I usually go to the movies with friends",
                "I'm studying English because I want to travel",
                "My best friend is very funny and kind",
                "I enjoy reading books in my free time",
                "Last summer, I visited the beach with my family"
            ],
            "advanced": [
                "I believe that education is the key to personal development",
                "Technology has revolutionized the way we communicate",
                "Cultural diversity enriches our society in many ways",
                "Environmental sustainability should be a global priority",
                "Learning a new language opens doors to different perspectives"
            ]
        }
        
        return {
            "respuesta": """🎯 **I'm here to help you!**

💬 **You can talk about anything that interests you:**
• Your daily activities and routines
• Your hobbies, interests, and passions  
• Your family, friends, and relationships
• Your goals, dreams, and aspirations
• Your opinions on various topics

📝 **Example responses for your level:**
""" + "\n".join(f"• {ej}" for ej in ejemplos.get(nivel, ejemplos["beginner"][:3])) + """

💪 **Remember:** The most important thing is to **try**. Every attempt helps you improve!""",
            "tipo": "ayuda_explicita",
            "pregunta_seguimiento": True,
            "nivel_detectado": nivel,
            "pronunciation_score": 50,
            "ejemplos_respuesta": ejemplos.get(nivel, ejemplos["beginner"])
        }
    
    def _respuesta_en_espanol(self, texto_usuario: str) -> Dict[str, Any]:
        # Traducir lo que dijo el usuario
        translated = translator.translate_with_retry(texto_usuario, src='es', dest='en')
        
        return {
            "respuesta": f"""🌐 **I noticed you spoke in Spanish.**

🗣️ **You said in Spanish:** "{texto_usuario}"
🔤 **In English:** "{translated}"

🎯 **Try saying it in English:**
• Speak slowly and clearly
• Focus on pronouncing each word
• Don't worry about perfection

💡 **Tip:** Practice switching between languages. You're doing great!""",
            "tipo": "language_switch",
            "pregunta_seguimiento": True,
            "nivel_detectado": "beginner",
            "pronunciation_score": 40,
            "ejemplos_respuesta": [
                translated,
                "Can you say that in English?",
                "I'm practicing my English pronunciation"
            ]
        }
    
    def _generar_pregunta(self, nivel: str) -> str:
        preguntas = {
            "beginner": [
                "What is your favorite color and why?",
                "Do you have any pets? Tell me about them.",
                "What food do you like to eat?",
                "Where do you live? Describe your city.",
                "What time do you usually wake up?",
                "How many people are in your family?",
                "What's your favorite day of the week?",
                "Do you like to watch movies? Which ones?",
                "What's your favorite season?",
                "Can you describe your house or apartment?"
            ],
            "intermediate": [
                "What do you usually do on weekends?",
                "Describe your best friend's personality.",
                "What's your favorite hobby and why do you enjoy it?",
                "Tell me about your daily routine from morning to night.",
                "What are your plans for next weekend?",
                "What's the last book you read or movie you watched?",
                "Describe your hometown or where you grew up.",
                "What's your dream vacation destination?",
                "What skill would you like to learn next?",
                "Tell me about a happy memory from your childhood."
            ],
            "advanced": [
                "What are your professional or personal goals for the next 5 years?",
                "How has technology changed the way we live and work?",
                "What's your opinion on the impact of social media on society?",
                "Describe a significant challenge you've overcome and what you learned.",
                "What does success mean to you personally?",
                "How important is education in today's world?",
                "What global issue concerns you the most and why?",
                "Describe a cultural tradition from your country that you value.",
                "What skills do you think will be most important in the future job market?",
                "How do you handle stress and maintain work-life balance?"
            ]
        }
        
        # Seleccionar pregunta aleatoria
        question_list = preguntas.get(nivel, preguntas["beginner"])
        
        # Opcional: seleccionar tema aleatorio
        topic = random.choice(self.topics)
        personalized = question_list[random.randint(0, len(question_list)-1)]
        
        # A veces añadir referencia al tema
        if random.random() > 0.7:  # 30% de las veces
            return f"Thinking about {topic}, {personalized.lower()}"
        
        return personalized
    
    def _generar_ejemplos(self, nivel: str) -> List[str]:
        ejemplos = {
            "beginner": [
                "I like to eat pizza and watch movies",
                "My family has four people: my parents, my sister, and me",
                "I wake up at 7 am and go to school at 8 am",
                "My favorite color is blue because it's calm",
                "I live in a city with many parks and restaurants"
            ],
            "intermediate": [
                "On weekends, I usually meet friends for coffee or go hiking",
                "I'm studying English because I plan to travel abroad next year",
                "My best friend is very supportive and always makes me laugh",
                "In my free time, I enjoy reading mystery novels and cooking",
                "Last year, I visited Paris and was amazed by the Eiffel Tower"
            ],
            "advanced": [
                "I believe that continuous learning is essential for personal growth",
                "Technology has transformed communication but also created new challenges",
                "Cultural exchange programs can help bridge understanding between nations",
                "Environmental conservation requires both individual and collective action",
                "Learning multiple languages provides cognitive benefits and cultural insights"
            ]
        }
        
        return ejemplos.get(nivel, ejemplos["beginner"])[:3]

coach = SistemaCoach()

# ============================================
# JUEGO DE VOCABULARIO COMPLETO
# ============================================
class VocabularyGame:
    def __init__(self):
        self.vocabulary = self._load_vocabulary()
    
    def _load_vocabulary(self) -> Dict[str, List[str]]:
        return {
            "easy": [
                "house", "dog", "cat", "sun", "water", "food", "friend", 
                "family", "time", "music", "book", "school", "teacher",
                "student", "city", "country", "number", "color", "day", "night",
                "car", "table", "chair", "door", "window", "apple", "orange",
                "milk", "bread", "rice", "beach", "mountain", "river", "forest"
            ],
            "normal": [
                "The cat is on the table",
                "I like rock music",
                "I have a big and playful dog", 
                "Today is very sunny and hot",
                "We go to school every day",
                "My family is very important to me",
                "The book is interesting and educational",
                "I need to drink fresh water",
                "My friend is coming to visit me today",
                "What is the weather like today in your city?",
                "The food is very delicious",
                "I am learning English quickly",
                "The city is big and modern",
                "I love the beach in summer",
                "The student studies a lot"
            ],
            "hard": [
                "The scientific research demonstrated significant improvements",
                "Global economic trends indicate substantial growth potential",
                "Environmental sustainability requires collaborative efforts worldwide",
                "Technological advancements continue to revolutionize industries",
                "Cognitive behavioral therapy has proven effective for many patients",
                "The entrepreneur developed an innovative business strategy",
                "Artificial intelligence is transforming various sectors globally",
                "Renewable energy sources are essential for sustainable development",
                "The researcher conducted a comprehensive literature review",
                "International collaboration fosters scientific breakthroughs"
            ]
        }
    
    def get_random_word(self, difficulty: str) -> Dict[str, Any]:
        if difficulty not in self.vocabulary:
            difficulty = "easy"
        
        word = random.choice(self.vocabulary[difficulty])
        
        # Generar pista según dificultad
        hint = self._generate_hint(word, difficulty)
        
        return {
            "word": word,
            "difficulty": difficulty,
            "points_base": {"easy": 10, "normal": 25, "hard": 50}[difficulty],
            "suggested_time": {"easy": 15, "normal": 30, "hard": 45}[difficulty],
            "hint": hint,
            "id": str(uuid.uuid4())[:8]
        }
    
    def _generate_hint(self, word: str, difficulty: str) -> str:
        if difficulty == "easy":
            return f"Starts with: '{word[0].upper()}'"
        elif difficulty == "normal":
            # Para frases en español, dar traducción
            try:
                translated = translator.translate_with_retry(word, src='es', dest='en')
                words = translated.split()
                if len(words) > 2:
                    return f"Translates to: '{' '.join(words[:2])}...'"
                return f"Translates to: '{translated}'"
            except:
                return "Try to pronounce each word clearly"
        else:
            # Para frases difíciles en inglés, dar palabras clave
            keywords = word.split()[:2]
            return f"Keywords: {', '.join(keywords)}"
    
    def validate_answer(self, original: str, user_answer: str, difficulty: str) -> Dict[str, Any]:
        user_clean = user_answer.strip().lower()
        
        # Detectar idioma
        lang, confidence = translator.detect_language(user_answer)
        
        # Para easy y normal, traducir del español al inglés
        correct_translation = ""
        if difficulty in ["easy", "normal"]:
            try:
                correct_translation = translator.translate_with_retry(original, src='es', dest='en')
                correct_translation = correct_translation.lower().strip()
            except:
                correct_translation = original.lower().strip()
        else:
            correct_translation = original.lower().strip()
        
        # Verificar si habló en español cuando debería ser inglés
        if difficulty in ["easy", "normal"] and lang == 'es' and confidence > 0.6:
            return {
                "is_correct": False,
                "user_answer": user_answer,
                "correct_answer": correct_translation,
                "original_word": original,
                "points_earned": 0,
                "message": "You spoke in Spanish! Try saying it in English. 🎯",
                "xp_earned": 1,
                "language_detected": "es",
                "accuracy": 0.0
            }
        
        # Comparar respuestas
        is_correct = self._compare_answers(user_clean, correct_translation, difficulty)
        
        points_base = {"easy": 10, "normal": 25, "hard": 50}[difficulty]
        points = points_base if is_correct else max(1, points_base // 5)
        
        # XP adicional por complejidad
        xp = 5
        if difficulty == "normal":
            xp = 8
        elif difficulty == "hard":
            xp = 12
        
        if not is_correct:
            xp = 1
        
        messages = {
            "easy": {
                True: "Perfect! 🎉 Great pronunciation for a beginner!",
                False: "Almost! Listen carefully and try again. 💪"
            },
            "normal": {
                True: "Excellent! 👏 Your pronunciation is improving!",
                False: "Good attempt! Focus on the difficult words. 📚"
            },
            "hard": {
                True: "Outstanding! 🏆 Advanced pronunciation mastered!",
                False: "Challenging phrase! Keep practicing. 🎯"
            }
        }
        
        return {
            "is_correct": is_correct,
            "user_answer": user_answer,
            "correct_answer": correct_translation,
            "original_word": original,
            "points_earned": points,
            "message": messages[difficulty][is_correct],
            "xp_earned": xp,
            "language_detected": lang,
            "accuracy": 100.0 if is_correct else 50.0
        }
    
    def _compare_answers(self, user_answer: str, correct: str, difficulty: str) -> bool:
        if not user_answer or not correct:
            return False
        
        # Normalizar
        user_norm = self._normalize_text(user_answer)
        correct_norm = self._normalize_text(correct)
        
        # Comparación exacta
        if user_norm == correct_norm:
            return True
        
        # Para easy, ser más flexible
        if difficulty == "easy":
            user_words = set(user_norm.split())
            correct_words = set(correct_norm.split())
            
            # Si comparten al menos una palabra clave
            intersection = user_words.intersection(correct_words)
            if len(intersection) > 0:
                return True
            
            # Verificar si contiene la palabra principal
            main_word = correct_norm.split()[0] if correct_norm.split() else ""
            if main_word and main_word in user_norm:
                return True
        
        # Para normal, verificar estructura
        elif difficulty == "normal":
            user_words = user_norm.split()
            correct_words = correct_norm.split()
            
            if len(user_words) < 2 or len(correct_words) < 2:
                return False
            
            # Verificar si contiene palabras clave (al menos 50%)
            common = set(user_words).intersection(set(correct_words))
            if len(common) >= len(correct_words) * 0.5:
                return True
        
        # Para hard, requerir mayor precisión
        else:
            # Usar similitud de secuencia
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, user_norm, correct_norm).ratio()
            return similarity >= 0.7
        
        return False
    
    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        
        text = text.lower().strip()
        
        # Remover artículos
        articles = ['the ', 'a ', 'an ', 'el ', 'la ', 'los ', 'las ', 'un ', 'una ']
        for article in articles:
            text = text.replace(article, ' ')
        
        # Remover puntuación y espacios extra
        text = re.sub(r'[^\w\s]', '', text)
        text = ' '.join(text.split())
        
        return text

game = VocabularyGame()

# ============================================
# PROCESADOR DE AUDIO
# ============================================
class AudioProcessor:
    def process_audio(self, audio_file) -> Tuple[io.BytesIO, float]:
        try:
            audio_bytes = audio_file.read()
            
            if len(audio_bytes) > Config.AUDIO_FILE_MAX_SIZE:
                raise ValueError(f"Audio file too large (max {Config.AUDIO_FILE_MAX_SIZE/1024/1024}MB)")
            
            # Detectar formato
            filename = audio_file.filename.lower() if audio_file.filename else ''
            if filename.endswith('.m4a'):
                audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="m4a")
            elif filename.endswith('.mp3'):
                audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
            else:
                audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            
            # Optimizar para reconocimiento
            audio = audio.set_channels(1).set_frame_rate(16000)
            duration = len(audio) / 1000.0
            
            # Exportar a WAV
            wav_buffer = io.BytesIO()
            audio.export(wav_buffer, format="wav")
            wav_buffer.seek(0)
            
            logger.info(f"Audio processed: {duration:.2f}s")
            return wav_buffer, duration
            
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            raise Exception(f"Could not process audio: {str(e)}")
    
    def transcribe_audio(self, wav_buffer: io.BytesIO) -> str:
        recognizer = sr.Recognizer()
        
        try:
            with sr.AudioFile(wav_buffer) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language='en-US')
                return text.strip()
        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return ""
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return ""
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""

audio_processor = AudioProcessor()

# ============================================
# ENDPOINTS DE LA API
# ============================================
@app.before_request
def before_request():
    """Log cada request"""
    logger.info(f"{request.method} {request.path}")

@app.after_request
def after_request(response):
    """Añadir headers CORS"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-User-ID,X-Session-ID')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Eli English Tutor",
        "version": "5.0.0",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "/api/health": "Health check",
            "/api/conversar_audio": "Audio conversation with Eli",
            "/api/juego/palabra": "Get vocabulary game word",
            "/api/juego/validar": "Validate game answer",
            "/api/obtener_pregunta": "Get conversation question",
            "/api/sesion/iniciar": "Start new session",
            "/api/estadisticas": "Get user statistics"
        },
        "features": [
            "Real-time pronunciation analysis",
            "Vocabulary game with level detection",
            "Personalized conversation practice",
            "Progress tracking and gamification"
        ]
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Eli Backend",
        "sessions_active": len(session_manager.sessions),
        "translator_status": "active" if translator.translator else "fallback",
        "version": "5.0.0"
    })

@app.route('/api/sesion/iniciar', methods=['POST'])
def iniciar_sesion():
    try:
        data = request.json or {}
        user_id = data.get('user_id', f"user_{uuid.uuid4().hex[:8]}")
        
        session = session_manager.create_session(user_id)
        
        return jsonify({
            "estado": "exito",
            "user_id": user_id,
            "session_id": session.session_id,
            "welcome_message": "🎯 Welcome to Eli English Tutor! Ready to practice and improve your English skills?",
            "initial_level": session.current_level,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Session start error: {e}")
        return jsonify({
            "estado": "error",
            "mensaje": f"Error starting session: {str(e)}"
        }), 500

@app.route('/api/conversar_audio', methods=['POST'])
def conversar_audio():
    if 'audio' not in request.files:
        return jsonify({
            "estado": "error",
            "respuesta": "No audio file provided. Please record your voice."
        }), 400
    
    audio_file = request.files['audio']
    pregunta_actual = request.form.get('pregunta_actual', '')
    session_id = request.form.get('session_id', '')
    
    try:
        # Procesar audio
        wav_buffer, duracion = audio_processor.process_audio(audio_file)
        
        # Transcribir
        texto = audio_processor.transcribe_audio(wav_buffer)
        
        if not texto:
            return jsonify({
                "estado": "error",
                "respuesta": """🎤 **I couldn't hear any clear speech.**

💡 **Tips for better recording:**
• Speak for 2-3 seconds clearly
• Make sure you're in a quiet environment
• Hold the microphone close to your mouth
• Try saying: "Hello, how are you today?"

🔊 **Example phrases to try:**
• "My name is [your name]"
• "I like to practice English"
• "Today is a good day for learning" """
            }), 400
        
        logger.info(f"User said: '{texto}' ({duracion:.2f}s)")
        
        # Obtener respuesta del coach
        respuesta = coach.generar_respuesta(texto, duracion)
        
        # Actualizar sesión
        xp_earned = 10
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                session.add_conversation(texto, respuesta["respuesta"], respuesta["pronunciation_score"])
                session.xp += xp_earned
                session.update_level()
                session_manager.update_session(session_id, xp=session.xp)
        
        return jsonify({
            "estado": "exito",
            "respuesta": respuesta["respuesta"],
            "transcripcion": texto,
            "nueva_pregunta": respuesta.get("next_question", ""),
            "correcciones_pronunciacion": respuesta.get("correcciones", []),
            "consejos": respuesta.get("consejos", []),
            "nivel_detectado": respuesta["nivel_detectado"],
            "pronunciation_score": respuesta["pronunciation_score"],
            "ejemplos_respuesta": respuesta.get("ejemplos_respuesta", []),
            "session_id": session_id,
            "xp_earned": xp_earned,
            "audio_duration": duracion
        })
    
    except ValueError as e:
        logger.error(f"Audio size error: {e}")
        return jsonify({
            "estado": "error",
            "respuesta": f"Audio file too large. Please record a shorter message (max 10MB)."
        }), 413
    except Exception as e:
        logger.error(f"Conversation error: {traceback.format_exc()}")
        return jsonify({
            "estado": "error",
            "respuesta": f"Error processing audio. Please try again. Technical: {str(e)[:100]}"
        }), 500

@app.route('/api/juego/palabra', methods=['GET'])
def obtener_palabra_juego():
    try:
        dificultad = request.args.get('dificultad', 'easy')
        palabra_data = game.get_random_word(dificultad)
        
        return jsonify({
            "estado": "exito",
            "palabra": palabra_data["word"],
            "dificultad": palabra_data["difficulty"],
            "puntos_base": palabra_data["points_base"],
            "tiempo_sugerido": palabra_data["suggested_time"],
            "pista": palabra_data["hint"],
            "id": palabra_data["id"]
        })
    
    except Exception as e:
        logger.error(f"Game word error: {e}")
        return jsonify({
            "estado": "error",
            "mensaje": f"Error getting game word: {str(e)}"
        }), 500

@app.route('/api/juego/validar', methods=['POST'])
def validar_respuesta_juego():
    try:
        data = request.json or {}
        palabra_original = data.get('palabra_original', '')
        respuesta_usuario = data.get('respuesta_usuario', '')
        dificultad = data.get('dificultad', 'easy')
        session_id = data.get('session_id', '')
        
        if not palabra_original or not respuesta_usuario:
            return jsonify({
                "estado": "error",
                "mensaje": "Missing required fields"
            }), 400
        
        resultado = game.validate_answer(palabra_original, respuesta_usuario, dificultad)
        
        # Actualizar sesión
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                session.game_stats["games_played"] += 1
                session.game_stats["total_attempts"] += 1
                if resultado["is_correct"]:
                    session.game_stats["correct_answers"] += 1
                    session.game_stats["total_points"] += resultado["points_earned"]
                session.xp += resultado["xp_earned"]
        
        return jsonify({
            "estado": "exito",
            "es_correcta": resultado["is_correct"],
            "respuesta_usuario": resultado["user_answer"],
            "traduccion_correcta": resultado["correct_answer"],
            "palabra_original": resultado["original_word"],
            "puntos_obtenidos": resultado["points_earned"],
            "mensaje": resultado["message"],
            "xp_earned": resultado["xp_earned"],
            "language_detected": resultado.get("language_detected", "en"),
            "accuracy": resultado["accuracy"]
        })
    
    except Exception as e:
        logger.error(f"Game validation error: {e}")
        return jsonify({
            "estado": "error",
            "mensaje": f"Error validating answer: {str(e)}"
        }), 500

@app.route('/api/obtener_pregunta', methods=['GET'])
def obtener_pregunta():
    try:
        nivel = request.args.get('nivel', 'beginner')
        pregunta = coach._generar_pregunta(nivel)
        
        return jsonify({
            "estado": "exito",
            "pregunta": pregunta,
            "nivel": nivel,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Get question error: {e}")
        return jsonify({
            "estado": "error",
            "mensaje": f"Error getting question: {str(e)}"
        }), 500

@app.route('/api/estadisticas', methods=['GET'])
def obtener_estadisticas():
    try:
        session_id = request.args.get('session_id')
        user_id = request.args.get('user_id')
        
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                return jsonify({
                    "estado": "exito",
                    "stats": session.to_dict(),
                    "conversation_history": session.conversation_history[-10:],  # Últimas 10
                    "pronunciation_trend": session.pronunciation_scores[-5:] if session.pronunciation_scores else []
                })
        
        # Estadísticas globales
        return jsonify({
            "estado": "exito",
            "global_stats": {
                "total_sessions": len(session_manager.sessions),
                "active_sessions": len([s for s in session_manager.sessions.values() 
                                      if (datetime.now() - s.last_interaction).seconds < 300]),
                "service_uptime": int(time.time() - start_time),
                "translator_status": "active" if translator.translator else "fallback_mode"
            }
        })
    
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({
            "estado": "error",
            "mensaje": f"Error getting statistics: {str(e)}"
        }), 500

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Endpoint de prueba"""
    return jsonify({
        "status": "ok",
        "message": "Eli backend is working correctly",
        "timestamp": datetime.now().isoformat(),
        "googletrans_test": translator.translate_with_retry("hola", src='es', dest='en'),
        "session_count": len(session_manager.sessions)
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "estado": "error",
        "mensaje": "Endpoint not found. Check the documentation at /"
    }), 404

@app.errorhandler(413)
def too_large(error):
    return jsonify({
        "estado": "error",
        "mensaje": "File too large. Maximum audio size is 10MB."
    }), 413

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "estado": "error",
        "mensaje": "Internal server error. Please try again later."
    }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {traceback.format_exc()}")
    return jsonify({
        "estado": "error",
        "mensaje": f"An unexpected error occurred: {str(e)[:100]}"
    }), 500

# ============================================
# INICIALIZACIÓN Y EJECUCIÓN
# ============================================
if __name__ == '__main__':
    start_time = time.time()
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 60)
    print("🚀 ELI ENGLISH TUTOR BACKEND v5.0")
    print("=" * 60)
    print(f"📊 Starting on port: {port}")
    print(f"🔧 Translator: {'ACTIVE' if translator.translator else 'FALLBACK MODE'}")
    print(f"🎯 Coach system: READY")
    print(f"🎮 Game system: READY")
    print(f"🎤 Audio processor: READY")
    print(f"💾 Session manager: READY")
    print("=" * 60)
    print("✅ Server initialized successfully!")
    print("=" * 60)
    
    # Para desarrollo
    if os.environ.get('FLASK_ENV') == 'development':
        app.run(host='0.0.0.0', port=port, debug=True, threaded=True)
    else:
        # Para producción
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)