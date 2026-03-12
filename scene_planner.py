import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

VIDEO_PRODUCER_PROMPT = """You are an expert video producer and aviation analyst.
Create a detailed video plan for a 2.5-3 minute animated explainer summary.

REQUIREMENTS:
- Create EXACTLY 22 scenes (minimum 20, maximum 24)
- Each scene: 6-9 seconds duration
- Total duration: 150-180 seconds
- Cover EVERY news article provided
- Preserve all key numbers, names, dollar figures, percentages, dates

VISUAL STYLE:
- Cinematic framing: low-angle wide shot, overhead view, close-up, medium shot
- Lighting: golden hour for optimism, cool blue for challenges, warm amber for historical, crisp studio for data
- Modern high-tech aesthetic: glass-walled rooms, advanced assembly lines, sleek terminals
- Animated infographics for data/statistics
- Color grading: legacy warm, somber muted, vibrant optimistic, neutral documentary

VIDEO STRUCTURE:
SECTION 1 - MACROECONOMIC (scenes 1-6):
- West Asia conflict impact on Indian aviation/energy security
- Iran warships docking at Indian ports
- 279 international flights cancelled
- Trump ordering defence contractors to quadruple production
- Energy security for one crore Indian citizens in Gulf
- Transition scene to competitor analysis

SECTION 2 - COMPETITORS (scenes 7-22):
1. GE Aerospace $1B US investment, 5000 hires, LEAP engine
2. Airbus 880,000 sq ft Bengaluru tech centre, 5000 employees, $1.5B sourcing
3. Embraer E175 India assembly line, 200-order threshold, 1800 routes
4. India 2nd largest arms importer (8.2%), Russia share drop, Rafale deal, defence budget
5. Defence Vision 2047, integrated theatre commands, Aatmanirbharta
6. Navy Chief on industrial complex, self-reliance
7. Flying Wedge FWD YAMA swarm interceptor, $10,000 vs $4M Patriot
8. ADA AMCA 98% pressure recovery, stealth fighter intake
9. Ghatak 13-ton UCAV, Kaveri engine, 1000km radius
10. Piyush Goyal on startup ecosystem, MSMEs, semiconductors
11. TVS Supply Chain + Caterpillar, 40,000 sq ft Chennai warehouse

CONSTRAINTS:
- Unbiased, professional tone
- Strictly factual, no invented data
- visual_prompt: describe SINGLE IMAGE (not video)
- audio_script: 2-4 sentences with specific facts
- on_screen_text: short labels with key numbers

Output JSON:
{
  "textual_summary": "Comprehensive factual summary with all numbers",
  "scenes": [
    {
      "scene_number": 1,
      "section": "Macroeconomic",
      "duration_seconds": 7,
      "visual_prompt": "Single-image description",
      "audio_script": "Narration with facts and numbers",
      "on_screen_text": "Short label"
    }
  ],
  "overall_style": "Visual style description"
}

Aviation News Context:
"""


def generate_scene_plan(context, model="gpt-4o"):
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert video producer and aviation analyst. Output valid JSON only."},
            {"role": "user", "content": VIDEO_PRODUCER_PROMPT + context}
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    result = response.choices[0].message.content
    return json.loads(result)


def save_scene_plan(plan, output_path):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    return output_path
