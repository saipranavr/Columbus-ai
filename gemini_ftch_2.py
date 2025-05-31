import os
import json # For parsing potential JSON in Gemini's responses
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
# This should be a valid model identifier that supports your needs (e.g., grounding if available via API)
# For the "2.0" equivalent, you might need to use a specific identifier like "gemini-1.0-pro"
# or check the latest documentation for available general-purpose models.
# "gemini-1.5-flash-latest" is often a good choice for speed and capability.
MODEL_NAME = "gemini-2.5-flash-preview-05-20" # Or "gemini-1.0-pro" or other valid model

# Standard safety settings
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(MODEL_NAME, safety_settings=SAFETY_SETTINGS)
    print(f"✅ Successfully configured Gemini model: {MODEL_NAME}")
except Exception as e:
    print(f"🛑 Error configuring Gemini or creating model: {e}")
    exit()


def call_gemini_api(prompt_text, task_description="task"):
    """
    Calls the Gemini API with the given prompt.
    """
    print(f"\n🤖 Sending prompt to Gemini for: {task_description}...")
    try:
        response = model.generate_content(prompt_text)
        if response.text:
            return response.text
        else:
            if response.parts:
                return "".join(part.text for part in response.parts if hasattr(part, 'text'))
            print(f"⚠️ Gemini response for {task_description} was empty or had no text part.")
            # You can inspect response.prompt_feedback here for blocked reasons
            if response.prompt_feedback:
                print(f"   Prompt Feedback: {response.prompt_feedback}")
            return None
    except Exception as e:
        print(f"🛑 Error calling Gemini API for {task_description}: {e}")
        return None

def parse_video_discovery_response(response_text):
    """
    Parses Gemini's response to extract video URLs and their initial info.
    Attempts to parse JSON first, then falls back to line-by-line.
    """
    videos = []
    if not response_text:
        return videos
    try:
        # Try to parse as JSON if Gemini formats it that way
        # Gemini might need a very explicit prompt to return clean JSON.
        potential_json = response_text.strip()
        if potential_json.startswith("```json"):
            potential_json = potential_json[7:]
            if potential_json.endswith("```"):
                potential_json = potential_json[:-3]
        data = json.loads(potential_json)
        if isinstance(data, list) and all(isinstance(item, dict) and "url" in item and "info" in item for item in data):
            return data
        else: # It was valid JSON but not the expected list of dicts
            print("⚠️ JSON response from Gemini was not in the expected list-of-dictionaries format for videos.")
    except json.JSONDecodeError:
        # Fallback to line-by-line parsing if not valid JSON
        current_url = None
        current_info_lines = []
        for line in response_text.splitlines():
            line_stripped = line.strip()
            if not line_stripped: continue

            # Heuristic: Lines starting with "URL:" or "http" are likely URLs
            if line_stripped.upper().startswith("URL:") or line_stripped.startswith("http"):
                if current_url and current_info_lines: # Save previous entry
                    videos.append({"url": current_url.strip(), "info": " ".join(current_info_lines).strip()})
                    current_info_lines = [] # Reset for next video's info
                current_url = line_stripped.split("URL:", 1)[-1].strip() if line_stripped.upper().startswith("URL:") else line_stripped
            # Heuristic: Lines starting with "Info:" or are context for a current_url
            elif (line_stripped.upper().startswith("INFO:") or line_stripped.upper().startswith("TITLE:")) and current_url:
                current_info_lines.append(line_stripped.split(":", 1)[-1].strip())
            elif current_url: # Assumed to be part of the info for the current_url
                current_info_lines.append(line_stripped)

        if current_url and current_info_lines: # Save the last entry
            videos.append({"url": current_url.strip(), "info": " ".join(current_info_lines).strip()})

    if not videos:
         print("⚠️ Could not parse video URLs and info from Gemini's discovery response. Ensure the prompt asks for a clear format.")
         print(f"   Raw response snippet: {response_text[:500]}")

    return videos


# --- Core Functions ---

def discover_videos_and_initial_info(location, local_language_name, num_videos_total=7, num_local_videos=2):
    """
    Asks Gemini to discover video URLs and provide initial info about them.
    """
    task_description = f"Video Discovery for {location}"
    prompt = f"""
    You are a helpful travel research assistant. I need to find YouTube video information for a travel guide about "{location}".

    Please find approximately {num_videos_total} YouTube video URLs that would be highly relevant for a tourist.
    Focus on videos covering:
    - Popular landmarks and attractions.
    - Local restaurants and unique cuisine (not just tourist traps).
    - Tips for using convenience stores effectively.
    - General travel tips and cultural insights for "{location}".

    IMPORTANT:
    1. Include approximately {num_local_videos} videos that are likely in the {local_language_name} language, as these might contain unique local recommendations not typically found in English tourist guides. The rest should be in English.
    2. For EACH video, provide:
        a. The full YouTube URL.
        b. A brief (1-2 sentence) initial piece of information, such as the video's likely title or its main topic, to give context.
    3. Ground your suggestions using your knowledge and simulated search capabilities to ensure relevance and potential quality. Try to find videos that seem informative or from knowledgeable creators.

    Present the information clearly for each video.
    Desired output format is a list where each item is a video. For example:
    URL: [video_url_1]
    Info: [brief_info_about_video_1]

    URL: [video_url_2]
    Info: [brief_info_about_video_2_in_{local_language_name}_if_applicable]

    ... and so on.
    Do not include any other commentary before or after this list.
    """
    response_text = call_gemini_api(prompt, task_description)
    if response_text:
        return parse_video_discovery_response(response_text)
    return []


def generate_detailed_summaries(video_info_list, location, local_language_name):
    """
    Generates detailed summaries for each video using Gemini.
    """
    all_summaries = []
    if not video_info_list:
        print("No video information provided to generate summaries.")
        return all_summaries

    print(f"\n--- Generating Detailed Summaries for {len(video_info_list)} videos ---")
    for i, video_info in enumerate(video_info_list):
        url = video_info.get("url")
        initial_info = video_info.get("info", "No initial info provided.")
        task_description = f"Detailed Summary for video {i+1} ({url})"

        prompt = f"""
        You are a helpful travel content analyst.
        Consider a YouTube video with the URL: {url}
        The video is likely about: "{initial_info}"

        Task:
        Using your knowledge and simulated Google Search capabilities to infer the video's content (based on its likely title, description, or publicly available information related to this URL or topic):
        1. Generate a concise but detailed summary in ENGLISH (approximately 150-250 words).
        2. The summary MUST focus on extracting the following types of information if likely present:
            - Key landmarks or attractions mentioned or shown.
            - Specific restaurants, food stalls, or types of local cuisine recommended.
            - Any tips or information regarding local convenience stores (e.g., useful items, services).
            - Unique local travel tips, cultural insights, or hidden gems suggested.
        3. If the video's initial info suggests it might be in {local_language_name}, pay special attention to extracting unique local insights that might not be in typical English guides. Ensure the entire summary is in clear English.
        4. Ensure the summary is plausible, credible, and based on the likely content of such a video.

        Provide only the summary text. Do not add any conversational filler before or after the summary.
        """
        summary_text = call_gemini_api(prompt, task_description)
        if summary_text:
            all_summaries.append({
                "url": url,
                "initial_info": initial_info,
                "detailed_summary": summary_text.strip()
            })
            print(f"  ✅ Summary generated for video {i+1}.")
            print("---------------")
            print(summary_text)
            print("---------------")
        else:
            print(f"  ⚠️ Failed to generate summary for video {i+1}.")
    return all_summaries


def generate_final_script(summaries, location):
    """
    Generates the final YouTube video script based on all collected summaries,
    with a professional personal assistant tone.
    """
    if not summaries:
        print("No summaries provided to generate the final script.")
        return None

    task_description = f"Final Video Script for {location} (Professional Tone)"
    formatted_summaries_text = "\n\n---\n\n".join(
        f"Insights from Video (likely about: {s['initial_info']}):\n{s['detailed_summary']}"
        for s in summaries if s.get('detailed_summary') # Ensure summary exists
    )
    if not formatted_summaries_text:
        print("No valid summaries available to create script from.")
        return None

    prompt = f"""
    You are a highly capable AI personal assistant, specializing in creating detailed and insightful travel briefings with the knowledge of a seasoned travel content creator.
    Your task is to synthesize the provided travel insights into a clear, informative, and well-structured script suitable for a sophisticated travel briefing or a professionally toned video guide about "{location}".

    You have been provided with detailed insights extracted from several relevant YouTube videos. These insights are below:
    --- BEGIN INSIGHTS ---
    {formatted_summaries_text}
    --- END INSIGHTS ---

    Script Requirements:
    1.  **Overall Goal:** Synthesize these insights into a coherent, informative, and professional script. The output should be helpful and actionable for someone planning a trip.
    2.  **Length:** Aim for a script that would be approximately 5-7 minutes of speaking time.
    3.  **Language:** English.
    4.  **Content Sections (ensure these are covered if information is available in the insights):**
        *   **Concise Introduction:** Briefly introduce "{location}" and the purpose of the briefing.
        *   **Key Landmarks & Attractions:** Present significant sights from the insights with relevant details.
        *   **Culinary Experiences:** Discuss local cuisine, notable restaurants, or food types mentioned.
        *   **Practical Information (e.g., Convenience Stores):** If tips on convenience stores or other practicalities are available, integrate them.
        *   **Noteworthy Travel Tips & Unique Observations:** Include any standout advice or unique perspectives from the insights.
        *   **Cultural Context (if any):** Weave in any cultural information provided.
        *   **Summary & Closing Remarks:** Conclude with a brief summary or helpful closing thoughts.
    5.  **Grounding & Credibility:**
        *   Base the script *primarily* on the provided insights.
        *   You may use your simulated Google Search capabilities to:
            *   Verify the spelling or current official names of places mentioned.
            *   Add a brief, verifiable, factual detail or context to 1-2 key landmarks or dishes if it significantly enhances understanding and fits naturally.
            *   Ensure any specific claims (e.g., opinions on "best") are attributed or presented as observations from the source insights rather than absolute facts, unless widely verifiable.
    6.  **Style & Tone:**
        *   **Professional & Assistant-Like:** The tone should be that of a knowledgeable, efficient, and calm personal assistant – clear, articulate, and trustworthy.
        *   **Insightful, Not Hyped:** Avoid overly enthusiastic, exaggerated, or "vlogger-slang" language. Focus on delivering valuable information with a composed demeanor.
        *   **Structured & Clear:** Use clear language and a logical flow.
        *   **Visual Suggestions:** You can still include suggestions for visuals, framed professionally (e.g., "[Visual: Kinkaku-ji Temple, showcasing its golden facade.]", "[Consider a brief shot of various items available at a typical convenience store.]").
    7.  **Structure:** Organize with clear segments.

    Do not invent information not supported by the provided summaries or your grounded verification.
    Provide only the complete script.
    """
    script_text = call_gemini_api(prompt, task_description)
    return script_text


# --- Main Application Flow ---
if __name__ == "__main__":
    print("✨ Welcome to the AI Travel Guide Script Generator! ✨")
    target_location = input("Enter the travel destination (e.g., 'Kyoto, Japan'): ").strip()
    if not target_location:
        print("No location entered. Exiting.")
        exit()

    default_local_language = "the local language of the destination" # Generic default
    location_lower = target_location.lower()
    if "japan" in location_lower or "tokyo" in location_lower or "kyoto" in location_lower or "osaka" in location_lower:
        default_local_language = "Japanese"
    elif "france" in location_lower or "paris" in location_lower:
        default_local_language = "French"
    elif "korea" in location_lower or "seoul" in location_lower:
        default_local_language = "Korean"
    elif "italy" in location_lower or "rome" in location_lower or "florence" in location_lower:
        default_local_language = "Italian"
    elif "spain" in location_lower or "barcelona" in location_lower or "madrid" in location_lower:
        default_local_language = "Spanish"


    print(f"\nInitiating travel guide generation for: {target_location}")
    print(f"Attempting to include insights from videos in: {default_local_language}")

    # Step 1: Discover Videos and get initial info
    # Use the full path to your venv's python if needed, e.g.,
    # "D:\\Path\\To\\Your\\venv\\Scripts\\python.exe your_script.py" when running from cmd
    # This script assumes it's run by the correct interpreter already.

    discovered_video_info = discover_videos_and_initial_info(target_location, default_local_language)

    if not discovered_video_info:
        print(f"🛑 No video information could be discovered for {target_location}. Exiting.")
        exit()

    print(f"\n✅ Discovered {len(discovered_video_info)} initial video candidates.")
    for i, vid_info in enumerate(discovered_video_info):
        print(f"  {i+1}. URL: {vid_info.get('url', 'N/A')}, Initial Info: {vid_info.get('info', 'N/A')}")


    # Step 2: Generate Detailed Summaries
    detailed_summaries = generate_detailed_summaries(discovered_video_info, target_location, default_local_language)

    if not detailed_summaries:
        print(f"🛑 No detailed summaries could be generated for {target_location}. Exiting.")
        exit()

    print(f"\n✅ Generated {len(detailed_summaries)} detailed summaries.")


    # Step 3: Generate Final Script
    final_script = generate_final_script(detailed_summaries, target_location)

    if final_script:
        print(f"\n🎉 Successfully generated the final video script for {target_location}! 🎉")
        print("\n--- Your Professional Travel Briefing Script ---")
        print(final_script)

        script_filename = f"{target_location.lower().replace(', ', '_').replace(' ', '_')}_travel_script.txt"
        try:
            with open(script_filename, "w", encoding="utf-8") as f:
                f.write(f"# Travel Briefing Script for: {target_location}\n\n")
                f.write(final_script)
            print(f"\n📄 Script also saved to {script_filename}")
        except Exception as e:
            print(f"⚠️ Error saving script to file: {e}")
    else:
        print(f"🛑 Failed to generate the final video script for {target_location}.")