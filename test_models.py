"""Test script to list available Gemini models."""

import google.generativeai as genai
from app.config import settings

# Configure the API
genai.configure(api_key=settings.google_api_key)

print("🔍 Listing all available Gemini models:\n")
print("-" * 80)

for model in genai.list_models():
    if "generateContent" in model.supported_generation_methods:
        print(f"✅ Model: {model.name}")
        print(f"   Display Name: {model.display_name}")
        print(f"   Description: {model.description}")
        print(f"   Methods: {model.supported_generation_methods}")
        print("-" * 80)
