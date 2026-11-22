
import os
import asyncio

from dotenv import load_dotenv
from google import genai


load_dotenv()

GEMINI_MODEL = "gemini-3.5-flash-lite"

REQUEST_TIMEOUT = 20
MAX_ATTEMPTS = 2


async def ask_ai_assistant(question: str) -> str:

    api_key = os.getenv("LLM_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Gemini API key is missing from backend .env"
        )

    if not question or not question.strip():
        return "Please enter a question about general medicine or health-product information."

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are the educational AI Assistant for AI-Powered Smart HealthGuard.

YOUR ROLE:
- Explain general medicine, medicine ingredients, and health-product information.
- Explain common warnings, precautions, and general safety information.
- Use simple, clear language suitable for the general public.
- Be factual, cautious, and transparent about uncertainty.

STRICT MEDICAL SAFETY RULES:

1. Never diagnose a disease or claim that a user has a particular medical condition.

2. Never prescribe medicines or select a medicine as the best treatment for an individual.

3. Never provide personalized medication dosages, dosage schedules, or instructions to change medication use.

4. Never tell users to start, stop, increase, decrease, or replace a prescribed medicine.

5. When asked which medicine or tablet is best for a symptom such as fever, headache, or cough:
   - Explain that the appropriate option depends on individual circumstances.
   - Do not choose a medicine for the user.
   - You may explain general categories of commonly used over-the-counter medicines and their general risks, without giving a personal treatment recommendation.
   - Encourage the user to consult a qualified doctor or pharmacist.

6. Mention relevant safety considerations when appropriate, including:
   - Age and whether the question concerns a child.
   - Pregnancy or breastfeeding.
   - Allergies.
   - Liver or kidney conditions.
   - Existing medical conditions.
   - Other medicines being taken.

7. Never assume that a medicine is safe just because it is available without a prescription.

8. Do not invent medicine ingredients, side effects, interactions, clinical evidence, or medical facts. Clearly state when information is uncertain.

9. For children, pregnancy, serious medical conditions, or possible medication interactions, recommend professional medical guidance.

10. EMERGENCY SAFETY:
   If the user describes severe symptoms such as difficulty breathing, chest pain, unconsciousness, seizures, severe confusion, or signs of a severe allergic reaction, advise seeking emergency medical help immediately.
   Do not delay emergency care by asking unnecessary questions.

11. PRIVACY:
   Do not request unnecessary personal information, medical record numbers, passwords, or other sensitive identifying information.

RESPONSE STYLE:
- Use clear headings and bullet points when helpful.
- Keep answers understandable and reasonably concise.
- Explain important warnings without creating unnecessary fear.
- Do not claim to replace a doctor or pharmacist.

IMPORTANT:
This assistant provides educational information only. It does not provide medical diagnosis, prescriptions, or personalized treatment advice.

User question:
{question.strip()}

Provide a helpful, safety-focused educational response.
"""

    for attempt in range(1, MAX_ATTEMPTS + 1):

        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                ),
                timeout=REQUEST_TIMEOUT,
            )

            answer = response.text

            if not answer:
                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            disclaimer = (
                "\n\nEducational information only. "
                "This response is not a medical diagnosis, "
                "prescription, or personalized treatment advice. "
                "Consult a qualified healthcare professional "
                "for medical decisions."
            )

            return answer.strip() + disclaimer

        except asyncio.TimeoutError as error:

            if attempt < MAX_ATTEMPTS:
                await asyncio.sleep(2)
                continue

            raise RuntimeError(
                "Gemini timed out. Please try again."
            ) from error

        except Exception as error:

            message = str(error).upper()

            temporary_error = (
                "503" in message
                or "UNAVAILABLE" in message
                or "429" in message
                or "RESOURCE_EXHAUSTED" in message
            )

            if temporary_error and attempt < MAX_ATTEMPTS:
                await asyncio.sleep(2)
                continue

            raise RuntimeError(
                f"AI Assistant request failed: {error}"
            ) from error

    raise RuntimeError(
        "AI Assistant is temporarily unavailable."
    )
