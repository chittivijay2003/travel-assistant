"""Travel Service - Business Logic Layer.

This module handles the core business logic for the Travel Assistant API:
- Building detailed travel prompts
- Calling Gemini models in parallel with latency tracking via LangChain
- Comparing model responses with multiple metrics
- Error handling for partial failures
"""

import time
import asyncio
import re
from typing import Tuple, Optional, Dict
from app.models import (
    TravelRequest,
    TravelAssistantResponse,
    ModelResponse,
    ComparisonData,
)
from app.services.gemini_client import flash_model, pro_model
from app.utils.logging_utils import (
    log_model_latency,
    log_error,
)


def build_travel_prompt(request: TravelRequest) -> str:
    """Build a comprehensive, detailed travel planning prompt.

    Args:
        request: TravelRequest with destination, travel_dates, and preferences

    Returns:
        str: Detailed prompt for the AI model
    """
    prompt = f"""You are an expert travel advisor with deep knowledge of global destinations, 
local cultures, and travel planning. Create a comprehensive, personalized travel itinerary.

📍 DESTINATION: {request.destination}
📅 TRAVEL DATES: {request.travel_dates}
❤️ PREFERENCES: {request.preferences}

Please provide a detailed itinerary including:

1. **Day-by-Day Itinerary**
   - Organized by day with morning, afternoon, and evening activities
   - Realistic timing and distances between locations
   - Mix of must-see attractions and hidden gems
   - Align activities with the traveler's stated preferences

2. **Must-Visit Attractions**
   - Top landmarks and cultural sites
   - Best times to visit (to avoid crowds)
   - Estimated costs and ticket information
   - Insider tips for each attraction

3. **Culinary Recommendations**
   - Local specialties and signature dishes aligned with preferences
   - Recommended restaurants (budget-friendly to fine dining based on budget level)
   - Street food spots and local markets
   - Dining etiquette tips

4. **Cultural Tips & Etiquette**
   - Local customs and traditions
   - Dos and don'ts
   - Basic phrases in local language
   - Dress codes for religious/cultural sites
   - Tipping practices

5. **Transportation & Logistics**
   - How to get around (metro, bus, taxi, walking)
   - Transportation passes or cards to consider
   - Airport/station transfer options
   - Apps useful for navigation

6. **Budget Guidance**
   - Estimated daily costs (accommodation, food, activities)
   - Money-saving tips
   - Best areas to stay based on budget level
   - Currency and payment tips

7. **Practical Tips**
   - Best SIM card/internet options
   - Safety considerations
   - Weather considerations for the travel dates
   - Packing suggestions
   - Emergency contacts

Make your recommendations specific, practical, and tailored to the traveler's profile and stated preferences. 
Include personal insights and insider tips where relevant."""

    return prompt


async def call_model_with_latency(
    model, prompt: str, model_name: str
) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """Call a Gemini model via LangChain and measure response time with error handling.

    Args:
        model: The LangChain ChatGoogleGenerativeAI instance
        prompt: The prompt to send to the model
        model_name: Name of the model (for error messages)

    Returns:
        Tuple of (response_text, latency_ms, error_message)
        - If successful: (response, latency, None)
        - If failed: (None, None, error_message)
    """
    try:
        start_time = time.time()
        response = await model.ainvoke(prompt)
        end_time = time.time()

        latency_ms = int((end_time - start_time) * 1000)
        response_text = response.content

        # Log model latency
        log_model_latency(model_name, latency_ms)

        return response_text, latency_ms, None

    except Exception as e:
        error_msg = f"Error calling {model_name}: {str(e)}"
        log_error(e, context=f"call_model_with_latency_{model_name}")
        return None, None, error_msg


def parse_response_sections(response: str) -> Dict[str, str]:
    """Parse response into itinerary and highlights sections.

    Args:
        response: Raw response from model

    Returns:
        dict: Parsed sections with 'itinerary' and 'highlights'
    """
    # Try to extract day-by-day itinerary
    itinerary_match = re.search(
        r"Day-by-Day Itinerary.*?(?=\n\n(?:\d+\.|Must-Visit|Culinary|Cultural|Transportation|Budget|Practical|$))",
        response,
        re.DOTALL | re.IGNORECASE,
    )
    itinerary = itinerary_match.group(0) if itinerary_match else response[:1000]

    # Try to extract highlights (attractions, food, etc.)
    highlights_match = re.search(
        r"(Must-Visit.*?(?=\n\n(?:\d+\.|Culinary|Cultural|Transportation|Budget|Practical|$)))",
        response,
        re.DOTALL | re.IGNORECASE,
    )
    highlights = highlights_match.group(0) if highlights_match else response[1000:2000]

    return {"itinerary": itinerary.strip(), "highlights": highlights.strip()}


def analyze_response_characteristics(response: str) -> dict:
    """Analyze characteristics of a model response.

    Args:
        response: The model's response text

    Returns:
        dict: Various metrics about the response including structure and tone
    """
    lines = response.split("\n")
    words = response.split()
    sentences = response.split(".")

    # Get tone analysis
    tone_analysis = analyze_tone_for_gemini(response)

    return {
        "char_count": len(response),
        "word_count": len(words),
        "line_count": len(lines),
        "sentence_count": len(sentences),
        "avg_word_length": sum(len(word) for word in words) / len(words)
        if words
        else 0,
        "has_bullet_points": "•" in response or "-" in response or "*" in response,
        "has_numbering": any(
            line.strip().startswith(("1.", "2.", "3.")) for line in lines
        ),
        "tone": tone_analysis,  # Add tone analysis to characteristics
    }


def analyze_tone_for_gemini(response: str) -> dict:
    """
    Analyze tone, richness, and stylistic character of a Gemini model response.
    Enhanced for comparing Gemini Flash vs Gemini Pro output.
    """

    response_lower = response.lower()

    # -----------------------------
    # 1. Keyword categories (your lists)
    # -----------------------------
    formal_words = [
        "therefore",
        "furthermore",
        "additionally",
        "consequently",
        "moreover",
        "nevertheless",
        "accordingly",
        "thus",
        "hence",
        "subsequently",
        "comprehensive",
        "recommend",
        "suggest",
        "consider",
        "ensure",
    ]
    casual_words = [
        "awesome",
        "great",
        "amazing",
        "wonderful",
        "fantastic",
        "cool",
        "fun",
        "exciting",
        "lovely",
        "beautiful",
        "stunning",
        "incredible",
        "fabulous",
        "perfect",
        "excellent",
        "brilliant",
    ]
    descriptive_words = [
        "vibrant",
        "charming",
        "picturesque",
        "magnificent",
        "breathtaking",
        "enchanting",
        "delightful",
        "exquisite",
        "splendid",
        "majestic",
        "iconic",
        "renowned",
        "celebrated",
        "historic",
        "authentic",
    ]
    action_words = [
        "explore",
        "discover",
        "experience",
        "enjoy",
        "visit",
        "try",
        "taste",
        "wander",
        "stroll",
        "immerse",
        "venture",
        "embark",
    ]

    # -----------------------------
    # 2. Base counts
    # -----------------------------
    formality_score = sum(word in response_lower for word in formal_words)
    enthusiasm_score = sum(word in response_lower for word in casual_words)
    descriptive_score = sum(word in response_lower for word in descriptive_words)
    action_score = sum(word in response_lower for word in action_words)

    exclamations = response.count("!")
    questions = response.count("?")
    personal_tone_score = response_lower.count(" you ") + response_lower.count("your ")
    emoji_count = sum(ord(c) > 127000 for c in response)

    # -----------------------------
    # 3. New metrics for model comparison
    # -----------------------------
    sentences = re.split(r"[.!?]+", response)
    sentences = [s.strip() for s in sentences if s.strip()]
    avg_sentence_length = sum(len(s.split()) for s in sentences) / max(
        len(sentences), 1
    )

    words = re.findall(r"\b[a-zA-Z]+\b", response_lower)
    unique_words = set(words)
    vocabulary_richness = len(unique_words) / max(len(words), 1)

    adjectives = [
        w for w in words if w.endswith(("y", "ful", "ous", "ive", "ic", "al"))
    ]
    adjective_density = len(adjectives) / max(len(words), 1)

    # -----------------------------
    # 4. Tone classification
    # -----------------------------
    if descriptive_score > formality_score and descriptive_score > action_score:
        writing_style = "descriptive"
    elif action_score > descriptive_score:
        writing_style = "action-oriented"
    elif personal_tone_score > 3:
        writing_style = "conversational"
    else:
        writing_style = "informative"

    if formality_score > enthusiasm_score * 1.5:
        tone_type = "formal"
    elif enthusiasm_score > formality_score * 1.5:
        tone_type = "casual"
    else:
        tone_type = "balanced"

    return {
        "formality_score": formality_score,
        "enthusiasm_score": enthusiasm_score + exclamations,
        "descriptive_richness": descriptive_score,
        "action_orientation": action_score,
        "personal_tone_score": personal_tone_score,
        "exclamations": exclamations,
        "questions": questions,
        "emoji_count": emoji_count,
        # Advanced metrics
        "avg_sentence_length": avg_sentence_length,
        "vocabulary_richness": round(vocabulary_richness, 4),
        "adjective_density": round(adjective_density, 4),
        # Classification
        "tone_type": tone_type,
        "writing_style": writing_style,
    }


def generate_comparison(
    flash_response: Optional[str],
    flash_latency: Optional[int],
    pro_response: Optional[str],
    pro_latency: Optional[int],
) -> ComparisonData:
    """Generate detailed comparison with strengths and recommendation.

    Args:
        flash_response: Response from Flash model (or None if failed)
        flash_latency: Flash model latency in ms (or None if failed)
        pro_response: Response from Pro model (or None if failed)
        pro_latency: Pro model latency in ms (or None if failed)

    Returns:
        ComparisonData: Structured comparison data
    """
    # Handle partial failures
    if flash_response is None and pro_response is None:
        return ComparisonData(
            summary="Both models failed to generate responses.",
            flash_strengths=[],
            pro_strengths=[],
            recommended_plan="Unable to generate recommendations due to errors.",
        )

    if flash_response is None:
        return ComparisonData(
            summary=f"Flash model failed. Pro model responded successfully in {pro_latency}ms.",
            flash_strengths=[],
            pro_strengths=["Successfully generated response", "Only available option"],
            recommended_plan="Use Pro model response (Flash unavailable).",
        )

    if pro_response is None:
        return ComparisonData(
            summary=f"Pro model failed. Flash model responded successfully in {flash_latency}ms.",
            flash_strengths=[
                "Successfully generated response",
                "Only available option",
            ],
            pro_strengths=[],
            recommended_plan="Use Flash model response (Pro unavailable).",
        )

    # Both succeeded - detailed comparison
    flash_chars = analyze_response_characteristics(flash_response)
    pro_chars = analyze_response_characteristics(pro_response)

    # Speed analysis
    speed_diff_pct = (
        ((pro_latency - flash_latency) / pro_latency * 100) if pro_latency > 0 else 0
    )

    # Build summary
    summary_parts = []

    if flash_latency < pro_latency:
        summary_parts.append(
            f"⚡ Gemini Flash responded {speed_diff_pct:.1f}% faster ({flash_latency}ms vs {pro_latency}ms)."
        )
    else:
        summary_parts.append(
            f"Both models had similar response times (Flash: {flash_latency}ms, Pro: {pro_latency}ms)."
        )

    # Detail level analysis
    length_diff_pct = (
        (
            (pro_chars["char_count"] - flash_chars["char_count"])
            / flash_chars["char_count"]
            * 100
        )
        if flash_chars["char_count"] > 0
        else 0
    )

    if abs(length_diff_pct) > 20:
        if pro_chars["char_count"] > flash_chars["char_count"]:
            summary_parts.append(
                f"📝 Pro provided {length_diff_pct:.1f}% more content with richer details."
            )
        else:
            summary_parts.append(
                "📝 Flash provided more concise output focused on key highlights."
            )

    # Tone comparison summary
    flash_tone = flash_chars["tone"]
    pro_tone = pro_chars["tone"]

    if flash_tone["tone_type"] != pro_tone["tone_type"]:
        summary_parts.append(
            f"🎨 Flash has a {flash_tone['tone_type']} tone vs Pro's {pro_tone['tone_type']} tone."
        )

    if abs(flash_tone["enthusiasm_score"] - pro_tone["enthusiasm_score"]) > 3:
        more_enthusiastic = (
            "Flash"
            if flash_tone["enthusiasm_score"] > pro_tone["enthusiasm_score"]
            else "Pro"
        )
        summary_parts.append(
            f"✨ {more_enthusiastic} uses more enthusiastic and engaging language."
        )

    if abs(flash_tone["descriptive_richness"] - pro_tone["descriptive_richness"]) > 2:
        more_descriptive = (
            "Flash"
            if flash_tone["descriptive_richness"] > pro_tone["descriptive_richness"]
            else "Pro"
        )
        summary_parts.append(f"🖼️ {more_descriptive} provides more vivid descriptions.")

    summary = " ".join(summary_parts)

    # Identify strengths
    flash_strengths = [
        "Faster response time" if flash_latency < pro_latency else "Quick turnaround"
    ]
    pro_strengths = [
        "More comprehensive details"
        if pro_chars["char_count"] > flash_chars["char_count"]
        else "Detailed analysis"
    ]

    if flash_chars["has_bullet_points"]:
        flash_strengths.append("Well-structured with bullet points")
    if pro_chars["has_numbering"]:
        pro_strengths.append("Organized with numbered sections")

    # Tone comparison
    flash_tone = flash_chars["tone"]
    pro_tone = pro_chars["tone"]

    # Add tone-based strengths
    if flash_tone["enthusiasm_score"] > pro_tone["enthusiasm_score"]:
        flash_strengths.append(f"More engaging tone ({flash_tone['tone_type']})")
    elif pro_tone["enthusiasm_score"] > flash_tone["enthusiasm_score"]:
        pro_strengths.append(f"More enthusiastic style ({pro_tone['tone_type']})")

    if flash_tone["descriptive_richness"] > pro_tone["descriptive_richness"]:
        flash_strengths.append("More vivid and descriptive language")
    elif pro_tone["descriptive_richness"] > flash_tone["descriptive_richness"]:
        pro_strengths.append("Richer descriptive vocabulary")

    if flash_tone["personal_tone_score"] > pro_tone["personal_tone_score"]:
        flash_strengths.append("More personal and conversational")
    elif pro_tone["personal_tone_score"] > flash_tone["personal_tone_score"]:
        pro_strengths.append("More personalized approach")

    if flash_tone["action_orientation"] > pro_tone["action_orientation"]:
        flash_strengths.append("More action-oriented recommendations")
    elif pro_tone["action_orientation"] > flash_tone["action_orientation"]:
        pro_strengths.append("More actionable suggestions")

    # Recommendation with tone consideration
    if speed_diff_pct > 30 and length_diff_pct < 50:
        recommended_plan = (
            "Use Flash for quick planning; sufficient detail with faster response."
        )
    elif length_diff_pct > 50:
        recommended_plan = "Use Pro for comprehensive itinerary with cultural insights and detailed recommendations."
    else:
        recommended_plan = "Both responses are comparable. Flash for speed, Pro for depth. Consider merging key highlights from both."

    return ComparisonData(
        summary=summary,
        flash_strengths=flash_strengths,
        pro_strengths=pro_strengths,
        recommended_plan=recommended_plan,
    )


async def process_travel_request(request: TravelRequest) -> TravelAssistantResponse:
    """Main service function to process travel requests with parallel model calls.

    This function:
    1. Builds a detailed travel prompt
    2. Calls Flash and Pro models in parallel (using asyncio.gather)
    3. Measures latency for each model
    4. Handles partial failures gracefully
    5. Generates comprehensive comparison

    Args:
        request: TravelRequest with destination, dates, and preferences

    Returns:
        TravelAssistantResponse with both model outputs and comparison

    Raises:
        Exception: Only if both models fail
    """
    # Build the prompt
    prompt = build_travel_prompt(request)

    # Call both models in parallel
    results = await asyncio.gather(
        call_model_with_latency(flash_model, prompt, "Gemini Flash"),
        call_model_with_latency(pro_model, prompt, "Gemini Pro"),
        return_exceptions=True,
    )

    flash_response, flash_latency, flash_error = results[0]
    pro_response, pro_latency, pro_error = results[1]

    # Handle complete failure
    if flash_error and pro_error:
        raise Exception(f"Both models failed. Flash: {flash_error}, Pro: {pro_error}")

    # Create model responses
    if flash_error:
        flash_model_response = ModelResponse(
            model="gemini-flash-latest",
            latency_ms=0,
            itinerary=f"[Flash Model Error: {flash_error}]",
            highlights="",
            raw_response=f"Error: {flash_error}",
        )
    else:
        flash_sections = parse_response_sections(flash_response)
        flash_model_response = ModelResponse(
            model="gemini-flash-latest",
            latency_ms=flash_latency,
            itinerary=flash_sections["itinerary"],
            highlights=flash_sections["highlights"],
            raw_response=flash_response,
        )

    if pro_error:
        pro_model_response = ModelResponse(
            model="gemini-pro-latest",
            latency_ms=0,
            itinerary=f"[Pro Model Error: {pro_error}]",
            highlights="",
            raw_response=f"Error: {pro_error}",
        )
    else:
        pro_sections = parse_response_sections(pro_response)
        pro_model_response = ModelResponse(
            model="gemini-pro-latest",
            latency_ms=pro_latency,
            itinerary=pro_sections["itinerary"],
            highlights=pro_sections["highlights"],
            raw_response=pro_response,
        )

    # Generate comparison
    comparison = generate_comparison(
        flash_response if not flash_error else None,
        flash_latency if not flash_error else None,
        pro_response if not pro_error else None,
        pro_latency if not pro_error else None,
    )

    # Build and return response
    return TravelAssistantResponse(
        request=request,
        flash=flash_model_response,
        pro=pro_model_response,
        comparison=comparison,
    )
