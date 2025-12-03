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
# OPTIMIZACIONES PARA RENDER GRATUITO
# ============================================
# Configurar límites de memoria para plan gratuito (512MB)
try:
    import resource
    # Limitar a 400MB para dejar espacio para el sistema
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (400 * 1024 * 1024, hard))
    logger_memory = logging.getLogger('memory')
    logger_memory.info(f"Memory limit set to 400MB")
except:
    pass

# Configurar logging optimizado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('eli_app.log', mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Reducir logs verbosos en producción
if os.environ.get('RENDER'):
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    logging.getLogger('httpx').setLevel(logging.ERROR)

print("=" * 60)
print("🚀 Eli English Tutor - Backend Optimizado para Render")
print("📁 Archivo: eli_backend.py")
print("=" * 60)

# ============================================
# CONFIGURACIÓN
# ============================================
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'eli-secret-key-' + str(uuid.uuid4())[:8])
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB máximo
    AUDIO_FILE_MAX_SIZE = 5 * 1024 * 1024  # 5MB para audio
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    # Optimizaciones para googletrans
    TRANSLATION_TIMEOUT = 15
    TRANSLATION_RETRIES = 3

app = Flask(__name__)
app.config.from_object(Config)

# CORS optimizado para Render
CORS(app, resources={
    r"/api/*": {
        "origins": ["*", "https://*.onrender.com", "http://localhost:*", "http://localhost:3000"],
        "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "X-User-ID", "X-Session-ID", "X-Requested-With"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": False,
        "max_age": 600
    }
})

# Middleware para optimizar respuestas
@app.after_request
def after_request(response):
    """Añadir headers de optimización"""
    response.headers.add('X-ELI-Version', '5.0.0')
    response.headers.add('X-ELI-Optimized', 'Render-Free-Tier')
    
    # Headers de cache para recursos estáticos
    if request.path.startswith('/static/'):
        response.headers.add('Cache-Control', 'public, max-age=3600')
    
    return response

# ============================================
# GOOGLETRANS CON MANEJO DE ERRORES ROBUSTO
# ============================================
class RobustTranslator:
    def __init__(self):
        self.translator = None
        self.cache = {}
        self.cache_size = 200  # Tamaño máximo de cache
        self.initialization_attempts = 0
        self.max_init_attempts = 5
        self._initialize_translator_with_retry()
    
    def _initialize_translator_with_retry(self):
        """Inicializar googletrans con múltiples intentos y delay"""
        for attempt in range(self.max_init_attempts):
            try:
                # Intentar importar e inicializar
                from googletrans import Translator
                self.translator = Translator(
                    timeout=app.config['TRANSLATION_TIMEOUT'],
                    service_urls=[
                        'translate.google.com',
                        'translate.google.co.kr',
                        'translate.google.es'
                    ]
                )
                
                # Test simple
                test_result = self.translator.translate('hello', src='en', dest='es')
                if test_result and hasattr(test_result, 'text'):
                    logger.info(f"✅ Googletrans initialized successfully (attempt {attempt + 1})")
                    self.initialization_attempts = attempt + 1
                    return
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} to initialize googletrans failed: {str(e)[:100]}")
                if attempt < self.max_init_attempts - 1:
                    # Esperar antes de reintentar
                    time.sleep(1 + attempt)  # Backoff exponencial
        
        logger.error("❌ Failed to initialize googletrans after all attempts. Using fallback mode.")
        self.translator = None
    
    def _manage_cache(self, key, value=None):
        """Manejo de cache LRU"""
        if value is not None:
            # Añadir/actualizar en cache
            if key in self.cache:
                del self.cache[key]
            elif len(self.cache) >= self.cache_size:
                # Eliminar el más antiguo (primero en OrderedDict)
                oldest = next(iter(self.cache))
                del self.cache[oldest]
            
            self.cache[key] = {
                'value': value,
                'timestamp': time.time()
            }
            return value
        
        # Obtener del cache
        if key in self.cache:
            item = self.cache[key]
            # Actualizar timestamp (LRU)
            del self.cache[key]
            self.cache[key] = item
            return item['value']
        
        return None
    
    def translate_with_retry(self, text, src='auto', dest='en', retries=2):
        """Traducir con cache y múltiples reintentos"""
        if not text or not isinstance(text, str) or len(text.strip()) == 0:
            return text
        
        # Cache key
        cache_key = f"trans_{hash(text)}_{src}_{dest}"
        
        # Verificar cache primero
        cached = self._manage_cache(cache_key)
        if cached is not None:
            return cached
        
        # Si no hay traductor, intentar reinicializar
        if not self.translator:
            self._initialize_translator_with_retry()
            if not self.translator:
                fallback = self._fallback_translate(text, dest)
                self._manage_cache(cache_key, fallback)
                return fallback
        
        # Intentar traducción con reintentos
        last_exception = None
        for attempt in range(retries):
            try:
                result = self.translator.translate(text, src=src, dest=dest)
                
                if hasattr(result, 'text'):
                    translated = result.text
                else:
                    translated = str(result)
                
                # Guardar en cache
                self._manage_cache(cache_key, translated)
                return translated
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Translation attempt {attempt + 1} failed: {str(e)[:80]}")
                
                # Esperar antes de reintentar
                if attempt < retries - 1:
                    time.sleep(0.5 * (attempt + 1))
        
        # Si todos los intentos fallan, usar fallback
        logger.error(f"All translation attempts failed for: '{text[:50]}...'")
        fallback = self._fallback_translate(text, dest)
        self._manage_cache(cache_key, fallback)
        return fallback
    
    def detect_language(self, text, retries=2):
        """Detectar idioma con cache"""
        if not text or not isinstance(text, str):
            return 'en', 0.8
        
        cache_key = f"detect_{hash(text)}"
        
        # Verificar cache
        cached = self._manage_cache(cache_key)
        if cached is not None:
            return cached
        
        # Si no hay traductor
        if not self.translator:
            result = self._simple_language_detection(text)
            self._manage_cache(cache_key, result)
            return result
        
        # Detectar con googletrans
        last_exception = None
        for attempt in range(retries):
            try:
                detection = self.translator.detect(text)
                
                lang = detection.lang if hasattr(detection, 'lang') else 'en'
                confidence = getattr(detection, 'confidence', 0.8)
                
                result = (lang, min(float(confidence), 0.95))
                self._manage_cache(cache_key, result)
                return result
                
            except Exception as e:
                last_exception = e
                if attempt < retries - 1:
                    time.sleep(0.3)
        
        # Fallback si falla
        result = self._simple_language_detection(text)
        self._manage_cache(cache_key, result)
        return result
    
    def _simple_language_detection(self, text):
        """Detección simple cuando googletrans falla"""
        text_lower = text.lower()
        
        # Indicadores de español
        spanish_indicators = [
            ' el ', ' la ', ' los ', ' las ', ' un ', ' una ', ' unos ', ' unas ',
            ' de ', ' que ', ' y ', ' en ', ' por ', ' con ', ' para ', ' sin ',
            ' sobre ', ' entre ', ' hasta ', ' desde ', ' hacia ', ' durante ',
            ' según ', ' mediante ', ' además ', ' aunque ', ' porque ', ' cuando ',
            ' donde ', ' como ', ' pero ', ' sino ', ' aunque ', ' mientras ',
            ' porque ', ' pues ', ' entonces ', ' luego ', ' ahora ', ' siempre ',
            ' nunca ', ' también ', ' tampoco ', ' quizás ', ' tal vez ', ' acaso '
        ]
        
        # Indicadores de inglés
        english_indicators = [
            ' the ', ' a ', ' an ', ' and ', ' but ', ' or ', ' because ', ' if ',
            ' when ', ' where ', ' why ', ' how ', ' what ', ' which ', ' who ',
            ' whose ', ' whom ', ' that ', ' this ', ' these ', ' those ', ' then ',
            ' there ', ' their ', ' they\'re ', ' you ', ' your ', ' you\'re ',
            ' we ', ' our ', ' us ', ' he ', ' him ', ' his ', ' she ', ' her ',
            ' it ', ' its ', ' i ', ' me ', ' my ', ' mine '
        ]
        
        # Contar ocurrencias
        spanish_count = sum(1 for indicator in spanish_indicators if indicator in f' {text_lower} ')
        english_count = sum(1 for indicator in english_indicators if indicator in f' {text_lower} ')
        
        # Determinar idioma
        if spanish_count > english_count:
            confidence = 0.5 + (spanish_count * 0.05)
            return 'es', min(confidence, 0.9)
        elif english_count > spanish_count:
            confidence = 0.5 + (english_count * 0.05)
            return 'en', min(confidence, 0.9)
        else:
            # Empate o sin indicadores claros
            return 'en', 0.6
    
    def _fallback_translate(self, text, dest='en'):
        """Traducción de respaldo mejorada para educación"""
        # Diccionario educativo ampliado
        educational_dict = {
            # Saludos básicos
            'hola': 'hello', 'adiós': 'goodbye', 'buenos días': 'good morning',
            'buenas tardes': 'good afternoon', 'buenas noches': 'good night',
            'por favor': 'please', 'gracias': 'thank you', 'de nada': 'you\'re welcome',
            'lo siento': 'i\'m sorry', 'perdón': 'excuse me', 'con permiso': 'excuse me',
            
            # Preguntas comunes
            'cómo estás': 'how are you', 'qué tal': 'how are you',
            'cómo te llamas': 'what is your name', 'cuántos años tienes': 'how old are you',
            'de dónde eres': 'where are you from', 'dónde vives': 'where do you live',
            'qué haces': 'what do you do', 'a qué te dedicas': 'what do you do for a living',
            
            # Vocabulario escolar
            'escuela': 'school', 'colegio': 'school', 'universidad': 'university',
            'maestro': 'teacher', 'profesor': 'teacher', 'estudiante': 'student',
            'alumno': 'student', 'clase': 'class', 'curso': 'course',
            'examen': 'exam', 'prueba': 'test', 'tarea': 'homework',
            'libro': 'book', 'cuaderno': 'notebook', 'lápiz': 'pencil',
            'pluma': 'pen', 'borrador': 'eraser', 'mochila': 'backpack',
            
            # Familia
            'familia': 'family', 'padres': 'parents', 'madre': 'mother',
            'padre': 'father', 'mamá': 'mom', 'papá': 'dad',
            'hermano': 'brother', 'hermana': 'sister', 'abuelo': 'grandfather',
            'abuela': 'grandmother', 'tío': 'uncle', 'tía': 'aunt',
            'primo': 'cousin', 'sobrino': 'nephew', 'sobrina': 'niece',
            
            # Casa
            'casa': 'house', 'hogar': 'home', 'apartamento': 'apartment',
            'habitación': 'room', 'dormitorio': 'bedroom', 'sala': 'living room',
            'cocina': 'kitchen', 'baño': 'bathroom', 'comedor': 'dining room',
            'jardín': 'garden', 'garaje': 'garage', 'puerta': 'door',
            'ventana': 'window', 'techo': 'roof', 'pared': 'wall',
            
            # Comida
            'comida': 'food', 'desayuno': 'breakfast', 'almuerzo': 'lunch',
            'cena': 'dinner', 'agua': 'water', 'leche': 'milk',
            'pan': 'bread', 'arroz': 'rice', 'frijoles': 'beans',
            'carne': 'meat', 'pollo': 'chicken', 'pescado': 'fish',
            'ensalada': 'salad', 'fruta': 'fruit', 'verdura': 'vegetable',
            'manzana': 'apple', 'naranja': 'orange', 'plátano': 'banana',
            'fresa': 'strawberry', 'uva': 'grape', 'sandía': 'watermelon',
            
            # Animales
            'animal': 'animal', 'perro': 'dog', 'gato': 'cat',
            'pájaro': 'bird', 'pez': 'fish', 'caballo': 'horse',
            'vaca': 'cow', 'cerdo': 'pig', 'oveja': 'sheep',
            'conejo': 'rabbit', 'tortuga': 'turtle', 'serpiente': 'snake',
            
            # Colores
            'color': 'color', 'rojo': 'red', 'azul': 'blue',
            'verde': 'green', 'amarillo': 'yellow', 'naranja': 'orange',
            'morado': 'purple', 'rosa': 'pink', 'blanco': 'white',
            'negro': 'black', 'gris': 'gray', 'marrón': 'brown',
            
            # Números (1-20)
            'uno': 'one', 'dos': 'two', 'tres': 'three',
            'cuatro': 'four', 'cinco': 'five', 'seis': 'six',
            'siete': 'seven', 'ocho': 'eight', 'nueve': 'nine',
            'diez': 'ten', 'once': 'eleven', 'doce': 'twelve',
            'trece': 'thirteen', 'catorce': 'fourteen', 'quince': 'fifteen',
            'dieciséis': 'sixteen', 'diecisiete': 'seventeen', 'dieciocho': 'eighteen',
            'diecinueve': 'nineteen', 'veinte': 'twenty',
            
            # Días y tiempo
            'día': 'day', 'semana': 'week', 'mes': 'month',
            'año': 'year', 'hoy': 'today', 'mañana': 'tomorrow',
            'ayer': 'yesterday', 'lunes': 'monday', 'martes': 'tuesday',
            'miércoles': 'wednesday', 'jueves': 'thursday', 'viernes': 'friday',
            'sábado': 'saturday', 'domingo': 'sunday',
            
            # Verbos comunes (infinitivo -> presente simple)
            'ser': 'to be', 'estar': 'to be', 'tener': 'to have',
            'hacer': 'to do', 'ir': 'to go', 'venir': 'to come',
            'ver': 'to see', 'mirar': 'to look', 'escuchar': 'to listen',
            'hablar': 'to speak', 'decir': 'to say', 'pensar': 'to think',
            'saber': 'to know', 'conocer': 'to know', 'querer': 'to want',
            'amar': 'to love', 'gustar': 'to like', 'necesitar': 'to need',
            'poder': 'can', 'deber': 'should', 'estudiar': 'to study',
            'aprender': 'to learn', 'enseñar': 'to teach', 'trabajar': 'to work',
            'jugar': 'to play', 'comer': 'to eat', 'beber': 'to drink',
            'dormir': 'to sleep', 'despertar': 'to wake up', 'levantarse': 'to get up',
            
            # Frases educativas comunes
            'no entiendo': 'i don\'t understand',
            'puede repetir por favor': 'can you repeat please',
            'hablo un poco de inglés': 'i speak a little english',
            'estoy aprendiendo inglés': 'i am learning english',
            'quiero practicar mi pronunciación': 'i want to practice my pronunciation',
            'cómo se pronuncia esta palabra': 'how do you pronounce this word',
            'puede hablar más despacio por favor': 'can you speak slower please',
            'qué significa esta palabra': 'what does this word mean',
            'cómo se escribe': 'how do you spell it',
            'puedo ir al baño': 'can i go to the bathroom',
            'necesito ayuda': 'i need help',
            'no sé la respuesta': 'i don\'t know the answer',
            'puede explicarlo de nuevo': 'can you explain it again',
            'es correcto': 'is it correct',
            'puedo intentarlo': 'can i try',
            'quiero participar': 'i want to participate',
            'me gusta esta clase': 'i like this class',
            'el inglés es importante': 'english is important',
            'quiero viajar al extranjero': 'i want to travel abroad',
            'necesito practicar más': 'i need to practice more'
        }
        
        text_lower = text.lower().strip()
        
        # 1. Buscar coincidencia exacta en el diccionario
        if text_lower in educational_dict:
            return educational_dict[text_lower]
        
        # 2. Buscar frases que contengan patrones conocidos
        for phrase_es, phrase_en in educational_dict.items():
            if phrase_es in text_lower and len(phrase_es) > 3:
                # Reemplazar la frase encontrada
                result = text_lower.replace(phrase_es, phrase_en)
                
                # Capitalizar primera letra si es necesario
                if text[0].isupper():
                    result = result[0].upper() + result[1:]
                
                return result
        
        # 3. Traducción palabra por palabra (como último recurso)
        words = re.findall(r'\b[a-záéíóúñ]+\b', text_lower, re.IGNORECASE)
        translated_words = []
        
        for word in words:
            if word in educational_dict:
                translated_words.append(educational_dict[word])
            else:
                # Mantener palabras desconocidas
                translated_words.append(word)
        
        result = ' '.join(translated_words)
        
        # 4. Si no se tradujo nada, devolver el texto original
        if result == text_lower:
            return text
        
        # Capitalizar si el original estaba capitalizado
        if text and text[0].isupper():
            result = result[0].upper() + result[1:]
        
        return result

# Instancia global del traductor
translator = RobustTranslator()

# ============================================
# MODELOS DE DATOS OPTIMIZADOS
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
            "vocabulary_mastered": 0
        }
        self.xp = 0
        self.level = 1
        self.daily_streak = 0
        self.streak_last_date = datetime.now().date()
        self.created_at = datetime.now()
        self.last_interaction = datetime.now()
        self.pronunciation_scores = []
        self.last_10_scores = []
        self.weak_points = {}
        self.achievements = []
        
        # Inicializar weak points con categorías comunes
        self.weak_points = {
            "pronunciation": {},
            "vocabulary": {},
            "grammar": {},
            "fluency": {}
        }
    
    def add_conversation(self, user_text: str, eli_response: str, score: float, corrections=None):
        """Añadir conversación con análisis de puntos débiles"""
        entry = {
            "user": user_text[:150],
            "eli": eli_response[:300],
            "score": score,
            "timestamp": datetime.now().isoformat(),
            "corrections": corrections or []
        }
        
        self.conversation_history.append(entry)
        self.pronunciation_scores.append(score)
        self.last_10_scores.append(score)
        
        # Analizar puntos débiles basados en correcciones
        if corrections:
            for correction in corrections:
                category = self._categorize_correction(correction)
                if category:
                    word = correction.get('word', 'unknown')
                    if word not in self.weak_points[category]:
                        self.weak_points[category][word] = 1
                    else:
                        self.weak_points[category][word] += 1
        
        # Limitar tamaño para optimizar memoria
        if len(self.conversation_history) > 20:
            self.conversation_history.pop(0)
        if len(self.pronunciation_scores) > 30:
            self.pronunciation_scores.pop(0)
        if len(self.last_10_scores) > 10:
            self.last_10_scores.pop(0)
        
        # Verificar logros
        self._check_achievements()
        
        # Actualizar streak diario
        self._update_streak()
    
    def _categorize_correction(self, correction):
        """Categorizar corrección para análisis"""
        word = correction.get('word', '').lower()
        
        # Palabras problemáticas de pronunciación
        pronunciation_words = {'the', 'think', 'this', 'very', 'water', 'world', 'right', 'light'}
        if word in pronunciation_words:
            return "pronunciation"
        
        # Palabras gramaticales
        grammar_words = {'is', 'are', 'was', 'were', 'have', 'has', 'do', 'does'}
        if word in grammar_words:
            return "grammar"
        
        return "vocabulary"
    
    def _check_achievements(self):
        """Verificar y otorgar logros"""
        achievements_to_check = [
            ("first_conversation", len(self.conversation_history) >= 1),
            ("conversation_streak_5", len(self.conversation_history) >= 5),
            ("conversation_streak_10", len(self.conversation_history) >= 10),
            ("high_score_90", any(score >= 90 for score in self.last_10_scores)),
            ("consistent_80", len([s for s in self.last_10_scores if s >= 80]) >= 5)
        ]
        
        for achievement_id, condition in achievements_to_check:
            if condition and achievement_id not in self.achievements:
                self.achievements.append(achievement_id)
    
    def _update_streak(self):
        """Actualizar racha diaria"""
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        if self.streak_last_date == yesterday:
            self.daily_streak += 1
        elif self.streak_last_date < yesterday:
            self.daily_streak = 1
        
        self.streak_last_date = today
    
    def update_level(self):
        """Actualizar nivel basado en rendimiento"""
        if not self.last_10_scores:
            return
        
        avg_score = sum(self.last_10_scores) / len(self.last_10_scores)
        
        # Subir de nivel basado en XP
        if self.xp >= 100 and self.level < 2:
            self.level = 2
        elif self.xp >= 300 and self.level < 3:
            self.level = 3
        elif self.xp >= 600 and self.level < 4:
            self.level = 4
        elif self.xp >= 1000 and self.level < 5:
            self.level = 5
        
        # Actualizar nivel de dificultad
        if avg_score >= 85 and self.current_level != "advanced":
            self.current_level = "advanced"
        elif avg_score >= 70 and self.current_level == "beginner":
            self.current_level = "intermediate"
        elif avg_score < 60 and self.current_level != "beginner":
            self.current_level = "beginner"
    
    def to_dict(self):
        """Convertir a dict optimizado para JSON"""
        avg_score = sum(self.last_10_scores) / len(self.last_10_scores) if self.last_10_scores else 0
        
        # Obtener puntos débiles principales
        main_weak_points = {}
        for category, words in self.weak_points.items():
            if words:
                sorted_words = sorted(words.items(), key=lambda x: x[1], reverse=True)[:3]
                main_weak_points[category] = dict(sorted_words)
        
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "current_level": self.current_level,
            "xp": self.xp,
            "level": self.level,
            "game_stats": self.game_stats,
            "conversation_count": len(self.conversation_history),
            "avg_pronunciation_score": round(avg_score, 1),
            "daily_streak": self.daily_streak,
            "achievements": self.achievements[:5],
            "weak_points": main_weak_points,
            "last_interaction": self.last_interaction.isoformat(),
            "created_at": self.created_at.isoformat()
        }

# ============================================
# GESTIÓN DE SESIONES CON LIMPIEZA AUTOMÁTICA
# ============================================
class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutos
        self.max_sessions = 100  # Máximo para plan gratuito
        self.session_timeout = 3600  # 1 hora de inactividad
    
    def create_session(self, user_id: str):
        """Crear nueva sesión con gestión de memoria"""
        # Limpiar sesiones antiguas si estamos cerca del límite
        if len(self.sessions) >= self.max_sessions * 0.8:
            self._force_cleanup()
        
        session_id = f"{user_id[:6]}_{int(time.time())}_{uuid.uuid4().hex[:4]}"
        session = UserSession(user_id, session_id)
        self.sessions[session_id] = session
        
        logger.info(f"New session created: {session_id} (Total: {len(self.sessions)})")
        return session
    
    def get_session(self, session_id: str):
        """Obtener sesión y actualizar tiempo"""
        session = self.sessions.get(session_id)
        if session:
            session.last_interaction = datetime.now()
        return session
    
    def update_session(self, session_id: str, **kwargs):
        """Actualizar propiedades de sesión"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            session.last_interaction = datetime.now()
    
    def _auto_cleanup(self):
        """Limpieza automática periódica"""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        self.last_cleanup = current_time
        cutoff_time = datetime.now() - timedelta(seconds=self.session_timeout)
        
        sessions_to_remove = []
        for session_id, session in self.sessions.items():
            if session.last_interaction < cutoff_time:
                sessions_to_remove.append(session_id)
        
        removed_count = 0
        for session_id in sessions_to_remove:
            if session_id in self.sessions:
                del self.sessions[session_id]
                removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Auto-cleaned {removed_count} inactive sessions")
            
            # Forzar garbage collection
            import gc
            gc.collect()
    
    def _force_cleanup(self):
        """Limpieza forzada cuando hay muchas sesiones"""
        logger.warning(f"Force cleanup triggered. Sessions: {len(self.sessions)}")
        
        # Ordenar sesiones por última interacción (más antiguas primero)
        sorted_sessions = sorted(
            self.sessions.items(),
            key=lambda x: x[1].last_interaction
        )
        
        # Eliminar la mitad más antigua si excede el límite
        if len(sorted_sessions) > self.max_sessions:
            to_remove = len(sorted_sessions) - (self.max_sessions // 2)
            for i in range(to_remove):
                session_id, _ = sorted_sessions[i]
                if session_id in self.sessions:
                    del self.sessions[session_id]
            
            logger.warning(f"Force removed {to_remove} sessions")
            
            import gc
            gc.collect()

session_manager = SessionManager()

# ============================================
# SISTEMA COACH CONVERSACIONAL (TIPO PRAKTIKA AI)
# ============================================
class SistemaCoach:
    def __init__(self):
        self.topics = [
            "daily routine", "family and friends", "hobbies and interests", 
            "food and cooking", "weather and seasons", "travel and vacations",
            "work and careers", "school and education", "sports and fitness",
            "music and movies", "technology and gadgets", "future plans and goals",
            "memories and experiences", "culture and traditions", "health and wellness"
        ]
        
        self.question_cache = {}
        self.last_cache_cleanup = time.time()
        
        # Frases de motivación por nivel
        self.motivational_phrases = {
            "beginner": [
                "Great effort! Every word you speak brings you closer to fluency!",
                "You're doing amazing! Learning a new language takes courage!",
                "Perfect! Practice makes permanent. Keep going!",
                "Well done! Remember, every expert was once a beginner!",
                "Excellent try! Your pronunciation is getting better each time!"
            ],
            "intermediate": [
                "Impressive! You're forming more complex sentences naturally!",
                "Outstanding! Your vocabulary is expanding beautifully!",
                "Fantastic! Your sentence structure is becoming more natural!",
                "Wonderful! You're expressing ideas more fluently!",
                "Superb! Your confidence in speaking is really showing!"
            ],
            "advanced": [
                "Exceptional! You're speaking with near-native fluency!",
                "Remarkable! Your command of the language is impressive!",
                "Brilliant! You're using advanced vocabulary naturally!",
                "Masterful! Your pronunciation is excellent!",
                "Outstanding! You're communicating complex ideas with ease!"
            ]
        }
    
    def _clean_cache(self):
        """Limpiar cache periódicamente"""
        current_time = time.time()
        if current_time - self.last_cache_cleanup > 300:  # 5 minutos
            self.question_cache = {
                k: v for k, v in self.question_cache.items()
                if current_time - v['timestamp'] < 300
            }
            self.last_cache_cleanup = current_time
    
    def detectar_nivel_usuario(self, texto: str, duracion_audio: float) -> str:
        """Detectar nivel similar a Praktika AI"""
        if not texto or len(texto.strip()) < 3:
            return "beginner"
        
        texto = texto.strip()
        palabras = texto.split()
        word_count = len(palabras)
        
        # Análisis de complejidad
        advanced_indicators = {
            'words': {'although', 'however', 'therefore', 'furthermore', 
                     'meanwhile', 'consequently', 'nevertheless', 'moreover',
                     'nonetheless', 'regardless', 'subsequently'},
            'structures': ['if i were', 'i wish i had', 'should have', 'would have',
                          'could have', 'might have', 'must have', 'had i known'],
            'tenses': ['have been', 'had been', 'will have', 'would be', 'could be']
        }
        
        # Contar indicadores avanzados
        advanced_word_count = 0
        for word in palabras:
            if word.lower() in advanced_indicators['words']:
                advanced_word_count += 1
        
        # Verificar estructuras complejas
        complex_structure_count = 0
        texto_lower = texto.lower()
        for structure in advanced_indicators['structures']:
            if structure in texto_lower:
                complex_structure_count += 1
        
        # Verificar tiempos verbales complejos
        complex_tense_count = 0
        for tense in advanced_indicators['tenses']:
            if tense in texto_lower:
                complex_tense_count += 1
        
        # Calcular puntuación de nivel
        score = 0
        
        # Puntuación por longitud
        if word_count > 15:
            score += 4
        elif word_count > 10:
            score += 3
        elif word_count > 6:
            score += 2
        elif word_count > 3:
            score += 1
        
        # Puntuación por palabras avanzadas
        score += advanced_word_count * 2
        
        # Puntuación por estructuras complejas
        score += complex_structure_count * 3
        
        # Puntuación por tiempos verbales complejos
        score += complex_tense_count * 2
        
        # Puntuación por fluidez (duración vs palabras)
        if duracion_audio > 0:
            words_per_second = word_count / duracion_audio
            if 2.0 <= words_per_second <= 3.5:  # Rango de habla natural
                score += 2
            elif words_per_second > 3.5:  # Habla rápida pero comprensible
                score += 1
        
        # Determinar nivel basado en score
        if score >= 10:
            return "advanced"
        elif score >= 5:
            return "intermediate"
        else:
            return "beginner"
    
    def analizar_pronunciacion(self, texto: str, audio_duration: float):
        """Análisis de pronunciación detallado como Praktika AI"""
        if not texto or len(texto.strip()) < 2:
            return {
                'score': 0,
                'problem_words': [],
                'tips': ["Try speaking for at least 2-3 seconds"],
                'detected_level': "beginner",
                'word_count': 0,
                'duration': audio_duration,
                'fluency_score': 0,
                'intonation_score': 0,
                'clarity_score': 0
            }
        
        texto = texto.strip()
        palabras = texto.lower().split()
        word_count = len(palabras)
        nivel = self.detectar_nivel_usuario(texto, audio_duration)
        
        # Base de datos de palabras problemáticas con guías fonéticas
        pronunciation_guide = {
            # Consonantes problemáticas
            'the': {'sound': 'ðə', 'tip': 'Lengua entre dientes para el "th"'},
            'think': {'sound': 'θɪŋk', 'tip': '"Th" suave, sin vibración'},
            'this': {'sound': 'ðɪs', 'tip': '"Th" con vibración'},
            'very': {'sound': 'vɛri', 'tip': 'Morder suavemente el labio inferior'},
            'water': {'sound': 'wɔːtər', 'tip': 'Pronunciar la "t" claramente'},
            'world': {'sound': 'wɜːrld', 'tip': 'Tres sílabas: wor-l-d'},
            'right': {'sound': 'raɪt', 'tip': '"R" fuerte, como un rugido suave'},
            'light': {'sound': 'laɪt', 'tip': '"L" clara, lengua en el paladar'},
            'she': {'sound': 'ʃi', 'tip': 'Labios redondeados para "sh"'},
            'usually': {'sound': 'juːʒuəli', 'tip': 'Sonido "zh" como en "vision"'},
            'question': {'sound': 'kwɛstʃən', 'tip': '"Ch" suave, no "sh"'},
            'picture': {'sound': 'pɪktʃər', 'tip': '"Ch" no "ture"'},
            'comfortable': {'sound': 'kʌmftəbəl', 'tip': 'Tres sílabas, la "t" es suave'},
            'interesting': {'sound': 'ɪntrəstɪŋ', 'tip': 'Tres sílabas: in-tres-ting'},
            'library': {'sound': 'laɪbrɛri', 'tip': 'Tres sílabas: li-bra-ry'},
            
            # Vocales problemáticas
            'beach': {'sound': 'biːtʃ', 'tip': 'Vocal larga "ee"'},
            'bitch': {'sound': 'bɪtʃ', 'tip': 'Vocal corta "i"'},
            'sheet': {'sound': 'ʃiːt', 'tip': 'Vocal larga "ee"'},
            'shit': {'sound': 'ʃɪt', 'tip': 'Vocal corta "i"'},
            'full': {'sound': 'fʊl', 'tip': 'Vocal "u" corta'},
            'fool': {'sound': 'fuːl', 'tip': 'Vocal "oo" larga'},
            
            # Grupos consonánticos
            'strength': {'sound': 'strɛŋθ', 'tip': '"ng" + "th"'},
            'months': {'sound': 'mʌnθs', 'tip': '"nth" + "s"'},
            'sixth': {'sound': 'sɪksθ', 'tip': '"ks" + "th"'},
            
            # Palabras comúnmente mal pronunciadas
            'pronunciation': {'sound': 'prəˌnʌnsiˈeɪʃən', 'tip': '5 sílabas, acento en la 4ta'},
            'mischievous': {'sound': 'mɪstʃɪvəs', 'tip': '3 sílabas, no 4'},
            'espresso': {'sound': 'ɛˈsprɛsoʊ', 'tip': 'No "expresso"'},
            'specific': {'sound': 'spəˈsɪfɪk', 'tip': 'Acento en la segunda sílaba'},
            'probably': {'sound': 'ˈprɒbəbli', 'tip': '2 sílabas, no 3'},
            'literally': {'sound': 'ˈlɪtərəli', 'tip': '4 sílabas, no 5'}
        }
        
        # Detectar palabras problemáticas
        problem_words = []
        for palabra in palabras:
            clean_word = re.sub(r'[^\w]', '', palabra)
            if clean_word in pronunciation_guide:
                guide = pronunciation_guide[clean_word]
                problem_words.append({
                    'word': clean_word,
                    'sound': guide['sound'],
                    'tip': guide['tip'],
                    'example': f"Repeat: {clean_word} -> /{guide['sound']}/"
                })
                
                # Limitar a 4 palabras problemáticas máximo
                if len(problem_words) >= 4:
                    break
        
        # Calcular puntuaciones individuales
        base_score = 70.0
        
        # 1. Puntuación de claridad (35%)
        clarity_score = 80.0
        if problem_words:
            clarity_score -= len(problem_words) * 5
        if word_count >= 5:
            clarity_score += 5
        
        # 2. Puntuación de fluidez (35%)
        fluency_score = 75.0
        if audio_duration > 0:
            words_per_second = word_count / audio_duration
            
            # Rango ideal: 2.0 - 3.5 palabras por segundo
            if 2.0 <= words_per_second <= 3.5:
                fluency_score += 15
            elif 1.5 <= words_per_second < 2.0:
                fluency_score += 10
            elif words_per_second < 1.0:
                fluency_score -= 10  # Demasiado lento
            elif words_per_second > 4.0:
                fluency_score -= 5   # Demasiado rápido
        
        # 3. Puntuación de entonación (30%)
        intonation_score = 65.0
        
        # Bonus por preguntas (entonación ascendente)
        if texto.endswith('?'):
            intonation_score += 10
        
        # Bonus por oraciones completas
        if texto[0].isupper() and texto.endswith(('.', '!', '?')):
            intonation_score += 5
        
        # Bonus por variedad de tono (basado en puntuación)
        punctuation_count = sum(1 for char in texto if char in ',;:')
        if punctuation_count > 0:
            intonation_score += min(punctuation_count * 3, 10)
        
        # Ajustar por nivel
        if nivel == "intermediate":
            base_score += 5
            fluency_score += 5
        elif nivel == "advanced":
            base_score += 10
            fluency_score += 10
            intonation_score += 10
        
        # Penalización por problemas específicos
        if problem_words:
            clarity_score -= len(problem_words) * 3
        
        # Calcular puntuación final ponderada
        final_score = (
            (clarity_score * 0.35) +
            (fluency_score * 0.35) +
            (intonation_score * 0.30)
        )
        
        # Asegurar rango
        final_score = max(30.0, min(99.0, final_score))
        
        # Generar consejos personalizados
        tips = []
        
        # Consejos de claridad
        if clarity_score < 75:
            if problem_words:
                practice_words = ', '.join(pw['word'] for pw in problem_words[:2])
                tips.append(f"Practice clarity: {practice_words}")
            else:
                tips.append("Focus on clear articulation of each sound")
        
        # Consejos de fluidez
        if fluency_score < 75:
            if audio_duration > 0:
                wps = word_count / audio_duration
                if wps < 1.5:
                    tips.append("Try speaking a bit faster, aim for 2-3 words per second")
                elif wps > 4.0:
                    tips.append("Slow down slightly for better clarity")
        
        # Consejos de entonación
        if intonation_score < 70:
            if not texto.endswith(('.', '!', '?')):
                tips.append("Practice using proper sentence endings (., !, ?)")
            if punctuation_count == 0 and word_count > 8:
                tips.append("Use commas to create natural pauses in long sentences")
        
        # Consejos específicos por nivel
        if nivel == "beginner":
            if word_count < 4:
                tips.append("Try forming longer sentences (4+ words)")
            if audio_duration < 2.0:
                tips.append("Speak for at least 2 seconds to practice rhythm")
        
        elif nivel == "intermediate":
            if not any(word in texto.lower() for word in ['and', 'but', 'because', 'so']):
                tips.append("Use connecting words to make sentences flow better")
            if fluency_score >= 80:
                tips.append("Great fluency! Now work on natural intonation patterns")
        
        else:  # advanced
            if final_score < 85:
                tips.append("Aim for more natural, native-like rhythm and stress")
            if intonation_score >= 85:
                tips.append("Excellent intonation! Your speech sounds very natural")
        
        # Añadir frase motivacional
        if final_score >= 85:
            tips.append(random.choice([
                "🌟 Excellent pronunciation! You sound very natural!",
                "🎯 Near-perfect! Your hard work is paying off!",
                "💫 Outstanding! You're mastering English pronunciation!"
            ]))
        
        return {
            'score': round(final_score, 1),
            'problem_words': problem_words[:3],  # Máximo 3
            'tips': tips[:4],  # Máximo 4 tips
            'detected_level': nivel,
            'word_count': word_count,
            'duration': round(audio_duration, 2),
            'fluency_score': round(fluency_score, 1),
            'intonation_score': round(intonation_score, 1),
            'clarity_score': round(clarity_score, 1),
            'words_per_second': round(word_count / audio_duration, 2) if audio_duration > 0 else 0
        }
    
    def generar_respuesta(self, texto_usuario: str, duracion_audio: float = 0):
        """Generar respuesta similar a Praktika AI"""
        texto_original = texto_usuario.strip()
        texto_lower = texto_original.lower()
        
        # Respuesta para audio vacío o muy corto
        if not texto_original or len(texto_original) < 2:
            return self._respuesta_sin_audio()
        
        # Respuesta de ayuda explícita
        help_keywords = ['help', 'ayuda', 'i dont know', 'no sé', 'what should i say',
                        'no sé qué decir', 'qué digo', 'help me']
        
        if any(keyword in texto_lower for keyword in help_keywords):
            return self._respuesta_ayuda(texto_original, duracion_audio)
        
        # Detectar idioma
        lang, confidence = translator.detect_language(texto_original)
        
        # Si habló en español (con alta confianza)
        if lang == 'es' and confidence > 0.7:
            return self._respuesta_en_espanol(texto_original)
        
        # Análisis completo de pronunciación
        analisis = self.analizar_pronunciacion(texto_original, duracion_audio)
        
        # Frase motivacional aleatoria según nivel
        motivational = random.choice(self.motivational_phrases[analisis['detected_level']])
        
        # Construir respuesta estructurada
        response_parts = []
        
        # 1. Encabezado motivacional
        response_parts.append(f"## 🎯 {motivational}")
        
        # 2. Lo que dijo el usuario
        response_parts.append(f"\n### 🗣️ **You said:**")
        response_parts.append(f"> \"{texto_original}\"")
        
        # 3. Puntuación general
        score_emoji = "🌟" if analisis['score'] >= 90 else "⭐" if analisis['score'] >= 80 else "📊"
        response_parts.append(f"\n### {score_emoji} **Overall Score: {analisis['score']}/100**")
        
        # 4. Desglose de puntuaciones
        response_parts.append(f"\n#### 📈 **Detailed Analysis:**")
        response_parts.append(f"• **Clarity:** {analisis['clarity_score']}/100")
        response_parts.append(f"• **Fluency:** {analisis['fluency_score']}/100")
        response_parts.append(f"• **Intonation:** {analisis['intonation_score']}/100")
        
        if analisis['words_per_second'] > 0:
            wps = analisis['words_per_second']
            speed_status = "Perfect! 🎯" if 2.0 <= wps <= 3.5 else "Good" if 1.5 <= wps < 2.0 else "Needs adjustment"
            response_parts.append(f"• **Speaking Rate:** {wps} words/sec ({speed_status})")
        
        # 5. Correcciones específicas
        if analisis['problem_words']:
            response_parts.append(f"\n#### 🎯 **Pronunciation Focus:**")
            
            for i, pw in enumerate(analisis['problem_words'], 1):
                response_parts.append(f"\n**{i}. {pw['word'].upper()}**")
                response_parts.append(f"   🔤 **Correct:** /{pw['sound']}/")
                response_parts.append(f"   💡 **Tip:** {pw['tip']}")
                response_parts.append(f"   🎧 **Practice:** \"{pw['example']}\"")
        
        # 6. Consejos personalizados
        if analisis['tips']:
            response_parts.append(f"\n#### 💡 **Personalized Tips:**")
            for tip in analisis['tips']:
                response_parts.append(f"• {tip}")
        
        # 7. Próximo paso
        next_question = self._generar_pregunta(analisis['detected_level'])
        response_parts.append(f"\n#### 💬 **Let's Continue:**")
        response_parts.append(f"{next_question}")
        
        # 8. Ejemplos si el score es bajo
        if analisis['score'] < 70:
            examples = self._generar_ejemplos(analisis['detected_level'])
            response_parts.append(f"\n#### 📝 **Practice Examples:**")
            for example in examples[:2]:
                response_parts.append(f"• \"{example}\"")
        
        # 9. Instrucción para repetir si es necesario
        if analisis['score'] < 60:
            response_parts.append(f"\n#### 🔁 **Practice This:**")
            response_parts.append(f"Try repeating: \"{texto_original}\"")
            response_parts.append(f"Focus on: {', '.join(pw['word'] for pw in analisis['problem_words'][:2]) if analisis['problem_words'] else 'clear pronunciation'}")
        
        # Unificar respuesta
        full_response = "\n".join(response_parts)
        
        return {
            "respuesta": full_response,
            "tipo": "conversacion",
            "correcciones": analisis['problem_words'],
            "consejos": analisis['tips'],
            "pregunta_seguimiento": True,
            "nivel_detectado": analisis['detected_level'],
            "pronunciation_score": analisis['score'],
            "next_question": next_question,
            "ejemplos_respuesta": self._generar_ejemplos(analisis['detected_level'])[:3],
            "detailed_scores": {
                "clarity": analisis['clarity_score'],
                "fluency": analisis['fluency_score'],
                "intonation": analisis['intonation_score']
            }
        }
    
    def _respuesta_sin_audio(self):
        """Respuesta cuando no se detecta audio"""
        return {
            "respuesta": """## 🎤 **I Didn't Hear Anything**

### 🤔 **Possible Reasons:**
• You might not have spoken loud enough
• The recording might be too short
• There could be too much background noise

### 💡 **Tips for Better Recording:**
1. **Speak clearly** for at least 2-3 seconds
2. **Hold the microphone** about 15-20 cm from your mouth
3. **Choose a quiet place** with minimal background noise
4. **Make sure** your microphone is working properly

### 🔊 **Example Phrases to Try:**
• "Hello, my name is [your name]"
• "I enjoy learning English"
• "Today I want to practice my pronunciation"
• "My favorite hobby is [your hobby]"

### 🎯 **Ready When You Are!**
Press record and try again. Remember, every attempt helps you improve! 🚀""",
            "tipo": "ayuda",
            "pronunciation_score": 0,
            "nivel_detectado": "beginner",
            "ejemplos_respuesta": [
                "Hello, my name is...",
                "I like to learn English",
                "Today is a good day to practice"
            ]
        }
    
    def _respuesta_ayuda(self, texto_usuario: str, duracion_audio: float):
        """Respuesta cuando el usuario pide ayuda"""
        nivel = self.detectar_nivel_usuario(texto_usuario, duracion_audio)
        
        # Temas sugeridos por nivel
        suggested_topics = {
            "beginner": [
                "Your name and age",
                "Where you live",
                "Your family members",
                "Your favorite colors",
                "Basic daily activities"
            ],
            "intermediate": [
                "Your daily routine",
                "Your hobbies and interests",
                "Your favorite movies or books",
                "Your plans for the weekend",
                "A recent experience"
            ],
            "advanced": [
                "Your career goals",
                "Your opinions on current events",
                "A book that influenced you",
                "Your travel experiences",
                "Your thoughts on technology"
            ]
        }
        
        # Frases de ejemplo por nivel
        example_phrases = {
            "beginner": [
                "My name is Maria and I'm 16 years old.",
                "I live in Mexico City with my family.",
                "I have one brother and two sisters.",
                "My favorite color is blue.",
                "I go to school from Monday to Friday."
            ],
            "intermediate": [
                "On weekdays, I wake up at 6 AM and go to school.",
                "In my free time, I enjoy playing soccer and watching movies.",
                "My favorite movie is Avengers because I like superheroes.",
                "This weekend, I'm planning to visit my grandparents.",
                "Last week, I went to a concert with my friends."
            ],
            "advanced": [
                "In the next five years, I hope to study engineering at university.",
                "I believe that climate change is the most important issue facing our generation.",
                "The book '1984' by George Orwell made me think about privacy in modern society.",
                "When I traveled to Canada last summer, I was impressed by the cultural diversity.",
                "Artificial intelligence has the potential to revolutionize education in positive ways."
            ]
        }
        
        topics = suggested_topics.get(nivel, suggested_topics["beginner"])
        examples = example_phrases.get(nivel, example_phrases["beginner"])
        
        response_lines = [
            "## 🆘 **I'm Here to Help You!**",
            "\n### 🎯 **You Can Talk About Anything:**",
            "Don't worry about making mistakes - that's how we learn!",
            "\n### 💬 **Suggested Topics for Your Level:**"
        ]
        
        for i, topic in enumerate(topics[:5], 1):
            response_lines.append(f"{i}. {topic}")
        
        response_lines.append("\n### 📝 **Example Phrases:**")
        for example in examples[:4]:
            response_lines.append(f"• \"{example}\"")
        
        response_lines.append("\n### 💪 **Tips for Success:**")
        response_lines.append("1. **Relax** - Take a deep breath before speaking")
        response_lines.append("2. **Speak slowly** - Focus on clarity, not speed")
        response_lines.append("3. **Use simple words** - You don't need complex vocabulary")
        response_lines.append("4. **Practice regularly** - Even 5 minutes a day helps")
        
        response_lines.append("\n### 🚀 **Ready to Try?**")
        response_lines.append(f"Try saying something about: **{random.choice(topics)}**")
        
        return {
            "respuesta": "\n".join(response_lines),
            "tipo": "ayuda_explicita",
            "pronunciation_score": 50,
            "nivel_detectado": nivel,
            "ejemplos_respuesta": examples[:3]
        }
    
    def _respuesta_en_espanol(self, texto_usuario: str):
        """Respuesta cuando el usuario habla en español"""
        try:
            translated = translator.translate_with_retry(texto_usuario, src='es', dest='en')
        except:
            translated = "[Translation unavailable]"
        
        response_lines = [
            "## 🌍 **I Notice You Spoke in Spanish**",
            "\n### 🗣️ **What You Said in Spanish:**",
            f"> \"{texto_usuario}\"",
            "\n### 🔤 **English Translation:**",
            f"> \"{translated}\"",
            "\n### 🎯 **Now Try Saying It in English:**",
            "1. **Listen carefully** to the English version",
            "2. **Repeat slowly** word by word",
            "3. **Focus on pronunciation** of each sound",
            "4. **Put it all together** in a complete sentence",
            "\n### 💡 **Language Switching Tips:**",
            "• Practice thinking directly in English",
            "• Don't translate word-for-word in your head",
            "• Focus on the message, not perfect grammar",
            "• Use cognates (similar words in both languages)",
            "\n### 🔊 **Practice Phrase:**",
            f"Try saying: \"{translated}\"",
            "\n### ✅ **Remember:**",
            "Switching between languages is a great skill!",
            "You're training your brain to be bilingual! 🧠"
        ]
        
        return {
            "respuesta": "\n".join(response_lines),
            "tipo": "language_switch",
            "pronunciation_score": 40,
            "nivel_detectado": "beginner",
            "ejemplos_respuesta": [translated, "Can you say that in English?", "I'm practicing my English pronunciation"]
        }
    
    def _generar_pregunta(self, nivel: str) -> str:
        """Generar pregunta contextual con cache"""
        self._clean_cache()
        
        cache_key = f"q_{nivel}_{datetime.now().strftime('%H')}"
        
        if cache_key in self.question_cache:
            return self.question_cache[cache_key]['question']
        
        # Banco de preguntas por nivel
        question_bank = {
            "beginner": [
                "What is your name and how old are you?",
                "Where do you live and what is your city like?",
                "Do you have any brothers or sisters? Tell me about them.",
                "What is your favorite color and why do you like it?",
                "What time do you usually wake up in the morning?",
                "What is your favorite food and when do you eat it?",
                "Do you have any pets? What are their names?",
                "What is your favorite day of the week and why?",
                "What subjects do you study at school?",
                "What do you like to do on weekends?",
                "What is your favorite season and what do you do during it?",
                "Can you describe your house or apartment?",
                "What is your favorite sport or physical activity?",
                "What kind of music do you like to listen to?",
                "What is your favorite movie or TV show?"
            ],
            "intermediate": [
                "What does your typical weekday look like from morning to night?",
                "Describe your best friend. What makes them special?",
                "What are your hobbies and how did you get interested in them?",
                "What was the last book you read or movie you watched? What did you think of it?",
                "What are your plans for next weekend or your next vacation?",
                "Describe your hometown or the place where you grew up.",
                "What is your dream vacation destination and what would you do there?",
                "What is a skill or hobby you would like to learn in the future?",
                "Tell me about a happy memory from your childhood.",
                "What do you usually do with your friends when you hang out?",
                "Describe a teacher or mentor who has influenced you.",
                "What are some traditions or celebrations in your family or culture?",
                "How do you usually spend your free time after school or work?",
                "What is something you're really good at and how did you learn it?",
                "If you could travel anywhere in the world, where would you go and why?"
            ],
            "advanced": [
                "What are your professional or personal goals for the next five years?",
                "How has technology changed the way we live and work in recent years?",
                "What is your opinion on the impact of social media on society and relationships?",
                "Describe a significant challenge you've overcome and what you learned from it.",
                "What does success mean to you personally, and how do you measure it?",
                "How important is education in today's world, and what changes would you make to the education system?",
                "What global issue concerns you the most, and what do you think should be done about it?",
                "Describe a cultural tradition from your country that you value and why it's important.",
                "What skills do you think will be most important in the future job market, and why?",
                "How do you handle stress and maintain work-life balance in your daily life?",
                "What role do you think artificial intelligence will play in our future society?",
                "How can individuals contribute to environmental sustainability in their daily lives?",
                "What is the most important lesson life has taught you so far?",
                "How has learning English changed your perspective or opportunities?",
                "What advice would you give to someone who is just starting to learn English?"
            ]
        }
        
        # Seleccionar pregunta aleatoria
        questions = question_bank.get(nivel, question_bank["beginner"])
        selected_question = random.choice(questions)
        
        # Opcionalmente, añadir contexto del tema
        if random.random() > 0.5:  # 50% de probabilidad
            topic = random.choice(self.topics)
            contextual_questions = [
                f"Thinking about {topic}, {selected_question.lower()}",
                f"In the context of {topic}, {selected_question.lower()}",
                f"Regarding {topic}, {selected_question.lower()}"
            ]
            selected_question = random.choice(contextual_questions)
        
        # Guardar en cache
        self.question_cache[cache_key] = {
            'question': selected_question,
            'timestamp': time.time()
        }
        
        # Limitar tamaño del cache
        if len(self.question_cache) > 100:
            # Eliminar el más antiguo
            oldest_key = min(self.question_cache.keys(), 
                           key=lambda k: self.question_cache[k]['timestamp'])
            del self.question_cache[oldest_key]
        
        return selected_question
    
    def _generar_ejemplos(self, nivel: str):
        """Generar ejemplos de respuesta por nivel"""
        examples_bank = {
            "beginner": [
                "My name is Carlos and I'm 17 years old.",
                "I live in Guadalajara, which is a big city in Mexico.",
                "I have two brothers. Their names are Luis and Miguel.",
                "My favorite color is green because it reminds me of nature.",
                "I usually wake up at 6:30 AM on school days.",
                "I love pizza and I eat it every Friday with my family.",
                "I have a dog named Max. He's brown and very friendly.",
                "My favorite day is Saturday because I don't have school.",
                "At school, I study math, science, history, and English.",
                "On weekends, I like to play video games with my friends."
            ],
            "intermediate": [
                "On a typical weekday, I wake up at 6 AM, go to school from 7 to 3, do homework in the afternoon, and relax in the evening.",
                "My best friend is Ana. She's very funny, loyal, and always supports me when I need help.",
                "My main hobbies are playing guitar and soccer. I started playing guitar when I was 12 after hearing my uncle play.",
                "The last movie I watched was Spider-Man. I really enjoyed it because of the special effects and the story.",
                "Next weekend, I'm planning to visit my cousins who live in another city. We haven't seen each other in months.",
                "I grew up in a small town near the mountains. It was quiet and peaceful, with lots of nature around.",
                "My dream vacation would be to visit Japan. I'd love to see Tokyo, try authentic sushi, and learn about Japanese culture.",
                "I'd like to learn how to code. I think it's an important skill for the future and I enjoy solving problems.",
                "A happy memory from my childhood is when my whole family went to the beach. We built sandcastles and swam all day.",
                "When I hang out with friends, we usually go to the mall, watch movies, or just talk at someone's house."
            ],
            "advanced": [
                "In the next five years, I hope to finish university, start my career in engineering, and possibly travel abroad.",
                "Technology has dramatically changed our lives by making information instantly accessible and connecting people globally.",
                "Social media has both positive and negative impacts. It helps people stay connected but can also spread misinformation.",
                "A significant challenge I overcame was learning English. It taught me persistence and the value of consistent practice.",
                "Success to me means achieving personal growth while making a positive impact on others, not just accumulating wealth.",
                "Education is crucial for personal and societal development. I would make it more practical and focused on critical thinking.",
                "Climate change concerns me the most. We need global cooperation to reduce emissions and develop sustainable technologies.",
                "In my culture, we celebrate Day of the Dead. It's important because it helps us remember and honor our ancestors.",
                "Critical thinking, adaptability, and digital literacy will be essential skills in the future job market.",
                "I handle stress by exercising regularly, practicing mindfulness, and maintaining a balanced schedule."
            ]
        }
        
        examples = examples_bank.get(nivel, examples_bank["beginner"])
        
        # Seleccionar 3 ejemplos aleatorios
        if len(examples) > 3:
            return random.sample(examples, 3)
        return examples

coach = SistemaCoach()

# ============================================
# JUEGO DE VOCABULARIO COMPLETO
# ============================================
class VocabularyGame:
    def __init__(self):
        self.vocabulary = self._load_vocabulary()
        self.game_history = {}
        self.max_game_history = 50
        
    def _load_vocabulary(self):
        """Cargar vocabulario por nivel de dificultad"""
        return {
            "easy": [
                "house", "dog", "cat", "sun", "water", "food", "friend", 
                "family", "time", "music", "book", "school", "teacher",
                "student", "city", "country", "number", "color", "day", "night",
                "car", "table", "chair", "door", "window", "apple", "orange",
                "milk", "bread", "rice", "beach", "mountain", "river", "forest",
                "sky", "cloud", "rain", "wind", "earth", "fire", "tree", "flower",
                "bird", "fish", "horse", "cow", "sheep", "chicken", "egg", "meat"
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
                "The student studies a lot for exams",
                "My teacher explains things clearly",
                "I eat breakfast at seven o'clock",
                "The car is blue and new",
                "I read books in my free time",
                "We play soccer on weekends"
            ],
            "hard": [
                "The scientific research demonstrated significant improvements in the methodology",
                "Global economic trends indicate substantial growth potential in emerging markets",
                "Environmental sustainability requires collaborative efforts worldwide to address climate change",
                "Technological advancements continue to revolutionize various industries and business models",
                "Cognitive behavioral therapy has proven effective for many patients with anxiety disorders",
                "The entrepreneur developed an innovative business strategy to penetrate new markets",
                "Artificial intelligence is transforming various sectors globally through automation and data analysis",
                "Renewable energy sources are essential for sustainable development and reducing carbon emissions",
                "The researcher conducted a comprehensive literature review to identify knowledge gaps",
                "International collaboration fosters scientific breakthroughs and accelerates innovation"
            ]
        }
    
    def get_random_word(self, difficulty: str):
        """Obtener palabra aleatoria con metadatos"""
        if difficulty not in self.vocabulary:
            difficulty = "easy"
        
        word = random.choice(self.vocabulary[difficulty])
        
        # Generar pista según dificultad
        hint = self._generate_hint(word, difficulty)
        
        # Calcular tiempo sugerido
        word_count = len(word.split())
        suggested_time = min(60, max(15, word_count * 5))
        
        # Puntos base
        points_map = {"easy": 15, "normal": 30, "hard": 60}
        
        return {
            "word": word,
            "difficulty": difficulty,
            "points_base": points_map[difficulty],
            "suggested_time": suggested_time,
            "hint": hint,
            "id": str(uuid.uuid4())[:8],
            "word_count": word_count,
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_hint(self, word: str, difficulty: str) -> str:
        """Generar pista útil según dificultad"""
        if difficulty == "easy":
            # Para palabras simples
            first_letter = word[0].upper()
            word_length = len(word)
            
            hints = [
                f"Starts with: '{first_letter}'",
                f"Has {word_length} letters",
                f"Rhymes with words ending in '{word[-2:]}'",
                f"Think of: {self._get_similar_word(word)}"
            ]
            return random.choice(hints)
        
        elif difficulty == "normal":
            # Para frases en español, dar traducción
            try:
                translated = translator.translate_with_retry(word, src='es', dest='en')
                if translated and translated.lower() != word.lower():
                    words = translated.split()
                    if len(words) > 2:
                        return f"English: '{' '.join(words[:2])}...'"
                    return f"English: '{translated}'"
            except:
                pass
            
            # Pistas para frases en inglés
            words = word.split()
            if len(words) > 1:
                return f"Contains {len(words)} words. First word: '{words[0]}'"
            return "Try to pronounce each word clearly"
        
        else:  # hard
            # Para frases difíciles
            keywords = word.split()[:3]
            hint_type = random.choice([
                f"Keywords: {', '.join(keywords)}",
                f"Topic: {self._identify_topic(word)}",
                f"Complex sentence with {len(word.split())} words"
            ])
            return hint_type
    
    def _get_similar_word(self, word):
        """Obtener palabra similar para pistas"""
        similar_words = {
            'house': 'home', 'dog': 'pet', 'cat': 'animal', 'sun': 'star',
            'water': 'liquid', 'food': 'meal', 'friend': 'companion',
            'family': 'relatives', 'time': 'clock', 'music': 'melody'
        }
        return similar_words.get(word.lower(), 'common word')
    
    def _identify_topic(self, phrase):
        """Identificar tema de frase compleja"""
        topics = {
            'research': 'academic',
            'economic': 'business',
            'environmental': 'science',
            'technological': 'innovation',
            'cognitive': 'psychology',
            'entrepreneur': 'business',
            'artificial': 'technology',
            'renewable': 'energy',
            'international': 'global'
        }
        
        for keyword, topic in topics.items():
            if keyword in phrase.lower():
                return topic
        
        return "advanced topic"
    
    def validate_answer(self, original: str, user_answer: str, difficulty: str):
        """Validar respuesta del usuario"""
        user_clean = user_answer.strip()
        
        if not user_clean:
            return {
                "is_correct": False,
                "user_answer": "",
                "correct_answer": original,
                "original_word": original,
                "points_earned": 0,
                "message": "Please provide an answer",
                "xp_earned": 0,
                "accuracy": 0.0,
                "detailed_feedback": "No response detected"
            }
        
        # Detectar idioma
        lang, confidence = translator.detect_language(user_answer)
        
        # Para niveles easy y normal, esperamos español
        expected_lang = "es" if difficulty in ["easy", "normal"] else "en"
        
        # Traducción correcta esperada
        correct_translation = ""
        if difficulty in ["easy", "normal"]:
            try:
                # Traducir del inglés al español (lo que el usuario debería decir)
                correct_translation = translator.translate_with_retry(original, src='en', dest='es')
                correct_translation = correct_translation.lower().strip()
            except:
                correct_translation = original.lower().strip()
        else:
            correct_translation = original.lower().strip()
        
        # Verificar si habló en el idioma incorrecto
        language_issue = False
        if expected_lang == "es" and lang == "en" and confidence > 0.6:
            language_issue = True
            message = "You spoke in English! Try saying it in Spanish. 🎯"
        elif expected_lang == "en" and lang == "es" and confidence > 0.6:
            language_issue = True
            message = "You spoke in Spanish! Try saying it in English. 🎯"
        
        if language_issue:
            return {
                "is_correct": False,
                "user_answer": user_answer,
                "correct_answer": correct_translation,
                "original_word": original,
                "points_earned": max(1, {"easy": 3, "normal": 5, "hard": 8}[difficulty]),
                "message": message,
                "xp_earned": 2,
                "language_detected": lang,
                "accuracy": 30.0,
                "detailed_feedback": f"Language detected: {lang.upper()}. Expected: {expected_lang.upper()}"
            }
        
        # Comparar respuestas
        is_correct = self._compare_answers(user_clean.lower(), correct_translation, difficulty)
        
        # Calcular puntos
        points_base = {"easy": 15, "normal": 30, "hard": 60}[difficulty]
        if is_correct:
            points_earned = points_base
            xp_earned = {"easy": 10, "normal": 15, "hard": 25}[difficulty]
        else:
            points_earned = max(5, points_base // 4)
            xp_earned = {"easy": 3, "normal": 5, "hard": 8}[difficulty]
        
        # Mensajes personalizados
        messages = {
            "easy": {
                True: "Perfect! 🎉 Great pronunciation for a beginner!",
                False: "Almost! Listen carefully and try again. 💪"
            },
            "normal": {
                True: "Excellent! 👏 Your pronunciation is improving nicely!",
                False: "Good attempt! Focus on the difficult words. 📚"
            },
            "hard": {
                True: "Outstanding! 🏆 Advanced pronunciation mastered!",
                False: "Challenging phrase! Keep practicing. 🎯"
            }
        }
        
        # Calcular precisión
        accuracy = 100.0 if is_correct else self._calculate_accuracy(user_clean, correct_translation)
        
        # Feedback detallado
        detailed_feedback = self._generate_detailed_feedback(
            user_clean, correct_translation, is_correct, difficulty
        )
        
        return {
            "is_correct": is_correct,
            "user_answer": user_answer,
            "correct_answer": correct_translation,
            "original_word": original,
            "points_earned": points_earned,
            "message": messages[difficulty][is_correct],
            "xp_earned": xp_earned,
            "language_detected": lang,
            "accuracy": accuracy,
            "detailed_feedback": detailed_feedback
        }
    
    def _compare_answers(self, user_answer: str, correct: str, difficulty: str) -> bool:
        """Comparar respuestas con tolerancia según dificultad"""
        if not user_answer or not correct:
            return False
        
        # Normalizar texto
        def normalize(text):
            text = text.lower()
            text = re.sub(r'[^\w\s]', '', text)  # Remover puntuación
            text = ' '.join(text.split())  # Normalizar espacios
            return text
        
        user_norm = normalize(user_answer)
        correct_norm = normalize(correct)
        
        # Comparación exacta
        if user_norm == correct_norm:
            return True
        
        # Para easy: ser muy tolerante
        if difficulty == "easy":
            user_words = set(user_norm.split())
            correct_words = set(correct_norm.split())
            
            # Si tiene al menos la palabra principal
            if len(user_words.intersection(correct_words)) >= 1:
                return True
            
            # Usar similitud de secuencia
            from difflib import SequenceMatcher
            return SequenceMatcher(None, user_norm, correct_norm).ratio() >= 0.7
        
        # Para normal: tolerancia media
        elif difficulty == "normal":
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, user_norm, correct_norm).ratio()
            
            # Requerir palabras clave
            user_words = user_norm.split()
            correct_words = correct_norm.split()
            
            # Debe contener al menos 50% de las palabras clave
            common_words = set(user_words).intersection(set(correct_words))
            if len(common_words) >= len(correct_words) * 0.5 and similarity >= 0.6:
                return True
        
        # Para hard: alta precisión
        else:
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, user_norm, correct_norm).ratio()
            return similarity >= 0.8
        
        return False
    
    def _calculate_accuracy(self, user_answer: str, correct: str) -> float:
        """Calcular precisión porcentual"""
        from difflib import SequenceMatcher
        
        user_norm = ' '.join(user_answer.lower().split())
        correct_norm = ' '.join(correct.lower().split())
        
        similarity = SequenceMatcher(None, user_norm, correct_norm).ratio()
        return round(similarity * 100, 1)
    
    def _generate_detailed_feedback(self, user_answer, correct, is_correct, difficulty):
        """Generar feedback detallado"""
        if is_correct:
            feedbacks = {
                "easy": "Perfect pronunciation! Every sound was clear and accurate.",
                "normal": "Excellent! Your sentence flow and word stress were very natural.",
                "hard": "Outstanding! You mastered complex pronunciation patterns smoothly."
            }
            return feedbacks.get(difficulty, "Great job!")
        
        # Feedback para respuestas incorrectas
        user_words = user_answer.split()
        correct_words = correct.split()
        
        # Encontrar diferencias
        missing_words = [w for w in correct_words if w not in user_words]
        extra_words = [w for w in user_words if w not in correct_words]
        
        feedback_parts = []
        
        if missing_words:
            feedback_parts.append(f"Missing words: {', '.join(missing_words[:3])}")
        
        if extra_words:
            feedback_parts.append(f"Extra words: {', '.join(extra_words[:3])}")
        
        if not missing_words and not extra_words:
            feedback_parts.append("Word order or pronunciation needs adjustment")
        
        # Consejos según dificultad
        tips = {
            "easy": "Listen to each sound carefully and repeat slowly.",
            "normal": "Focus on linking words together smoothly.",
            "hard": "Break down complex words into syllables and practice each part."
        }
        
        if feedback_parts:
            feedback = f"{'; '.join(feedback_parts)}. {tips.get(difficulty, 'Keep practicing!')}"
        else:
            feedback = tips.get(difficulty, "Keep practicing!")
        
        return feedback

game = VocabularyGame()

# ============================================
# PROCESADOR DE AUDIO OPTIMIZADO
# ============================================
class AudioProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.pause_threshold = 0.8
        self.recognizer.operation_timeout = None
        self.recognizer.phrase_threshold = 0.3
        self.recognizer.non_speaking_duration = 0.5
        
    def process_audio(self, audio_file):
        """Procesar archivo de audio optimizado para memoria"""
        try:
            # Leer archivo en chunks para ahorrar memoria
            max_size = app.config['AUDIO_FILE_MAX_SIZE']
            audio_bytes = audio_file.read(max_size)
            
            if len(audio_bytes) > max_size:
                raise ValueError(
                    f"Audio file too large. Maximum size: {max_size/1024/1024:.1f}MB"
                )
            
            if len(audio_bytes) < 1024:  # 1KB mínimo
                raise ValueError("Audio file is too small or empty")
            
            # Detectar formato
            filename = audio_file.filename.lower() if audio_file.filename else ''
            
            # Convertir a AudioSegment
            audio_segment = self._load_audio_segment(audio_bytes, filename)
            
            # Obtener duración
            duration = len(audio_segment) / 1000.0
            
            # Verificar duración mínima
            if duration < 0.5:
                raise ValueError("Audio is too short (minimum 0.5 seconds)")
            
            # Optimizar para reconocimiento de voz
            optimized_audio = self._optimize_audio(audio_segment)
            
            # Exportar a WAV en memoria
            wav_buffer = io.BytesIO()
            optimized_audio.export(
                wav_buffer, 
                format="wav",
                parameters=["-ac", "1", "-ar", "16000", "-sample_fmt", "s16"]
            )
            wav_buffer.seek(0)
            
            # Log de procesamiento
            logger.info(
                f"Audio processed: {duration:.2f}s, "
                f"{len(audio_bytes)/1024:.0f}KB -> {len(wav_buffer.getvalue())/1024:.0f}KB"
            )
            
            return wav_buffer, duration
            
        except Exception as e:
            logger.error(f"Audio processing error: {str(e)[:150]}")
            raise
    
    def _load_audio_segment(self, audio_bytes, filename):
        """Cargar segmento de audio según formato"""
        try:
            if filename.endswith('.m4a') or filename.endswith('.mp4'):
                return AudioSegment.from_file(io.BytesIO(audio_bytes), format="m4a")
            elif filename.endswith('.mp3'):
                return AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
            elif filename.endswith('.wav'):
                return AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav")
            elif filename.endswith('.ogg'):
                return AudioSegment.from_file(io.BytesIO(audio_bytes), format="ogg")
            elif filename.endswith('.flac'):
                return AudioSegment.from_file(io.BytesIO(audio_bytes), format="flac")
            else:
                # Intentar detección automática
                return AudioSegment.from_file(io.BytesIO(audio_bytes))
        except Exception as e:
            logger.error(f"Error loading audio segment: {str(e)[:100]}")
            raise ValueError(f"Unsupported audio format or corrupted file: {str(e)[:50]}")
    
    def _optimize_audio(self, audio_segment):
        """Optimizar audio para reconocimiento de voz"""
        # Convertir a mono si es estéreo
        if audio_segment.channels > 1:
            audio_segment = audio_segment.set_channels(1)
        
        # Establecer frecuencia de muestreo estándar
        if audio_segment.frame_rate != 16000:
            audio_segment = audio_segment.set_frame_rate(16000)
        
        # Normalizar volumen (opcional, puede ayudar)
        # audio_segment = audio_segment.normalize()
        
        # Recortar silencio inicial/final (opcional)
        # audio_segment = audio_segment.strip_silence(silence_len=100, silence_thresh=-40)
        
        return audio_segment
    
    def transcribe_audio(self, wav_buffer: io.BytesIO) -> str:
        """Transcribir audio a texto"""
        try:
            with sr.AudioFile(wav_buffer) as source:
                # Ajustar para ruido ambiental
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Grabar audio
                audio_data = self.recognizer.record(source)
                
                # Intentar reconocimiento con Google Speech Recognition
                text = self.recognizer.recognize_google(
                    audio_data,
                    language='en-US',  # Inglés americano
                    show_all=False
                )
                
                if text and isinstance(text, str):
                    logger.info(f"Transcription successful: '{text[:50]}...'")
                    return text.strip()
                else:
                    logger.warning("Transcription returned empty or invalid result")
                    return ""
                    
        except sr.UnknownValueError:
            logger.warning("Google Speech Recognition could not understand audio")
            return ""
        except sr.RequestError as e:
            logger.warning(f"Could not request results from Google Speech Recognition service: {e}")
            return ""
        except Exception as e:
            logger.error(f"Transcription error: {str(e)[:100]}")
            return ""

audio_processor = AudioProcessor()

# ============================================
# ENDPOINTS DE LA API
# ============================================
@app.before_request
def before_request():
    """Middleware para optimizar requests"""
    # Limpieza automática periódica de sesiones
    if random.random() < 0.05:  # 5% de probabilidad por request
        session_manager._auto_cleanup()
    
    # Registrar request (sin cuerpos grandes)
    if request.content_length and request.content_length < 1024:  # Solo logs pequeños
        logger.debug(f"{request.method} {request.path}")

@app.after_request
def after_request(response):
    """Middleware para respuestas"""
    # Añadir headers de seguridad y optimización
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Headers específicos para Render
    if os.environ.get('RENDER'):
        response.headers['X-Render-Host'] = 'eli-english-tutor'
    
    return response

@app.route('/')
def home():
    """Endpoint raíz con información del servicio"""
    return jsonify({
        "status": "online",
        "service": "Eli English Tutor - Backend Service",
        "version": "5.0.0",
        "filename": "eli_backend.py",
        "optimized_for": "Render Free Tier",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "/api/health": "Health check",
            "/api/sesion/iniciar": "Start new session (POST)",
            "/api/conversar_audio": "Conversation with audio (POST)",
            "/api/juego/palabra": "Get vocabulary word (GET)",
            "/api/juego/validar": "Validate game answer (POST)",
            "/api/estadisticas": "Get user statistics (GET)"
        },
        "features": [
            "Real-time pronunciation analysis",
            "Intelligent conversation coach",
            "Vocabulary games with scoring",
            "Multi-level difficulty system",
            "Progress tracking and achievements",
            "Audio processing and transcription"
        ],
        "memory_usage": f"{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.1f} MB" if 'resource' in globals() else "Unknown"
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint optimizado"""
    try:
        # Verificar componentes críticos
        translator_status = "active" if translator.translator else "fallback"
        
        # Verificar memoria
        memory_info = {}
        if 'resource' in globals():
            usage = resource.getrusage(resource.RUSAGE_SELF)
            memory_info = {
                "max_rss_mb": usage.ru_maxrss / 1024,
                "user_time": usage.ru_utime,
                "system_time": usage.ru_stime
            }
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "flask": "active",
                "translator": translator_status,
                "session_manager": "active",
                "audio_processor": "active",
                "coach_system": "active",
                "game_system": "active"
            },
            "statistics": {
                "active_sessions": len(session_manager.sessions),
                "translator_cache_size": len(translator.cache) if hasattr(translator, 'cache') else 0,
                "question_cache_size": len(coach.question_cache) if hasattr(coach, 'question_cache') else 0,
                "translator_init_attempts": translator.initialization_attempts if hasattr(translator, 'initialization_attempts') else 0
            },
            "memory": memory_info,
            "service": "Eli Backend",
            "version": "5.0.0"
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            "status": "degraded",
            "error": str(e)[:100],
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/sesion/iniciar', methods=['POST'])
def iniciar_sesion():
    """Iniciar nueva sesión de usuario"""
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id')
        
        # Generar user_id si no se proporciona
        if not user_id or not isinstance(user_id, str) or len(user_id.strip()) == 0:
            user_id = f"user_{uuid.uuid4().hex[:8]}"
        else:
            user_id = user_id.strip()[:50]  # Limitar longitud
        
        # Crear sesión
        session = session_manager.create_session(user_id)
        
        # Información de bienvenida
        welcome_info = {
            "beginner": "🎯 Welcome to Eli! Let's start your English journey together!",
            "intermediate": "🌟 Welcome back! Ready to take your English to the next level?",
            "advanced": "💫 Welcome! Let's polish your English skills to perfection!"
        }
        
        return jsonify({
            "estado": "exito",
            "user_id": user_id,
            "session_id": session.session_id,
            "welcome_message": welcome_info.get(session.current_level, "Welcome to Eli English Tutor!"),
            "initial_level": session.current_level,
            "xp": session.xp,
            "level": session.level,
            "created_at": session.created_at.isoformat(),
            "instructions": {
                "conversation": "Send audio recordings to practice conversation",
                "games": "Play vocabulary games to improve pronunciation",
                "tips": "Focus on clear pronunciation and natural rhythm"
            }
        })
        
    except Exception as e:
        logger.error(f"Session start error: {traceback.format_exc()[:200]}")
        return jsonify({
            "estado": "error",
            "mensaje": f"Error starting session: {str(e)[:100]}",
            "error_code": "SESSION_INIT_FAILED"
        }), 500

@app.route('/api/conversar_audio', methods=['POST'])
def conversar_audio():
    """Procesar audio y generar respuesta conversacional"""
    # Verificar que hay archivo de audio
    if 'audio' not in request.files:
        return jsonify({
            "estado": "error",
            "respuesta": "No audio file provided. Please record your voice message.",
            "error_code": "NO_AUDIO_FILE"
        }), 400
    
    audio_file = request.files['audio']
    session_id = request.form.get('session_id', '').strip()
    pregunta_actual = request.form.get('pregunta_actual', '').strip()
    
    # Verificar archivo de audio
    if audio_file.filename == '':
        return jsonify({
            "estado": "error", 
            "respuesta": "No audio file selected.",
            "error_code": "EMPTY_FILENAME"
        }), 400
    
    try:
        # 1. Procesar audio
        logger.info(f"Processing audio from session: {session_id[:8] if session_id else 'new'}")
        wav_buffer, duracion = audio_processor.process_audio(audio_file)
        
        # 2. Transcribir audio
        texto_transcrito = audio_processor.transcribe_audio(wav_buffer)
        
        # 3. Verificar transcripción
        if not texto_transcrito or len(texto_transcrito.strip()) < 2:
            return jsonify({
                "estado": "error",
                "respuesta": coach._respuesta_sin_audio()["respuesta"],
                "error_code": "NO_SPEECH_DETECTED",
                "audio_duration": duracion,
                "session_id": session_id
            }), 400
        
        logger.info(f"User transcription: '{texto_transcrito[:80]}...' ({duracion:.1f}s)")
        
        # 4. Obtener respuesta del coach
        respuesta = coach.generar_respuesta(texto_transcrito, duracion)
        
        # 5. Actualizar sesión si existe
        xp_earned = 15
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                session.add_conversation(
                    texto_transcrito, 
                    respuesta["respuesta"], 
                    respuesta["pronunciation_score"],
                    respuesta.get("correcciones", [])
                )
                session.xp += xp_earned
                session.update_level()
                session_manager.update_session(session_id, xp=session.xp)
                
                logger.info(f"Session updated: {session_id[:8]}, XP: {session.xp}, Level: {session.level}")
        
        # 6. Preparar respuesta
        response_data = {
            "estado": "exito",
            "respuesta": respuesta["respuesta"],
            "transcripcion": texto_transcrito,
            "nueva_pregunta": respuesta.get("next_question", ""),
            "correcciones_pronunciacion": respuesta.get("correcciones", []),
            "consejos": respuesta.get("consejos", []),
            "nivel_detectado": respuesta["nivel_detectado"],
            "pronunciation_score": respuesta["pronunciation_score"],
            "ejemplos_respuesta": respuesta.get("ejemplos_respuesta", []),
            "session_id": session_id,
            "xp_earned": xp_earned,
            "audio_duration": duracion,
            "tipo_respuesta": respuesta.get("tipo", "conversacion"),
            "detailed_scores": respuesta.get("detailed_scores", {})
        }
        
        # Limpiar memoria
        del wav_buffer
        
        return jsonify(response_data)
        
    except ValueError as e:
        # Error de tamaño o formato de archivo
        error_msg = str(e)
        if "too large" in error_msg.lower():
            return jsonify({
                "estado": "error",
                "respuesta": f"Audio file too large. Maximum size: {app.config['AUDIO_FILE_MAX_SIZE']/1024/1024:.1f}MB",
                "error_code": "FILE_TOO_LARGE"
            }), 413
        else:
            return jsonify({
                "estado": "error",
                "respuesta": f"Invalid audio file: {error_msg}",
                "error_code": "INVALID_AUDIO"
            }), 400
            
    except Exception as e:
        logger.error(f"Conversation error: {traceback.format_exc()[:300]}")
        return jsonify({
            "estado": "error",
            "respuesta": "An error occurred while processing your audio. Please try again.",
            "error_code": "PROCESSING_ERROR",
            "technical_info": str(e)[:100] if app.debug else None
        }), 500

@app.route('/api/juego/palabra', methods=['GET'])
def obtener_palabra_juego():
    """Obtener palabra/frase para juego de vocabulario"""
    try:
        dificultad = request.args.get('dificultad', 'easy')
        session_id = request.args.get('session_id', '')
        
        # Validar dificultad
        if dificultad not in ['easy', 'normal', 'hard']:
            dificultad = 'easy'
        
        # Obtener palabra
        palabra_data = game.get_random_word(dificultad)
        
        # Registrar en sesión si existe
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                session.game_stats["games_played"] += 1
        
        return jsonify({
            "estado": "exito",
            "palabra": palabra_data["word"],
            "dificultad": palabra_data["difficulty"],
            "puntos_base": palabra_data["points_base"],
            "tiempo_sugerido": palabra_data["suggested_time"],
            "pista": palabra_data["hint"],
            "id": palabra_data["id"],
            "word_count": palabra_data["word_count"],
            "timestamp": palabra_data["timestamp"],
            "instructions": {
                "easy": "Pronounce this word clearly in Spanish",
                "normal": "Say this sentence in Spanish with good pronunciation",
                "hard": "Repeat this complex sentence in English with clear pronunciation"
            }
        })
        
    except Exception as e:
        logger.error(f"Game word error: {str(e)[:100]}")
        return jsonify({
            "estado": "error",
            "mensaje": "Error getting game word. Please try again.",
            "error_code": "GAME_WORD_ERROR"
        }), 500

@app.route('/api/juego/validar', methods=['POST'])
def validar_respuesta_juego():
    """Validar respuesta del juego de vocabulario"""
    try:
        data = request.get_json(silent=True) or {}
        
        # Obtener datos requeridos
        palabra_original = data.get('palabra_original', '')
        respuesta_usuario = data.get('respuesta_usuario', '')
        dificultad = data.get('dificultad', 'easy')
        session_id = data.get('session_id', '')
        game_id = data.get('game_id', '')
        
        # Validar datos requeridos
        if not palabra_original or not respuesta_usuario:
            return jsonify({
                "estado": "error",
                "mensaje": "Missing required fields: palabra_original and respuesta_usuario",
                "error_code": "MISSING_FIELDS"
            }), 400
        
        # Validar dificultad
        if dificultad not in ['easy', 'normal', 'hard']:
            dificultad = 'easy'
        
        # Validar respuesta
        resultado = game.validate_answer(palabra_original, respuesta_usuario, dificultad)
        
        # Actualizar sesión
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                session.game_stats["total_attempts"] += 1
                
                if resultado["is_correct"]:
                    session.game_stats["correct_answers"] += 1
                    session.game_stats["total_points"] += resultado["points_earned"]
                    session.game_stats["vocabulary_mastered"] += 1
                
                session.xp += resultado["xp_earned"]
                session.update_level()
                
                logger.info(f"Game result for session {session_id[:8]}: "
                          f"Correct: {resultado['is_correct']}, "
                          f"Points: {resultado['points_earned']}, "
                          f"Total XP: {session.xp}")
        
        # Preparar respuesta
        response_data = {
            "estado": "exito",
            "es_correcta": resultado["is_correct"],
            "respuesta_usuario": resultado["user_answer"],
            "traduccion_correcta": resultado["correct_answer"],
            "palabra_original": resultado["original_word"],
            "puntos_obtenidos": resultado["points_earned"],
            "mensaje": resultado["message"],
            "xp_earned": resultado["xp_earned"],
            "language_detected": resultado.get("language_detected", "unknown"),
            "accuracy": resultado["accuracy"],
            "detailed_feedback": resultado.get("detailed_feedback", ""),
            "next_action": "continue" if resultado["is_correct"] else "retry",
            "session_id": session_id,
            "game_id": game_id
        }
        
        # Añadir sugerencia si la respuesta fue incorrecta
        if not resultado["is_correct"]:
            response_data["suggestion"] = "Try listening to the correct pronunciation and repeat slowly."
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Game validation error: {str(e)[:100]}")
        return jsonify({
            "estado": "error",
            "mensaje": "Error validating game answer. Please try again.",
            "error_code": "VALIDATION_ERROR"
        }), 500

@app.route('/api/estadisticas', methods=['GET'])
def obtener_estadisticas():
    """Obtener estadísticas de usuario o globales"""
    try:
        session_id = request.args.get('session_id')
        user_id = request.args.get('user_id')
        detailed = request.args.get('detailed', 'false').lower() == 'true'
        
        # Estadísticas de sesión específica
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                session_data = session.to_dict()
                
                response_data = {
                    "estado": "exito",
                    "stats": session_data,
                    "session_active": True,
                    "time_since_last_interaction": str(datetime.now() - session.last_interaction)
                }
                
                # Datos detallados si se solicitan
                if detailed:
                    response_data.update({
                        "conversation_history": session.conversation_history[-5:],
                        "pronunciation_trend": session.last_10_scores,
                        "weak_points_detail": session.weak_points
                    })
                
                return jsonify(response_data)
            else:
                return jsonify({
                    "estado": "error",
                    "mensaje": "Session not found or expired",
                    "error_code": "SESSION_NOT_FOUND"
                }), 404
        
        # Estadísticas por user_id (todas las sesiones)
        elif user_id:
            user_sessions = [
                session for session in session_manager.sessions.values()
                if session.user_id == user_id
            ]
            
            if user_sessions:
                total_stats = {
                    "total_sessions": len(user_sessions),
                    "total_xp": sum(s.xp for s in user_sessions),
                    "total_conversations": sum(len(s.conversation_history) for s in user_sessions),
                    "avg_pronunciation_score": sum(
                        sum(s.last_10_scores)/len(s.last_10_scores) if s.last_10_scores else 0
                        for s in user_sessions
                    ) / len(user_sessions) if user_sessions else 0
                }
                
                return jsonify({
                    "estado": "exito",
                    "user_id": user_id,
                    "total_stats": total_stats,
                    "active_sessions": [s.session_id for s in user_sessions],
                    "message": f"Found {len(user_sessions)} sessions for user {user_id}"
                })
            else:
                return jsonify({
                    "estado": "error",
                    "mensaje": f"No sessions found for user {user_id}",
                    "error_code": "USER_NOT_FOUND"
                }), 404
        
        # Estadísticas globales del servicio
        else:
            active_sessions = [
                s for s in session_manager.sessions.values()
                if (datetime.now() - s.last_interaction).seconds < 300  # 5 minutos
            ]
            
            # Calcular estadísticas agregadas
            if session_manager.sessions:
                total_conversations = sum(len(s.conversation_history) for s in session_manager.sessions.values())
                total_games_played = sum(s.game_stats["games_played"] for s in session_manager.sessions.values())
                total_points = sum(s.game_stats["total_points"] for s in session_manager.sessions.values())
            else:
                total_conversations = total_games_played = total_points = 0
            
            # Información del sistema
            system_info = {}
            if 'resource' in globals():
                usage = resource.getrusage(resource.RUSAGE_SELF)
                system_info = {
                    "memory_usage_mb": usage.ru_maxrss / 1024,
                    "user_cpu_time": usage.ru_utime,
                    "system_cpu_time": usage.ru_stime
                }
            
            return jsonify({
                "estado": "exito",
                "global_stats": {
                    "total_sessions": len(session_manager.sessions),
                    "active_sessions": len(active_sessions),
                    "total_conversations": total_conversations,
                    "total_games_played": total_games_played,
                    "total_points_earned": total_points,
                    "service_uptime": int(time.time() - app_start_time) if 'app_start_time' in globals() else 0,
                    "translator_status": "active" if translator.translator else "fallback",
                    "translator_cache_size": len(translator.cache) if hasattr(translator, 'cache') else 0,
                    "question_cache_size": len(coach.question_cache) if hasattr(coach, 'question_cache') else 0
                },
                "system_info": system_info,
                "service": "Eli English Tutor",
                "version": "5.0.0",
                "timestamp": datetime.now().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Stats error: {str(e)[:100]}")
        return jsonify({
            "estado": "error",
            "mensaje": "Error getting statistics",
            "error_code": "STATS_ERROR"
        }), 500

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Endpoint de prueba para verificar funcionalidades"""
    try:
        # Probar traductor
        translation_test = translator.translate_with_retry("hello", src='en', dest='es')
        
        # Probar detección de idioma
        lang_test, confidence_test = translator.detect_language("hola mundo")
        
        # Probar generación de pregunta
        question_test = coach._generar_pregunta("beginner")
        
        return jsonify({
            "status": "ok",
            "service": "Eli Backend Test",
            "timestamp": datetime.now().isoformat(),
            "tests": {
                "translator": {
                    "status": "active" if translator.translator else "fallback",
                    "translation_test": translation_test,
                    "detection_test": {"language": lang_test, "confidence": confidence_test}
                },
                "coach": {
                    "question_generation": question_test,
                    "cache_size": len(coach.question_cache) if hasattr(coach, 'question_cache') else 0
                },
                "sessions": {
                    "total": len(session_manager.sessions),
                    "manager_status": "active"
                },
                "game": {
                    "vocabulary_size": {
                        "easy": len(game.vocabulary.get('easy', [])),
                        "normal": len(game.vocabulary.get('normal', [])),
                        "hard": len(game.vocabulary.get('hard', []))
                    }
                }
            },
            "system": {
                "python_version": sys.version,
                "flask_version": "2.3.3",
                "memory_usage_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 if 'resource' in globals() else "unknown"
            }
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)[:200],
            "traceback": traceback.format_exc()[:500] if app.debug else None
        }), 500

# ============================================
# MANEJADORES DE ERROR
# ============================================
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "estado": "error",
        "mensaje": "Endpoint not found. Please check the API documentation at /",
        "error_code": "ENDPOINT_NOT_FOUND"
    }), 404

@app.errorhandler(413)
def too_large(error):
    return jsonify({
        "estado": "error",
        "mensaje": f"File too large. Maximum size: {app.config['MAX_CONTENT_LENGTH']/1024/1024:.1f}MB",
        "error_code": "FILE_TOO_LARGE"
    }), 413

@app.errorhandler(429)
def too_many_requests(error):
    return jsonify({
        "estado": "error",
        "mensaje": "Too many requests. Please try again later.",
        "error_code": "RATE_LIMIT_EXCEEDED"
    }), 429

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 Internal Server Error: {traceback.format_exc()[:500]}")
    return jsonify({
        "estado": "error",
        "mensaje": "Internal server error. Our team has been notified.",
        "error_code": "INTERNAL_SERVER_ERROR"
    }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Manejador global de excepciones"""
    logger.error(f"Unhandled exception: {traceback.format_exc()[:500]}")
    
    # Determinar código de error apropiado
    if isinstance(e, ValueError):
        status_code = 400
        error_code = "BAD_REQUEST"
    elif isinstance(e, KeyError):
        status_code = 400
        error_code = "MISSING_KEY"
    else:
        status_code = 500
        error_code = "UNKNOWN_ERROR"
    
    return jsonify({
        "estado": "error",
        "mensaje": f"An error occurred: {str(e)[:100]}",
        "error_code": error_code,
        "details": traceback.format_exc()[:200] if app.debug else None
    }), status_code

# ============================================
# INICIALIZACIÓN Y EJECUCIÓN
# ============================================
if __name__ == '__main__':
    # Tiempo de inicio de la aplicación
    app_start_time = time.time()
    
    # Configurar puerto
    port = int(os.environ.get('PORT', 5000))
    
    # Determinar modo
    debug_mode = os.environ.get('FLASK_DEBUG', '').lower() in ('true', '1', 'yes')
    
    # Información de inicio
    print("=" * 70)
    print("🚀 ELI ENGLISH TUTOR BACKEND - Optimizado para Render")
    print("=" * 70)
    print(f"📁 Archivo principal: eli_backend.py")
    print(f"🌐 Puerto: {port}")
    print(f"🔧 Modo: {'Debug' if debug_mode else 'Production'}")
    print(f"💾 Memoria límite: 400MB")
    print(f"📊 Sesiones máximas: 100")
    print(f"🔤 Traductor: {'ACTIVO' if translator.translator else 'MODO FALLBACK'}")
    print(f"🎯 Coach: INICIADO ({len(coach.topics)} temas)")
    print(f"🎮 Juego: INICIADO ({sum(len(v) for v in game.vocabulary.values())} palabras)")
    print(f"🎤 Audio: OPTIMIZADO")
    print("=" * 70)
    print("✅ Servidor inicializado exitosamente!")
    print("=" * 70)
    
    # Forzar garbage collection inicial
    import gc
    gc.collect()
    
    # Iniciar servidor
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode,
        threaded=True,
        use_reloader=debug_mode
    )