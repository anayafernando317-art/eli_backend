import os
import sys
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import speech_recognition as sr
import random
import traceback
from pydub import AudioSegment
import io
import uuid
import time
from datetime import datetime, timedelta
import json
import re

# ============================================
# CONFIGURACIÓN INICIAL
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Reducir logs en producción
if os.environ.get('RENDER'):
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)

print("=" * 60)
print("🚀 Eli English Tutor - Backend Unificado v6.0")
print("🎯 TODA la lógica en backend - Flutter solo interfaz")
print("=" * 60)

# ============================================
# CONFIGURACIÓN FLASK
# ============================================
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'eli-secret-key-' + str(uuid.uuid4())[:8])
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    AUDIO_FILE_MAX_SIZE = 5 * 1024 * 1024

app = Flask(__name__)
app.config.from_object(Config)

CORS(app, resources={
    r"/api/*": {
        "origins": ["*", "https://*.onrender.com", "http://localhost:*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-User-ID", "X-Session-ID"]
    }
})

# ============================================
# TRADUCTOR HÍBRIDO INTELIGENTE
# ============================================
class HybridTranslator:
    def __init__(self):
        self.local_dict = self._create_educational_dictionary()
        self.external_translator = None
        self.use_external = True
        self.translation_cache = {}
        self.cache_size = 200
        
        self._try_init_external()
        logger.info(f"✅ HybridTranslator inicializado. Externo: {self.use_external}")
    
    def _try_init_external(self):
        """Intentar inicializar deep-translator"""
        try:
            from deep_translator import GoogleTranslator
            self.external_translator = GoogleTranslator(source='auto', target='en')
            test = self.external_translator.translate('hola')
            if test and test.lower() == 'hello':
                logger.info("✅ Traductor externo (Google) listo")
                self.use_external = True
            else:
                self.use_external = False
        except Exception as e:
            logger.warning(f"⚠️ Traductor externo falló: {str(e)[:80]}")
            self.use_external = False
    
    def _create_educational_dictionary(self):
        """Diccionario educativo COMPLETO para preparatoria"""
        return {
            # === SALUDOS Y CORTESÍA ===
            'hola': 'hello', 'adiós': 'goodbye', 'buenos días': 'good morning',
            'buenas tardes': 'good afternoon', 'buenas noches': 'good night',
            'por favor': 'please', 'gracias': 'thank you', 'de nada': 'you are welcome',
            'lo siento': 'i am sorry', 'perdón': 'excuse me', 'con permiso': 'excuse me',
            
            # === PERSONAS Y FAMILIA ===
            'yo': 'i', 'tú': 'you', 'él': 'he', 'ella': 'she', 'nosotros': 'we',
            'ustedes': 'you', 'ellos': 'they', 'persona': 'person', 'gente': 'people',
            'hombre': 'man', 'mujer': 'woman', 'niño': 'child', 'niña': 'girl',
            'amigo': 'friend', 'familia': 'family', 'padre': 'father', 'madre': 'mother',
            'hermano': 'brother', 'hermana': 'sister', 'hijo': 'son', 'hija': 'daughter',
            
            # === LUGARES ===
            'casa': 'house', 'escuela': 'school', 'trabajo': 'work', 'ciudad': 'city',
            'país': 'country', 'mundo': 'world', 'calle': 'street', 'parque': 'park',
            'restaurante': 'restaurant', 'hospital': 'hospital', 'tienda': 'store',
            'biblioteca': 'library', 'universidad': 'university', 'playa': 'beach',
            
            # === TIEMPO ===
            'hoy': 'today', 'mañana': 'tomorrow', 'ayer': 'yesterday',
            'día': 'day', 'noche': 'night', 'semana': 'week', 'mes': 'month',
            'año': 'year', 'hora': 'hour', 'minuto': 'minute', 'segundo': 'second',
            'lunes': 'monday', 'martes': 'tuesday', 'miércoles': 'wednesday',
            'jueves': 'thursday', 'viernes': 'friday', 'sábado': 'saturday',
            'domingo': 'sunday',
            
            # === COMIDA ===
            'agua': 'water', 'comida': 'food', 'desayuno': 'breakfast',
            'almuerzo': 'lunch', 'cena': 'dinner', 'fruta': 'fruit',
            'verdura': 'vegetable', 'carne': 'meat', 'pescado': 'fish',
            'pan': 'bread', 'arroz': 'rice', 'leche': 'milk', 'café': 'coffee',
            'té': 'tea', 'azúcar': 'sugar', 'sal': 'salt',
            
            # === EDUCACIÓN ===
            'profesor': 'teacher', 'estudiante': 'student', 'clase': 'class',
            'libro': 'book', 'papel': 'paper', 'lápiz': 'pencil', 'pluma': 'pen',
            'computadora': 'computer', 'internet': 'internet', 'aprender': 'learn',
            'estudiar': 'study', 'enseñar': 'teach', 'examen': 'exam',
            'pregunta': 'question', 'respuesta': 'answer',
            
            # === VERBOS COMUNES ===
            'ser': 'to be', 'estar': 'to be', 'tener': 'to have', 'hacer': 'to do',
            'ir': 'to go', 'venir': 'to come', 'ver': 'to see', 'mirar': 'to look',
            'escuchar': 'to listen', 'hablar': 'to speak', 'decir': 'to say',
            'pensar': 'to think', 'saber': 'to know', 'querer': 'to want',
            'gustar': 'to like', 'amar': 'to love', 'odiar': 'to hate',
            'comprar': 'to buy', 'vender': 'to sell', 'trabajar': 'to work',
            'jugar': 'to play', 'dormir': 'to sleep', 'despertar': 'to wake up',
            
            # === ADJETIVOS ===
            'bueno': 'good', 'malo': 'bad', 'grande': 'big', 'pequeño': 'small',
            'alto': 'tall', 'bajo': 'short', 'feliz': 'happy', 'triste': 'sad',
            'inteligente': 'smart', 'importante': 'important', 'difícil': 'difficult',
            'fácil': 'easy', 'rápido': 'fast', 'lento': 'slow', 'nuevo': 'new',
            'viejo': 'old', 'joven': 'young', 'hermoso': 'beautiful', 'feo': 'ugly',
            
            # === FRASES COMUNES ===
            '¿cómo estás?': 'how are you?', '¿qué tal?': 'how is it going?',
            '¿qué pasa?': 'what\'s up?', 'mucho gusto': 'nice to meet you',
            '¿cómo te llamas?': 'what is your name?', 'me llamo': 'my name is',
            '¿de dónde eres?': 'where are you from?', 'soy de': 'i am from',
            '¿cuántos años tienes?': 'how old are you?', 'tengo años': 'i am years old',
            '¿qué hora es?': 'what time is it?', 'son las': 'it is',
            '¿dónde está?': 'where is?', 'aquí está': 'here it is',
            'no entiendo': 'i don\'t understand', '¿puedes repetir?': 'can you repeat?',
            'habla más despacio': 'speak more slowly', '¿cómo se dice?': 'how do you say?',
            'necesito ayuda': 'i need help'
        }
    
    def translate_with_retry(self, text, src='auto', dest='en', retries=1):
        """Traducir texto con estrategia híbrida"""
        if not text or not isinstance(text, str) or len(text.strip()) == 0:
            return text
        
        text_lower = text.lower().strip()
        cache_key = f"{text_lower}_{dest}"
        
        if cache_key in self.translation_cache:
            return self._format_translation(text, self.translation_cache[cache_key])
        
        local_result = self._search_local_dict(text_lower)
        if local_result:
            self.translation_cache[cache_key] = local_result
            return self._format_translation(text, local_result)
        
        should_use_external = (
            self.use_external and 
            self.external_translator and 
            len(text) > 2 and
            not self._is_already_english(text_lower)
        )
        
        if should_use_external:
            try:
                self.external_translator.source = src
                self.external_translator.target = dest
                translated = self.external_translator.translate(text)
                
                if translated and translated.lower() != text_lower:
                    self.translation_cache[cache_key] = translated
                    if len(text_lower) < 50:
                        self.local_dict[text_lower] = translated.lower()
                    return self._format_translation(text, translated)
            except Exception as e:
                logger.warning(f"External translation failed: {str(e)[:80]}")
                self.use_external = False
        
        fallback = self._word_by_word_translation(text)
        self.translation_cache[cache_key] = fallback
        return self._format_translation(text, fallback)
    
    def detect_language(self, text, retries=0):
        """Detectar idioma de forma inteligente"""
        if not text or not isinstance(text, str):
            return 'en', 0.8
        
        text_lower = text.lower()
        
        spanish_words = ['el', 'la', 'los', 'las', 'un', 'una', 'de', 'que', 
                        'y', 'en', 'por', 'con', 'para', 'sin', 'sobre']
        
        english_words = ['the', 'a', 'an', 'and', 'but', 'or', 'because', 'if',
                        'when', 'where', 'why', 'how', 'what', 'which', 'who']
        
        spanish_count = 0
        english_count = 0
        
        words = text_lower.split()
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word in spanish_words:
                spanish_count += 1
            if clean_word in english_words:
                english_count += 1
        
        total = spanish_count + english_count
        if total == 0:
            return 'en', 0.6
        
        if spanish_count > english_count:
            confidence = 0.5 + (spanish_count / total) * 0.4
            return 'es', min(confidence, 0.95)
        else:
            confidence = 0.5 + (english_count / total) * 0.4
            return 'en', min(confidence, 0.95)
    
    def _search_local_dict(self, text):
        """Buscar en diccionario local de forma inteligente"""
        if text in self.local_dict:
            return self.local_dict[text]
        
        for phrase_es, phrase_en in self.local_dict.items():
            if len(phrase_es) > 4 and phrase_es in text:
                result = text.replace(phrase_es, phrase_en)
                return result
        
        return None
    
    def _is_already_english(self, text):
        """Verificar si el texto ya está en inglés"""
        english_words = ['the', 'and', 'but', 'because', 'when', 'where', 'why']
        words = text.split()
        english_word_count = sum(1 for word in words if word in english_words)
        
        if len(words) > 0:
            english_ratio = english_word_count / len(words)
            return english_ratio > 0.3
        return False
    
    def _word_by_word_translation(self, text):
        """Traducción palabra por palabra"""
        words = text.split()
        translated_words = []
        
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word.lower())
            if clean_word in self.local_dict:
                translated_words.append(self.local_dict[clean_word])
            else:
                translated_words.append(word)
        
        return ' '.join(translated_words)
    
    def _format_translation(self, original, translated):
        """Formatear traducción manteniendo capitalización"""
        if original and len(original) > 0 and original[0].isupper():
            if translated and len(translated) > 0:
                translated = translated[0].upper() + translated[1:]
        return translated

translator = HybridTranslator()

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
            "total_attempts": 0,
            "vocabulary_games": 0,
            "pronunciation_games": 0
        }
        self.xp = 0
        self.level = 1
        self.created_at = datetime.now()
        self.last_interaction = datetime.now()
        self.pronunciation_scores = []
        self.game_history = []
        self.last_question = ""
        self.needs_scaffolding = False
        self.current_topic = "general"
    
    def add_conversation(self, user_text: str, eli_response: str, score: float):
        self.conversation_history.append({
            "user": user_text[:100],
            "eli": eli_response[:500],
            "score": score,
            "timestamp": datetime.now().isoformat()
        })
        self.pronunciation_scores.append(score)
        
        if len(self.conversation_history) > 20:
            self.conversation_history.pop(0)
        if len(self.pronunciation_scores) > 10:
            self.pronunciation_scores.pop(0)
    
    def add_game_result(self, game_type: str, correct: bool, points: int):
        self.game_history.append({
            "game_type": game_type,
            "correct": correct,
            "points": points,
            "timestamp": datetime.now().isoformat()
        })
        
        self.game_stats["games_played"] += 1
        self.game_stats["total_points"] += points
        
        if game_type == "vocabulary":
            self.game_stats["vocabulary_games"] += 1
        elif game_type == "pronunciation":
            self.game_stats["pronunciation_games"] += 1
        
        if correct:
            self.game_stats["correct_answers"] += 1
            self.xp += points
        
        self.game_stats["total_attempts"] += 1
        
        if len(self.game_history) > 50:
            self.game_history.pop(0)
    
    def update_level(self):
        if not self.pronunciation_scores:
            return
        
        avg_score = sum(self.pronunciation_scores) / len(self.pronunciation_scores)
        
        if avg_score >= 80:
            self.current_level = "advanced"
        elif avg_score >= 60:
            self.current_level = "intermediate"
        else:
            self.current_level = "beginner"
    
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
            "game_history_count": len(self.game_history),
            "last_interaction": self.last_interaction.isoformat(),
            "current_topic": self.current_topic,
            "needs_scaffolding": self.needs_scaffolding,
            "last_question": self.last_question
        }

class SessionManager:
    def __init__(self):
        self.sessions = {}
    
    def create_session(self, user_id: str):
        session_id = f"{user_id[:6]}_{int(time.time())}"
        session = UserSession(user_id, session_id)
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str):
        session = self.sessions.get(session_id)
        if session:
            session.last_interaction = datetime.now()
        return session
    
    def update_session(self, session_id: str, **kwargs):
        if session_id in self.sessions:
            session = self.sessions[session_id]
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            session.last_interaction = datetime.now()

session_manager = SessionManager()

# ============================================
# SISTEMA COACH UNIFICADO (TODO EN UNO)
# ============================================
class SistemaCoachUnificado:
    def __init__(self):
        self.topics = [
            "daily routine", "family", "hobbies", "food", "weather",
            "school", "future plans", "travel", "music", "sports"
        ]
        
        # Scaffolding por nivel
        self.scaffolding_templates = {
            "beginner": [
                "My name is ______ and I like ______.",
                "I am from ______ and I study ______.",
                "Today is ______ and I feel ______.",
                "I have ______ and my favorite ______ is ______.",
                "I like to ______ because it is ______."
            ],
            "intermediate": [
                "On weekends, I usually ______ because ______.",
                "My favorite hobby is ______ since ______.",
                "Recently, I have been ______ which makes me feel ______.",
                "Although ______, I still ______ because ______.",
                "When I have free time, I enjoy ______ as it helps me ______."
            ],
            "advanced": [
                "From my perspective, ______ demonstrates that ______.",
                "The implications of ______ suggest that ______.",
                "Despite ______, it is evident that ______ consequently ______.",
                "Throughout my experience, I have learned that ______ therefore ______.",
                "Considering ______, one can observe that ______ which leads to ______."
            ]
        }
        
        # Vocabulario por tema
        self.topic_vocabulary = {
            "daily routine": ["wake up", "get dressed", "have breakfast", "go to school", 
                            "study", "have lunch", "do homework", "relax", "go to bed"],
            "family": ["parents", "siblings", "grandparents", "relatives", "close",
                      "supportive", "loving", "spend time", "traditions"],
            "hobbies": ["reading", "sports", "music", "drawing", "cooking",
                       "gaming", "watching movies", "collecting", "photography"],
            "food": ["breakfast", "lunch", "dinner", "snacks", "healthy",
                    "delicious", "restaurant", "cook", "recipe", "favorite"],
            "weather": ["sunny", "rainy", "cloudy", "windy", "temperature",
                       "season", "hot", "cold", "forecast", "climate"],
            "school": ["subjects", "teachers", "classmates", "homework", "exams",
                      "projects", "learning", "knowledge", "education"],
            "future plans": ["career", "university", "travel", "goals", "dreams",
                           "aspirations", "achieve", "plan", "prepare"],
            "travel": ["destinations", "culture", "language", "adventure", "sightseeing",
                      "memories", "experience", "explore", "discover"],
            "music": ["genres", "instruments", "concerts", "artists", "songs",
                     "lyrics", "rhythm", "melody", "playlist"],
            "sports": ["team", "competition", "exercise", "health", "practice",
                      "skills", "championship", "players", "strategy"]
        }
        
        # Palabras clave para detectar necesidad de ayuda
        self.help_keywords = [
            'help', 'ayuda', 'i dont know', "i don't know", 'no sé',
            'what should i say', 'how do i say', 'i cant', "i can't",
            'qué puedo decir', "i'm not sure", 'i need help',
            'no entiendo', "i don't understand", 'no puedo',
            'qué digo', 'what do i say', 'cómo se dice',
            'i need assistance', 'can you help', 'ayúdame'
        ]
        
        # Detectar temas en preguntas
        self.topic_patterns = {
            'daily routine': ['routine', 'day', 'morning', 'wake up', 'schedule'],
            'family': ['family', 'parents', 'brother', 'sister', 'mother', 'father'],
            'hobbies': ['hobby', 'free time', 'like to do', 'enjoy', 'interest'],
            'food': ['food', 'eat', 'restaurant', 'dish', 'cook', 'meal'],
            'travel': ['travel', 'visit', 'country', 'city', 'trip', 'vacation'],
            'school': ['school', 'study', 'learn', 'education', 'teacher'],
            'work': ['work', 'job', 'career', 'profession', 'office'],
            'future': ['future', 'plan', 'goal', 'dream', 'aspiration']
        }
    
    def detectar_nivel_usuario(self, texto: str, duracion_audio: float) -> str:
        """Detectar nivel del usuario"""
        if not texto or len(texto.strip()) < 3:
            return "beginner"
        
        palabras = texto.split()
        word_count = len(palabras)
        
        advanced_words = {'although', 'however', 'therefore', 'furthermore', 
                         'meanwhile', 'consequently', 'nevertheless'}
        
        advanced_count = sum(1 for word in palabras if word.lower() in advanced_words)
        
        score = 0
        if word_count > 10: score += 3
        elif word_count > 5: score += 2
        elif word_count > 2: score += 1
        
        score += advanced_count * 2
        
        if score >= 6: return "advanced"
        elif score >= 3: return "intermediate"
        return "beginner"
    
    def analizar_pronunciacion(self, texto: str, audio_duration: float):
        """Análisis de pronunciación"""
        if not texto:
            return {
                'score': 0,
                'problem_words': [],
                'tips': ["Try speaking for at least 2 seconds"],
                'detected_level': "beginner",
                'word_count': 0,
                'duration': audio_duration
            }
        
        palabras = texto.lower().split()
        nivel = self.detectar_nivel_usuario(texto, audio_duration)
        
        problem_patterns = {
            'the': 'ðə (tongue between teeth)',
            'think': 'θɪŋk (soft "th")',
            'this': 'ðɪs (vibrating "th")',
            'very': 'vɛri (bite lower lip)',
            'water': 'wɔːtər (pronounce the "t")'
        }
        
        problem_words = []
        for palabra in palabras[:5]:
            clean = re.sub(r'[^\w]', '', palabra)
            if clean in problem_patterns:
                problem_words.append({
                    'word': clean,
                    'explanation': problem_patterns[clean]
                })
        
        score = 65.0
        
        if audio_duration >= 2.0:
            score += 10
        if len(palabras) >= 5:
            score += 5
        
        if problem_words:
            score -= len(problem_words) * 5
        
        if nivel == "intermediate":
            score += 5
        elif nivel == "advanced":
            score += 10
        
        score = max(30.0, min(98.0, score))
        
        tips = []
        if nivel == "beginner":
            if len(palabras) < 3:
                tips.append("Try to form longer sentences (minimum 3 words)")
            if audio_duration < 1.5:
                tips.append("Speak for at least 2 seconds to practice rhythm")
        
        elif nivel == "intermediate":
            if not problem_words and len(palabras) > 5:
                tips.append("Great! Now try using connecting words")
        
        if problem_words:
            tips.append(f"Practice: {', '.join(pw['word'] for pw in problem_words[:2])}")
        
        return {
            'score': round(score, 1),
            'problem_words': problem_words[:2],
            'tips': tips[:3],
            'detected_level': nivel,
            'word_count': len(palabras),
            'duration': round(audio_duration, 1)
        }
    
    def procesar_mensaje_completo(self, texto_usuario: str, duracion_audio: float = 0, 
                                  last_question: str = "", session_data: dict = None):
        """
        PROCESA TODO EN UN SOLO PASO - EL CEREBRO COMPLETO
        
        Retorna una respuesta completa que Flutter solo necesita mostrar
        """
        if not texto_usuario or len(texto_usuario.strip()) < 2:
            return self._respuesta_sin_audio()
        
        texto_lower = texto_usuario.lower().strip()
        
        # 1. DETECTAR NECESIDAD DE AYUDA (Scaffolding)
        necesita_ayuda = any(keyword in texto_lower for keyword in self.help_keywords)
        es_muy_corto = len(texto_usuario.strip()) < 3
        es_no_sé = texto_lower in ["i don't know", "no sé", "idk", "no se"]
        
        # 2. SI NECESITA AYUDA, DAR SCAFFOLDING COMPLETO
        if necesita_ayuda or es_muy_corto or es_no_sé:
            return self._generar_scaffolding_completo(texto_usuario, last_question, session_data)
        
        # 3. Detectar idioma
        lang, confidence = translator.detect_language(texto_usuario)
        if lang == 'es' and confidence > 0.6:
            return self._respuesta_en_espanol(texto_usuario)
        
        # 4. Analizar pronunciación normal
        analisis = self.analizar_pronunciacion(texto_usuario, duracion_audio)
        
        # 5. Detectar tema de la conversación
        detected_topic = self._detectar_tema(texto_usuario, last_question)
        
        # 6. Generar respuesta apropiada
        if analisis['score'] < 50:
            response_type = "needs_improvement"
        elif analisis['score'] > 85:
            response_type = "excellent"
        else:
            response_type = "normal_feedback"
        
        # 7. Construir respuesta completa
        respuesta_completa = self._construir_respuesta_completa(
            texto_usuario, analisis, response_type, detected_topic, last_question
        )
        
        # 8. Preparar datos para scaffolding si el score es bajo
        scaffolding_data = None
        if analisis['score'] < 60 or analisis['word_count'] < 4:
            scaffolding_data = self._preparar_scaffolding_data(
                detected_topic, analisis['detected_level'], last_question
            )
        
        return {
            "type": "conversation_response",
            "message": respuesta_completa,
            "pronunciation_score": analisis['score'],
            "detected_level": analisis['detected_level'],
            "corrections": analisis['problem_words'],
            "tips": analisis['tips'],
            "word_count": analisis['word_count'],
            "duration": analisis['duration'],
            "needs_scaffolding": scaffolding_data is not None,
            "scaffolding_data": scaffolding_data,
            "next_question": self._generar_pregunta_seguimiento(detected_topic, analisis['detected_level']),
            "detected_topic": detected_topic,
            "xp_earned": self._calcular_xp(analisis['score'], analisis['word_count']),
            "response_type": response_type,
            "timestamp": datetime.now().isoformat()
        }
    
    def _generar_scaffolding_completo(self, texto_usuario: str, last_question: str, session_data: dict = None):
        """Generar scaffolding completo como Praktika"""
        # Determinar nivel
        nivel = "beginner"
        if session_data and 'current_level' in session_data:
            nivel = session_data['current_level']
        
        # Detectar tema
        tema = self._detectar_tema_de_pregunta(last_question) if last_question else "general"
        
        # Plantilla de scaffolding
        scaffolding = random.choice(self.scaffolding_templates[nivel])
        
        # Vocabulario del tema
        vocab = self.topic_vocabulary.get(tema, ["useful words for this topic"])
        
        # Ejemplo completo
        example = self._generate_example_for_topic(tema, nivel)
        
        # Consejos específicos
        tips = self._get_scaffolding_tips(nivel)
        
        response_text = f"""## 🆘 **I'll Help You Structure Your Answer!**

### 🎯 **Topic:** {tema.capitalize()}

### 📝 **Sentence Starter:**
\"{scaffolding}\"

### 🔤 **Useful Vocabulary:**
{', '.join(vocab[:6])}

### 💡 **How to Build Your Answer:**
1. **Choose** words from the vocabulary list
2. **Fill in** the blanks in the sentence starter
3. **Add** details to make it personal
4. **Practice** saying it out loud

### ✨ **Example Complete Answer:**
\"{example}\"

### 🎤 **Now It's Your Turn:**
Record your answer using the structure above!

### 🔄 **Remember:** It's okay to make mistakes. That's how we learn! 💪"""
        
        return {
            "type": "scaffolding_response",
            "message": response_text,
            "pronunciation_score": 0,
            "detected_level": nivel,
            "needs_scaffolding": True,
            "scaffolding_data": {
                "template": scaffolding,
                "examples": [example],
                "vocabulary": vocab[:6],
                "topic": tema,
                "level": nivel,
                "tips": tips
            },
            "next_question": f"Tell me about {tema}",
            "detected_topic": tema,
            "xp_earned": 10,  # XP por pedir ayuda
            "response_type": "scaffolding",
            "timestamp": datetime.now().isoformat()
        }
    
    def _respuesta_sin_audio(self):
        """Respuesta cuando no hay audio"""
        return {
            "type": "no_speech",
            "message": """🎤 **I Didn't Hear Anything**

💡 **Tips for Better Recording:**
• Speak clearly for 2-3 seconds
• Be in a quiet place
• Hold microphone closer

🔊 **Try Saying:**
• "Hello, my name is..."
• "I like to practice English"
• "Today is a good day"

🎯 **Ready when you are!**""",
            "pronunciation_score": 0,
            "detected_level": "beginner",
            "needs_scaffolding": True,
            "scaffolding_data": {
                "template": "Hello, my name is...",
                "examples": ["Hello, my name is [Your Name]", "I like to learn English"],
                "vocabulary": ["hello", "name", "my", "like", "learn"],
                "topic": "introduction",
                "level": "beginner"
            },
            "next_question": "What is your name?",
            "xp_earned": 0
        }
    
    def _respuesta_en_espanol(self, texto_usuario: str):
        """Respuesta cuando habla en español"""
        translated = translator.translate_with_retry(texto_usuario, src='es', dest='en')
        
        return {
            "type": "language_switch",
            "message": f"""🌐 **I Notice You Spoke in Spanish**

🗣️ **In Spanish:** "{texto_usuario}"
🔤 **In English:** "{translated}"

🎯 **Try Saying It in English Now:**
1. Listen to the English version
2. Repeat slowly word by word
3. Focus on pronunciation
4. Put it all together

💡 **Tip:** Don't translate word-for-word. Think of the message!

🔁 **Practice:** "{translated}" """,
            "pronunciation_score": 40,
            "detected_level": "beginner",
            "needs_scaffolding": True,
            "scaffolding_data": {
                "template": translated,
                "examples": [translated],
                "vocabulary": ["practice", "speak", "english", "slowly"],
                "topic": "translation",
                "level": "beginner"
            },
            "next_question": "Can you say that in English?",
            "xp_earned": 5
        }
    
    def _detectar_tema(self, texto: str, last_question: str = ""):
        """Detectar tema de la conversación"""
        texto_lower = (texto + " " + last_question).lower()
        
        for tema, palabras in self.topic_patterns.items():
            for palabra in palabras:
                if palabra in texto_lower:
                    return tema
        
        # Si no se detecta, elegir aleatorio basado en nivel
        return random.choice(self.topics)
    
    def _detectar_tema_de_pregunta(self, pregunta: str):
        """Detectar tema específico de una pregunta"""
        if not pregunta:
            return "general"
        
        pregunta_lower = pregunta.lower()
        for tema, palabras in self.topic_patterns.items():
            for palabra in palabras:
                if palabra in pregunta_lower:
                    return tema
        
        return "general"
    
    def _construir_respuesta_completa(self, texto_usuario: str, analisis: dict, 
                                     response_type: str, tema: str, last_question: str):
        """Construir respuesta completa de feedback"""
        motivational_phrases = {
            "beginner": "🎉 **Great effort!** You're making progress!",
            "intermediate": "🌟 **Well done!** Your English is improving!",
            "advanced": "💫 **Excellent!** Very impressive English!"
        }
        
        nivel = analisis['detected_level']
        motivational = motivational_phrases.get(nivel, "🎉 Good job!")
        
        parts = [motivational]
        parts.append(f"🗣️ **You said:** \"{texto_usuario}\"")
        parts.append(f"📊 **Pronunciation Score:** {analisis['score']}/100")
        
        if analisis['problem_words']:
            parts.append("\n🎯 **Focus on:**")
            for pw in analisis['problem_words']:
                parts.append(f"• **{pw['word']}**: {pw['explanation']}")
        
        if analisis['tips']:
            parts.append("\n💡 **Tips:**")
            for tip in analisis['tips']:
                parts.append(f"• {tip}")
        
        # Sugerencia de scaffolding si el score es bajo
        if analisis['score'] < 60:
            parts.append("\n🆘 **Need more help?** Try using this structure:")
            scaffolding = random.choice(self.scaffolding_templates[nivel])
            parts.append(f"\"{scaffolding}\"")
        
        # Próxima pregunta relacionada
        next_q = self._generar_pregunta_seguimiento(tema, nivel)
        parts.append(f"\n💬 **Next question:** {next_q}")
        
        return "\n".join(parts)
    
    def _preparar_scaffolding_data(self, tema: str, nivel: str, last_question: str = ""):
        """Preparar datos de scaffolding"""
        scaffolding = random.choice(self.scaffolding_templates[nivel])
        vocab = self.topic_vocabulary.get(tema, ["words", "phrases", "sentences"])
        example = self._generate_example_for_topic(tema, nivel)
        tips = self._get_scaffolding_tips(nivel)
        
        return {
            "template": scaffolding,
            "examples": [example],
            "vocabulary": vocab[:6],
            "topic": tema,
            "level": nivel,
            "tips": tips,
            "is_help_response": True
        }
    
    def _generar_pregunta_seguimiento(self, tema: str, nivel: str):
        """Generar pregunta de seguimiento"""
        preguntas_por_tema = {
            "daily routine": {
                "beginner": "What time do you usually wake up?",
                "intermediate": "Describe your typical morning routine.",
                "advanced": "How has your daily routine evolved over the years?"
            },
            "family": {
                "beginner": "Do you have any brothers or sisters?",
                "intermediate": "What activities do you enjoy doing with your family?",
                "advanced": "How have family dynamics changed in modern society?"
            },
            "hobbies": {
                "beginner": "What do you like to do in your free time?",
                "intermediate": "How did you develop your interest in your favorite hobby?",
                "advanced": "How do hobbies contribute to personal development?"
            },
            "food": {
                "beginner": "What is your favorite food?",
                "intermediate": "Describe the last meal you really enjoyed.",
                "advanced": "How does food culture reflect a society's values?"
            }
        }
        
        if tema in preguntas_por_tema and nivel in preguntas_por_tema[tema]:
            return preguntas_por_tema[tema][nivel]
        
        # Preguntas genéricas por nivel
        preguntas_genericas = {
            "beginner": [
                "What is your name and where are you from?",
                "Do you have any pets?",
                "What is your favorite color?",
                "What do you like to do on weekends?"
            ],
            "intermediate": [
                "What are your plans for next weekend?",
                "Describe your hometown.",
                "What skill would you like to learn?",
                "Tell me about a happy memory."
            ],
            "advanced": [
                "What are your goals for the next 5 years?",
                "How has technology changed education?",
                "What global issue concerns you most?",
                "What does success mean to you?"
            ]
        }
        
        return random.choice(preguntas_genericas.get(nivel, preguntas_genericas["beginner"]))
    
    def _generate_example_for_topic(self, topic: str, nivel: str) -> str:
        """Generar ejemplo para un tema específico"""
        examples_by_topic = {
            "daily routine": {
                "beginner": "I wake up at 7 AM, go to school, and do homework in the afternoon.",
                "intermediate": "My daily routine starts with waking up at 6:30, followed by school, studying, and some leisure time in the evening.",
                "advanced": "Throughout my day, I maintain a structured routine that balances academic responsibilities with personal development activities."
            },
            "family": {
                "beginner": "My family has four people: my parents, my sister, and me.",
                "intermediate": "My family is very important to me. We support each other and spend quality time together on weekends.",
                "advanced": "The dynamics within my family have significantly influenced my values and personal development throughout the years."
            },
            "hobbies": {
                "beginner": "I like to play soccer and watch movies.",
                "intermediate": "In my free time, I enjoy reading novels and playing guitar, which helps me relax and be creative.",
                "advanced": "My hobbies, particularly reading and music, serve as both creative outlets and opportunities for continuous learning."
            },
            "general": {
                "beginner": "I enjoy learning English because it helps me communicate with people.",
                "intermediate": "Learning English has opened many opportunities for me to connect with different cultures.",
                "advanced": "Mastering English has been instrumental in broadening my global perspective and professional opportunities."
            }
        }
        
        if topic in examples_by_topic and nivel in examples_by_topic[topic]:
            return examples_by_topic[topic][nivel]
        
        generic_examples = {
            "beginner": f"I like {topic} because it's interesting.",
            "intermediate": f"I enjoy {topic} as it allows me to learn new things and have fun.",
            "advanced": f"Engaging with {topic} provides valuable insights and contributes to personal growth."
        }
        
        return generic_examples.get(nivel, f"I find {topic} very interesting.")
    
    def _get_scaffolding_tips(self, nivel: str):
        """Consejos específicos por nivel"""
        tips = {
            "beginner": [
                "Speak slowly and clearly",
                "Use simple sentences",
                "Don't worry about mistakes"
            ],
            "intermediate": [
                "Try using connecting words",
                "Add details to your answers",
                "Focus on pronunciation of difficult words"
            ],
            "advanced": [
                "Use complex sentence structures",
                "Incorporate idiomatic expressions",
                "Focus on intonation and rhythm"
            ]
        }
        return tips.get(nivel, tips["beginner"])
    
    def _calcular_xp(self, score: float, word_count: int) -> int:
        """Calcular XP ganado"""
        base_xp = 10
        score_bonus = int(score / 10)
        length_bonus = min(word_count, 10)
        
        total_xp = base_xp + score_bonus + length_bonus
        return min(total_xp, 30)  # Máximo 30 XP por respuesta

coach_unificado = SistemaCoachUnificado()

# ============================================
# PROCESADOR DE AUDIO
# ============================================
class AudioProcessor:
    def process_audio(self, audio_file):
        try:
            audio_bytes = audio_file.read(app.config['AUDIO_FILE_MAX_SIZE'])
            
            if len(audio_bytes) > app.config['AUDIO_FILE_MAX_SIZE']:
                raise ValueError(f"Audio too large (max {app.config['AUDIO_FILE_MAX_SIZE']/1024/1024}MB)")
            
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            duration = len(audio) / 1000.0
            
            audio = audio.set_channels(1).set_frame_rate(16000)
            
            wav_buffer = io.BytesIO()
            audio.export(wav_buffer, format="wav")
            wav_buffer.seek(0)
            
            logger.info(f"Audio processed: {duration:.2f}s")
            return wav_buffer, duration
            
        except Exception as e:
            logger.error(f"Audio processing error: {str(e)[:100]}")
            raise
    
    def transcribe_audio(self, wav_buffer: io.BytesIO) -> str:
        recognizer = sr.Recognizer()
        
        try:
            with sr.AudioFile(wav_buffer) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language='en-US')
                return text.strip()
        except sr.UnknownValueError:
            return ""
        except Exception:
            return ""

audio_processor = AudioProcessor()

# ============================================
# ENDPOINTS DE LA API
# ============================================
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Eli English Tutor v6.0 (Unificado)",
        "version": "6.0.0",
        "timestamp": datetime.now().isoformat(),
        "architecture": "Backend-only intelligence",
        "features": ["Unified Processing", "Smart Scaffolding", "Complete Analysis", "Games"]
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "sessions_active": len(session_manager.sessions),
        "coach": "unified",
        "games_available": True
    })

# ============================================
# ENDPOINT PRINCIPAL UNIFICADO
# ============================================
@app.route('/api/process-audio', methods=['POST'])
def process_audio_unified():
    """
    ENDPOINT PRINCIPAL - TODO se procesa aquí
    
    Flutter solo envía audio y recibe respuesta completa
    """
    try:
        # Validar audio
        if 'audio' not in request.files:
            return jsonify({
                "status": "error",
                "message": "No audio file provided",
                "type": "no_audio"
            }), 400
        
        audio_file = request.files['audio']
        session_id = request.form.get('session_id', '')
        user_id = request.form.get('user_id', 'default_user')
        current_question = request.form.get('current_question', '')
        
        logger.info(f"🔊 Processing audio - Session: {session_id}, Question: {current_question[:50]}...")
        
        # 1. Procesar audio
        wav_buffer, duration = audio_processor.process_audio(audio_file)
        transcription = audio_processor.transcribe_audio(wav_buffer)
        
        # 2. Obtener o crear sesión
        session = session_manager.get_session(session_id)
        if not session:
            session = session_manager.create_session(user_id)
        
        # Actualizar pregunta actual si se proporciona
        if current_question:
            session.last_question = current_question
        
        # 3. Si no hay transcripción, usar respuesta especial
        if not transcription or len(transcription.strip()) < 2:
            logger.info("No speech detected")
            response = coach_unificado._respuesta_sin_audio()
            
            return jsonify({
                "status": "success",
                "data": response
            })
        
        logger.info(f"Transcription: {transcription}")
        
        # 4. PROCESAR CON EL COACH UNIFICADO
        session_data = session.to_dict()
        response = coach_unificado.procesar_mensaje_completo(
            texto_usuario=transcription,
            duracion_audio=duration,
            last_question=session.last_question,
            session_data=session_data
        )
        
        # 5. Actualizar sesión con los resultados
        session.add_conversation(
            transcription,
            response["message"],
            response["pronunciation_score"]
        )
        session.xp += response["xp_earned"]
        session.update_level()
        
        # Actualizar tema si se detectó
        if "detected_topic" in response:
            session.current_topic = response["detected_topic"]
        
        # Actualizar necesidad de scaffolding
        session.needs_scaffolding = response.get("needs_scaffolding", False)
        
        # Actualizar última pregunta si hay nueva
        if response.get("next_question"):
            session.last_question = response["next_question"]
        
        # 6. Preparar respuesta final para Flutter
        final_response = {
            "status": "success",
            "data": {
                **response,
                "session_info": {
                    "session_id": session_id,
                    "user_id": user_id,
                    "current_level": session.current_level,
                    "xp": session.xp,
                    "xp_earned": response["xp_earned"],
                    "total_xp": session.xp,
                    "conversation_count": len(session.conversation_history),
                    "current_topic": session.current_topic,
                    "needs_scaffolding": session.needs_scaffolding,
                    "last_question": session.last_question
                },
                "transcription": transcription,
                "duration": round(duration, 2),
                "audio_processed": True,
                "response_timestamp": datetime.now().isoformat()
            }
        }
        
        logger.info(f"✅ Processing complete - Score: {response['pronunciation_score']}, XP: {response['xp_earned']}, Type: {response['type']}")
        
        return jsonify(final_response)
        
    except ValueError as e:
        logger.error(f"File too large: {e}")
        return jsonify({
            "status": "error",
            "message": "Audio file too large (max 5MB)",
            "type": "file_too_large"
        }), 413
    except Exception as e:
        logger.error(f"❌ Error in unified endpoint: {str(e)[:200]}")
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "type": "server_error"
        }), 500

# ============================================
# ENDPOINTS COMPLEMENTARIOS (para Flutter)
# ============================================
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
            "welcome_message": "🎯 Welcome to Eli! Let's practice English!",
            "initial_level": session.current_level,
            "session_info": session.to_dict()
        })
    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)[:100]}), 500

@app.route('/api/get-question', methods=['POST'])
def get_question():
    """Obtener pregunta para el usuario"""
    try:
        data = request.json or {}
        session_id = data.get('session_id', '')
        topic = data.get('topic', '')
        
        level = "beginner"
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                level = session.current_level
                if topic:
                    session.current_topic = topic
        
        # Usar el coach unificado para generar pregunta
        question = coach_unificado._generar_pregunta_seguimiento(
            topic if topic else "general", 
            level
        )
        
        # Actualizar sesión
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                session.last_question = question
        
        return jsonify({
            "status": "success",
            "data": {
                "question": question,
                "topic": topic if topic else "general",
                "level": level,
                "difficulty": {"beginner": "easy", "intermediate": "medium", "advanced": "hard"}.get(level, "easy"),
                "session_id": session_id
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get-question: {str(e)[:100]}")
        return jsonify({
            "status": "success",
            "data": {
                "question": "Tell me about yourself",
                "topic": "general",
                "level": "beginner",
                "difficulty": "easy",
                "session_id": session_id if 'session_id' in locals() else ""
            }
        })

@app.route('/api/get-scaffolding', methods=['POST'])
def get_scaffolding():
    """
    Endpoint para cuando Flutter explícitamente pide scaffolding
    (por ejemplo, botón de ayuda)
    """
    try:
        data = request.json or {}
        user_text = data.get('user_text', '')
        session_id = data.get('session_id', '')
        question = data.get('question', '')
        
        # Obtener sesión
        session = None
        if session_id:
            session = session_manager.get_session(session_id)
        
        # Usar el coach unificado para generar scaffolding
        nivel = session.current_level if session else "beginner"
        tema = coach_unificado._detectar_tema_de_pregunta(question) if question else "general"
        
        scaffolding_data = coach_unificado._preparar_scaffolding_data(tema, nivel, question)
        
        response_text = f"""## 💡 **Help with: {tema.capitalize()}**

### 📝 **Use this structure:**
\"{scaffolding_data['template']}\"

### 🔤 **Vocabulary to use:**
{', '.join(scaffolding_data['vocabulary'])}

### ✨ **Example:**
\"{scaffolding_data['examples'][0]}\"

### 💡 **Tips:**
{' • '.join(scaffolding_data['tips'])}

🎤 **Now try recording your answer!**"""
        
        return jsonify({
            "status": "success",
            "data": {
                "type": "explicit_scaffolding",
                "message": response_text,
                "scaffolding_data": scaffolding_data,
                "question": question,
                "topic": tema,
                "level": nivel,
                "session_id": session_id
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get-scaffolding: {str(e)[:100]}")
        return jsonify({
            "status": "error",
            "message": str(e)[:100]
        }), 500

@app.route('/api/estadisticas', methods=['GET'])
def obtener_estadisticas():
    try:
        session_id = request.args.get('session_id')
        
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                return jsonify({
                    "estado": "exito", 
                    "stats": session.to_dict(),
                    "game_stats": session.game_stats,
                    "recent_conversations": session.conversation_history[-5:] if session.conversation_history else []
                })
        
        return jsonify({
            "estado": "exito",
            "global_stats": {
                "total_sessions": len(session_manager.sessions),
                "active_sessions": len([s for s in session_manager.sessions.values() 
                                      if (datetime.now() - s.last_interaction).seconds < 3600])
            }
        })
    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)[:100]}), 500

# ============================================
# ENDPOINTS DE COMPATIBILIDAD
# ============================================
@app.route('/api/conversar_audio', methods=['POST'])
def conversar_audio():
    """Endpoint antiguo para compatibilidad"""
    try:
        if 'audio' not in request.files:
            return jsonify({"estado": "error", "respuesta": "No audio file"}), 400
        
        # Redirigir al endpoint unificado
        return process_audio_unified()
    
    except Exception as e:
        logger.error(f"Error in conversar_audio: {str(e)[:100]}")
        return jsonify({"estado": "error", "respuesta": "Error processing audio"}), 500

# ============================================
# EJECUCIÓN
# ============================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 60)
    print(f"🚀 Eli English Tutor v6.0 - BACKEND UNIFICADO")
    print(f"📡 Port: {port}")
    print(f"🎯 TODO la inteligencia está aquí")
    print(f"📱 Flutter solo muestra respuestas")
    print("=" * 60)
    print()
    print("✅ ENDPOINTS DISPONIBLES:")
    print("POST /api/process-audio          - Procesa audio (PRINCIPAL)")
    print("POST /api/get-question           - Obtiene pregunta")
    print("POST /api/get-scaffolding        - Ayuda explícita")
    print("POST /api/sesion/iniciar         - Inicia sesión")
    print("GET  /api/estadisticas           - Estadísticas")
    print("GET  /api/health                 - Health check")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)