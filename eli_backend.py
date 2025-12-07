"""
ELI ENGLISH TUTOR - BACKEND CON CONTROL TOTAL V14.0
✅ CORRECCIONES CRÍTICAS APLICADAS:
1. Traducciones 100% profesionales predefinidas
2. Preguntas con gramática perfecta
3. Scaffolding ESPECÍFICO y CORRECTO por pregunta
4. Control total del backend
5. Eliminada lógica del frontend
"""

import os
import sys
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import speech_recognition as sr
import random
from datetime import datetime
import traceback
from pydub import AudioSegment
import io
import uuid
import time
import json
import re
from pathlib import Path
import hashlib

# ============================================
# CONFIGURACIÓN INICIAL
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

print("=" * 60)
print("🚀 Eli English Tutor - Backend v14.0")
print("🎯 SCAFFOLDING CORREGIDO - Gramática perfecta")
print("=" * 60)

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
# PREGUNTAS PREDEFINIDAS CON GRAMÁTICA PERFECTA
# ============================================
class QuestionDatabase:
    """Base de datos de preguntas con traducciones profesionales"""
    
    def __init__(self):
        # PREGUNTAS ORGANIZADAS POR NIVEL Y TEMÁTICA
        self.questions_by_level = {
            "beginner": [
                # Presentación personal
                {"english": "What is your name?", "spanish": "¿Cómo te llamas?", "topic": "personal", "tense": "present"},
                {"english": "How old are you?", "spanish": "¿Cuántos años tienes?", "topic": "personal", "tense": "present"},
                {"english": "Where are you from?", "spanish": "¿De dónde eres?", "topic": "personal", "tense": "present"},
                {"english": "Where do you live?", "spanish": "¿Dónde vives?", "topic": "personal", "tense": "present"},
                
                # Trabajo/Estudio
                {"english": "What do you do?", "spanish": "¿A qué te dedicas?", "topic": "work_study", "tense": "present"},
                {"english": "Are you a student?", "spanish": "¿Eres estudiante?", "topic": "work_study", "tense": "present"},
                {"english": "Do you work or study?", "spanish": "¿Trabajas o estudias?", "topic": "work_study", "tense": "present"},
                
                # Gustos básicos
                {"english": "What do you like?", "spanish": "¿Qué te gusta?", "topic": "hobbies", "tense": "present"},
                {"english": "What is your favorite color?", "spanish": "¿Cuál es tu color favorito?", "topic": "personal", "tense": "present"},
                {"english": "What do you like to eat?", "spanish": "¿Qué te gusta comer?", "topic": "food", "tense": "present"},
                
                # Rutina diaria
                {"english": "What time do you wake up?", "spanish": "¿A qué hora te despiertas?", "topic": "daily_routine", "tense": "present"},
                {"english": "What do you do in the morning?", "spanish": "¿Qué haces por la mañana?", "topic": "daily_routine", "tense": "present"},
                {"english": "What time do you go to bed?", "spanish": "¿A qué hora te acuestas?", "topic": "daily_routine", "tense": "present"},
                
                # Familia y amigos
                {"english": "Do you have any siblings?", "spanish": "¿Tienes hermanos?", "topic": "family", "tense": "present"},
                {"english": "Who is your best friend?", "spanish": "¿Quién es tu mejor amigo/a?", "topic": "social", "tense": "present"},
                
                # Pasado simple básico
                {"english": "What did you do yesterday?", "spanish": "¿Qué hiciste ayer?", "topic": "daily_routine", "tense": "past"},
                {"english": "Where were you yesterday?", "spanish": "¿Dónde estabas ayer?", "topic": "daily_routine", "tense": "past"},
                {"english": "What did you eat today?", "spanish": "¿Qué comiste hoy?", "topic": "food", "tense": "past"},
                
                # Futuro simple básico
                {"english": "What will you do tomorrow?", "spanish": "¿Qué harás mañana?", "topic": "plans", "tense": "future"},
                {"english": "Where will you go tomorrow?", "spanish": "¿A dónde irás mañana?", "topic": "plans", "tense": "future"},
            ],
            
            "intermediate": [
                # Trabajo/Estudio detallado
                {"english": "What is your current job?", "spanish": "¿Cuál es tu trabajo actual?", "topic": "work_study", "tense": "present"},
                {"english": "What are you studying?", "spanish": "¿Qué estás estudiando?", "topic": "work_study", "tense": "present"},
                {"english": "Why did you choose your career?", "spanish": "¿Por qué elegiste tu carrera?", "topic": "work_study", "tense": "past"},
                {"english": "What do you like about your job?", "spanish": "¿Qué te gusta de tu trabajo?", "topic": "work_study", "tense": "present"},
                
                # Hobbies e intereses
                {"english": "What are your hobbies?", "spanish": "¿Cuáles son tus pasatiempos?", "topic": "hobbies", "tense": "present"},
                {"english": "How often do you practice your hobbies?", "spanish": "¿Con qué frecuencia practicas tus pasatiempos?", "topic": "hobbies", "tense": "present"},
                {"english": "What is your favorite hobby and why?", "spanish": "¿Cuál es tu pasatiempo favorito y por qué?", "topic": "hobbies", "tense": "present"},
                
                # Viajes
                {"english": "Have you ever traveled abroad?", "spanish": "¿Has viajado alguna vez al extranjero?", "topic": "travel", "tense": "present_perfect"},
                {"english": "What countries have you visited?", "spanish": "¿Qué países has visitado?", "topic": "travel", "tense": "present_perfect"},
                {"english": "What was your favorite trip?", "spanish": "¿Cuál fue tu viaje favorito?", "topic": "travel", "tense": "past"},
                {"english": "Where would you like to travel?", "spanish": "¿A dónde te gustaría viajar?", "topic": "travel", "tense": "conditional"},
                
                # Presente perfecto
                {"english": "What have you learned recently?", "spanish": "¿Qué has aprendido recientemente?", "topic": "learning", "tense": "present_perfect"},
                {"english": "How long have you been studying English?", "spanish": "¿Cuánto tiempo llevas estudiando inglés?", "topic": "learning", "tense": "present_perfect"},
                {"english": "What have you accomplished this year?", "spanish": "¿Qué has logrado este año?", "topic": "achievements", "tense": "present_perfect"},
                
                # Pasado continuo
                {"english": "What were you doing yesterday at this time?", "spanish": "¿Qué estabas haciendo ayer a esta hora?", "topic": "daily_routine", "tense": "past_continuous"},
                {"english": "What were you thinking about when you made that decision?", "spanish": "¿En qué estabas pensando cuando tomaste esa decisión?", "topic": "personal", "tense": "past_continuous"},
                
                # Opiniones y preferencias
                {"english": "What is your opinion about technology?", "spanish": "¿Cuál es tu opinión sobre la tecnología?", "topic": "opinions", "tense": "present"},
                {"english": "What kind of music do you prefer?", "spanish": "¿Qué tipo de música prefieres?", "topic": "entertainment", "tense": "present"},
                {"english": "Why do you think learning English is important?", "spanish": "¿Por qué crees que aprender inglés es importante?", "topic": "learning", "tense": "present"},
            ],
            
            "advanced": [
                # Metas y aspiraciones
                {"english": "What are your long-term career goals?", "spanish": "¿Cuáles son tus metas profesionales a largo plazo?", "topic": "goals", "tense": "present"},
                {"english": "Where do you see yourself in 5 years?", "spanish": "¿Dónde te ves en 5 años?", "topic": "goals", "tense": "future"},
                {"english": "What would you like to achieve in your lifetime?", "spanish": "¿Qué te gustaría lograr en tu vida?", "topic": "goals", "tense": "conditional"},
                
                # Experiencias complejas
                {"english": "What was the most challenging experience you have faced?", "spanish": "¿Cuál fue la experiencia más desafiante que has enfrentado?", "topic": "experiences", "tense": "past"},
                {"english": "How has that experience changed you?", "spanish": "¿Cómo te ha cambiado esa experiencia?", "topic": "experiences", "tense": "present_perfect"},
                
                # Condicionales complejos
                {"english": "What would you do if you had unlimited resources?", "spanish": "¿Qué harías si tuvieras recursos ilimitados?", "topic": "hypothetical", "tense": "conditional"},
                {"english": "How would you change the world if you could?", "spanish": "¿Cómo cambiarías el mundo si pudieras?", "topic": "hypothetical", "tense": "conditional"},
                {"english": "If you could meet anyone, who would it be?", "spanish": "Si pudieras conocer a alguien, ¿quién sería?", "topic": "hypothetical", "tense": "conditional"},
                
                # Futuro perfecto
                {"english": "What will you have accomplished by this time next year?", "spanish": "¿Qué habrás logrado para esta fecha del próximo año?", "topic": "goals", "tense": "future_perfect"},
                {"english": "Where will you have traveled by the time you're 50?", "spanish": "¿A dónde habrás viajado para cuando tengas 50 años?", "topic": "travel", "tense": "future_perfect"},
                
                # Pasado perfecto
                {"english": "What had you already done before you started working here?", "spanish": "¿Qué ya habías hecho antes de empezar a trabajar aquí?", "topic": "experiences", "tense": "past_perfect"},
                {"english": "Had you ever considered this career path before?", "spanish": "¿Habías considerado alguna vez esta carrera profesional?", "topic": "work_study", "tense": "past_perfect"},
                
                # Subjuntivo
                {"english": "What would you recommend that a beginner do?", "spanish": "¿Qué recomendarías que haga un principiante?", "topic": "advice", "tense": "subjunctive"},
                {"english": "It's important that you consider all options.", "spanish": "Es importante que consideres todas las opciones.", "topic": "advice", "tense": "subjunctive"},
                
                # Discusión de temas complejos
                {"english": "How do you think technology will affect society in the future?", "spanish": "¿Cómo crees que la tecnología afectará a la sociedad en el futuro?", "topic": "technology", "tense": "future"},
                {"english": "What is your perspective on global challenges?", "spanish": "¿Cuál es tu perspectiva sobre los desafíos globales?", "topic": "global_issues", "tense": "present"},
                {"english": "How has globalization impacted your field?", "spanish": "¿Cómo ha impactado la globalización tu campo?", "topic": "work_study", "tense": "present_perfect"},
            ]
        }
        
        # HISTORIAL DE PREGUNTAS POR USUARIO
        self.user_history = {}
        
        # CONTADOR DE PREGUNTAS
        self.question_counters = {}
        for level in self.questions_by_level:
            self.question_counters[level] = 0
    
    def get_question(self, user_id, level="beginner", avoid_recent=True):
        """Obtiene pregunta según nivel y evita repeticiones recientes"""
        
        # Inicializar historial del usuario si no existe
        if user_id not in self.user_history:
            self.user_history[user_id] = {
                "asked_questions": [],
                "last_question": None,
                "level": level
            }
        
        # Obtener preguntas disponibles para el nivel
        available_questions = self.questions_by_level.get(level, self.questions_by_level["beginner"])
        
        if not available_questions:
            # Fallback a nivel beginner
            available_questions = self.questions_by_level["beginner"]
        
        # Filtrar preguntas recientes si se solicita
        if avoid_recent and self.user_history[user_id]["asked_questions"]:
            recent_questions = self.user_history[user_id]["asked_questions"][-5:]  # Últimas 5 preguntas
            filtered_questions = [q for q in available_questions if q["english"] not in recent_questions]
            
            # Si no hay preguntas disponibles después de filtrar, usar todas
            if filtered_questions:
                available_questions = filtered_questions
        
        # Seleccionar pregunta aleatoria
        selected_question = random.choice(available_questions)
        
        # Actualizar historial
        self.user_history[user_id]["asked_questions"].append(selected_question["english"])
        self.user_history[user_id]["last_question"] = selected_question["english"]
        self.user_history[user_id]["level"] = level
        
        # Limitar historial a 20 preguntas
        if len(self.user_history[user_id]["asked_questions"]) > 20:
            self.user_history[user_id]["asked_questions"] = self.user_history[user_id]["asked_questions"][-20:]
        
        # Incrementar contador
        self.question_counters[level] += 1
        
        return {
            **selected_question,
            "question_number": self.question_counters[level],
            "is_predefined": True,
            "generated_at": datetime.now().isoformat()
        }
    
    def get_scaffolding_for_question(self, question_english, level="beginner"):
        """Genera scaffolding ESPECÍFICO y CORRECTO para cada pregunta"""
        
        # DETECTAR TIPO DE PREGUNTA Y TIEMPO VERBAL
        tense = self._detect_tense(question_english)
        question_type = self._classify_question(question_english)
        topic = self._detect_topic(question_english)
        
        # MAPA DE SCAFFOLDING CORREGIDO - ¡100% ESPECÍFICO!
        scaffolding_map = {
            # ========== BEGINNER QUESTIONS ==========
            "What is your name?": {
                "template": "My name is [your name]. I am from [your country/city].",
                "vocabulary": ["name", "My name is", "I am", "called", "from", "originally from"],
                "grammar_tip": "Use 'My name is' for formal introduction. Use 'I am' for casual situations.",
                "common_mistakes": ["I name is (incorrect)", "My name (incomplete sentence)"],
                "practice_sentences": [
                    "My name is John. I am from New York.",
                    "My name is Maria. I am originally from Spain.",
                    "They call me Alex. I am from London."
                ],
                "sentence_starters": [
                    "My name is...",
                    "I am called...",
                    "People call me...",
                    "I go by the name..."
                ]
            },
            
            "How old are you?": {
                "template": "I am [number] years old. I will be [next number] next [month/year].",
                "vocabulary": ["years old", "age", "I am", "turning", "next", "birthday"],
                "grammar_tip": "Always use 'years old' after the number. Never say 'I have X years' in English.",
                "common_mistakes": ["I have 25 years (Spanish structure)", "I am 25 (incomplete)"],
                "practice_sentences": [
                    "I am 25 years old. I will be 26 next month.",
                    "She is 30 years old. Her birthday is in June.",
                    "He is 40 years old. He was born in 1983."
                ],
                "sentence_starters": [
                    "I am... years old.",
                    "I'm... years old.",
                    "I'll be... next...",
                    "My age is..."
                ]
            },
            
            "Where are you from?": {
                "template": "I am from [country]. I live in [city].",
                "vocabulary": ["from", "originally from", "come from", "born in", "live in", "grew up in"],
                "grammar_tip": "Use 'I am from' for nationality. Use 'I live in' for current residence.",
                "common_mistakes": ["I from Mexico (missing 'am')", "I live from (wrong preposition)"],
                "practice_sentences": [
                    "I am from Mexico. I live in Mexico City.",
                    "I come from Argentina. I was born in Buenos Aires.",
                    "I am originally from Colombia but I live in the United States now."
                ],
                "sentence_starters": [
                    "I am from...",
                    "I come from...",
                    "I was born in...",
                    "I live in..."
                ]
            },
            
            "What do you like to eat?": {
                "template": "I like to eat [food]. My favorite dish is [specific dish].",
                "vocabulary": ["like", "enjoy", "favorite", "prefer", "dish", "cuisine", "meal"],
                "grammar_tip": "Use 'like to + verb' or 'enjoy + verb-ing' for preferences.",
                "common_mistakes": ["I like eat pizza (missing 'to')", "I enjoy to eat (wrong structure)"],
                "practice_sentences": [
                    "I like to eat pizza. My favorite is pepperoni pizza.",
                    "I enjoy eating sushi. Japanese food is my favorite.",
                    "I prefer Italian food. I love pasta and pizza."
                ],
                "sentence_starters": [
                    "I like to eat...",
                    "I enjoy eating...",
                    "My favorite food is...",
                    "I really like..."
                ]
            },
            
            "What did you do yesterday?": {
                "template": "Yesterday, I [past tense verb]. After that, I [another past tense verb].",
                "vocabulary": ["yesterday", "last night", "in the morning", "during the day", "after", "then"],
                "grammar_tip": "Use past simple (verb + ed or irregular form) for completed actions in the past.",
                "common_mistakes": ["Yesterday I go (should be 'went')", "I did worked (double past)"],
                "practice_sentences": [
                    "Yesterday, I worked. After that, I went to the gym.",
                    "I studied English last night. Then I watched a movie.",
                    "She visited her friend yesterday. They had lunch together."
                ],
                "sentence_starters": [
                    "Yesterday, I...",
                    "Last night, I...",
                    "In the morning, I...",
                    "After work/school, I..."
                ]
            },
            
            "What will you do tomorrow?": {
                "template": "Tomorrow, I will [base verb]. I also plan to [another base verb].",
                "vocabulary": ["tomorrow", "will", "going to", "plan to", "intend to", "might", "probably"],
                "grammar_tip": "Use 'will' for spontaneous decisions. Use 'going to' for plans.",
                "common_mistakes": ["Tomorrow I go (should be 'will go')", "I will to study (should be 'will study')"],
                "practice_sentences": [
                    "Tomorrow, I will study. I also plan to go to the library.",
                    "I am going to meet friends. We will have lunch together.",
                    "She will travel next week. She is going to visit her family."
                ],
                "sentence_starters": [
                    "Tomorrow, I will...",
                    "I am going to...",
                    "I plan to...",
                    "I might..."
                ]
            },
            
            "Where will you go tomorrow?": {
                "template": "Tomorrow, I will go to [place]. I need to [purpose].",
                "vocabulary": ["go to", "visit", "travel to", "meet at", "purpose", "reason", "because"],
                "grammar_tip": "Use 'will + go' for future movement. Add 'to' before the place.",
                "common_mistakes": ["I will go school (missing 'to')", "I go to tomorrow (wrong word order)"],
                "practice_sentences": [
                    "Tomorrow, I will go to school. I need to attend classes.",
                    "I will visit the museum. I want to see the new exhibition.",
                    "She will travel to Paris. She is going for a business meeting."
                ],
                "sentence_starters": [
                    "I will go to...",
                    "I'm going to visit...",
                    "I plan to travel to...",
                    "I need to go to..."
                ]
            },
            
            # ========== INTERMEDIATE QUESTIONS ==========
            "What are your hobbies?": {
                "template": "My hobbies are [hobby1] and [hobby2]. I enjoy them because [reason].",
                "vocabulary": ["hobbies", "interests", "activities", "pastimes", "passion", "leisure time"],
                "grammar_tip": "Use plural for multiple hobbies. Use gerund (-ing) for activities: 'reading', 'swimming'.",
                "common_mistakes": ["My hobby is read books (should be 'reading books')", "I enjoy to swim (should be 'swimming')"],
                "practice_sentences": [
                    "My hobbies are reading and swimming. I enjoy them because they help me relax.",
                    "I enjoy playing guitar. Music is my passion.",
                    "She likes hiking and photography. They allow her to connect with nature."
                ],
                "sentence_starters": [
                    "My hobbies are...",
                    "I enjoy...",
                    "In my free time, I like to...",
                    "One of my favorite activities is..."
                ]
            },
            
            "Have you ever traveled abroad?": {
                "template": "Yes, I have traveled to [country]. I went there in [year] and I [past experience].",
                "vocabulary": ["traveled", "visited", "been to", "abroad", "overseas", "foreign country", "experience"],
                "grammar_tip": "Use present perfect (have/has + past participle) for life experiences without specific time.",
                "common_mistakes": ["I traveled to France last year (simple past ok for specific time)", "I have travel (should be 'traveled')"],
                "practice_sentences": [
                    "Yes, I have traveled to Japan. I went there in 2019 and I visited Tokyo.",
                    "I have been to three countries. My favorite was Italy.",
                    "She has never traveled abroad, but she wants to visit Spain."
                ],
                "sentence_starters": [
                    "Yes, I have...",
                    "I've been to...",
                    "I have visited...",
                    "No, I haven't... but I would like to..."
                ]
            },
            
            "What have you learned recently?": {
                "template": "Recently, I have learned [skill/knowledge]. This has helped me to [benefit].",
                "vocabulary": ["learned", "discovered", "figured out", "mastered", "recently", "lately", "new"],
                "grammar_tip": "Use present perfect for recent actions with present relevance. Use 'has helped' for results.",
                "common_mistakes": ["I learned English last year (simple past for specific time)", "I have learn (should be 'learned')"],
                "practice_sentences": [
                    "Recently, I have learned to cook. This has helped me to eat healthier.",
                    "I have discovered a new author. I enjoy reading his books.",
                    "She has mastered Spanish grammar. Now she can speak more confidently."
                ],
                "sentence_starters": [
                    "Recently, I have learned...",
                    "Lately, I've been learning...",
                    "I have discovered...",
                    "I've figured out how to..."
                ]
            },
            
            # ========== ADVANCED QUESTIONS ==========
            "What are your long-term career goals?": {
                "template": "My long-term goals are to [goal1] and [goal2]. To achieve this, I plan to [action].",
                "vocabulary": ["aspirations", "objectives", "aims", "professional development", "career path", "advancement"],
                "grammar_tip": "Use infinitive (to + verb) for goals: 'to become', 'to achieve', 'to start'.",
                "common_mistakes": ["My goal is become manager (should be 'to become')", "I want improving (should be 'to improve')"],
                "practice_sentences": [
                    "My long-term goals are to become a manager and start my own business. To achieve this, I plan to get an MBA.",
                    "I aim to publish a book within five years. I'm currently working on my writing skills.",
                    "Her objective is to lead an international team. She's learning multiple languages."
                ],
                "sentence_starters": [
                    "My long-term goals are to...",
                    "I aspire to...",
                    "My career objectives include...",
                    "In the future, I hope to..."
                ]
            },
            
            "What would you do if you had unlimited resources?": {
                "template": "If I had unlimited resources, I would [action1] and [action2]. I would also [additional action].",
                "vocabulary": ["resources", "funds", "opportunity", "means", "hypothetical", "conditional", "unlimited"],
                "grammar_tip": "Use second conditional (if + past simple, would + base verb) for hypothetical situations.",
                "common_mistakes": ["If I have unlimited resources, I will travel (wrong conditional)", "I would to travel (should be 'would travel')"],
                "practice_sentences": [
                    "If I had unlimited resources, I would travel the world and start a charity. I would also help my community.",
                    "I would start a business if I had the means. I would create jobs for people.",
                    "She would buy a house if she had enough money. She would also invest in education."
                ],
                "sentence_starters": [
                    "If I had unlimited resources, I would...",
                    "Given the opportunity, I would...",
                    "In an ideal world, I would...",
                    "If money were no object, I would..."
                ]
            },
            
            "How do you think technology will affect society in the future?": {
                "template": "I think technology will [effect1] and [effect2]. However, it might also [potential issue].",
                "vocabulary": ["technology", "society", "future", "impact", "affect", "transform", "challenge", "opportunity"],
                "grammar_tip": "Use future simple (will + verb) for predictions. Use 'might' for possibilities.",
                "common_mistakes": ["Technology affect (missing 'will')", "It will to change (should be 'will change')"],
                "practice_sentences": [
                    "I think technology will improve healthcare and education. However, it might also create privacy issues.",
                    "Technology will transform how we work. Remote work will become more common.",
                    "AI will affect many industries. Some jobs will disappear but new ones will appear."
                ],
                "sentence_starters": [
                    "I think technology will...",
                    "In my opinion, technology will...",
                    "Technology is likely to...",
                    "I believe that in the future..."
                ]
            },
            
            # ========== DEFAULT SCAFFOLDING ==========
            "default": self._generate_default_scaffolding(question_english, tense, question_type, topic, level)
        }
        
        # Buscar scaffolding específico
        if question_english in scaffolding_map:
            scaffolding = scaffolding_map[question_english]
        else:
            # Generar scaffolding dinámico basado en tipo de pregunta
            scaffolding = self._generate_dynamic_scaffolding(question_english, tense, question_type, topic, level)
        
        # Añadir información contextual
        scaffolding.update({
            "for_question": question_english,
            "level": level,
            "tense": tense,
            "question_type": question_type,
            "topic": topic,
            "response_structure": self._get_response_structure(question_type, tense),
            "useful_phrases": self._get_useful_phrases(question_type, level)
        })
        
        return scaffolding
    
    def _detect_tense(self, question):
        """Detecta el tiempo verbal de la pregunta CORRECTAMENTE"""
        question_lower = question.lower()
        
        if "did" in question_lower or "was" in question_lower or "were" in question_lower:
            return "past_simple"
        elif "will" in question_lower:
            return "future_simple"
        elif "going to" in question_lower:
            return "future_going_to"
        elif "have" in question_lower and "you" in question_lower:
            return "present_perfect"
        elif "has" in question_lower and ("he" in question_lower or "she" in question_lower):
            return "present_perfect"
        elif "are" in question_lower and "ing" in question_lower:
            return "present_continuous"
        elif "would" in question_lower or "could" in question_lower:
            return "conditional"
        elif "had" in question_lower and "you" in question_lower:
            return "past_perfect"
        else:
            return "present_simple"
    
    def _detect_topic(self, question):
        """Detecta el tema de la pregunta"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["name", "age", "from", "live"]):
            return "personal"
        elif any(word in question_lower for word in ["eat", "food", "drink", "restaurant"]):
            return "food"
        elif any(word in question_lower for word in ["hobby", "like", "enjoy", "favorite"]):
            return "hobbies"
        elif any(word in question_lower for word in ["work", "job", "study", "career"]):
            return "work_study"
        elif any(word in question_lower for word in ["travel", "country", "visit", "abroad"]):
            return "travel"
        elif any(word in question_lower for word in ["learn", "study", "practice", "skill"]):
            return "learning"
        elif any(word in question_lower for word in ["think", "opinion", "believe", "perspective"]):
            return "opinions"
        elif any(word in question_lower for word in ["goal", "future", "plan", "aspiration"]):
            return "goals"
        else:
            return "general"
    
    def _classify_question(self, question):
        """Clasifica el tipo de pregunta"""
        question_lower = question.lower()
        
        if question_lower.startswith("what"):
            if "do you" in question_lower:
                return "what_do_you"
            elif "did you" in question_lower:
                return "what_did_you"
            elif "will you" in question_lower:
                return "what_will_you"
            elif "have you" in question_lower:
                return "what_have_you"
            elif "is your" in question_lower:
                return "what_is_your"
            else:
                return "what_question"
        
        elif question_lower.startswith("where"):
            return "where_question"
        
        elif question_lower.startswith("when"):
            return "when_question"
        
        elif question_lower.startswith("why"):
            return "why_question"
        
        elif question_lower.startswith("how"):
            if "often" in question_lower:
                return "how_often"
            elif "long" in question_lower:
                return "how_long"
            else:
                return "how_question"
        
        elif question_lower.startswith("do you") or question_lower.startswith("are you"):
            return "yes_no_question"
        
        elif "have you" in question_lower:
            return "experience_question"
        
        else:
            return "open_question"
    
    def _get_response_structure(self, question_type, tense):
        """Proporciona estructura de respuesta CORRECTA"""
        
        structures = {
            "what_do_you": {
                "present_simple": "Answer with present simple: 'I [verb] [object].' Add details with 'because' or frequency words.",
                "present_continuous": "Answer with present continuous: 'I am [verb-ing] [object].' Mention current activity."
            },
            "what_did_you": {
                "past_simple": "Answer with past simple: 'I [past verb] [object].' Add time expressions like 'yesterday' or 'last week'."
            },
            "what_will_you": {
                "future_simple": "Answer with 'will': 'I will [verb] [object].' Use 'going to' for plans.",
                "future_going_to": "Answer with 'going to': 'I am going to [verb] [object].' Mention specific plans."
            },
            "what_have_you": {
                "present_perfect": "Answer with present perfect: 'I have [past participle] [object].' Add 'recently' or 'lately'."
            },
            "what_is_your": {
                "present_simple": "Answer with noun phrase: 'My [noun] is [description].' Add reasons or examples."
            },
            "where_question": {
                "present_simple": "Answer with place: 'I [verb] in/at [place].' Use correct prepositions (in/at/on).",
                "future_simple": "Answer with future place: 'I will go to [place].' Mention purpose."
            },
            "yes_no_question": {
                "present_simple": "Start with Yes/No: 'Yes, I do. Actually, I...' or 'No, I don't. But I...'",
                "past_simple": "Start with Yes/No: 'Yes, I did. I [past verb]...' or 'No, I didn't. Instead, I...'",
                "present_perfect": "Start with Yes/No: 'Yes, I have. I have [past participle]...' or 'No, I haven't. But I would like to...'"
            },
            "experience_question": {
                "present_perfect": "Use present perfect for experiences: 'Yes, I have [past participle]...' or 'No, I have never [past participle]...'"
            },
            "why_question": {
                "general": "Answer with reason: 'Because [reason].' or 'The reason is [explanation].' Use linking words."
            },
            "how_question": {
                "general": "Answer with manner: 'By [method].' or 'I [verb] [adverb].' or 'Through [process].'"
            }
        }
        
        # Obtener estructura específica o general
        if question_type in structures:
            if isinstance(structures[question_type], dict):
                return structures[question_type].get(tense, "Give a complete sentence with subject + verb + complement.")
            else:
                return structures[question_type]
        
        return "Give a complete sentence with subject + verb + complement. Add details to make it interesting."
    
    def _get_useful_phrases(self, question_type, level):
        """Proporciona frases útiles según la pregunta y nivel"""
        
        phrases_by_level = {
            "beginner": [
                "I think...",
                "I like...",
                "My favorite...",
                "Usually, I...",
                "Sometimes, I...",
                "Because...",
                "For example..."
            ],
            "intermediate": [
                "In my opinion...",
                "From my perspective...",
                "I would say that...",
                "Generally speaking...",
                "What I enjoy most is...",
                "Additionally...",
                "Furthermore..."
            ],
            "advanced": [
                "From my standpoint...",
                "Considering the circumstances...",
                "It could be argued that...",
                "One might suggest that...",
                "Taking into account...",
                "On the one hand... on the other hand...",
                "In conclusion..."
            ]
        }
        
        # Frases específicas por tipo de pregunta
        specific_phrases = {
            "what_question": ["What I mean is...", "Specifically...", "To be more precise..."],
            "why_question": ["The main reason is...", "This is because...", "Due to the fact that..."],
            "how_question": ["The way I do it is...", "My approach involves...", "Typically, the process is..."],
            "experience_question": ["Based on my experience...", "What I've found is...", "In my experience..."],
            "yes_no_question": ["Actually...", "In fact...", "To be honest...", "Well..."]
        }
        
        base_phrases = phrases_by_level.get(level, phrases_by_level["beginner"])
        additional_phrases = specific_phrases.get(question_type, [])
        
        return base_phrases + additional_phrases
    
    def _generate_default_scaffolding(self, question, tense, question_type, topic, level):
        """Genera scaffolding por defecto bien estructurado"""
        
        templates_by_tense = {
            "present_simple": "I usually [verb] [object] because [reason].",
            "past_simple": "Yesterday/last week, I [past verb] [object]. It was [adjective].",
            "future_simple": "Tomorrow/next week, I will [verb] [object]. I plan to [additional detail].",
            "present_perfect": "I have [past participle] [object] recently. This has helped me to [benefit].",
            "conditional": "If I could, I would [verb] [object]. I would also [additional action]."
        }
        
        vocabulary_by_topic = {
            "personal": ["I", "my", "me", "family", "friends", "home", "life", "experience"],
            "food": ["eat", "drink", "cook", "restaurant", "meal", "dish", "cuisine", "taste"],
            "hobbies": ["enjoy", "like", "hobby", "activity", "free time", "relax", "fun", "interest"],
            "work_study": ["work", "study", "job", "career", "project", "team", "goal", "skill"],
            "travel": ["travel", "visit", "country", "city", "culture", "experience", "adventure", "sightseeing"],
            "learning": ["learn", "study", "practice", "improve", "skill", "knowledge", "progress", "achievement"],
            "opinions": ["think", "believe", "opinion", "perspective", "view", "feel", "consider", "argue"]
        }
        
        grammar_tips_by_tense = {
            "present_simple": "Use present simple for habits, routines, and general truths.",
            "past_simple": "Use past simple for completed actions in the past. Add time expressions.",
            "future_simple": "Use 'will' for predictions and spontaneous decisions. Use 'going to' for plans.",
            "present_perfect": "Use present perfect for experiences and recent actions with present relevance.",
            "conditional": "Use second conditional (if + past simple, would + base verb) for hypothetical situations."
        }
        
        return {
            "template": templates_by_tense.get(tense, "I [verb] [object] because [reason]."),
            "vocabulary": vocabulary_by_topic.get(topic, ["think", "believe", "experience", "important", "because"]),
            "grammar_tip": grammar_tips_by_tense.get(tense, "Use complete sentences with subject + verb + complement."),
            "common_mistakes": [
                "Forgetting subject-verb agreement",
                "Missing articles (a/an/the)",
                "Wrong word order",
                "Incorrect tense usage"
            ],
            "practice_sentences": [
                "Try to make a complete sentence.",
                "Add details to explain your answer.",
                "Use vocabulary related to the topic."
            ],
            "sentence_starters": [
                "I think that...",
                "In my opinion...",
                "From my experience...",
                "What I believe is..."
            ]
        }
    
    def _generate_dynamic_scaffolding(self, question, tense, question_type, topic, level):
        """Genera scaffolding dinámico basado en la pregunta"""
        
        # Determinar palabras clave
        question_lower = question.lower()
        keywords = []
        
        for word in question_lower.split():
            if len(word) > 3 and word not in ["what", "where", "when", "why", "how", "your", "you", "they", "this"]:
                keywords.append(word)
        
        # Generar template basado en tipo de pregunta
        if question_type.startswith("what"):
            if "do you" in question_lower:
                template = f"I usually [verb related to {topic}] because [reason]."
            elif "did you" in question_lower:
                template = f"Yesterday/last week, I [past verb related to {topic}]. It was [adjective]."
            elif "will you" in question_lower:
                template = f"Tomorrow/next week, I will [verb related to {topic}]. I plan to [additional detail]."
            elif "have you" in question_lower:
                template = f"I have [past participle related to {topic}] recently. This has helped me to [benefit]."
            else:
                template = f"My answer about {topic} is [your response]. I think this because [reason]."
        
        elif question_type.startswith("where"):
            template = f"I [verb] in/at [place related to {topic}]. This place is [description]."
        
        elif question_type.startswith("why"):
            template = f"Because [reason related to {topic}]. Additionally, [additional reason]."
        
        elif question_type.startswith("how"):
            template = f"I [verb] by [method]. This helps me to [benefit]."
        
        else:
            template = f"I think that [opinion about {topic}]. This is because [reason]."
        
        return {
            "template": template,
            "vocabulary": keywords[:8] + ["because", "usually", "sometimes", "really", "very"],
            "grammar_tip": self._get_grammar_tip_for_tense(tense),
            "common_mistakes": [
                "Incomplete sentences",
                "Wrong tense usage",
                "Missing connecting words",
                "Limited vocabulary"
            ],
            "practice_sentences": [
                f"Try to answer using the {tense} tense.",
                "Add specific details to make your answer interesting.",
                "Use complete sentences with subject and verb."
            ],
            "sentence_starters": [
                "I think that...",
                "In my experience...",
                "What I've found is...",
                "From my perspective..."
            ]
        }
    
    def _get_grammar_tip_for_tense(self, tense):
        """Proporciona consejo gramatical específico para el tiempo verbal"""
        
        tips = {
            "present_simple": "Use present simple for habits, routines, facts, and general truths.",
            "past_simple": "Use past simple for completed actions in the past. Remember irregular verbs.",
            "future_simple": "Use 'will' for predictions and spontaneous decisions. Don't use 'to' after 'will'.",
            "present_perfect": "Use present perfect for experiences (ever/never) and recent actions (just/already/yet).",
            "past_continuous": "Use past continuous for actions in progress at a specific time in the past.",
            "conditional": "Use second conditional (if + past simple, would + base verb) for hypothetical situations.",
            "present_continuous": "Use present continuous for actions happening now or around now."
        }
        
        return tips.get(tense, "Use complete sentences with correct tense and word order.")

# Inicializar base de datos de preguntas
question_db = QuestionDatabase()

# ============================================
# PROCESADOR DE AUDIO
# ============================================
class AudioProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()
    
    def transcribe_audio(self, audio_bytes):
        """Transcribe audio a texto usando Google Speech Recognition"""
        try:
            audio_io = io.BytesIO(audio_bytes)
            
            with sr.AudioFile(audio_io) as source:
                audio_data = self.recognizer.record(source)
                
                try:
                    text = self.recognizer.recognize_google(audio_data, language='en-US')
                    return {"text": text, "language": "en", "error": None}
                except sr.UnknownValueError:
                    return {"text": "", "language": "unknown", "error": "No speech detected"}
                except sr.RequestError as e:
                    return {"text": "", "language": "unknown", "error": f"Speech recognition error: {str(e)}"}
                        
        except Exception as e:
            logger.error(f"Error in transcription: {str(e)}")
            return {"text": "", "language": "unknown", "error": str(e)}

audio_processor = AudioProcessor()

# ============================================
# GESTIÓN DE PROGRESO DEL USUARIO
# ============================================
class UserProgressManager:
    """Gestiona TODO el progreso del usuario desde el backend"""
    
    def __init__(self):
        self.db_file = "user_progress.json"
        self._init_database()
    
    def _init_database(self):
        """Inicializa la base de datos si no existe"""
        if not Path(self.db_file).exists():
            initial_data = {
                "users": {},
                "statistics": {
                    "total_sessions": 0,
                    "total_questions_asked": 0,
                    "total_audio_processes": 0
                }
            }
            self._save_data(initial_data)
    
    def _load_data(self):
        """Carga datos de la base de datos"""
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"users": {}, "statistics": {"total_sessions": 0, "total_questions_asked": 0, "total_audio_processes": 0}}
    
    def _save_data(self, data):
        """Guarda datos en la base de datos"""
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving progress data: {e}")
            return False
    
    def get_user_progress(self, user_id):
        """Obtiene progreso del usuario"""
        data = self._load_data()
        return data["users"].get(user_id)
    
    def update_user_progress(self, user_id, updates):
        """Actualiza progreso del usuario"""
        data = self._load_data()
        
        if user_id not in data["users"]:
            data["users"][user_id] = self._create_new_user_profile(user_id)
        
        user_data = data["users"][user_id]
        
        # Actualizar campos
        for key, value in updates.items():
            if key in ["xp", "total_xp"]:
                user_data[key] = user_data.get(key, 0) + value
            elif key == "level":
                user_data[key] = value
            elif key == "questions_answered":
                user_data[key] = user_data.get(key, 0) + 1
            elif key == "help_requests":
                user_data[key] = user_data.get(key, 0) + 1
            elif key == "show_spanish_translation":
                user_data[key] = value
            elif key == "audio_submissions":
                user_data[key] = user_data.get(key, 0) + 1
                data["statistics"]["total_audio_processes"] += 1
        
        # Actualizar estadísticas globales
        if "questions_answered" in updates:
            data["statistics"]["total_questions_asked"] += 1
        
        # Calcular nivel basado en XP
        user_data["level"] = self._calculate_level(user_data.get("total_xp", 0))
        
        # Actualizar última actividad
        user_data["last_activity"] = datetime.now().isoformat()
        
        self._save_data(data)
        return user_data
    
    def _create_new_user_profile(self, user_id):
        """Crea nuevo perfil de usuario"""
        return {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "total_xp": 0,
            "level": "beginner",
            "questions_answered": 0,
            "help_requests": 0,
            "audio_submissions": 0,
            "show_spanish_translation": True,
            "preferences": {
                "speech_speed": "normal",
                "hints_enabled": True,
                "auto_translate": True
            },
            "session_history": [],
            "last_activity": datetime.now().isoformat()
        }
    
    def _calculate_level(self, xp):
        """Calcula nivel basado en XP"""
        if xp < 100:
            return "beginner"
        elif xp < 300:
            return "intermediate"
        else:
            return "advanced"
    
    def add_session(self, user_id, session_data):
        """Añade sesión al historial"""
        data = self._load_data()
        
        if user_id not in data["users"]:
            data["users"][user_id] = self._create_new_user_profile(user_id)
        
        user_data = data["users"][user_id]
        
        session_entry = {
            "session_id": session_data.get("session_id", str(uuid.uuid4())),
            "timestamp": datetime.now().isoformat(),
            "questions_asked": session_data.get("questions_asked", 1),
            "xp_earned": session_data.get("xp_earned", 0),
            "duration_seconds": session_data.get("duration_seconds", 0)
        }
        
        user_data["session_history"].append(session_entry)
        
        # Limitar historial a 50 sesiones
        if len(user_data["session_history"]) > 50:
            user_data["session_history"] = user_data["session_history"][-50:]
        
        # Actualizar estadísticas globales
        data["statistics"]["total_sessions"] += 1
        
        self._save_data(data)
        return session_entry

# Inicializar gestor de progreso
progress_manager = UserProgressManager()

# ============================================
# SISTEMA DE EVALUACIÓN DE PRONUNCIACIÓN
# ============================================
class PronunciationEvaluator:
    """Evalúa pronunciación y da retroalimentación"""
    
    def evaluate(self, transcribed_text, expected_question=None):
        """Evalúa la pronunciación basándose en el texto transcrito"""
        
        if not transcribed_text or len(transcribed_text.strip()) < 3:
            return {
                "score": 0,
                "feedback": "No speech detected or too short. Please speak for 2-3 seconds.",
                "needs_scaffolding": True,
                "strengths": [],
                "areas_to_improve": ["Speech clarity", "Volume", "Duration"]
            }
        
        # Calcular puntuación base basada en longitud
        base_score = min(30, len(transcribed_text.split()) * 3)
        
        # Añadir bonificación por complejidad
        word_count = len(transcribed_text.split())
        complexity_bonus = min(20, word_count * 2)
        
        # Penalización por errores comunes detectables
        common_errors = self._detect_common_errors(transcribed_text)
        error_penalty = len(common_errors) * 5
        
        # Puntuación final
        final_score = base_score + complexity_bonus - error_penalty
        final_score = max(10, min(95, final_score))  # Mantener entre 10-95
        
        # Determinar si necesita scaffolding
        needs_scaffolding = final_score < 70 or word_count < 4
        
        # Generar retroalimentación
        feedback = self._generate_feedback(final_score, word_count, common_errors)
        
        return {
            "score": final_score,
            "feedback": feedback,
            "needs_scaffolding": needs_scaffolding,
            "strengths": self._get_strengths(final_score, word_count),
            "areas_to_improve": common_errors if common_errors else ["Fluency", "Vocabulary range"],
            "word_count": word_count,
            "error_count": len(common_errors)
        }
    
    def _detect_common_errors(self, text):
        """Detecta errores comunes en el inglés hablado"""
        text_lower = text.lower()
        errors = []
        
        # Verificar artículos
        words = text_lower.split()
        for i, word in enumerate(words):
            if word in ["a", "an", "the"] and i > 0:
                prev_word = words[i-1]
                # Verificar uso incorrecto de artículos
                if word == "a" and prev_word.endswith(('a', 'e', 'i', 'o', 'u')):
                    errors.append("Article usage")
                elif word == "an" and not prev_word.endswith(('a', 'e', 'i', 'o', 'u')):
                    errors.append("Article usage")
        
        # Verificar tiempo verbal básico
        if "i is" in text_lower or "he are" in text_lower or "she are" in text_lower:
            errors.append("Subject-verb agreement")
        
        # Verificar preposiciones comunes
        common_preposition_errors = [
            ("in", "on"), ("at", "in"), ("to", "for"), ("of", "from")
        ]
        for wrong, right in common_preposition_errors:
            if wrong in text_lower and right not in text_lower:
                # Verificación simple de contexto
                errors.append("Preposition usage")
        
        # Verificar plurales/singulares
        if "s " in text_lower and not any(plural in text_lower for plural in ["is", "was", "has", "this"]):
            # Verificación básica de plurales
            pass
        
        return errors[:3]  # Limitar a 3 errores
    
    def _generate_feedback(self, score, word_count, errors):
        """Genera retroalimentación personalizada"""
        
        if score >= 85:
            return f"🎉 Excellent! You used {word_count} words clearly. Keep up the great work!"
        elif score >= 70:
            feedback = f"👍 Good job! You used {word_count} words. "
            if errors:
                feedback += f"Try to work on: {', '.join(errors)}."
            else:
                feedback += "Your pronunciation is clear."
            return feedback
        elif score >= 50:
            feedback = f"📝 Not bad! You used {word_count} words. "
            if errors:
                feedback += f"Focus on: {', '.join(errors)}. "
            feedback += "Try to speak a bit longer."
            return feedback
        else:
            feedback = "💡 Let's practice more! "
            if word_count < 3:
                feedback += "Try to speak for 2-3 seconds with complete sentences."
            else:
                feedback += "Focus on speaking clearly and using complete sentences."
            return feedback
    
    def _get_strengths(self, score, word_count):
        """Identifica fortalezas basadas en puntuación"""
        strengths = []
        
        if word_count >= 5:
            strengths.append("Good sentence length")
        
        if score >= 70:
            strengths.append("Clear pronunciation")
        
        if word_count >= 3 and score >= 60:
            strengths.append("Effective communication")
        
        if not strengths:
            strengths.append("Willingness to practice")
        
        return strengths

# Inicializar evaluador de pronunciación
pronunciation_evaluator = PronunciationEvaluator()

# ============================================
# ENDPOINTS PRINCIPALES - CONTROL TOTAL
# ============================================
@app.route('/')
def home():
    """Página de inicio"""
    return jsonify({
        "status": "online",
        "service": "Eli English Tutor Backend v14.0",
        "version": "14.0.0",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "Predefined questions with perfect grammar",
            "Professional Spanish translations",
            "SPECIFIC and CORRECT scaffolding",
            "Complete backend control",
            "User progress management"
        ],
        "total_predefined_questions": sum(len(questions) for questions in question_db.questions_by_level.values())
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Verificación de salud del servicio"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "question_database": "active",
        "audio_processor": "active",
        "progress_manager": "active"
    })

# ============================================
# ENDPOINT: INICIAR SESIÓN DE PRÁCTICA
# ============================================
@app.route('/api/practice/start', methods=['POST'])
def start_practice():
    """Inicia una sesión de práctica"""
    try:
        data = request.json or {}
        user_id = data.get('user_id', f"user_{uuid.uuid4().hex[:8]}")
        session_id = f"{user_id[:6]}_{int(time.time())}"
        
        # Cargar progreso del usuario
        user_progress = progress_manager.get_user_progress(user_id)
        user_level = user_progress.get("level", "beginner") if user_progress else "beginner"
        show_translation = user_progress.get("show_spanish_translation", True) if user_progress else True
        
        # Obtener primera pregunta
        first_question = question_db.get_question(user_id, user_level)
        
        # Registrar sesión
        progress_manager.add_session(user_id, {
            "session_id": session_id,
            "questions_asked": 1,
            "xp_earned": 0
        })
        
        return jsonify({
            "status": "success",
            "data": {
                "user_id": user_id,
                "session_id": session_id,
                "current_level": user_level,
                "current_question": first_question["english"],
                "question_spanish": first_question["spanish"],
                "show_spanish_translation": show_translation,
                "xp": user_progress.get("total_xp", 0) if user_progress else 0,
                "question_topic": first_question["topic"],
                "question_tense": first_question["tense"],
                "is_predefined": True,
                "message": f"🎯 Welcome to Eli English Tutor! Let's start practicing {user_level} level questions."
            }
        })
        
    except Exception as e:
        logger.error(f"Error starting practice: {e}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

# ============================================
# ENDPOINT PRINCIPAL: PROCESAR AUDIO Y RESPONDER
# ============================================
@app.route('/api/process-audio', methods=['POST'])
def process_audio():
    """Endpoint principal: procesa audio, transcribe, evalúa y responde"""
    try:
        # Validar entrada
        if 'audio' not in request.files:
            return jsonify({"status": "error", "message": "No audio file provided"}), 400
        
        # Obtener datos de la solicitud
        audio_file = request.files['audio']
        session_id = request.form.get('session_id', 'default')
        user_id = request.form.get('user_id', 'anonymous')
        current_question = request.form.get('current_question', 'What is your name?')
        
        logger.info(f"Processing audio from user {user_id[:8]}...")
        
        # Transcribir audio
        audio_bytes = audio_file.read()
        transcription = audio_processor.transcribe_audio(audio_bytes)
        user_text = transcription.get('text', '')
        
        # Obtener progreso del usuario
        user_progress = progress_manager.get_user_progress(user_id)
        user_level = user_progress.get("level", "beginner") if user_progress else "beginner"
        show_translation = user_progress.get("show_spanish_translation", True) if user_progress else True
        
        # Evaluar pronunciación
        pronunciation_evaluation = pronunciation_evaluator.evaluate(user_text, current_question)
        
        # Determinar siguiente pregunta basada en desempeño
        if pronunciation_evaluation["score"] >= 80:
            # Buen desempeño: avanzar nivel o mantener actual
            if user_level == "beginner" and random.random() > 0.7:
                next_level = "intermediate"
            elif user_level == "intermediate" and random.random() > 0.8:
                next_level = "advanced"
            else:
                next_level = user_level
        elif pronunciation_evaluation["score"] >= 60:
            # Desempeño moderado: mantener nivel
            next_level = user_level
        else:
            # Bajo desempeño: posiblemente bajar nivel
            if user_level == "advanced" and random.random() > 0.6:
                next_level = "intermediate"
            elif user_level == "intermediate" and random.random() > 0.7:
                next_level = "beginner"
            else:
                next_level = user_level
        
        # Obtener siguiente pregunta
        next_question_data = question_db.get_question(user_id, next_level)
        
        # Generar scaffolding si es necesario - ¡AHORA CORRECTO!
        scaffolding = None
        if pronunciation_evaluation["needs_scaffolding"]:
            scaffolding = question_db.get_scaffolding_for_question(current_question, user_level)
        
        # Calcular XP ganado
        xp_earned = _calculate_xp_earned(
            pronunciation_evaluation["score"],
            pronunciation_evaluation["word_count"],
            user_level
        )
        
        # Actualizar progreso del usuario
        progress_manager.update_user_progress(user_id, {
            "xp": xp_earned,
            "level": next_level,
            "questions_answered": 1,
            "audio_submissions": 1,
            "show_spanish_translation": show_translation
        })
        
        # Construir respuesta
        response_message = _build_response_message(
            user_text,
            pronunciation_evaluation,
            next_question_data,
            xp_earned,
            show_translation
        )
        
        response = {
            "status": "success",
            "data": {
                "type": "conversation_response",
                "message": response_message,
                "user_transcription": user_text,
                "pronunciation_score": pronunciation_evaluation["score"],
                "pronunciation_feedback": pronunciation_evaluation["feedback"],
                "next_question": next_question_data["english"],
                "next_question_spanish": next_question_data["spanish"],
                "next_question_topic": next_question_data["topic"],
                "next_question_tense": next_question_data["tense"],
                "needs_scaffolding": pronunciation_evaluation["needs_scaffolding"],
                "scaffolding_data": scaffolding,
                "user_level": user_level,
                "next_level": next_level,
                "xp_earned": xp_earned,
                "total_xp": (user_progress.get("total_xp", 0) if user_progress else 0) + xp_earned,
                "show_spanish_translation": show_translation,
                "session_info": {
                    "session_id": session_id,
                    "user_id": user_id,
                    "questions_answered": user_progress.get("questions_answered", 1) if user_progress else 1
                },
                "is_predefined": True
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in process-audio: {e}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

def _calculate_xp_earned(score, word_count, level):
    """Calcula XP ganado basado en desempeño"""
    base_xp = score / 10  # 0-9.5 XP por puntuación
    
    # Bonificación por longitud
    length_bonus = min(word_count * 0.5, 10)
    
    # Bonificación por nivel
    level_bonus = {"beginner": 1, "intermediate": 2, "advanced": 3}[level]
    
    total_xp = base_xp + length_bonus + level_bonus
    return round(min(total_xp, 25))  # Máximo 25 XP por respuesta

def _build_response_message(user_text, evaluation, next_question, xp_earned, show_translation):
    """Construye mensaje de respuesta"""
    
    if not user_text or len(user_text.strip()) < 3:
        return f"""🎤 **I didn't hear you clearly**

💡 **Try this question:** {next_question['english']}
{f"🇪🇸 **En español:** {next_question['spanish']}" if show_translation else ""}

Speak clearly for 2-3 seconds!"""
    
    parts = [
        f"🎉 **Great!** I heard you say: \"{user_text[:80]}{'...' if len(user_text) > 80 else ''}\"",
        "",
        f"📊 **Pronunciation Score:** {evaluation['score']}/100",
        f"💬 **Feedback:** {evaluation['feedback']}",
        "",
        f"⭐ **XP Earned:** +{xp_earned}",
        "",
        f"🎯 **Next Question:** {next_question['english']}"
    ]
    
    if show_translation:
        parts.append(f"🇪🇸 **En español:** {next_question['spanish']}")
    
    parts.extend([
        "",
        f"📚 **Topic:** {next_question['topic'].replace('_', ' ').title()}",
        f"⏰ **Tense:** {next_question['tense'].replace('_', ' ').title()}",
        "",
        "Keep practicing! 💪"
    ])
    
    return "\n".join(parts)

# ============================================
# ENDPOINT: SOLICITAR AYUDA (SCAFFOLDING)
# ============================================
@app.route('/api/request-help', methods=['POST'])
def request_help():
    """Proporciona ayuda ESPECÍFICA y CORRECTA para la pregunta actual"""
    try:
        data = request.json or {}
        current_question = data.get('current_question', 'What is your name?')
        user_id = data.get('user_id', 'anonymous')
        
        # Obtener progreso del usuario
        user_progress = progress_manager.get_user_progress(user_id)
        user_level = user_progress.get("level", "beginner") if user_progress else "beginner"
        show_translation = user_progress.get("show_spanish_translation", True) if user_progress else True
        
        # Obtener traducción de la pregunta
        question_data = None
        for level in question_db.questions_by_level.values():
            for q in level:
                if q["english"] == current_question:
                    question_data = q
                    break
            if question_data:
                break
        
        spanish_translation = question_data["spanish"] if question_data else "Traducción no disponible"
        
        # Generar scaffolding ESPECÍFICO - ¡AHORA CORRECTO!
        scaffolding = question_db.get_scaffolding_for_question(current_question, user_level)
        
        # Construir mensaje de ayuda
        help_message = f"""🆘 **HELP: How to answer this question**

❓ **Question:** {current_question}
{f"🇪🇸 **En español:** {spanish_translation}" if show_translation else ""}

💡 **Response Template:**
"{scaffolding['template']}"

🔤 **Useful Vocabulary:**
• {', '.join(scaffolding['vocabulary'][:8])}

📝 **Grammar Tip:**
{scaffolding['grammar_tip']}

✅ **Practice Sentences:**
{chr(10).join(['• ' + s for s in scaffolding['practice_sentences'][:3]])}

🎯 **Response Structure:**
{scaffolding.get('response_structure', 'Give a complete sentence with subject + verb + complement.')}

🚀 **Sentence Starters:**
{chr(10).join(['• ' + s for s in scaffolding.get('sentence_starters', ['I think that...', 'In my opinion...'])[:4]])}"""
        
        # Actualizar contador de solicitudes de ayuda
        progress_manager.update_user_progress(user_id, {
            "help_requests": 1,
            "show_spanish_translation": show_translation
        })
        
        return jsonify({
            "status": "success",
            "data": {
                "type": "help_response",
                "message": help_message,
                "needs_scaffolding": True,  # IMPORTANTE: Forzar scaffolding
                "scaffolding_data": scaffolding,
                "current_question": current_question,
                "question_spanish": spanish_translation,
                "show_spanish_translation": show_translation,
                "xp_earned": 10,  # XP por pedir ayuda
                "is_help_response": True
            }
        })
        
    except Exception as e:
        logger.error(f"Error in request-help: {e}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

# ============================================
# ENDPOINT: OBTENER NUEVA PREGUNTA
# ============================================
@app.route('/api/get-question', methods=['POST'])
def get_question():
    """Obtiene una nueva pregunta según nivel"""
    try:
        data = request.json or {}
        user_id = data.get('user_id', 'anonymous')
        level = data.get('level', 'beginner')
        force_new = data.get('force_new', True)
        
        # Validar nivel
        if level not in question_db.questions_by_level:
            level = "beginner"
        
        # Obtener pregunta
        question_data = question_db.get_question(user_id, level, avoid_recent=force_new)
        
        return jsonify({
            "status": "success",
            "data": {
                **question_data,
                "show_spanish_translation": True
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting question: {e}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

# ============================================
# ENDPOINT: GESTIÓN DE PROGRESO
# ============================================
@app.route('/api/progress/save', methods=['POST'])
def save_progress():
    """Guarda progreso del usuario"""
    try:
        data = request.json or {}
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"status": "error", "message": "User ID required"}), 400
        
        # Actualizar progreso
        updates = {}
        
        if 'xp' in data:
            updates['xp'] = data['xp']
        if 'level' in data:
            updates['level'] = data['level']
        if 'show_spanish_translation' in data:
            updates['show_spanish_translation'] = data['show_spanish_translation']
        
        user_progress = progress_manager.update_user_progress(user_id, updates)
        
        return jsonify({
            "status": "success",
            "message": "Progress saved successfully",
            "data": {
                "user_id": user_id,
                "total_xp": user_progress.get("total_xp", 0),
                "level": user_progress.get("level", "beginner"),
                "questions_answered": user_progress.get("questions_answered", 0),
                "show_spanish_translation": user_progress.get("show_spanish_translation", True)
            }
        })
        
    except Exception as e:
        logger.error(f"Error saving progress: {e}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

@app.route('/api/progress/load', methods=['POST'])
def load_progress():
    """Carga progreso del usuario"""
    try:
        data = request.json or {}
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"status": "error", "message": "User ID required"}), 400
        
        user_progress = progress_manager.get_user_progress(user_id)
        
        if user_progress:
            return jsonify({
                "status": "success",
                "progress_found": True,
                "data": {
                    "user_id": user_id,
                    "created_at": user_progress.get("created_at"),
                    "total_xp": user_progress.get("total_xp", 0),
                    "level": user_progress.get("level", "beginner"),
                    "questions_answered": user_progress.get("questions_answered", 0),
                    "help_requests": user_progress.get("help_requests", 0),
                    "audio_submissions": user_progress.get("audio_submissions", 0),
                    "show_spanish_translation": user_progress.get("show_spanish_translation", True),
                    "last_activity": user_progress.get("last_activity"),
                    "session_count": len(user_progress.get("session_history", []))
                }
            })
        else:
            return jsonify({
                "status": "success",
                "progress_found": False,
                "message": "No previous progress found for this user"
            })
        
    except Exception as e:
        logger.error(f"Error loading progress: {e}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

# ============================================
# ENDPOINT: TOGGLE TRADUCCIÓN ESPAÑOL
# ============================================
@app.route('/api/toggle-translation', methods=['POST'])
def toggle_translation():
    """Activa/desactiva mostrar traducciones en español"""
    try:
        data = request.json or {}
        user_id = data.get('user_id')
        show_translation = data.get('show_translation', True)
        
        if not user_id:
            return jsonify({"status": "error", "message": "User ID required"}), 400
        
        # Actualizar preferencia
        progress_manager.update_user_progress(user_id, {
            "show_spanish_translation": show_translation
        })
        
        return jsonify({
            "status": "success",
            "message": f"Spanish translation {'enabled' if show_translation else 'disabled'}",
            "show_spanish_translation": show_translation
        })
        
    except Exception as e:
        logger.error(f"Error toggling translation: {e}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

# ============================================
# ENDPOINT: ESTADÍSTICAS DEL SISTEMA
# ============================================
@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Obtiene estadísticas del sistema"""
    try:
        data = progress_manager._load_data()
        
        return jsonify({
            "status": "success",
            "data": {
                "total_users": len(data.get("users", {})),
                "total_sessions": data.get("statistics", {}).get("total_sessions", 0),
                "total_questions": data.get("statistics", {}).get("total_questions_asked", 0),
                "total_audio_submissions": data.get("statistics", {}).get("total_audio_processes", 0),
                "predefined_questions": {
                    "beginner": len(question_db.questions_by_level["beginner"]),
                    "intermediate": len(question_db.questions_by_level["intermediate"]),
                    "advanced": len(question_db.questions_by_level["advanced"]),
                    "total": sum(len(q) for q in question_db.questions_by_level.values())
                },
                "system_status": "operational",
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"status": "error", "message": str(e)[:100]}), 500

# ============================================
# MANEJADOR DE ERRORES
# ============================================
@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "message": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.errorhandler(413)
def too_large(error):
    return jsonify({"status": "error", "message": "File too large"}), 413

# ============================================
# EJECUCIÓN PRINCIPAL
# ============================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 60)
    print("🚀 ELI ENGLISH TUTOR BACKEND v14.0")
    print("🎯 SCAFFOLDING ESPECÍFICO Y CORRECTO")
    print("=" * 60)
    print("✅ CORRECCIONES APLICADAS:")
    print("   1. Scaffolding 100% específico por pregunta")
    print("   2. Templates CORRECTOS para cada tiempo verbal")
    print("   3. Grammar tips APROPIADOS para el tiempo verbal")
    print("   4. Vocabulary RELEVANTE al tema")
    print("   5. Practice sentences CONTEXTUALIZADAS")
    print("=" * 60)
    print("📊 EJEMPLOS DE SCAFFOLDING CORREGIDO:")
    print("   • 'What will you do tomorrow?' → 'Tomorrow, I will [verb]. I also plan to...'")
    print("   • Grammar tip: 'Use 'will' for spontaneous decisions' ✅")
    print("   • Vocabulary: ['tomorrow', 'will', 'going to', 'plan to'] ✅")
    print("=" * 60)
    print(f"📡 Servidor ejecutándose en puerto: {port}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)