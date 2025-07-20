# AashaAI - Intelligent Emergency Response System 🚨

AashaAI is an AI-powered emergency response system that provides multilingual, intelligent call handling for emergency services. The system uses advanced natural language processing to quickly assess emergencies, gather critical information, and dispatch appropriate services while providing real-time safety guidance.

## 🎯 Project Goals

The primary goal of AashaAI is to revolutionize emergency response by:

- **Reducing Response Time**: Intelligent classification and information gathering to minimize dispatch delays
- **Breaking Language Barriers**: Multi-language support starting with English and Hindi
- **Improving Accuracy**: AI-driven analysis to ensure critical information is captured correctly
- **Providing Immediate Guidance**: Real-time safety instructions while emergency services are en route
- **Enhancing Accessibility**: Voice-first interface accessible to all users regardless of technical literacy

## 📊 Current Project State

### ✅ Implemented Features
- **Bilingual Support**: English and Hindi language support with automatic language selection
- **Intelligent Emergency Classification**: Automatic detection of emergency types (medical, fire, police, disaster)
- **Systematic Information Gathering**: Structured approach to collect location, emergency details, and caller information
- **Real-time AI Responses**: Context-aware responses using Google's Gemini AI
- **Twilio Integration**: Complete voice call handling and speech-to-text processing
- **Service Dispatch Simulation**: Emergency service dispatch confirmation and tracking
- **Ongoing Support**: Continuous assistance until emergency services arrive
- **Call State Management**: In-memory tracking of call progress and information gathered

### 🔧 Architecture
- **Backend**: FastAPI with Python 3.8+
- **AI Engine**: Google Gemini 2.5 Flash for natural language processing
- **Voice Platform**: Twilio Voice API with enhanced speech recognition
- **State Management**: In-memory storage (production-ready Redis integration planned)

## 🚀 Future Roadmap

### Phase 1: Enhanced Logging & Analytics
- **Comprehensive Logging**: Detailed call logs including duration, resolution time, and information accuracy
- **Performance Analytics**: High-level dashboards showing:
  - Average response time by emergency type
  - Most common emergency patterns
  - Language preference statistics
  - Call resolution success rates
  - Geographic emergency distribution
- **Quality Metrics**: AI confidence scores, missed information tracking, and caller satisfaction indicators

### Phase 2: Expanded Language Support
- **Additional Languages**: Support for regional Indian languages (Tamil, Telugu, Bengali, Marathi, Gujarati)
- **Automatic Language Detection**: Smart detection based on caller speech patterns
- **Cultural Context**: Region-specific emergency protocols and cultural sensitivity

### Phase 3: Advanced Features
- **Location Intelligence**: GPS integration and automatic location detection
- **Predictive Analytics**: Emergency pattern recognition and resource allocation optimization
- **Integration APIs**: Hospital, fire department, and police system integrations
- **Mobile Application**: Companion app for emergency contacts and medical information storage

## 🛠️ Setup Instructions

### Prerequisites
- Python 3.8 or higher
- Twilio account with phone number
- Google AI Studio API key
- ngrok or similar tunnel service for local development

### Environment Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/aashaai-emergency-system.git
cd aashaai-emergency-system
```

2. **Create conda environment**
```bash
conda env create -f environment.yml
conda activate aashaai-emergency
```

3. **Configure environment variables**
Create a `.env` file in the root directory:
```bash
# Google AI Configuration
GOOGLE_AI_API_KEY=your_google_ai_api_key_here

# Twilio Configuration  
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# Application Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Future: Database Configuration (when implemented)
# REDIS_URL=redis://localhost:6379
# DATABASE_URL=postgresql://user:pass@localhost/aashaai

# Future: Logging Configuration (when implemented)  
# LOG_LEVEL=INFO
# LOG_FILE_PATH=/var/log/aashaai/app.log
```

4. **Set up Twilio webhook**
- Start the application: `python main.py`
- Use ngrok to expose local server: `ngrok http 8000`
- Configure Twilio webhook URL: `https://your-ngrok-url.ngrok.io/voice`

### Google AI Studio Setup

1. **Get API Key**
   - Visit [Google AI Studio](https://aistudio.google.com/)
   - Create a new project or select existing one
   - Navigate to "Get API Key" 
   - Generate a new API key
   - Copy the key to your `.env` file

2. **Enable Required APIs**
   - Ensure Gemini API access is enabled for your project
   - Set up billing if required for production usage

### Twilio Setup

1. **Account Setup**
   - Create account at [Twilio Console](https://console.twilio.com/)
   - Purchase a phone number with voice capabilities
   - Note down Account SID and Auth Token

2. **Webhook Configuration**
   - Go to Phone Numbers → Manage → Active Numbers
   - Select your Twilio number
   - Set webhook URL for incoming calls to: `https://your-domain.com/voice`
   - Set HTTP method to POST

## 📡 API Endpoints

- `POST /voice` - Initial call handling and language selection
- `POST /set_lang` - Language preference setting  
- `POST /gather_information` - Emergency information collection
- `POST /dispatch_services` - Service dispatch and confirmation
- `POST /ongoing_support` - Continuous caller support
- `GET /call_status/{phone_number}` - Call status monitoring

## 🧪 Testing

### Local Testing
```bash
# Run the application
python main.py

# Test with curl (simulate Twilio webhook)
curl -X POST http://localhost:8000/voice \
  -d "From=+1234567890"
```

### Production Testing
- Call your Twilio number directly
- Test language selection (1 for English, 2 for Hindi)
- Test various emergency scenarios

## 📈 Monitoring & Analytics (Planned)

Future logging will capture:
- **Call Metrics**: Duration, completion rate, abandonment rate
- **Information Quality**: Time to gather required info, accuracy scores
- **Response Effectiveness**: Caller feedback, service dispatch success
- **System Performance**: AI response times, error rates, uptime
- **Usage Patterns**: Peak call times, geographic distribution, emergency types

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)  
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support, email support@aashaai.com or create an issue in this repository.

## ⚠️ Disclaimer

This system is designed to assist emergency services but should not be the sole method of emergency response. Always ensure proper backup communication methods and professional emergency service integration before production deployment.