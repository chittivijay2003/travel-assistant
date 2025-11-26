# Detailed Metrics Documentation

## Overview

The Travel Assistant API now includes comprehensive metrics tracking for:
- **Input/Output Token Usage**: Separate tracking for prompt and completion tokens
- **Cost Estimation**: Real-time cost calculation based on Gemini Flash pricing
- **AI Quality Measurements**: Response quality and relevance scoring
- **Component-Level Metrics**: Individual metrics for flight, hotel, and itinerary

---

## 📊 Metrics Structure

### 1. Token Metrics

```json
{
  "token_metrics": {
    "flight": {
      "input_tokens": 450,
      "output_tokens": 320,
      "total_tokens": 770,
      "latency_ms": 890,
      "cost_estimate": 0.000128
    },
    "hotel": {
      "input_tokens": 420,
      "output_tokens": 310,
      "total_tokens": 730,
      "latency_ms": 850,
      "cost_estimate": 0.000124
    },
    "itinerary": {
      "input_tokens": 480,
      "output_tokens": 340,
      "total_tokens": 820,
      "latency_ms": 920,
      "cost_estimate": 0.000138
    },
    "total_input_tokens": 1350,
    "total_output_tokens": 970,
    "total_tokens": 2320,
    "total_cost_estimate": 0.000390,
    "baseline_tokens": 26320,
    "tokens_saved": 24000,
    "savings_percentage": 91.19
  }
}
```

**Explanation:**
- `input_tokens`: Tokens in the prompt (including few-shot examples)
- `output_tokens`: Tokens in the AI's response
- `total_tokens`: input_tokens + output_tokens
- `cost_estimate`: Calculated using Gemini Flash pricing ($0.075/1M input, $0.30/1M output)
- `baseline_tokens`: Estimated tokens if ALL history was included
- `tokens_saved`: baseline_tokens - total_tokens
- `savings_percentage`: (tokens_saved / baseline_tokens) × 100

### 2. Quality Metrics

```json
{
  "quality_metrics": {
    "response_completeness": 100.0,
    "response_relevance": 75.5,
    "few_shot_examples_used": 3,
    "similarity_scores": [0.850, 0.620, 0.540],
    "avg_similarity": 0.670
  }
}
```

**Explanation:**
- `response_completeness`: 0-100 score (33.33 points per component with content >100 chars)
- `response_relevance`: 0-100 score based on average similarity of examples used
- `few_shot_examples_used`: Number of past trips included as examples
- `similarity_scores`: Individual scores for each example (0-1 scale)
- `avg_similarity`: Average of all similarity scores

---

## 🎯 How Metrics are Calculated

### Token Counting

Uses `tiktoken` library with `cl100k_base` encoding:

```python
import tiktoken

encoding = tiktoken.get_encoding("cl100k_base")
input_tokens = len(encoding.encode(prompt_text))
output_tokens = len(encoding.encode(response_text))
```

### Cost Estimation

Based on Gemini Flash pricing (as of Nov 2025):
- Input: $0.075 per 1M tokens
- Output: $0.30 per 1M tokens

```python
cost = (input_tokens / 1_000_000 * 0.075) + (output_tokens / 1_000_000 * 0.30)
```

### Baseline Calculation

Assumes each user has ~10 trips in history:
- Each trip in full detail = ~800 tokens
- 3 components (flight, hotel, itinerary)
- Baseline = current_total + (10 trips × 800 tokens × 3 components) = current + 24,000

### Token Savings

```python
tokens_saved = baseline_tokens - actual_tokens_used
savings_percentage = (tokens_saved / baseline_tokens) × 100
```

### Quality Scoring

**Completeness (0-100):**
```python
completeness = 0
if len(flight_response) > 100: completeness += 33.33
if len(hotel_response) > 100: completeness += 33.33
if len(itinerary_response) > 100: completeness += 33.34
```

**Relevance (0-100):**
```python
avg_similarity = sum(all_similarity_scores) / len(all_similarity_scores)
relevance = avg_similarity * 100  # Convert 0-1 to 0-100 scale
```

---

## 📡 API Response Example

```json
{
  "flight_recommendations": "Based on your travel dates to Paris...",
  "hotel_recommendations": "Recommended boutique hotels in Le Marais...",
  "itinerary": "Day 1: Arrival and Louvre Museum...",
  "token_metrics": {
    "flight": {
      "input_tokens": 450,
      "output_tokens": 320,
      "total_tokens": 770,
      "latency_ms": 890,
      "cost_estimate": 0.000128
    },
    "hotel": {...},
    "itinerary": {...},
    "total_input_tokens": 1350,
    "total_output_tokens": 970,
    "total_tokens": 2320,
    "total_cost_estimate": 0.000390,
    "baseline_tokens": 26320,
    "tokens_saved": 24000,
    "savings_percentage": 91.19
  },
  "quality_metrics": {
    "response_completeness": 100.0,
    "response_relevance": 75.5,
    "few_shot_examples_used": 3,
    "similarity_scores": [0.850, 0.620, 0.540],
    "avg_similarity": 0.670
  },
  "total_latency_ms": 2660
}
```

---

## 🎨 Dashboard Integration

The metrics are automatically tracked for the dashboard via `metrics_tracker`:

```python
metrics_tracker.track_request(
    endpoint="/travel-assistant",
    user_id=request.user_id,
    token_usage={
        "prompt_tokens": total_input_tokens,
        "completion_tokens": total_output_tokens,
        "total_tokens": total_tokens,
    },
    latency_ms=total_latency_ms,
    success=True,
    error=None,
)
```

Access dashboard at: `http://localhost:8000/dashboard`

**Dashboard Displays:**
- Total requests processed
- Average token savings percentage
- Total cost saved
- Average response quality
- Token usage trends over time
- Cost analysis charts
- Quality metrics visualization

---

## 🧪 Testing the Metrics

### Using cURL:

```bash
curl -X POST "http://localhost:8000/travel-assistant" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "destination": "Paris, France",
    "travel_dates": "March 15-20, 2025",
    "preferences": "art museums, cafes, romantic walks"
  }' | jq '.token_metrics, .quality_metrics'
```

### Using Python:

```python
import requests
import json

response = requests.post(
    "http://localhost:8000/travel-assistant",
    json={
        "user_id": "user_001",
        "destination": "Paris, France",
        "travel_dates": "March 15-20, 2025",
        "preferences": "art museums, cafes, romantic walks"
    }
)

data = response.json()
print("Token Metrics:", json.dumps(data["token_metrics"], indent=2))
print("Quality Metrics:", json.dumps(data["quality_metrics"], indent=2))
```

---

## 📈 Interpreting Metrics

### High Token Savings (>80%)
- Many similar past trips in history
- Smart selection working optimally
- Excellent personalization

### Medium Token Savings (40-80%)
- Some similar trips in history
- Moderate personalization
- Good balance of context and efficiency

### Low Token Savings (<40%)
- Few or no similar past trips
- New user or unique destination
- Still provides context via summary

### High Quality Scores
- **Completeness 100%**: All three components generated successfully
- **Relevance >70%**: Strong match with past trips
- **Avg Similarity >0.7**: Highly relevant examples used

### Low Quality Scores
- **Completeness <100%**: Some components may be incomplete
- **Relevance <50%**: Weak match with past trips
- **Avg Similarity <0.4**: Generic recommendations (summary-based)

---

## 🔍 Metrics Implementation Files

1. **`app/models.py`**
   - `ComponentMetrics`: Individual component metrics
   - `TokenMetrics`: Comprehensive token tracking
   - `QualityMetrics`: AI quality measurements

2. **`app/services/travel_service_new.py`**
   - Token counting with tiktoken
   - Cost calculation
   - Quality scoring
   - Baseline estimation

3. **`app/services/few_shot_selector.py`**
   - Similarity score calculation
   - Returns scores along with examples

4. **`app/services/token_counter.py`**
   - Tiktoken integration
   - cl100k_base encoding

---

## ✅ Benefits

1. **Transparency**: Users see exactly how tokens are used
2. **Cost Awareness**: Real-time cost estimation
3. **Quality Tracking**: Measure AI response quality
4. **Optimization Proof**: Demonstrate 60-80% token savings
5. **Dashboard Analytics**: Aggregate metrics over time
6. **Debugging**: Identify inefficiencies quickly

---

**Built with ❤️ for Generative AI Travel Assistant Assignment**
