# Travel Assistant API - Architecture & Request Flow

## 📋 Table of Contents
1. [High-Level Architecture](#high-level-architecture)
2. [Request Flow Diagram](#request-flow-diagram)
3. [Component Mapping](#component-mapping)
4. [LangChain Integration](#langchain-integration)
5. [Navigation & Routing](#navigation--routing)
6. [Data Flow](#data-flow)
7. [Error Handling Flow](#error-handling-flow)

---

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│  ┌────────────────┐              ┌──────────────────┐           │
│  │  Web Browser   │              │  API Clients     │           │
│  │  (index.html)  │              │  (curl/Postman)  │           │
│  └────────┬───────┘              └────────┬─────────┘           │
└───────────┼──────────────────────────────┼──────────────────────┘
            │                              │
            │ HTTP Requests                │
            ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI APPLICATION                           │
│                         (main.py)                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Middleware Layer                             │  │
│  │  • CORS Middleware (Cross-Origin Resource Sharing)       │  │
│  │  • Request ID Generation                                 │  │
│  │  • JSON Logging                                          │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                        │
│                         ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Router Layer                                 │  │
│  │  • Travel Router (app/routers/travel.py)                 │  │
│  │    - POST /api/travel-assistant                          │  │
│  │  • Root Router (main.py)                                 │  │
│  │    - GET /                                               │  │
│  │    - GET /health                                         │  │
│  └──────────────────────┬───────────────────────────────────┘  │
└────────────────────────┼────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Travel Service (app/services/travel_service.py)  │  │
│  │  • build_travel_prompt()                                 │  │
│  │  • call_model_with_latency()                            │  │
│  │  • generate_comparison()                                │  │
│  │  • process_travel_request() - Main Orchestrator        │  │
│  └──────────────────────┬───────────────────────────────────┘  │
└────────────────────────┼────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  LANGCHAIN INTEGRATION                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │        Gemini Client (app/services/gemini_client.py)     │  │
│  │                                                          │  │
│  │  ┌────────────────────┐    ┌────────────────────┐      │  │
│  │  │  Flash Model       │    │   Pro Model        │      │  │
│  │  │ (ChatGoogleGenAI)  │    │ (ChatGoogleGenAI)  │      │  │
│  │  │                    │    │                    │      │  │
│  │  │ • Temperature: 0.3 │    │ • Temperature: 0.3 │      │  │
│  │  │ • Max Tokens: 2048 │    │ • Max Tokens: 4096 │      │  │
│  │  │ • Fast responses   │    │ • Detailed output  │      │  │
│  │  └────────┬───────────┘    └────────┬───────────┘      │  │
│  └───────────┼──────────────────────────┼──────────────────┘  │
└──────────────┼──────────────────────────┼─────────────────────┘
               │                          │
               │ Parallel Execution       │
               │ (asyncio.gather)         │
               ▼                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GOOGLE GEMINI API                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            models/gemini-flash-latest                     │  │
│  │            models/gemini-pro-latest                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Request Flow Diagram

### **Complete Request-Response Flow**

```
1. CLIENT REQUEST
   │
   │ POST /api/travel-assistant
   │ Content-Type: application/json
   │ Body: {
   │   "destination": "Paris",
   │   "travel_dates": "Dec 1-5, 2025",
   │   "preferences": "culture, food"
   │ }
   ▼
2. FASTAPI ENTRY POINT (main.py)
   │
   ├─► CORS Middleware (validates origin)
   │
   ├─► Request Logging
   │   └─► Generate Request ID (UUID)
   │   └─► log_request() → logs/travel_assistant.log
   │
   ▼
3. ROUTER MATCHING (app/routers/travel.py)
   │
   ├─► URL Pattern Match: /api/travel-assistant
   ├─► HTTP Method Match: POST
   ├─► Request Validation (Pydantic)
   │   └─► TravelRequest model validates:
   │       • destination (required)
   │       • travel_dates (required)
   │       • preferences (required)
   │       • duration_days (optional)
   │       • budget_level (optional)
   │
   ▼
4. ENDPOINT HANDLER (@router.post)
   │
   ├─► Start latency timer
   ├─► Generate/retrieve request_id
   │
   ▼
5. SERVICE LAYER (travel_service.py)
   │
   ├─► process_travel_request(request)
   │   │
   │   ├─► STEP 5.1: Build Prompt
   │   │   └─► build_travel_prompt(request)
   │   │       • Constructs detailed AI prompt
   │   │       • Includes destination, dates, preferences
   │   │       • Adds structured request format
   │   │
   │   ├─► STEP 5.2: Parallel Model Execution
   │   │   └─► asyncio.gather(
   │   │         call_model_with_latency(flash_model, prompt),
   │   │         call_model_with_latency(pro_model, prompt)
   │   │       )
   │   │       │
   │   │       ├─► FLASH MODEL PATH
   │   │       │   ├─► Start timer (time.time())
   │   │       │   ├─► LangChain: flash_model.ainvoke(prompt)
   │   │       │   │   └─► ChatGoogleGenerativeAI wrapper
   │   │       │   │       └─► Google Gemini API call
   │   │       │   ├─► End timer
   │   │       │   ├─► Calculate latency_ms
   │   │       │   └─► log_model_latency("Gemini Flash", latency_ms)
   │   │       │
   │   │       └─► PRO MODEL PATH (parallel)
   │   │           ├─► Start timer (time.time())
   │   │           ├─► LangChain: pro_model.ainvoke(prompt)
   │   │           │   └─► ChatGoogleGenerativeAI wrapper
   │   │           │       └─► Google Gemini API call
   │   │           ├─► End timer
   │   │           ├─► Calculate latency_ms
   │   │           └─► log_model_latency("Gemini Pro", latency_ms)
   │   │
   │   ├─► STEP 5.3: Parse Responses
   │   │   ├─► parse_response_sections(flash_response)
   │   │   │   └─► Extract itinerary, highlights
   │   │   └─► parse_response_sections(pro_response)
   │   │       └─► Extract itinerary, highlights
   │   │
   │   ├─► STEP 5.4: Analyze & Compare
   │   │   └─► generate_comparison(flash_data, pro_data)
   │   │       ├─► analyze_response_characteristics()
   │   │       │   • Word count, char count
   │   │       │   • Structure analysis
   │   │       ├─► Calculate speed difference
   │   │       ├─► Identify strengths
   │   │       └─► Generate recommendation
   │   │
   │   └─► STEP 5.5: Build Response Object
   │       └─► TravelAssistantResponse(
   │             request=request,
   │             flash=ModelResponse(...),
   │             pro=ModelResponse(...),
   │             comparison=ComparisonData(...)
   │           )
   │
   ▼
6. RESPONSE PREPARATION
   │
   ├─► Calculate total latency
   ├─► Log latency metrics
   │   └─► log_info("Latency Metrics Summary", ...)
   │
   ├─► Serialize response (Pydantic → JSON)
   ├─► Log response
   │   └─► log_response(status=200, latency_ms, ...)
   │
   ▼
7. HTTP RESPONSE
   │
   └─► Status: 200 OK
       Content-Type: application/json
       Body: {
         "request": {...},
         "flash": {
           "model": "gemini-flash-latest",
           "latency_ms": 1234,
           "itinerary": "...",
           "highlights": "...",
           "raw_response": "..."
         },
         "pro": {
           "model": "gemini-pro-latest",
           "latency_ms": 2345,
           "itinerary": "...",
           "highlights": "...",
           "raw_response": "..."
         },
         "comparison": {
           "summary": "...",
           "flash_strengths": [...],
           "pro_strengths": [...],
           "recommended_plan": "..."
         }
       }
```

---

## 🗺️ Component Mapping

### **File Structure → Responsibility Mapping**

```
travel-assistant-api/
│
├── main.py ────────────────────► FastAPI App Initialization
│                                  • Creates FastAPI instance
│                                  • Registers routers
│                                  • Configures middleware
│                                  • Defines root endpoints
│
├── app/
│   ├── __init__.py ────────────► Package initialization
│   │
│   ├── config.py ──────────────► Configuration Management
│   │                              • Loads environment variables
│   │                              • Pydantic Settings class
│   │                              • API keys, model names, ports
│   │
│   ├── models.py ──────────────► Data Models (Pydantic)
│   │                              • TravelRequest (input)
│   │                              • ModelResponse (output)
│   │                              • ComparisonData
│   │                              • TravelAssistantResponse
│   │
│   ├── routers/ ───────────────► API Endpoints
│   │   ├── __init__.py
│   │   └── travel.py ──────────► Travel Assistant Endpoint
│   │                              • POST /api/travel-assistant
│   │                              • Request validation
│   │                              • Calls service layer
│   │                              • Logs requests/responses
│   │
│   ├── services/ ──────────────► Business Logic
│   │   ├── __init__.py
│   │   ├── gemini_client.py ───► LangChain Model Initialization
│   │   │                          • flash_model instance
│   │   │                          • pro_model instance
│   │   │                          • ChatGoogleGenerativeAI wrapper
│   │   │
│   │   └── travel_service.py ──► Core Service Logic
│   │                              • build_travel_prompt()
│   │                              • call_model_with_latency()
│   │                              • parse_response_sections()
│   │                              • generate_comparison()
│   │                              • process_travel_request()
│   │
│   ├── utils/ ─────────────────► Utilities
│   │   ├── __init__.py
│   │   └── logging_utils.py ───► Structured Logging
│   │                              • JSON formatter
│   │                              • Request ID correlation
│   │                              • log_request, log_response
│   │                              • log_model_latency
│   │                              • log_error
│   │
│   └── templates/ ─────────────► Frontend
│       └── index.html ─────────► Web UI
│                                  • Travel request form
│                                  • Response display
│                                  • Comparison visualization
│
├── .env ───────────────────────► Environment Variables
│                                  • GOOGLE_API_KEY
│                                  • Optional config overrides
│
├── requirements.txt ───────────► Python Dependencies
│                                  • FastAPI, Uvicorn
│                                  • LangChain packages
│                                  • Google Generative AI
│
└── logs/ ──────────────────────► Application Logs
    └── travel_assistant.log ───► JSON structured logs
```

---

## 🔗 LangChain Integration

### **LangChain Flow in Detail**

```
┌─────────────────────────────────────────────────────────────────┐
│              LANGCHAIN INTEGRATION LAYERS                        │
└─────────────────────────────────────────────────────────────────┘

1. INITIALIZATION PHASE (app/services/gemini_client.py)
   ═══════════════════════════════════════════════════════

   from langchain_google_genai import ChatGoogleGenerativeAI
   
   flash_model = ChatGoogleGenerativeAI(
       model="models/gemini-flash-latest",      ◄── Model identifier
       google_api_key=settings.google_api_key,  ◄── Authentication
       temperature=0.3,                         ◄── Creativity control
       max_output_tokens=2048                   ◄── Response length limit
   )
   
   • ChatGoogleGenerativeAI is a LangChain wrapper class
   • Handles API authentication automatically
   • Manages retry logic and error handling
   • Provides consistent interface across LLM providers


2. INVOCATION PHASE (app/services/travel_service.py)
   ══════════════════════════════════════════════════

   async def call_model_with_latency(model, prompt, model_name):
       │
       ├─► LangChain Method: model.ainvoke(prompt)
       │   │
       │   └─► LangChain Internal Flow:
       │       │
       │       ├─► 1. Prompt Processing
       │       │    └─► Convert string to LangChain Message format
       │       │
       │       ├─► 2. API Request Preparation
       │       │    ├─► Add model configuration (temp, tokens)
       │       │    ├─► Format request for Gemini API
       │       │    └─► Add authentication headers
       │       │
       │       ├─► 3. HTTP Request to Google
       │       │    └─► POST to Gemini API endpoint
       │       │        URL: generativelanguage.googleapis.com/v1beta/models/{model}/generateContent
       │       │
       │       ├─► 4. Response Handling
       │       │    ├─► Parse Gemini API response
       │       │    ├─► Extract generated content
       │       │    ├─► Handle errors/retries
       │       │    └─► Convert to LangChain Message format
       │       │
       │       └─► 5. Return AIMessage object
       │            └─► response.content contains text
       │
       └─► Extract: response_text = response.content


3. PARALLEL EXECUTION (asyncio.gather)
   ════════════════════════════════════

   results = await asyncio.gather(
       call_model_with_latency(flash_model, prompt, "Flash"),
       call_model_with_latency(pro_model, prompt, "Pro"),
       return_exceptions=True
   )
   
   Timeline:
   ────────────────────────────────────────────────
   Time →
   
   T0: Both models called simultaneously
   │
   ├─► Flash Model ──────────────────► Response (1200ms)
   │
   └─► Pro Model ────────────────────────────► Response (2300ms)
   
   T_max: asyncio.gather() waits for slowest (2300ms)
   
   • Both API calls happen concurrently
   • Total wait time = max(flash_latency, pro_latency)
   • NOT flash_latency + pro_latency (sequential)


4. ERROR HANDLING IN LANGCHAIN
   ════════════════════════════

   LangChain automatically handles:
   • Network timeouts
   • Rate limiting (with exponential backoff)
   • API errors (404, 500, etc.)
   • Token limit exceeded
   • Authentication failures
   
   Our wrapper adds:
   • Custom error messages
   • Logging
   • Graceful degradation (one model can fail)
```

### **Why LangChain?**

```
WITHOUT LANGCHAIN:                    WITH LANGCHAIN:
════════════════════                  ═══════════════

❌ Manual HTTP requests               ✅ Simple .ainvoke() method
❌ Handle auth headers                ✅ Auto authentication
❌ Parse JSON responses               ✅ Structured Message objects
❌ Implement retry logic              ✅ Built-in retry with backoff
❌ Error handling                     ✅ Comprehensive error handling
❌ Different code for each LLM        ✅ Same interface for all LLMs
❌ Prompt engineering boilerplate     ✅ Clean prompt handling

Example without LangChain:            Example with LangChain:
────────────────────────              ──────────────────────

import httpx                          response = await model.ainvoke(
                                        "Tell me about Paris"
async with httpx.AsyncClient() as client:  )
    response = await client.post(     print(response.content)
        "https://generativelanguage.googleapis.com/v1beta/models/...",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 2048
            }
        }
    )
    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
```

---

## 🧭 Navigation & Routing

### **URL Routing Table**

```
METHOD │ ENDPOINT                    │ HANDLER                │ PURPOSE
═══════╪════════════════════════════╪═══════════════════════╪═══════════════════════════
GET    │ /                          │ main.root()            │ Serve HTML interface
GET    │ /health                    │ main.health_check()    │ API health status
GET    │ /docs                      │ FastAPI auto           │ Swagger UI documentation
GET    │ /redoc                     │ FastAPI auto           │ ReDoc documentation
POST   │ /api/travel-assistant      │ travel.travel_assist() │ Main AI endpoint
```

### **Request Routing Flow**

```
HTTP Request arrives at server
│
├─► FastAPI receives at main.app
│
├─► Middleware stack (in order):
│   ├─► 1. CORS middleware
│   ├─► 2. Request logging middleware (implicit)
│   └─► 3. Custom logging (in endpoint)
│
├─► Route matching:
│   │
│   ├─► URL path matching
│   │   └─► Uses prefix + route
│   │       Example: "/api" (prefix) + "/travel-assistant" (route)
│   │
│   ├─► HTTP method matching
│   │   └─► @router.post, @router.get, etc.
│   │
│   └─► Parameter validation
│       └─► Pydantic models validate request body
│
├─► Execute endpoint handler
│   └─► Returns response object
│
└─► Response serialization
    └─► Pydantic model → JSON
```

### **Router Registration**

```python
# In main.py:

app = FastAPI()  # Create FastAPI instance

# Register travel router
app.include_router(travel_router)  
# ↓
# This adds all routes from app/routers/travel.py
# with their configured prefix ("/api")

# Routes become:
# - /api/travel-assistant (from travel.py)
```

---

## 📊 Data Flow

### **Request Data Transformation**

```
1. RAW HTTP REQUEST
   POST /api/travel-assistant
   Content-Type: application/json
   {
     "destination": "Paris",
     "travel_dates": "Dec 1-5",
     "preferences": "culture, food"
   }
   │
   ▼
2. FASTAPI VALIDATION
   Pydantic: TravelRequest
   │
   ├─► destination: str = "Paris"
   ├─► travel_dates: str = "Dec 1-5"
   ├─► preferences: str = "culture, food"
   ├─► duration_days: Optional[int] = None
   └─► budget_level: Optional[str] = "medium"
   │
   ▼
3. PROMPT GENERATION
   build_travel_prompt(request) → str
   │
   "You are an expert travel advisor...
    DESTINATION: Paris
    TRAVEL DATES: Dec 1-5
    PREFERENCES: culture, food
    ..."
   │
   ▼
4. LANGCHAIN PROCESSING
   flash_model.ainvoke(prompt)
   │
   ├─► Input: String prompt
   ├─► LangChain converts to: HumanMessage
   ├─► Sends to: Google Gemini API
   ├─► Receives: Gemini response JSON
   └─► Converts to: AIMessage
   │
   ▼
5. RESPONSE EXTRACTION
   response.content → str
   │
   "**Day-by-Day Itinerary**
    Day 1: Arrive in Paris...
    **Must-Visit Attractions**
    - Eiffel Tower..."
   │
   ▼
6. RESPONSE PARSING
   parse_response_sections(response)
   │
   {
     "itinerary": "Day 1: Arrive...",
     "highlights": "- Eiffel Tower..."
   }
   │
   ▼
7. MODEL RESPONSE OBJECT
   ModelResponse(
     model="gemini-flash-latest",
     latency_ms=1234,
     itinerary="...",
     highlights="...",
     raw_response="..."
   )
   │
   ▼
8. COMPARISON GENERATION
   generate_comparison(flash_data, pro_data)
   │
   ComparisonData(
     summary="Flash 45% faster...",
     flash_strengths=["Fast", "Concise"],
     pro_strengths=["Detailed", "Cultural insights"],
     recommended_plan="Use Pro for depth..."
   )
   │
   ▼
9. FINAL RESPONSE OBJECT
   TravelAssistantResponse(
     request=TravelRequest(...),
     flash=ModelResponse(...),
     pro=ModelResponse(...),
     comparison=ComparisonData(...)
   )
   │
   ▼
10. JSON SERIALIZATION
    Pydantic model_dump_json()
    │
    {
      "request": {...},
      "flash": {...},
      "pro": {...},
      "comparison": {...}
    }
    │
    ▼
11. HTTP RESPONSE
    Status: 200 OK
    Content-Type: application/json
    Body: {...}
```

---

## ⚠️ Error Handling Flow

```
ERROR SCENARIOS:
════════════════

1. VALIDATION ERROR
   │
   ├─► Invalid request data
   │   └─► Pydantic ValidationError
   │       └─► FastAPI auto-returns 422 Unprocessable Entity
   │           └─► Response: {"detail": [...validation errors...]}
   │
   └─► Example: Missing required field "destination"

2. SINGLE MODEL FAILURE
   │
   ├─► Flash model fails, Pro succeeds
   │   │
   │   ├─► call_model_with_latency() catches exception
   │   ├─► Returns: (None, None, error_message)
   │   ├─► log_error() logs the failure
   │   │
   │   └─► Response includes:
   │       ├─► flash: ModelResponse with error message
   │       └─► pro: ModelResponse with actual data
   │           └─► comparison: "Pro succeeded, Flash failed"
   │
   └─► User still gets usable response

3. BOTH MODELS FAIL
   │
   ├─► Flash fails AND Pro fails
   │   │
   │   ├─► process_travel_request() raises Exception
   │   ├─► log_error() logs both failures
   │   │
   │   └─► Router catches exception
   │       └─► HTTPException(500, "Both models failed...")
   │           └─► Response: {"detail": "Error message"}
   │
   └─► User gets clear error message

4. NETWORK/TIMEOUT ERROR
   │
   ├─► LangChain handles internally
   │   ├─► Automatic retry with exponential backoff
   │   ├─► Up to 3 retries
   │   │
   │   └─► If all retries fail:
   │       └─► Raises exception
   │           └─► Caught by call_model_with_latency()
   │               └─► Logged and handled gracefully
   │
   └─► Falls into scenario 2 or 3 above

5. API KEY ERROR
   │
   ├─► Invalid GOOGLE_API_KEY
   │   │
   │   └─► Gemini API returns 401 Unauthorized
   │       └─► LangChain raises AuthenticationError
   │           └─► Caught and logged
   │               └─► Returns 500 with descriptive message
   │
   └─► User instructed to check API key

LOGGING CHAIN:
══════════════

Error occurs
│
├─► log_error() called with:
│   ├─► exception object
│   ├─► context string
│   ├─► request_id
│   └─► additional data
│
├─► JSONFormatter formats:
│   {
│     "timestamp": "2025-11-24T...",
│     "level": "ERROR",
│     "request_id": "uuid",
│     "error_type": "NotFound",
│     "error_message": "404 model not found",
│     "context": "call_model_with_latency_Flash",
│     "exception": {
│       "type": "NotFound",
│       "message": "...",
│       "traceback": [...]
│     }
│   }
│
├─► Written to:
│   ├─► Console (stdout)
│   └─► File (logs/travel_assistant.log)
│
└─► Correlated by request_id for tracking
```

---

## 🎯 Key Takeaways

1. **Request Flow**: Client → FastAPI → Router → Service → LangChain → Gemini API
2. **LangChain Role**: Abstracts API complexity, provides retry logic, consistent interface
3. **Parallel Execution**: Both models called simultaneously with `asyncio.gather()`
4. **Error Handling**: Graceful degradation - works if one model fails
5. **Logging**: Structured JSON logs with request correlation
6. **Response Structure**: Pydantic models ensure type safety and auto-validation
7. **Navigation**: FastAPI auto-routes based on decorators and includes

---

## 📚 Related Documentation

- **API Documentation**: http://localhost:8001/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8001/redoc (ReDoc)
- **LangChain Docs**: https://python.langchain.com/docs/integrations/chat/google_generative_ai
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Gemini API**: https://ai.google.dev/docs

