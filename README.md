# 🌍 Travel Assistant API

Intelligent travel planning powered by Google Gemini AI and dynamic few-shot learning.

## ✨ Features

- **AI Travel Recommendations**: Flights, hotels, and itineraries using Google Gemini 2.5 Flash
- **Dynamic Few-Shot Learning**: Personalized responses from travel history
- **LangChain Templates**: Three specialized prompt templates
- **Token Optimization**: 60-80% token savings
- **Fast Response Caching**: Quick results for popular destinations

## 🚀 Quick Start

**Prerequisites**: Python 3.13+ and [Google Gemini API key](https://aistudio.google.com/apikey)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API key
echo 'GOOGLE_API_KEY=your_key_here' > .env

# 3. Run server
python -m uvicorn main:app --reload
```

**Server**: http://localhost:8000  
**API Docs**: http://localhost:8000/docs  
**Dashboard**: http://localhost:8000/dashboard/

### Test Request

```bash
curl -X POST http://localhost:8000/travel-assistant \
  -H "Content-Type: application/json" \
  -d '{"destination":"Paris","travel_dates":"June 2025","preferences":"museums"}'
```

---

## 📋 API Reference

**Endpoint**: `POST /travel-assistant`

**Request**:
```json
{
  "destination": "Paris, France",
  "travel_dates": "June 1-10, 2025",
  "preferences": "museums and food",
  "user_id": "guest_user"  // Optional
}
```

**Response**:
```json
{
  "flight_recommendations": "...",
  "hotel_recommendations": "...",
  "itinerary": "...",
  "token_usage": 1234,
  "latency_ms": 10500,
  "prompt_templates": {...},
  "selected_few_shot_examples": [...]
}
```

---

## 🧠 How It Works

**Dynamic Few-Shot Learning Pipeline**:
1. Retrieve user's travel history
2. Calculate similarity scores with current request
3. Select most relevant past trips as examples
4. Inject examples into AI prompts
5. Generate personalized recommendations

**Parallel Processing**: Three components (flights, hotels, itinerary) run simultaneously using `asyncio.gather()` for ~10-15 second total response time.

---

## 📁 Project Structure

```
travel-assistant/
├── app/
│   ├── config.py                    # API configuration
│   ├── models.py                    # Request/response models
│   ├── routers/
│   │   ├── travel.py                # Main API endpoint
│   │   └── dashboard.py             # Dashboard endpoints
│   ├── services/
│   │   ├── gemini_client.py         # Google Gemini AI client
│   │   ├── prompt_templates.py      # LangChain templates
│   │   ├── few_shot_selector.py     # Smart example selection
│   │   ├── user_history.py          # User history management
│   │   ├── token_counter.py         # Token tracking
│   │   └── travel_service_new.py    # Main service logic
│   ├── data/
│   │   ├── user_history.json        # User travel history
│   │   └── example_cache.json       # Cached examples
│   └── templates/
│       ├── index.html               # Landing page
│       └── dashboard.html           # Metrics dashboard
├── .env                              # API key configuration
├── .env.example                      # Environment template
├── main.py                           # FastAPI application
├── test.py                           # Test suite
├── requirements.txt                  # Dependencies
└── README.md                         # This file
```

---

## 🧪 Testing

```bash
python test.py
```

**Tests verify**: Response structure, token usage, latency, and validation errors.

**Expected output**: `Tests Passed: 3/3`

---

## 📊 Performance Metrics

### Token Optimization
- **Without optimization**: ~5000 tokens per request
- **With smart selection**: ~2000 tokens per request
- **Savings**: 60-80% for users with travel history

### Response Times
- **User history load**: ~5ms
- **Similarity calculation**: ~10ms per trip
- **AI generation**: ~10-15 seconds (3 parallel calls)
- **Total**: ~10-15 seconds end-to-end

---

## 🎯 Key Technical Concepts

### LangChain Prompt Templates
Reusable, structured prompts with dynamic variable injection:
```python
template = PromptTemplate(
    input_variables=["destination", "travel_dates", "preferences"],
    template="You are an expert travel planner. Plan a trip to {destination}..."
)
```

### Few-Shot Learning
Teaching AI by example instead of instructions:
```
Example (from past trip):
"User requested Paris, liked museums and food, rated 5/5"

Current request:
"Plan trip to Rome with museums and food"

AI learns: Similar interests → Apply successful patterns
```

### Similarity Scoring
Matching current request with past trips:
- **Destination match**: 40% weight
- **Preferences overlap**: 40% weight
- **Satisfaction rating**: 20% weight

**Score > 0.7**: Use full trip details  
**Score 0.4-0.7**: Use condensed summary  
**Score < 0.4**: Use general preferences only

---

## 🛠️ Configuration

### Environment Variables

Create `.env` file:
```bash
# Required
GOOGLE_API_KEY=your_actual_api_key_here

# Optional
API_PORT=8000
API_HOST=0.0.0.0
API_DEBUG=False
```

### Model Configuration

Default settings in `app/config.py`:
- **Model**: gemini-2.5-flash
- **Temperature**: 0.7
- **Max tokens**: 2048

---

## 🔗 Resources

- **API Docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8000/dashboard/
- [Google Gemini](https://ai.google.dev/) | [FastAPI](https://fastapi.tiangolo.com/) | [LangChain](https://python.langchain.com/)

---

**Author**: Chitti Vijay | **Repository**: [github.com/chittivijay2003/travel-assistant](https://github.com/chittivijay2003/travel-assistant)
