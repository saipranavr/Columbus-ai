import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- Configuration ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("🛑 GEMINI_API_KEY not found in .env file. Please create it.")
    exit()

# Configure the Gemini model
# IMPORTANT: Ensure this model ID is valid and accessible in your environment.
# The user requested "gemini-1.5-flash-preview-0514".
MODEL_NAME = "gemini-2.5-pro-preview-05-06" # User specified this model


# Standard safety settings
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

try:
    genai.configure(api_key=GEMINI_API_KEY)
    # Generation config can be used to influence output, e.g., temperature for creativity
    # For TTS scripts, a lower temperature might be good for more factual/consistent output.
    generation_config = genai.types.GenerationConfig(
        # candidate_count=1, # Usually default is 1
        # stop_sequences=['\n\n\n'], # Could be useful if Gemini adds too much space
        # max_output_tokens=8192, # Default for Flash 1.5 is 8192
        temperature=0.7 # A bit more controlled than default 0.9 or 1.0
    )
    model = genai.GenerativeModel(
        MODEL_NAME,
        safety_settings=SAFETY_SETTINGS,
        generation_config=generation_config
        )
    print(f"✅ Successfully configured Gemini model: {MODEL_NAME}")
except Exception as e:
    print(f"🛑 Error configuring Gemini or creating model: {e}")
    print(f"   Ensure the model name '{MODEL_NAME}' is correct and accessible.")
    exit()


def call_gemini_api(prompt_text, task_description="task"):
    """
    Calls the Gemini API with the given prompt.
    """
    print(f"\n🤖 Sending prompt to Gemini for: {task_description}...")
    try:
        # response = model.generate_content(prompt_text)
        response = model.generate_content("give me 3 Youtube links for 3 day trip in barcelona")
        # Accessing response.text should be the primary way for simple text models
        if hasattr(response, 'text') and response.text:
            return response.text.strip() # Added strip() here for cleaning
        elif response.parts: # Fallback for more complex response structures
            # Filter out non-text parts if any and join
            text_parts = [part.text for part in response.parts if hasattr(part, 'text')]
            if text_parts:
                return "".join(text_parts).strip() # Added strip() here

        # If no text, check for blocking
        print(f"⚠️ Gemini response for {task_description} was empty or had no text part.")
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
            print(f"   Prompt Feedback: {response.prompt_feedback}")
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if candidate.finish_reason != 1: # 1 = STOP (Natural stop)
                    print(f"   Candidate Finish Reason: {candidate.finish_reason.name} ({candidate.finish_reason.value})")
                    if candidate.safety_ratings:
                         for rating in candidate.safety_ratings:
                            if rating.probability.value > 1: # Higher values mean more likely blocked
                                print(f"     Safety Rating: {rating.category.name} - {rating.probability.name}")

        return None # Explicitly return None if no usable text
    except Exception as e:
        print(f"🛑 Error calling Gemini API for {task_description}: {e}")
        return None

def parse_video_discovery_response(response_text):
    """
    Parses Gemini's response to extract video URLs and their initial info.
    """
    videos = []
    if not response_text:
        return videos
    try:
        potential_json = response_text.strip()
        if potential_json.startswith("```json"):
            potential_json = potential_json[7:-3].strip() if potential_json.endswith("```") else potential_json[7:].strip()
        data = json.loads(potential_json)
        if isinstance(data, list) and all(isinstance(item, dict) and "url" in item and "info" in item for item in data):
            return data
        else:
            print("⚠️ JSON response from Gemini (video discovery) was not in the expected list-of-dictionaries format.")
    except json.JSONDecodeError:
        current_url = None
        current_info_lines = []
        for line in response_text.splitlines():
            line_stripped = line.strip()
            if not line_stripped: continue

            if line_stripped.upper().startswith("URL:") or line_stripped.startswith("http"):
                if current_url and current_info_lines:
                    videos.append({"url": current_url.strip(), "info": " ".join(current_info_lines).strip()})
                current_url = line_stripped.split("URL:", 1)[-1].strip() if line_stripped.upper().startswith("URL:") else line_stripped
                current_info_lines = []
            elif (line_stripped.upper().startswith("INFO:") or line_stripped.upper().startswith("TITLE:")) and current_url:
                current_info_lines.append(line_stripped.split(":", 1)[-1].strip())
            elif current_url:
                current_info_lines.append(line_stripped)

        if current_url and current_info_lines:
            videos.append({"url": current_url.strip(), "info": " ".join(current_info_lines).strip()})

    if not videos:
         print("⚠️ Could not parse video URLs and info from Gemini's discovery response.")
         print(f"   Raw response snippet: {response_text[:500]}")
    return videos


# --- Core Functions ---

def discover_videos_and_initial_info(location, local_language_name, num_videos_total=7, num_local_videos=2):
    task_description = f"Video Discovery for {location}"
    # Added instruction for JSON output format to aid parsing
    prompt = f"""
    You are a helpful travel research assistant for creating a travel guide about "{location}".

    Please find approximately {num_videos_total} YouTube video URLs relevant for a tourist.
    Focus on videos covering: landmarks, local restaurants, unique cuisine, convenience store tips, general travel advice, and cultural insights.

    Include approximately {num_local_videos} videos likely in the {local_language_name} language for unique local recommendations. The rest should be in English.
    Ground your suggestions using your knowledge and simulated search capabilities for relevance and quality.

    **Output Format Constraint:** Respond ONLY with a valid JSON list of objects. Each object must have two keys: "url" (string) and "info" (string, 1-2 sentence description/title).
    Example:
    ```json
    [
      {{"url": "https://www.youtube.com/watch?v=example1", "info": "A great overview of top landmarks in the city."}},
      {{"url": "https://www.youtube.com/watch?v=example2_local", "info": "({local_language_name} language) Exploring hidden food gems."}}
    ]
    ```
    Do not include any other text or commentary before or after the JSON list.
    """
    response_text = call_gemini_api(prompt, task_description)
    if response_text:
        return parse_video_discovery_response(response_text)
    return []


def generate_detailed_summaries(video_info_list, location, local_language_name):
    all_summaries = []
    if not video_info_list: return all_summaries
    print(f"\n--- Generating Detailed Summaries for {len(video_info_list)} videos ---")
    for i, video_info in enumerate(video_info_list):
        url = video_info.get("url", "N/A")
        initial_info = video_info.get("info", "No initial info provided.")
        task_description = f"Detailed Summary for video {i+1} ({url})"
        prompt = f"""
        You are a travel content analyst.
        Video URL: {url}
        Likely video content based on initial info: "{initial_info}"

        Task:
        Using simulated Google Search to infer the video's content (based on its title, description, or related public information):
        1. Generate a concise, detailed summary in ENGLISH (150-250 words).
        2. Focus on: key landmarks, specific food/restaurant recommendations, convenience store tips, unique local travel advice, cultural insights, or hidden gems.
        3. If the video seems to be in {local_language_name}, prioritize unique local insights not common in English guides, translated clearly into the English summary.
        4. Ensure the summary is plausible and credible.

        Provide ONLY the summary text. No conversational filler.
        """
        summary_text = call_gemini_api(prompt, task_description)
        if summary_text:
            all_summaries.append({
                "url": url, "initial_info": initial_info, "detailed_summary": summary_text
            })
            print(f"  ✅ Summary generated for video {i+1}.")
        else:
            print(f"  ⚠️ Failed to generate summary for video {i+1}.")
    return all_summaries


def generate_final_script(summaries, location):
    if not summaries: return None
    task_description = f"Final TTS Narration Script for {location}"
    formatted_summaries_text = "\n\n---\n\n".join(
        f"Insights from Video (likely about: {s['initial_info']}):\n{s['detailed_summary']}"
        for s in summaries if s.get('detailed_summary')
    )
    if not formatted_summaries_text: return None

    # This is the updated TTS-focused prompt
    prompt = f"""
    You are an expert AI scriptwriter, tasked with creating a narration-only script for a professional travel guide video about "{location}". This script will be directly fed into a Text-to-Speech (TTS) engine (e.g., Eleven Labs) for voice-over. Your output must be pure, clean, speakable text.

    Synthesize the provided travel insights into a seamless, natural-sounding narrative.
    --- BEGIN INSIGHTS ---
    {formatted_summaries_text}
    --- END INSIGHTS ---

    **CRITICAL SCRIPT REQUIREMENTS FOR TTS COMPATIBILITY:**
    1.  **NARRATION ONLY:** The entire output MUST be only the narrative text to be spoken by a single voice.
        *   DO NOT include any introductory or concluding meta-commentary from you, the AI (e.g., "Okay, here's the script...", "This script is ready for TTS...").
        *   DO NOT include any scene markers, section headers, or similar structural tags (e.g., "[SCENE START]", "[SECTION: LANDMARKS]", "**Introduction**").
        *   DO NOT include any character names, narrator tags, or speaker cues (e.g., "Narrator:", "Host:").
        *   DO NOT include any visual cues, camera directions, or parenthetical instructions in brackets or parentheses (e.g., "[Visual: Kinkaku-ji Temple]", "(Show footage of bustling market)", "(pause for effect)"). If a visual idea is absolutely critical to convey, you must weave a descriptive phrase into the narrative naturally. For example, instead of "[Visual: bustling market]", you could say, "The market itself is a bustling hive of activity, filled with the sights and sounds of local commerce." Otherwise, omit non-speakable cues entirely.
    2.  **CONTENT & STRUCTURE (as a continuous narrative):**
        *   Begin directly with a concise and engaging spoken introduction to "{location}".
        *   Smoothly transition to describe key landmarks and attractions.
        *   Naturally discuss culinary experiences, local cuisine, and notable food spots.
        *   Seamlessly integrate practical information (e.g., convenience stores) and noteworthy travel tips.
        *   Weave in cultural context or unique observations if available and relevant.
        *   Conclude with a thoughtful spoken summary or closing remarks, ending the narrative cleanly.
    3.  **TONE FOR NARRATION:**
        *   **Professional & Composed:** Maintain a tone that is knowledgeable, calm, clear, articulate, and trustworthy. Think of a seasoned documentary narrator or a highly competent personal assistant delivering a briefing.
        *   **Insightful, Not Overly Enthusiastic:** Avoid hyperbole, exaggerated excitement, or casual "vlogger" slang. The focus is on delivering valuable information with a composed and engaging demeanor.
    4.  **FLOW & PACING:** Ensure a logical flow between topics, using natural language transitions suitable for continuous narration. The text should be well-paced for speaking.
    5.  **LENGTH:** Target a script that would correspond to approximately 5-7 minutes of speaking time.
    6.  **LANGUAGE:** English.
    7.  **GROUNDING & CREDIBILITY:**
        *   The narrative should be based *primarily* on the provided insights.
        *   You may use your simulated Google Search capabilities to verify names, add brief factual details for enhanced clarity if they can be woven into the narration naturally, and ensure claims are presented appropriately (e.g., attributing opinions from source insights or using verifiable facts).

    Provide ONLY the speakable narration script.
    """
    script_text = call_gemini_api(prompt, task_description)
    return script_text


# --- Main Application Flow ---
if __name__ == "__main__":
    print("✨ Welcome to the AI TTS Travel Script Generator! ✨")
    # Forcing python.exe from venv if running directly and path issues occur:
    # "D:\\Path\\To\\Your\\venv\\Scripts\\python.exe" your_script.py
    target_location = input("Enter the travel destination (e.g., 'Kyoto, Japan'): ").strip()
    if not target_location: exit("No location entered.")

    default_local_language = "the local language of the destination"
    loc_low = target_location.lower()
    # Basic language mapping
    lang_map = {
        ("japan", "tokyo", "kyoto", "osaka"): "Japanese",
        ("france", "paris"): "French", ("korea", "seoul"): "Korean",
        ("italy", "rome", "florence"): "Italian",
        ("spain", "barcelona", "madrid"): "Spanish",
        ("germany", "berlin", "munich"): "German",
        ("india", "delhi", "mumbai", "ahmedabad"): "Hindi or the dominant regional language"
    }
    for keywords, lang in lang_map.items():
        if any(keyword in loc_low for keyword in keywords):
            default_local_language = lang
            break
    
    print(f"\nInitiating travel guide generation for: {target_location}")
    print(f"Attempting to include insights from videos in: {default_local_language}")

    discovered_video_info = discover_videos_and_initial_info(target_location, default_local_language)
    if not discovered_video_info: exit(f"🛑 No video info discovered for {target_location}.")
    print(f"\n✅ Discovered {len(discovered_video_info)} initial video candidates.")
    for i, vid in enumerate(discovered_video_info): print(f"  {i+1}. URL: {vid.get('url','N/A')}, Info: {vid.get('info','N/A')}")

    detailed_summaries = generate_detailed_summaries(discovered_video_info, target_location, default_local_language)
    if not detailed_summaries: exit(f"🛑 No detailed summaries generated for {target_location}.")
    print(f"\n✅ Generated {len(detailed_summaries)} detailed summaries.")

    final_script = generate_final_script(detailed_summaries, target_location)
    if final_script:
        print(f"\n🎉 TTS Narration Script for {target_location}: 🎉")
        print("\n--- SCRIPT START ---")
        print(final_script)
        print("--- SCRIPT END ---")
        filename = f"{target_location.lower().replace(', ','_').replace(' ','_')}_tts_script.txt"
        try:
            with open(filename, "w", encoding="utf-8") as f: f.write(final_script)
            print(f"\n📄 Script saved to {filename}")
        except Exception as e: print(f"⚠️ Error saving script: {e}")
    else:
        print(f"🛑 Failed to generate final TTS script for {target_location}.")