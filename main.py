from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv
from google import genai
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional

load_dotenv()
genai_client = genai.Client()

# Store call state (in production, use Redis or database)
CALL_STATE = {}  # {phone_number: {lang, emergency_type, location, severity, caller_info, stage, questions_asked}}

# Emergency types and their priorities
EMERGENCY_TYPES = {
    "medical": {"priority": 1, "keywords": ["heart", "breathing", "chest pain", "unconscious", "bleeding", "accident", "injured", "sick", "doctor", "hospital", "ambulance", "pain", "hurt"]},
    "fire": {"priority": 2, "keywords": ["fire", "smoke", "burning", "explosion", "gas leak", "flames", "burn"]},
    "police": {"priority": 3, "keywords": ["crime", "theft", "violence", "fight", "robbery", "assault", "domestic", "kidnap", "threat", "attack"]},
    "disaster": {"priority": 1, "keywords": ["flood", "earthquake", "cyclone", "building collapse", "landslide", "trapped", "storm"]}
}

# Required information for dispatch
REQUIRED_INFO = {
    "location": {"asked": False, "obtained": False, "value": None},
    "emergency_type": {"asked": False, "obtained": False, "value": None},
    "caller_condition": {"asked": False, "obtained": False, "value": None},
    "people_involved": {"asked": False, "obtained": False, "value": None}
}

# System prompts for different stages
SYSTEM_PROMPTS = {
    "emergency_classifier": """You are AashaAI emergency classifier. Analyze the caller's input and determine:

1. Emergency type: medical, fire, police, disaster, or unknown
2. If location information is mentioned (address, landmark, area name)
3. If caller's condition is clear (are they the victim or someone else)
4. If number of people affected is mentioned

Respond in JSON format:
{
    "emergency_type": "medical|fire|police|disaster|unknown",
    "location_mentioned": true/false,
    "location_details": "any location info found or null",
    "caller_condition": "victim|witness|family|unknown",
    "people_count": "number mentioned or unknown",
    "confidence": "high|medium|low"
}

Only classify what you're confident about. If unclear, mark as unknown.""",

    "location_questioner": """You are AashaAI location specialist. Your job is to get the exact emergency location.

Be direct and urgent:
- Ask for specific address, building name, landmark
- If they don't know exact address, ask for nearby landmarks, main roads
- Ask which city/area they are in
- Ask floor number if it's a building
- Be persistent but supportive

Sample questions in English:
"What is your exact location? Please give me the address."
"Which area or landmark are you near?"
"What city are you calling from?"

Sample questions in Hindi:
"आपका सटीक स्थान क्या है? कृपया पता बताएं।"
"आप किस इलाके या लैंडमार्क के पास हैं?"
"आप किस शहर से कॉल कर रहे हैं?"

Keep responses under 30 words. Be urgent but reassuring.""",

    "emergency_details_questioner": """You are AashaAI emergency details specialist. Get specific emergency information:

For medical: "What exactly happened? Is the person conscious? Are they breathing?"
For fire: "Is anyone trapped? How big is the fire? Can you safely evacuate?"
For police: "What is happening right now? Are you in immediate danger?"
For disaster: "What type of disaster? Are you trapped? How many people are affected?"

In Hindi:
For medical: "क्या हुआ था? व्यक्ति होश में है? सांस ले रहे हैं?"
For fire: "कोई फंसा है? आग कितनी बड़ी है? सुरक्षित बाहर निकल सकते हैं?"
For police: "अभी क्या हो रहा है? आप तत्काल खतरे में हैं?"
For disaster: "किस प्रकार की आपदा? फंसे हैं? कितने लोग प्रभावित हैं?"

Ask ONE specific question. Be direct and urgent.""",

    "dispatch_coordinator": """You are AashaAI dispatch coordinator. You have all required information. 

Confirm the dispatch:
1. Summarize: emergency type, location, people involved
2. Confirm emergency services are being sent
3. Give initial safety instructions
4. Keep caller on line

English format: "I'm dispatching [service type] to [location] for [emergency type]. Stay on the line. [Safety instruction]."
Hindi format: "मैं [location] पर [emergency type] के लिए [service type] भेज रहा हूं। लाइन पर रहें। [Safety instruction]।"

Keep under 50 words.""",

    "safety_instructor": """You are AashaAI safety instructor. Give immediate life-saving instructions while emergency services arrive.

MEDICAL: Check breathing, control bleeding, keep conscious, recovery position
FIRE: Get out safely, stay low, don't use elevator, meet outside
POLICE: Stay safe, don't confront, observe details, find secure location  
DISASTER: Don't enter damaged areas, signal for help, conserve energy

Give ONE clear instruction at a time. Keep responses under 40 words."""
}

app = FastAPI()

def get_ai_response(user_input: str, system_prompt: str, language: str = "en", context: str = "") -> str:
    """Get AI response with specific system prompt"""
    full_prompt = f"""Language: Respond in {language}
{system_prompt}

Context: {context}
User Input: {user_input}

Keep response under 50 words for voice calls. Be direct and urgent for emergencies."""
    
    try:
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"AI Error: {e}")
        return "मुझे समझने में समस्या हो रही है। कृपया दोबारा बताएं।" if language == "hi" else "I'm having trouble understanding. Please repeat."

def analyze_emergency_input(speech_input: str, language: str = "en") -> Dict[str, Any]:
    """Analyze emergency input for classification and information extraction"""
    try:
        response = get_ai_response(speech_input, SYSTEM_PROMPTS["emergency_classifier"], language)
        if "{" in response and "}" in response:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
    except Exception as e:
        print(f"Analysis error: {e}")
    
    # Fallback keyword detection
    for emergency_type, data in EMERGENCY_TYPES.items():
        for keyword in data["keywords"]:
            if keyword.lower() in speech_input.lower():
                return {
                    "emergency_type": emergency_type,
                    "location_mentioned": "address" in speech_input.lower() or "location" in speech_input.lower(),
                    "location_details": None,
                    "caller_condition": "unknown",
                    "people_count": "unknown",
                    "confidence": "medium"
                }
    
    return {
        "emergency_type": "unknown",
        "location_mentioned": False,
        "location_details": None,
        "caller_condition": "unknown",
        "people_count": "unknown",
        "confidence": "low"
    }

def get_next_required_question(call_state: Dict) -> str:
    """Determine what critical information is still needed"""
    required = call_state.get("required_info", REQUIRED_INFO.copy())
    
    # Priority order: location first, then emergency type, then details
    if not required["location"]["obtained"]:
        return "location"
    elif not required["emergency_type"]["obtained"]:
        return "emergency_type"
    elif not required["caller_condition"]["obtained"]:
        return "caller_condition"
    elif not required["people_involved"]["obtained"]:
        return "people_involved"
    else:
        return "dispatch_ready"

def update_required_info(call_state: Dict, speech_input: str, analysis: Dict):
    """Update what information we have obtained"""
    required = call_state.setdefault("required_info", REQUIRED_INFO.copy())
    
    # Check location
    if analysis.get("location_mentioned") or analysis.get("location_details"):
        required["location"]["obtained"] = True
        required["location"]["value"] = analysis.get("location_details") or "mentioned in call"
    
    # Check emergency type
    if analysis.get("emergency_type") != "unknown":
        required["emergency_type"]["obtained"] = True
        required["emergency_type"]["value"] = analysis.get("emergency_type")
    
    # Check caller condition
    if analysis.get("caller_condition") != "unknown":
        required["caller_condition"]["obtained"] = True
        required["caller_condition"]["value"] = analysis.get("caller_condition")
    
    # Check people count
    if analysis.get("people_count") != "unknown":
        required["people_involved"]["obtained"] = True
        required["people_involved"]["value"] = analysis.get("people_count")

@app.post("/voice", response_class=PlainTextResponse)
async def voice(From: str = Form(...)):
    """Initial call handling with language selection"""
    resp = VoiceResponse()
    
    # Initialize call state
    CALL_STATE[From] = {
        "stage": "language_selection",
        "start_time": datetime.now().isoformat(),
        "lang": None,
        "required_info": REQUIRED_INFO.copy(),
        "questions_asked": 0
    }
    
    gather = Gather(numDigits=1, action="/set_lang", timeout=8)
    gather.say(
        "आपातकालीन सेवाएं। आशा एआई। "
        "अंग्रेजी के लिए 1 दबाएं। हिंदी के लिए 2 दबाएं। "
        "Emergency services. AashaAI. Press 1 for English. Press 2 for Hindi.",
        language="hi-IN"
    )
    resp.append(gather)
    
    # Default to Hindi if no input
    resp.redirect("/emergency_start?lang=hi")
    return str(resp)

@app.post("/set_lang", response_class=PlainTextResponse)
async def set_lang(From: str = Form(...), Digits: str = Form(None)):
    """Set language and start emergency protocol"""
    resp = VoiceResponse()
    choice = (Digits or "").strip()
    
    if choice == "1":
        lang_code, lang_short = "en-US", "en"
        greeting = "Emergency services. What is your emergency and where are you located?"
    else:
        lang_code, lang_short = "hi-IN", "hi"
        greeting = "आपातकालीन सेवाएं। आपकी आपातकालीन स्थिति क्या है और आप कहाँ हैं?"

    CALL_STATE[From]["lang"] = {"code": lang_code, "short": lang_short}
    CALL_STATE[From]["stage"] = "information_gathering"
    
    resp.say(greeting, language=lang_code)

    gather = Gather(
        input="speech", 
        action="/gather_information", 
        speechTimeout="auto", 
        timeout=10, 
        language=lang_code,
        enhanced="true"
    )
    resp.append(gather)
    
    return str(resp)

@app.post("/gather_information", response_class=PlainTextResponse)
async def gather_information(From: str = Form(...), SpeechResult: str = Form(None)):
    """Systematically gather all required emergency information"""
    resp = VoiceResponse()
    
    call_state = CALL_STATE.get(From, {})
    lang_code = call_state.get("lang", {}).get("code", "en-US")
    lang_short = call_state.get("lang", {}).get("short", "en")
    
    if not SpeechResult:
        resp.say("कृपया स्पष्ट रूप से बताएं। मैं सुन रहा हूँ।" if lang_short == "hi" else "Please speak clearly. I'm listening.", language=lang_code)
        gather = Gather(input="speech", action="/gather_information", speechTimeout="auto", timeout=10, language=lang_code)
        resp.append(gather)
        return str(resp)

    print(f"Information gathering from {From}: {SpeechResult}")
    
    # Analyze the input
    analysis = analyze_emergency_input(SpeechResult, lang_short)
    
    # Update what information we have
    update_required_info(call_state, SpeechResult, analysis)
    call_state["questions_asked"] += 1
    
    # Determine what we still need
    next_needed = get_next_required_question(call_state)
    
    if next_needed == "dispatch_ready":
        # We have all required info - dispatch services
        resp.redirect("/dispatch_services")
        return str(resp)
    
    # Ask for missing information
    context = f"Already asked {call_state['questions_asked']} questions. Need: {next_needed}"
    
    if next_needed == "location":
        question_response = get_ai_response(
            f"Need exact location. Caller said: {SpeechResult}", 
            SYSTEM_PROMPTS["location_questioner"], 
            lang_short, 
            context
        )
    elif next_needed == "emergency_type":
        if lang_short == "hi":
            question_response = "आपकी आपातकालीन स्थिति क्या है? मेडिकल, आग, पुलिस, या कोई और समस्या?"
        else:
            question_response = "What type of emergency is this? Medical, fire, police, or other?"
    elif next_needed == "caller_condition":
        question_response = get_ai_response(
            f"Need to know caller's relation to emergency: {SpeechResult}",
            SYSTEM_PROMPTS["emergency_details_questioner"],
            lang_short,
            context
        )
    else:
        question_response = get_ai_response(
            SpeechResult,
            SYSTEM_PROMPTS["emergency_details_questioner"],
            lang_short,
            context
        )
    
    resp.say(question_response, language=lang_code)
    
    # Continue gathering information
    gather = Gather(
        input="speech", 
        action="/gather_information", 
        speechTimeout="auto", 
        timeout=15, 
        language=lang_code
    )
    resp.append(gather)
    
    return str(resp)

@app.post("/dispatch_services", response_class=PlainTextResponse)
async def dispatch_services(From: str = Form(...)):
    """Dispatch emergency services and provide ongoing support"""
    resp = VoiceResponse()
    
    call_state = CALL_STATE.get(From, {})
    lang_code = call_state.get("lang", {}).get("code", "en-US")
    lang_short = call_state.get("lang", {}).get("short", "en")
    required = call_state.get("required_info", {})
    
    # Create dispatch confirmation
    emergency_type = required.get("emergency_type", {}).get("value", "emergency")
    location = required.get("location", {}).get("value", "your location")
    
    dispatch_context = f"Emergency: {emergency_type}, Location: {location}"
    
    dispatch_message = get_ai_response(
        dispatch_context,
        SYSTEM_PROMPTS["dispatch_coordinator"],
        lang_short
    )
    
    call_state["stage"] = "services_dispatched"
    resp.say(dispatch_message, language=lang_code)
    
    # Provide initial safety instructions
    safety_instruction = get_ai_response(
        f"Emergency type: {emergency_type}",
        SYSTEM_PROMPTS["safety_instructor"],
        lang_short
    )
    
    resp.say(safety_instruction, language=lang_code)
    
    # Keep line open for ongoing support
    gather = Gather(
        input="speech", 
        action="/ongoing_support", 
        speechTimeout="auto", 
        timeout=20, 
        language=lang_code
    )
    gather.say(
        "सेवाएं आ रही हैं। कोई अपडेट है?" if lang_short == "hi" else "Help is on the way. Any updates?",
        language=lang_code
    )
    resp.append(gather)
    
    return str(resp)

@app.post("/ongoing_support", response_class=PlainTextResponse)
async def ongoing_support(From: str = Form(...), SpeechResult: str = Form(None)):
    """Provide ongoing support until emergency services arrive"""
    resp = VoiceResponse()
    
    call_state = CALL_STATE.get(From, {})
    lang_code = call_state.get("lang", {}).get("code", "en-US")
    lang_short = call_state.get("lang", {}).get("short", "en")
    emergency_type = call_state.get("required_info", {}).get("emergency_type", {}).get("value", "medical")
    
    if SpeechResult:
        # Provide appropriate guidance
        support_response = get_ai_response(
            f"Ongoing emergency support needed. Update: {SpeechResult}",
            SYSTEM_PROMPTS["safety_instructor"],
            lang_short,
            f"Emergency type: {emergency_type}, Services already dispatched"
        )
        resp.say(support_response, language=lang_code)
        
        print(f"Ongoing support to {From}: {SpeechResult} -> {support_response}")
    
    # Continue support
    gather = Gather(
        input="speech", 
        action="/ongoing_support", 
        speechTimeout="auto", 
        timeout=30, 
        language=lang_code
    )
    gather.say(
        "मैं यहाँ हूँ। कुछ और?" if lang_short == "hi" else "I'm here. Anything else?",
        language=lang_code
    )
    resp.append(gather)
    
    resp.say(
        "आपातकालीन सेवाएं पहुँचने वाली हैं। सुरक्षित रहें।" if lang_short == "hi" else "Emergency services should arrive soon. Stay safe.",
        language=lang_code
    )
    resp.hangup()
    
    return str(resp)

@app.get("/call_status/{phone_number}")
async def get_call_status(phone_number: str):
    """API endpoint to get current call status"""
    return CALL_STATE.get(phone_number, {"status": "no active call"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)