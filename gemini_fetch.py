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
# IMPORTANT: For actual grounding with Google Search,
# the API setup (e.g., Vertex AI, AI Studio with tools enabled) is crucial.
# This script simulates the *intent* of grounding in the prompts.
# The specific model name might change based on availability (e.g., "gemini-1.5-flash-latest")
MODEL_NAME = "gemini-2.0-flash" # Use the appropriate latest model identifier

# Standard safety settings (adjust if necessary, but usually good defaults)
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(MODEL_NAME, safety_settings=SAFETY_SETTINGS)


def call_gemini_api(prompt_text, task_description="task"):
    """
    Calls the Gemini API with the given prompt.
    Includes basic error handling and prints status.
    For a hackathon, this might use mock data if live calls are too slow/costly.
    """
    print(f"\n🤖 Sending prompt to Gemini for: {task_description}...")
    # print(f"   Prompt snippet: {prompt_text[:250].replace('\n', ' ')}...\n")
    try:
        # --- THIS IS WHERE THE ACTUAL API CALL HAPPENS ---
        # For actual grounding, ensure your API client/model is configured with search tools.
        response = model.generate_content(prompt_text)
        # --- END OF ACTUAL API CALL ---

        # print(f"💎 Gemini Raw Response Text (snippet for {task_description}): {response.text[:100]}...")
        if response.text:
            return response.text
        else:
            # Handle cases where response.text might be empty but parts exist
            # (though usually .text is populated for successful generations)
            if response.parts:
                return "".join(part.text for part in response.parts if hasattr(part, 'text'))
            print(f"⚠️ Gemini response for {task_description} was empty or had no text part.")
            return None

    except Exception as e:
        print(f"🛑 Error calling Gemini API for {task_description}: {e}")
        # print(f"   Full prompt that caused error: {prompt_text}") # For debugging
        return None

def parse_video_discovery_response(response_text):
    """
    Parses Gemini's response to extract video URLs and their initial info.
    This is a simple parser; more robust parsing might be needed for complex outputs.
    Assumes Gemini might return something like:
    1. URL: [url1]
       Info: [info1]
    2. URL: [url2]
       Info: [info2]
    Or a JSON-like structure.
    """
    videos = []
    if not response_text:
        return videos

    try:
        # Attempt to parse if Gemini returns a JSON string
        # (You might need to prompt Gemini to return JSON for easier parsing)
        data = json.loads(response_text)
        if isinstance(data, list) and all("url" in item and "info" in item for item in data):
            return data
    except json.JSONDecodeError:
        # Fallback to line-by-line parsing if not valid JSON
        current_url = None
        current_info = None
        for line in response_text.splitlines():
            line_lower = line.lower()
            if "url:" in line_lower:
                if current_url and current_info: # Save previous entry
                    videos.append({"url": current_url.strip(), "info": current_info.strip()})
                current_url = line.split(":", 1)[1].strip()
                current_info = None # Reset info for new URL
            elif "info:" in line_lower and current_url:
                current_info = line.split(":", 1)[1].strip()
            elif current_info and current_url: # Continuation of multi-line info
                 current_info += " " + line.strip()

        if current_url and current_info: # Save the last entry
            videos.append({"url": current_url.strip(), "info": current_info.strip()})

    if not videos:
         print("⚠️ Could not parse video URLs and info from Gemini's discovery response. Ensure the prompt asks for a clear format.")
         print(f"   Raw response was: {response_text[:500]}") # Show part of what was received

    return videos


# --- Core Functions ---

def discover_videos_and_initial_info(location, local_language_name, num_videos_total=7, num_local_videos=2):
    """
    Asks Gemini to discover video URLs and provide initial info about them.
    """
    task_description = f"Video Discovery for {location}"
    prompt = f"""
    You are a helpful travel research assistant. I need to find YouTube video information for a travel guide about "{location}".

    Please find {num_videos_total} YouTube video URLs that would be highly relevant for a tourist.
    Focus on videos covering:
    - Popular landmarks and attractions.
    - Local restaurants and unique cuisine (not just tourist traps).
    - Tips for using convenience stores effectively.
    - General travel tips and cultural insights for "{location}".

    IMPORTANT:
    1. Include approximately {num_local_videos} videos that are likely in the {local_language_name} language, as these might contain unique local recommendations not typically found in English tourist guides. The rest should be in English.
    2. For EACH video, provide:
        a. The full YouTube URL.
        b. A brief (1-2 sentence) initial piece of information, like the video's likely title or its main topic, to give context.
    3. Ground your suggestions using your knowledge and simulated search capabilities to ensure relevance and potential quality. Try to find videos that seem informative or from knowledgeable creators.

    Present the information clearly for each video. For example:
    1. URL: [video_url_1]
       Info: [brief_info_about_video_1]
    2. URL: [video_url_2]
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
        else:
            print(f"  ⚠️ Failed to generate summary for video {i+1}.")
    return all_summaries


def generate_final_script(summaries, location):
    """
    Generates the final YouTube video script based on all collected summaries.
    """
    if not summaries:
        print("No summaries provided to generate the final script.")
        return None

    task_description = f"Final Video Script for {location}"
    formatted_summaries_text = "\n\n---\n\n".join(
        f"Insights from Video (likely about: {s['initial_info']}):\n{s['detailed_summary']}"
        for s in summaries
    )

    prompt = f"""
    You are an expert YouTube travel vlogger scriptwriter.
    Your task is to create an engaging, informative, and credible YouTube video script for a travel guide about "{location}".

    You have been provided with detailed insights extracted from several relevant YouTube videos. These insights are below:
    --- BEGIN INSIGHTS ---
    {formatted_summaries_text}
    --- END INSIGHTS ---

    Script Requirements:
    1.  **Overall Goal:** Synthesize these insights into a coherent, engaging vlog-style script.
    2.  **Length:** Aim for a script that would be approximately 5-7 minutes of speaking time.
    3.  **Language:** English.
    4.  **Content Sections (ensure these are covered if information is available in the insights):**
        *   **Catchy Introduction:** Hook the viewer and introduce "{location}".
        *   **Popular Landmarks & Attractions:** Highlight key sights from the insights.
        *   **Local Cuisine & Restaurants:** Showcase food experiences, specific dishes, or restaurant types mentioned. Emphasize any unique local recommendations.
        *   **Convenience Store Wisdom:** If there are tips about local convenience stores, integrate them.
        *   **Unique Travel Tips & Hidden Gems:** Include any standout advice or lesser-known spots from the insights.
        *   **Cultural Insights (if any):** Weave in any cultural context provided.
        *   **Friendly Outro:** Thank viewers and encourage them to visit or engage.
    5.  **Grounding & Credibility:**
        *   Base the script *primarily* on the provided insights.
        *   You may use your simulated Google Search capabilities to:
            *   Verify the spelling or current names of places mentioned in the summaries.
            *   Add a brief, verifiable, interesting fact or context to 1-2 key landmarks or dishes if it enhances the script and fits naturally.
            *   Ensure any specific claims (e.g., "best ramen") are presented as opinions from the source videos rather than absolute facts, unless widely verifiable.
    6.  **Style & Tone:**
        *   Enthusiastic, friendly, authentic, and informative.
        *   Like a popular travel vlogger.
        *   Include cues for visuals (e.g., "[Show footage of Kiyomizu-dera Temple]", "[Close up of delicious takoyaki]").
    7.  **Structure:** Organize with clear segments. Use conversational language.

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

    # You might want to infer local language or ask the user
    # For simplicity, let's assume English for local videos if not specified,
    # or you can have a mapping or ask the user.
    # Example: for "Kyoto, Japan", local lang is "Japanese"
    default_local_language = "the local language of the destination"
    if "japan" in target_location.lower() or "tokyo" in target_location.lower() or "kyoto" in target_location.lower():
        default_local_language = "Japanese"
    elif "france" in target_location.lower() or "paris" in target_location.lower():
        default_local_language = "French"
    elif "korea" in target_location.lower() or "seoul" in target_location.lower():
        default_local_language = "Korean"
    # Add more mappings as needed or ask the user

    print(f"Searching for videos related to: {target_location}")
    print(f"Will try to include some videos in: {default_local_language}")

    # Step 1: Discover Videos and get initial info
    discovered_video_info = discover_videos_and_initial_info(target_location, default_local_language)

    if not discovered_video_info:
        print(f"🛑 No video information could be discovered for {target_location}. Exiting.")
        exit()

    print(f"\n✅ Discovered {len(discovered_video_info)} initial video candidates.")
    for i, vid_info in enumerate(discovered_video_info):
        print(f"  {i+1}. URL: {vid_info['url']}, Initial Info: {vid_info['info']}")


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
        print("\n--- Your Travel Guide Video Script ---")
        print(final_script)

        # Optionally, save to a file
        # with open(f"{target_location.replace(', ', '_').replace(' ', '_')}_travel_script.txt", "w", encoding="utf-8") as f:
        #     f.write(final_script)
        # print(f"\n📄 Script also saved to {target_location.replace(', ', '_').replace(' ', '_')}_travel_script.txt")
    else:
        print(f"🛑 Failed to generate the final video script for {target_location}.")