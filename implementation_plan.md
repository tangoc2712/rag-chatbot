# Implementation Plan - Integrate Google Gemini LLM

This plan outlines the steps to upgrade the current template-based response system to a true RAG system using Google's Gemini model via Google AI Studio.

## User Review Required

> [!IMPORTANT]
> **API Key Required**: You will need a Google AI Studio API Key.
> You can get one here: https://aistudio.google.com/app/apikey
> You will need to add this key to your `.env` file as `GOOGLE_API_KEY=your_key_here`.

## Proposed Changes

### Dependencies

#### [MODIFY] [requirements.txt](file:///Users/quangngoc/sorceCode/AI/fsoft_rag_chatbot/Ecommerce-RAG-Chatbot/requirements.txt)
- Add `google-generativeai`

### Configuration

#### [MODIFY] [src/config.py](file:///Users/quangngoc/sorceCode/AI/fsoft_rag_chatbot/Ecommerce-RAG-Chatbot/src/config.py)
- Add `GOOGLE_API_KEY` to the `Settings` class.

#### [MODIFY] [.env.example](file:///Users/quangngoc/sorceCode/AI/fsoft_rag_chatbot/Ecommerce-RAG-Chatbot/.env.example)
- Add `GOOGLE_API_KEY=` placeholder.

### RAG Implementation

#### [MODIFY] [src/rag/assistant.py](file:///Users/quangngoc/sorceCode/AI/fsoft_rag_chatbot/Ecommerce-RAG-Chatbot/src/rag/assistant.py)
- Import `google.generativeai as genai`.
- Update `__init__` to:
    - Load the API key from settings.
    - Configure `genai`.
    - Initialize the GenerativeModel (e.g., `gemini-1.5-flash`).
- Add `generate_llm_response(self, query: str, context: str) -> str` method.
- Update `process_query` to:
    - Retrieve data (products/orders) as before.
    - Instead of returning the formatted string directly, use it as `context`.
    - Call `generate_llm_response` with the query and context to get a natural language answer.

## Verification Plan

### Manual Verification
1.  User adds their API key to `.env`.
2.  Run `pip install -r requirements.txt`.
3.  Run the chat script: `python scripts/run.py chat`.
4.  Ask questions like:
    - "Recommend me some good guitars under $500"
    - "What is the status of my last order?"
5.  Verify the responses are natural and use the retrieved data correctly.
