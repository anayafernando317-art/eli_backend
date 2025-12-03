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
print("🚀 Eli English Tutor - Backend Optimizado v5.1")
print("📁 Archivo: eli_backend.py")
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
        
        # Intentar inicializar traductor externo
        self._try_init_external()
        
        logger.info(f"✅ HybridTranslator inicializado. Externo: {self.use_external}")
    
    def _try_init_external(self):
        """Intentar inicializar deep-translator"""
        try:
            from deep_translator import GoogleTranslator
            self.external_translator = GoogleTranslator(source='auto', target='en')
            # Test rápido
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
            
            # === PRESENTACIONES ===
            'cómo te llamas': 'what is your name', 'me llamo': 'my name is',
            'mucho gusto': 'nice to meet you', 'de dónde eres': 'where are you from',
            'soy de': 'i am from', 'cuántos años tienes': 'how old are you',
            'tengo años': 'i am years old', 'qué estudias': 'what do you study',
            'estudio': 'i study', 'voy a la escuela': 'i go to school',
            
            # === ESTADOS Y SENTIMIENTOS ===
            'cómo estás': 'how are you', 'estoy bien': 'i am fine',
            'estoy mal': 'i am not well', 'estoy feliz': 'i am happy',
            'estoy triste': 'i am sad', 'estoy cansado': 'i am tired',
            'estoy emocionado': 'i am excited', 'estoy nervioso': 'i am nervous',
            'estoy aburrido': 'i am bored', 'me siento bien': 'i feel good',
            
            # === PREGUNTAS COMUNES ===
            'qué haces': 'what are you doing', 'dónde vives': 'where do you live',
            'qué te gusta': 'what do you like', 'por qué': 'why',
            'cuándo': 'when', 'cómo': 'how', 'cuál': 'which',
            'quién': 'who', 'cuánto': 'how much', 'cuántos': 'how many',
            
            # === FAMILIA ===
            'mi familia': 'my family', 'mis padres': 'my parents',
            'mi madre': 'my mother', 'mi padre': 'my father',
            'mis hermanos': 'my siblings', 'mi hermana': 'my sister',
            'mi hermano': 'my brother', 'mis abuelos': 'my grandparents',
            
            # === ESCUELA Y EDUCACIÓN ===
            'la escuela': 'the school', 'el colegio': 'the school',
            'el maestro': 'the teacher', 'la maestra': 'the teacher',
            'los estudiantes': 'the students', 'la clase': 'the class',
            'el examen': 'the exam', 'la tarea': 'the homework',
            'el proyecto': 'the project', 'aprender': 'to learn',
            'estudiar': 'to study', 'enseñar': 'to teach',
            
            # === HOBBIES Y ACTIVIDADES ===
            'me gusta': 'i like', 'no me gusta': 'i do not like',
            'jugar': 'to play', 'leer': 'to read', 'escribir': 'to write',
            'dibujar': 'to draw', 'cantar': 'to sing', 'bailar': 'to dance',
            'correr': 'to run', 'nadar': 'to swim', 'cocinar': 'to cook',
            'ver televisión': 'to watch tv', 'escuchar música': 'to listen to music',
            
            # === RUTINA DIARIA ===
            'me despierto': 'i wake up', 'me levanto': 'i get up',
            'me baño': 'i take a shower', 'desayuno': 'i eat breakfast',
            'voy a la escuela': 'i go to school', 'almuerzo': 'i eat lunch',
            'regreso a casa': 'i return home', 'ceno': 'i eat dinner',
            'me duermo': 'i go to sleep', 'todos los días': 'every day',
            
            # === TIEMPO ===
            'hoy': 'today', 'mañana': 'tomorrow', 'ayer': 'yesterday',
            'la semana': 'the week', 'el fin de semana': 'the weekend',
            'el mes': 'the month', 'el año': 'the year',
            'en la mañana': 'in the morning', 'en la tarde': 'in the afternoon',
            'en la noche': 'at night', 'ahora': 'now', 'siempre': 'always',
            
            # === COMIDA ===
            'comida': 'food', 'desayuno': 'breakfast', 'almuerzo': 'lunch',
            'cena': 'dinner', 'agua': 'water', 'leche': 'milk',
            'pan': 'bread', 'arroz': 'rice', 'pollo': 'chicken',
            'carne': 'meat', 'pescado': 'fish', 'frutas': 'fruits',
            'verduras': 'vegetables', 'postre': 'dessert',
            
            # === LUGARES ===
            'casa': 'house', 'escuela': 'school', 'parque': 'park',
            'cine': 'movie theater', 'centro comercial': 'mall',
            'biblioteca': 'library', 'restaurante': 'restaurant',
            'playa': 'beach', 'ciudad': 'city', 'campo': 'countryside',
            
            # === ANIMALES ===
            'animal': 'animal', 'perro': 'dog', 'gato': 'cat',
            'pájaro': 'bird', 'pez': 'fish', 'caballo': 'horse',
            'vaca': 'cow', 'conejo': 'rabbit', 'tortuga': 'turtle',
            
            # === COLORES ===
            'color': 'color', 'rojo': 'red', 'azul': 'blue',
            'verde': 'green', 'amarillo': 'yellow', 'naranja': 'orange',
            'morado': 'purple', 'rosa': 'pink', 'blanco': 'white',
            'negro': 'black', 'gris': 'gray',
            
            # === NÚMEROS (1-20) ===
            'uno': 'one', 'dos': 'two', 'tres': 'three',
            'cuatro': 'four', 'cinco': 'five', 'seis': 'six',
            'siete': 'seven', 'ocho': 'eight', 'nueve': 'nine',
            'diez': 'ten', 'once': 'eleven', 'doce': 'twelve',
            'trece': 'thirteen', 'catorce': 'fourteen', 'quince': 'fifteen',
            'dieciséis': 'sixteen', 'diecisiete': 'seventeen', 'dieciocho': 'eighteen',
            'diecinueve': 'nineteen', 'veinte': 'twenty',
            
            # === DÍAS DE LA SEMANA ===
            'lunes': 'monday', 'martes': 'tuesday', 'miércoles': 'wednesday',
            'jueves': 'thursday', 'viernes': 'friday', 'sábado': 'saturday',
            'domingo': 'sunday',
            
            # === MESES ===
            'enero': 'january', 'febrero': 'february', 'marzo': 'march',
            'abril': 'april', 'mayo': 'may', 'junio': 'june',
            'julio': 'july', 'agosto': 'august', 'septiembre': 'september',
            'octubre': 'october', 'noviembre': 'november', 'diciembre': 'december',
            
            # === ESTACIONES ===
            'primavera': 'spring', 'verano': 'summer', 'otoño': 'autumn',
            'invierno': 'winter',
            
            # === TIEMPO ATMOSFÉRICO ===
            'sol': 'sun', 'lluvia': 'rain', 'nubes': 'clouds',
            'viento': 'wind', 'nieve': 'snow', 'calor': 'heat',
            'frío': 'cold', 'temperatura': 'temperature',
            
            # === PARTES DEL CUERPO ===
            'cabeza': 'head', 'ojos': 'eyes', 'nariz': 'nose',
            'boca': 'mouth', 'orejas': 'ears', 'manos': 'hands',
            'pies': 'feet', 'brazos': 'arms', 'piernas': 'legs',
            
            # === ROPA ===
            'ropa': 'clothes', 'camisa': 'shirt', 'pantalón': 'pants',
            'vestido': 'dress', 'zapatos': 'shoes', 'calcetines': 'socks',
            'chaqueta': 'jacket', 'sombrero': 'hat',
            
            # === TRANSPORTE ===
            'carro': 'car', 'autobús': 'bus', 'bicicleta': 'bicycle',
            'metro': 'subway', 'avión': 'airplane', 'barco': 'boat',
            
            # === TECNOLOGÍA ===
            'computadora': 'computer', 'teléfono': 'phone', 'internet': 'internet',
            'televisión': 'television', 'cámara': 'camera', 'videojuegos': 'video games',
            
            # === PROFESIONES ===
            'médico': 'doctor', 'profesor': 'teacher', 'ingeniero': 'engineer',
            'abogado': 'lawyer', 'científico': 'scientist', 'artista': 'artist',
            'músico': 'musician', 'deportista': 'athlete',
            
            # === FRASES ÚTILES PARA CLASE ===
            'no entiendo': 'i do not understand',
            'puede repetir por favor': 'can you repeat please',
            'más despacio por favor': 'slower please',
            'cómo se pronuncia': 'how do you pronounce',
            'qué significa': 'what does it mean',
            'cómo se escribe': 'how do you spell',
            'puedo intentarlo': 'can i try',
            'es correcto': 'is it correct',
            'necesito ayuda': 'i need help',
            'puedo ir al baño': 'can i go to the bathroom',
            'tengo una pregunta': 'i have a question',
            'no sé': 'i do not know',
            'estoy confundido': 'i am confused',
            'puede explicar de nuevo': 'can you explain again',
            'quiero participar': 'i want to participate',
            
            # === EXPRESIONES DE OPINIÓN ===
            'me gusta mucho': 'i like it a lot',
            'no me gusta nada': 'i do not like it at all',
            'pienso que': 'i think that',
            'creo que': 'i believe that',
            'en mi opinión': 'in my opinion',
            'estoy de acuerdo': 'i agree',
            'no estoy de acuerdo': 'i disagree',
            'tal vez': 'maybe',
            'probablemente': 'probably',
            'definitivamente': 'definitely',
            
            # === CONECTORES LÓGICOS ===
            'y': 'and', 'o': 'or', 'pero': 'but',
            'porque': 'because', 'cuando': 'when',
            'donde': 'where', 'como': 'how', 'si': 'if',
            'entonces': 'then', 'también': 'also',
            'además': 'besides', 'sin embargo': 'however',
            'por ejemplo': 'for example', 'en conclusión': 'in conclusion',
            
            # === VERBOS IMPORTANTES ===
            'ser': 'to be', 'estar': 'to be', 'tener': 'to have',
            'hacer': 'to do', 'ir': 'to go', 'venir': 'to come',
            'ver': 'to see', 'decir': 'to say', 'poder': 'can',
            'querer': 'to want', 'saber': 'to know', 'conocer': 'to know',
            'poner': 'to put', 'salir': 'to go out', 'volver': 'to return',
            'pedir': 'to ask for', 'seguir': 'to continue', 'encontrar': 'to find',
            'pensar': 'to think', 'sentir': 'to feel', 'vivir': 'to live',
            'empezar': 'to start', 'terminar': 'to finish', 'cambiar': 'to change',
            'esperar': 'to wait', 'buscar': 'to look for', 'encontrar': 'to find',
            'recordar': 'to remember', 'olvidar': 'to forget', 'elegir': 'to choose',
            'necesitar': 'to need', 'ayudar': 'to help', 'trabajar': 'to work',
            'ganar': 'to win', 'perder': 'to lose', 'comprar': 'to buy',
            'vender': 'to sell', 'pagar': 'to pay', 'costar': 'to cost',
            'viajar': 'to travel', 'visitar': 'to visit', 'conocer': 'to meet',
            'amar': 'to love', 'odiar': 'to hate', 'preferir': 'to prefer',
            
            # === ADJETIVOS COMUNES ===
            'grande': 'big', 'pequeño': 'small', 'alto': 'tall',
            'bajo': 'short', 'largo': 'long', 'corto': 'short',
            'ancho': 'wide', 'estrecho': 'narrow', 'nuevo': 'new',
            'viejo': 'old', 'joven': 'young', 'bonito': 'pretty',
            'feo': 'ugly', 'bueno': 'good', 'malo': 'bad',
            'fácil': 'easy', 'difícil': 'difficult', 'interesante': 'interesting',
            'aburrido': 'boring', 'divertido': 'fun', 'serio': 'serious',
            'importante': 'important', 'necesario': 'necessary', 'posible': 'possible',
            'imposible': 'impossible', 'rápido': 'fast', 'lento': 'slow',
            'caliente': 'hot', 'frío': 'cold', 'caro': 'expensive',
            'barato': 'cheap', 'limpio': 'clean', 'sucio': 'dirty',
            'lleno': 'full', 'vacío': 'empty', 'feliz': 'happy',
            'triste': 'sad', 'enojado': 'angry', 'calmado': 'calm',
            'ocupado': 'busy', 'libre': 'free', 'listo': 'ready',
            'cansado': 'tired', 'despierto': 'awake', 'dormido': 'asleep',
            
            # === FRASES COMPLEJAS PARA PRÁCTICA ===
            'me gustaría aprender inglés': 'i would like to learn english',
            'quiero mejorar mi pronunciación': 'i want to improve my pronunciation',
            'es difícil pero importante': 'it is difficult but important',
            'practico todos los días': 'i practice every day',
            'mi sueño es viajar al extranjero': 'my dream is to travel abroad',
            'la educación es fundamental': 'education is fundamental',
            'necesito practicar más': 'i need to practice more',
            'el esfuerzo vale la pena': 'the effort is worth it',
            'cada día aprendo algo nuevo': 'every day i learn something new',
            'confío en mis habilidades': 'i trust my abilities',
            'los errores son oportunidades': 'mistakes are opportunities',
            'la práctica hace al maestro': 'practice makes perfect',
            'nunca es tarde para aprender': 'it is never too late to learn',
            'tengo metas claras': 'i have clear goals',
            'quiero ser bilingüe': 'i want to be bilingual',
            'aprecio tu ayuda': 'i appreciate your help',
            'estoy comprometido con mi aprendizaje': 'i am committed to my learning',
            'la constancia es clave': 'consistency is key',
            'me motiva superarme': 'i am motivated to improve myself',
            'valoro esta oportunidad': 'i value this opportunity'
        }
    
    def translate_with_retry(self, text, src='auto', dest='en', retries=1):
        """Traducir texto con estrategia híbrida"""
        if not text or not isinstance(text, str) or len(text.strip()) == 0:
            return text
        
        text_lower = text.lower().strip()
        cache_key = f"{text_lower}_{dest}"
        
        # 1. Verificar caché
        if cache_key in self.translation_cache:
            return self._format_translation(text, self.translation_cache[cache_key])
        
        # 2. Buscar en diccionario local (INSTANTÁNEO)
        local_result = self._search_local_dict(text_lower)
        if local_result:
            self.translation_cache[cache_key] = local_result
            return self._format_translation(text, local_result)
        
        # 3. Si tenemos traductor externo y vale la pena usarlo
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
                    # Guardar en caché y en diccionario local si es útil
                    self.translation_cache[cache_key] = translated
                    if len(text_lower) < 50:  # Solo frases cortas al diccionario
                        self.local_dict[text_lower] = translated.lower()
                    return self._format_translation(text, translated)
            except Exception as e:
                logger.warning(f"External translation failed: {str(e)[:80]}")
                self.use_external = False
        
        # 4. Fallback: traducción palabra por palabra
        fallback = self._word_by_word_translation(text)
        self.translation_cache[cache_key] = fallback
        return self._format_translation(text, fallback)
    
    def detect_language(self, text, retries=0):
        """Detectar idioma de forma inteligente"""
        if not text or not isinstance(text, str):
            return 'en', 0.8
        
        text_lower = text.lower()
        
        # Palabras indicadoras
        spanish_words = ['el', 'la', 'los', 'las', 'un', 'una', 'de', 'que', 
                        'y', 'en', 'por', 'con', 'para', 'sin', 'sobre']
        
        english_words = ['the', 'a', 'an', 'and', 'but', 'or', 'because', 'if',
                        'when', 'where', 'why', 'how', 'what', 'which', 'who']
        
        # Contar ocurrencias
        spanish_count = 0
        english_count = 0
        
        words = text_lower.split()
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word in spanish_words:
                spanish_count += 1
            if clean_word in english_words:
                english_count += 1
        
        # Determinar resultado
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
        # Coincidencia exacta
        if text in self.local_dict:
            return self.local_dict[text]
        
        # Buscar frases que contengan el texto
        for phrase_es, phrase_en in self.local_dict.items():
            if len(phrase_es) > 4 and phrase_es in text:
                # Reemplazar la frase encontrada
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
            "total_attempts": 0
        }
        self.xp = 0
        self.level = 1
        self.created_at = datetime.now()
        self.last_interaction = datetime.now()
        self.pronunciation_scores = []
    
    def add_conversation(self, user_text: str, eli_response: str, score: float):
        self.conversation_history.append({
            "user": user_text[:100],
            "eli": eli_response[:500],
            "score": score,
            "timestamp": datetime.now().isoformat()
        })
        self.pronunciation_scores.append(score)
        
        # Limitar tamaño
        if len(self.conversation_history) > 20:
            self.conversation_history.pop(0)
        if len(self.pronunciation_scores) > 10:
            self.pronunciation_scores.pop(0)
    
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
            "last_interaction": self.last_interaction.isoformat()
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
# SISTEMA COACH MEJORADO (TIPO PRAKTIKA)
# ============================================
class SistemaCoach:
    def __init__(self):
        self.topics = [
            "daily routine", "family", "hobbies", "food", "weather",
            "school", "future plans", "travel", "music", "sports"
        ]
        
        # Frases de scaffolding por nivel
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
    
    def detectar_nivel_usuario(self, texto: str, duracion_audio: float) -> str:
        """Detectar nivel del usuario"""
        if not texto or len(texto.strip()) < 3:
            return "beginner"
        
        palabras = texto.split()
        word_count = len(palabras)
        
        # Palabras avanzadas
        advanced_words = {'although', 'however', 'therefore', 'furthermore', 
                         'meanwhile', 'consequently', 'nevertheless'}
        
        advanced_count = sum(1 for word in palabras if word.lower() in advanced_words)
        
        # Calcular score
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
        
        # Palabras problemáticas comunes
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
        
        # Calcular score
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
        
        # Consejos
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
    
    def generar_respuesta(self, texto_usuario: str, duracion_audio: float = 0):
        """Generar respuesta con scaffolding como Praktika"""
        texto_lower = texto_usuario.lower().strip()
        
        # 1. DETECTAR NECESIDAD DE AYUDA (KEY IMPROVEMENT)
        ayuda_keywords = [
            'no sé', 'no se', 'qué digo', 'what do i say', 
            'help me', 'ayúdame', 'cómo se dice', 'no entiendo',
            'i dont know', 'what should i say', 'how do i say',
            'no puedo', 'i cant', 'i can\'t', 'qué puedo decir'
        ]
        
        necesita_ayuda = any(keyword in texto_lower for keyword in ayuda_keywords)
        es_muy_corto = len(texto_usuario.strip()) < 3
        
        # 2. SI NECESITA AYUDA, DAR SCAFFOLDING COMPLETO
        if necesita_ayuda or es_muy_corto:
            return self._respuesta_con_scaffolding(texto_usuario, duracion_audio)
        
        # 3. Detectar idioma
        lang, confidence = translator.detect_language(texto_usuario)
        if lang == 'es' and confidence > 0.6:
            return self._respuesta_en_espanol(texto_usuario)
        
        # 4. Análisis normal
        analisis = self.analizar_pronunciacion(texto_usuario, duracion_audio)
        
        # 5. Construir respuesta
        response_parts = []
        
        # Encabezado motivacional
        motivational_phrases = {
            "beginner": "🎉 **Great effort!** You're making progress!",
            "intermediate": "🌟 **Well done!** Your English is improving!",
            "advanced": "💫 **Excellent!** Very impressive English!"
        }
        response_parts.append(motivational_phrases.get(analisis['detected_level'], "🎉 Good job!"))
        
        # Mostrar lo que dijo
        response_parts.append(f"🗣️ **You said:** \"{texto_usuario}\"")
        response_parts.append(f"📊 **Pronunciation Score:** {analisis['score']}/100")
        
        # Correcciones
        if analisis['problem_words']:
            response_parts.append("\n🎯 **Focus on:**")
            for pw in analisis['problem_words']:
                response_parts.append(f"• **{pw['word']}**: {pw['explanation']}")
        
        # Consejos
        if analisis['tips']:
            response_parts.append("\n💡 **Tips:**")
            for tip in analisis['tips']:
                response_parts.append(f"• {tip}")
        
        # Pregunta siguiente con scaffolding opcional
        next_q = self._generar_pregunta(analisis['detected_level'])
        response_parts.append(f"\n💬 **Next question:** {next_q}")
        
        # Si el score es bajo, ofrecer ayuda extra
        if analisis['score'] < 70:
            response_parts.append("\n🆘 **Need help answering?** Try using one of these starters:")
            scaffolding = random.choice(self.scaffolding_templates[analisis['detected_level']])
            response_parts.append(f"\"{scaffolding}\"")
        
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
    
    def _respuesta_con_scaffolding(self, texto_usuario: str, duracion_audio: float):
        """Dar ayuda estructurada tipo Praktika"""
        nivel = self.detectar_nivel_usuario(texto_usuario, duracion_audio)
        topic = random.choice(self.topics)
        
        # Plantilla de scaffolding
        scaffolding = random.choice(self.scaffolding_templates[nivel])
        
        # Vocabulario del tema
        vocab = self.topic_vocabulary.get(topic, ["words related to this topic"])
        
        # Ejemplo completo
        example = self._generate_example_for_topic(topic, nivel)
        
        response = f"""## 🆘 **I'll Help You Structure Your Answer!**

### 🎯 **Topic:** {topic.capitalize()}

### 📝 **Sentence Starter (Your Level):**
\"{scaffolding}\"

### 🔤 **Useful Vocabulary:**
{', '.join(vocab[:5])}

### 💡 **How to Build Your Answer:**
1. **Choose** words from the vocabulary list
2. **Fill in** the blanks in the sentence starter
3. **Add** details to make it personal
4. **Practice** saying it out loud

### ✨ **Example Complete Answer:**
\"{example}\"

### 🎤 **Now It's Your Turn:**
1. Use the sentence starter
2. Record your answer
3. I'll give you personalized feedback!

### 🔄 **Remember:** It's okay to make mistakes. That's how we learn! 💪"""

        return {
            "respuesta": response,
            "tipo": "scaffolding",
            "pronunciation_score": 0,
            "nivel_detectado": nivel,
            "next_question": f"Tell me about {topic}",
            "ejemplos_respuesta": [example],
            "scaffolding_template": scaffolding,
            "topic_vocabulary": vocab[:5]
        }
    
    def _respuesta_en_espanol(self, texto_usuario: str):
        """Respuesta cuando habla en español"""
        translated = translator.translate_with_retry(texto_usuario, src='es', dest='en')
        
        return {
            "respuesta": f"""🌐 **I Notice You Spoke in Spanish**

🗣️ **In Spanish:** "{texto_usuario}"
🔤 **In English:** "{translated}"

🎯 **Try Saying It in English Now:**
1. Listen to the English version
2. Repeat slowly word by word
3. Focus on pronunciation
4. Put it all together

💡 **Tip:** Don't translate word-for-word. Think of the message!

🔁 **Practice:** "{translated}" """,
            "tipo": "language_switch",
            "pronunciation_score": 40,
            "nivel_detectado": "beginner",
            "ejemplos_respuesta": [translated]
        }
    
    def _respuesta_sin_audio(self):
        """Respuesta cuando no hay audio"""
        return {
            "respuesta": """🎤 **I Didn't Hear Anything**

💡 **Tips for Better Recording:**
• Speak clearly for 2-3 seconds
• Be in a quiet place
• Hold microphone closer

🔊 **Try Saying:**
• "Hello, my name is..."
• "I like to practice English"
• "Today is a good day"

🎯 **Ready when you are!**""",
            "tipo": "ayuda",
            "pronunciation_score": 0,
            "nivel_detectado": "beginner"
        }
    
    def _generar_pregunta(self, nivel: str) -> str:
        """Generar pregunta contextual"""
        preguntas = {
            "beginner": [
                "What is your name and where are you from?",
                "Do you have any brothers or sisters?",
                "What is your favorite food?",
                "What time do you wake up?",
                "What is your favorite color?",
                "Do you have any pets?",
                "What do you like to do on weekends?",
                "What is your favorite subject in school?"
            ],
            "intermediate": [
                "What does your typical day look like?",
                "Describe your best friend.",
                "What are your hobbies and why do you enjoy them?",
                "What was the last movie you watched?",
                "What are your plans for next weekend?",
                "Describe your hometown.",
                "What skill would you like to learn?",
                "Tell me about a happy memory."
            ],
            "advanced": [
                "What are your goals for the next 5 years?",
                "How has technology changed education?",
                "What global issue concerns you most?",
                "Describe a challenge you've overcome.",
                "What does success mean to you?",
                "How important is learning English today?",
                "What cultural tradition do you value?",
                "How do you handle stress?"
            ]
        }
        
        questions = preguntas.get(nivel, preguntas["beginner"])
        return random.choice(questions)
    
    def _generar_ejemplos(self, nivel: str):
        """Generar ejemplos de respuesta"""
        ejemplos = {
            "beginner": [
                "My name is Carlos and I'm from Mexico City.",
                "I have one brother and two sisters.",
                "My favorite food is pizza because it's delicious.",
                "I wake up at 7 AM every day.",
                "My favorite color is blue because it's calm."
            ],
            "intermediate": [
                "On a typical day, I wake up at 6, go to school, study in the afternoon, and relax in the evening.",
                "My best friend is Ana. She's very funny and always supports me.",
                "I enjoy playing soccer because it helps me stay active and make friends.",
                "The last movie I watched was Spider-Man. I liked the special effects.",
                "Next weekend, I'm planning to visit my grandparents."
            ],
            "advanced": [
                "In the next 5 years, I hope to finish university and start my engineering career.",
                "Technology has made education more accessible through online resources.",
                "Climate change concerns me most because it affects our planet's future.",
                "A challenge I overcame was learning English, which taught me persistence.",
                "Success to me means achieving personal growth while helping others."
            ]
        }
        
        examples = ejemplos.get(nivel, ejemplos["beginner"])
        if len(examples) > 3:
            return random.sample(examples, 3)
        return examples
    
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
            }
        }
        
        # Obtener ejemplo para el tema y nivel, o uno genérico
        if topic in examples_by_topic and nivel in examples_by_topic[topic]:
            return examples_by_topic[topic][nivel]
        
        # Ejemplo genérico por nivel
        generic_examples = {
            "beginner": f"I like {topic} because it's interesting.",
            "intermediate": f"I enjoy {topic} as it allows me to learn new things and have fun.",
            "advanced": f"Engaging with {topic} provides valuable insights and contributes to personal growth."
        }
        
        return generic_examples.get(nivel, f"I find {topic} very interesting.")

coach = SistemaCoach()

# ============================================
# JUEGO DE VOCABULARIO
# ============================================
class VocabularyGame:
    def __init__(self):
        self.vocabulary = {
            "easy": ["house", "dog", "cat", "sun", "water", "food", "friend", "family"],
            "normal": ["I like music", "I have a dog", "Today is sunny", "My family is important"],
            "hard": ["Technology changes our lives", "Education is important", "Practice makes perfect"]
        }
    
    def get_random_word(self, difficulty: str):
        if difficulty not in self.vocabulary:
            difficulty = "easy"
        
        word = random.choice(self.vocabulary[difficulty])
        
        return {
            "word": word,
            "difficulty": difficulty,
            "points_base": {"easy": 10, "normal": 20, "hard": 30}[difficulty]
        }
    
    def validate_answer(self, original: str, user_answer: str, difficulty: str):
        user_clean = user_answer.strip().lower()
        
        # Detectar idioma
        lang, _ = translator.detect_language(user_answer)
        
        # Para easy y normal, esperamos español
        if difficulty in ["easy", "normal"] and lang == 'en':
            return {
                "is_correct": False,
                "points_earned": 5,
                "message": "You spoke in English! Try saying it in Spanish. 🎯"
            }
        
        # Comparación simple
        is_correct = user_clean == original.lower()
        
        return {
            "is_correct": is_correct,
            "points_earned": {"easy": 10, "normal": 20, "hard": 30}[difficulty] if is_correct else 5,
            "message": "Correct! 🎉" if is_correct else "Try again! 💪"
        }

game = VocabularyGame()

# ============================================
# PROCESADOR DE AUDIO
# ============================================
class AudioProcessor:
    def process_audio(self, audio_file):
        try:
            audio_bytes = audio_file.read(app.config['AUDIO_FILE_MAX_SIZE'])
            
            if len(audio_bytes) > app.config['AUDIO_FILE_MAX_SIZE']:
                raise ValueError(f"Audio too large (max {app.config['AUDIO_FILE_MAX_SIZE']/1024/1024}MB)")
            
            # Convertir a AudioSegment
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            duration = len(audio) / 1000.0
            
            # Optimizar
            audio = audio.set_channels(1).set_frame_rate(16000)
            
            # Exportar a WAV
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
        "service": "Eli English Tutor v5.1",
        "version": "5.1.0",
        "timestamp": datetime.now().isoformat(),
        "features": ["Pronunciation Analysis", "Scaffolded Learning", "Vocabulary Games"]
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "sessions_active": len(session_manager.sessions),
        "translator": "hybrid"
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
            "welcome_message": "🎯 Welcome to Eli! Let's practice English!",
            "initial_level": session.current_level
        })
    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)[:100]}), 500

@app.route('/api/conversar_audio', methods=['POST'])
def conversar_audio():
    if 'audio' not in request.files:
        return jsonify({"estado": "error", "respuesta": "No audio file"}), 400
    
    audio_file = request.files['audio']
    session_id = request.form.get('session_id', '')
    
    try:
        # Procesar audio
        wav_buffer, duracion = audio_processor.process_audio(audio_file)
        
        # Transcribir
        texto = audio_processor.transcribe_audio(wav_buffer)
        
        if not texto:
            return jsonify({
                "estado": "error",
                "respuesta": coach._respuesta_sin_audio()["respuesta"]
            }), 400
        
        logger.info(f"User said: '{texto[:50]}...' ({duracion:.1f}s)")
        
        # Obtener respuesta
        respuesta = coach.generar_respuesta(texto, duracion)
        
        # Actualizar sesión
        xp_earned = 15
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                session.add_conversation(texto, respuesta["respuesta"], respuesta["pronunciation_score"])
                session.xp += xp_earned
                session.update_level()
        
        return jsonify({
            "estado": "exito",
            "respuesta": respuesta["respuesta"],
            "transcripcion": texto,
            "nueva_pregunta": respuesta.get("next_question", ""),
            "nivel_detectado": respuesta["nivel_detectado"],
            "pronunciation_score": respuesta["pronunciation_score"],
            "session_id": session_id,
            "xp_earned": xp_earned,
            "audio_duration": duracion,
            "tipo_respuesta": respuesta.get("tipo", "conversacion")
        })
    
    except ValueError as e:
        return jsonify({"estado": "error", "respuesta": "Audio file too large (max 5MB)"}), 413
    except Exception as e:
        logger.error(f"Error: {str(e)[:100]}")
        return jsonify({"estado": "error", "respuesta": "Error processing audio"}), 500

@app.route('/api/juego/palabra', methods=['GET'])
def obtener_palabra_juego():
    try:
        dificultad = request.args.get('dificultad', 'easy')
        palabra_data = game.get_random_word(dificultad)
        
        return jsonify({
            "estado": "exito",
            "palabra": palabra_data["word"],
            "dificultad": palabra_data["difficulty"],
            "puntos_base": palabra_data["points_base"]
        })
    except Exception as e:
        return jsonify({"estado": "error"}), 500

@app.route('/api/juego/validar', methods=['POST'])
def validar_respuesta_juego():
    try:
        data = request.json or {}
        palabra_original = data.get('palabra_original', '')
        respuesta_usuario = data.get('respuesta_usuario', '')
        dificultad = data.get('dificultad', 'easy')
        
        if not palabra_original or not respuesta_usuario:
            return jsonify({"estado": "error", "mensaje": "Missing fields"}), 400
        
        resultado = game.validate_answer(palabra_original, respuesta_usuario, dificultad)
        
        return jsonify({
            "estado": "exito",
            "es_correcta": resultado["is_correct"],
            "puntos_obtenidos": resultado["points_earned"],
            "mensaje": resultado["message"]
        })
    except Exception as e:
        return jsonify({"estado": "error"}), 500

@app.route('/api/estadisticas', methods=['GET'])
def obtener_estadisticas():
    try:
        session_id = request.args.get('session_id')
        
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                return jsonify({"estado": "exito", "stats": session.to_dict()})
        
        return jsonify({
            "estado": "exito",
            "global_stats": {"total_sessions": len(session_manager.sessions)}
        })
    except Exception as e:
        return jsonify({"estado": "error"}), 500

# ============================================
# EJECUCIÓN
# ============================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 60)
    print(f"🚀 Eli English Tutor v5.1")
    print(f"📡 Port: {port}")
    print(f"🔧 Translator: HYBRID")
    print(f"🎯 Coach: IMPROVED WITH SCAFFOLDING")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)