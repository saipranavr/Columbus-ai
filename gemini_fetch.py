import os
import json # For parsing potential JSON in Gemini's responses
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
# To enable Google Search for grounding, you might need to configure tools.
# For RAG (Retrieval Augmented Generation) style grounding:
# from google.generativeai.types import Tool, GoogleSearchRetrieval

# --- Configuration ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("🛑 GEMINI_API_KEY not found in .env file. Please create it.")
    exit()

# Configure the Gemini model
# Using a model that supports grounding well.
MODEL_NAME = "gemini-1.5-flash-latest" # More standard and capable model

# Standard safety settings
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

genai.configure(api_key=GEMINI_API_KEY)

# OPTIONAL: For more explicit grounding, especially RAG-style, you might configure tools.
# If you want the model to explicitly use Google Search and potentially cite sources,
# you might add a search tool. For simpler "use your internal knowledge which is search-backed",
# strong prompting with a capable model is often the first step.
# Example of enabling a search tool for broader grounding (RAG-focused but can help):
# search_tool = Tool.from_Google Search_retrieval(Google Search_retrieval=GoogleSearchRetrieval())
# model = genai.GenerativeModel(MODEL_NAME, safety_settings=SAFETY_SETTINGS, tools=[search_tool])
# For now, we will rely on the model's inherent capabilities and strong prompting.
model = genai.GenerativeModel(MODEL_NAME, safety_settings=SAFETY_SETTINGS)


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
            # Try to print more debugging info if available
            # print(f"Debug: Full response object: {response}")
            # print(f"Debug: Prompt feedback: {response.prompt_feedback}")
            # print(f"Debug: Finish reason: {response.candidates[0].finish_reason if response.candidates else 'N/A'}")
            return None
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
        # Attempt to parse if Gemini returns a JSON string
        data = json.loads(response_text)
        if isinstance(data, list) and all("url" in item and "info" in item for item in data):
            return data
    except json.JSONDecodeError:
        # Fallback to line-by-line parsing
        current_url = None
        current_info = None
        for line in response_text.splitlines():
            line_strip = line.strip()
            if not line_strip: # Skip empty lines
                continue

            line_lower = line_strip.lower()
            # More robust parsing for URL and Info lines
            if line_lower.startswith("url:") or (line_lower.startswith(tuple(str(i) + "." for i in range(1,10))) and "url:" in line_lower) :
                if current_url and current_info: # Save previous entry
                    videos.append({"url": current_url.strip(), "info": current_info.strip()})
                try:
                    current_url = line_strip.split(":", 1)[1].strip()
                except IndexError:
                    print(f"Warning: Could not parse URL from line: {line_strip}")
                    current_url = None # Invalid line
                current_info = None # Reset info for new URL
            elif line_lower.startswith("info:") and current_url:
                try:
                    current_info = line_strip.split(":", 1)[1].strip()
                except IndexError:
                    print(f"Warning: Could not parse Info from line: {line_strip}")
                    current_info = "Info not parsed"
            elif current_info and current_url: # Continuation of multi-line info
                 current_info += " " + line_strip

        if current_url and current_info: # Save the last entry
            videos.append({"url": current_url.strip(), "info": current_info.strip()})

    if not videos:
         print("⚠️ Could not parse video URLs and info from Gemini's discovery response. Ensure the prompt asks for a clear format.")
         print(f"   Raw response was: {response_text[:500]}")

    return videos


# --- Core Functions ---

def discover_videos_and_initial_info(location, local_language_name, num_videos_total=7, num_local_videos=2):
    """
    Asks Gemini to discover video URLs and provide initial info, using its search capabilities.
    """
    task_description = f"Video Discovery for {location} (with grounding)"
    prompt = f"""
    You are a helpful travel research assistant. I need to find YouTube video information for a travel guide about "{location}".

    Please use your Google Search capabilities to find {num_videos_total} YouTube video URLs that would be highly relevant for a tourist.
    Focus on videos covering:
    - Popular landmarks and attractions.
    - Local restaurants and unique cuisine (not just tourist traps).
    - Tips for using convenience stores effectively.
    - General travel tips and cultural insights for "{location}".

    IMPORTANT:
    1. Include approximately {num_local_videos} videos that are likely in the {local_language_name} language, as these might contain unique local recommendations not typically found in English tourist guides. The rest should be in English.
    2. For EACH video, provide:
        a. The full YouTube URL.
        b. A brief (1-2 sentence) initial piece of information, like the video's likely title or its main topic, based on search results (e.g., video metadata).
    3. Ground your suggestions by finding videos that seem informative, recent, and from knowledgeable creators. Prioritize relevance and quality.

    Present the information clearly for each video. For example:
    1. URL: [video_url_1]
       Info: [brief_info_about_video_1 based on search]
    2. URL: [video_url_2]
       Info: [brief_info_about_video_2_in_{local_language_name}_if_applicable based on search]
    ... and so on.

    Do not include any other commentary before or after this list.
    """
    response_text = call_gemini_api(prompt, task_description)
    if response_text:
        return parse_video_discovery_response(response_text)
    return []


def generate_detailed_summaries(video_info_list, location, local_language_name):
    """
    Generates detailed summaries for each video using Gemini, grounded by search.
    """
    all_summaries = []
    if not video_info_list:
        print("No video information provided to generate summaries.")
        return all_summaries

    print(f"\n--- Generating Detailed Summaries for {len(video_info_list)} videos (with grounding) ---")
    for i, video_info in enumerate(video_info_list):
        url = video_info.get("url")
        initial_info = video_info.get("info", "No initial info provided.")
        task_description = f"Detailed Summary for video {i+1} ({url}) (with grounding)"

        prompt = f"""
        You are a helpful travel content analyst.
        Consider a YouTube video with the URL: {url}
        The video is likely about: "{initial_info}"

        Task:
        Leverage your Google Search capabilities to find publicly available information about this video (such as its title, description, channel, and any available transcripts or summaries, if possible) to understand its content more deeply.
        Based on this searched information:
        1. Generate a concise but detailed summary in ENGLISH (approximately 150-250 words).
        2. The summary MUST focus on extracting the following types of information if likely present in the video's content:
            - Key landmarks or attractions mentioned or shown.
            - Specific restaurants, food stalls, or types of local cuisine recommended.
            - Any tips or information regarding local convenience stores (e.g., useful items, services).
            - Unique local travel tips, cultural insights, or hidden gems suggested.
        3. If the video's initial info suggests it might be in {local_language_name}, use your search capabilities to understand its content and pay special attention to extracting unique local insights. Ensure the entire summary is in clear English.
        4. Ensure the summary is plausible, credible, and accurately reflects the likely content of the video based on your search.

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
    Generates the final YouTube video script, grounded with search for accuracy.
    """
    if not summaries:
        print("No summaries provided to generate the final script.")
        return None

    task_description = f"Final Video Script for {location} (with grounding)"
    formatted_summaries_text = "\n\n---\n\n".join(
        f"Insights from Video (likely about: {s['initial_info']} based on URL: {s['url']}):\n{s['detailed_summary']}" # Added URL for context
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
        * **Catchy Introduction:** Hook the viewer and introduce "{location}".
        * **Popular Landmarks & Attractions:** Highlight key sights.
        * **Local Cuisine & Restaurants:** Showcase food experiences.
        * **Convenience Store Wisdom:** Integrate tips if available.
        * **Unique Travel Tips & Hidden Gems:** Include standout advice.
        * **Cultural Insights (if any):** Weave in cultural context.
        * **Friendly Outro:** Thank viewers.
    5.  **Grounding & Credibility:**
        * Base the script *primarily* on the provided insights.
        * **Crucially, use your Google Search capabilities to:**
            * Verify the spelling, current names, and basic factual details (e.g., "Is X still open?", "What is Y famous for?") of places, restaurants, or specific items mentioned in the summaries.
            * Add a brief, verifiable, interesting fact or up-to-date context to 1-2 key landmarks or dishes if it enhances the script and fits naturally. These facts should be confirmable via a quick search.
            * Ensure any specific claims (e.g., "best ramen") are presented as opinions from the source videos (e.g., "One vlogger raved about this being the best ramen they had...") unless widely verifiable as objective facts through your search.
    6.  **Style & Tone:**
        * Enthusiastic, friendly, authentic, and informative. Like a popular travel vlogger.
        * Include cues for visuals (e.g., "[Show footage of Kiyomizu-dera Temple]", "[Close up of delicious takoyaki]").
    7.  **Structure:** Organize with clear segments. Use conversational language.

    Do not invent information not supported by the provided summaries or your grounded verification. If a detail from a summary seems dubious or outdated after your search, omit it or cautiously qualify it.
    Provide only the complete script.
    """
    script_text = call_gemini_api(prompt, task_description)
    return script_text


# --- Main Application Flow ---
if __name__ == "__main__":
    print("✨ Welcome to the AI Travel Guide Script Generator! (Grounding Enabled) ✨")
    target_location = input("Enter the travel destination (e.g., 'Kyoto, Japan'): ").strip()
    if not target_location:
        print("No location entered. Exiting.")
        exit()

    default_local_language = "the local language of the destination"
    # Improved language detection (simple version)
    target_location_lower = target_location.lower()
    if "japan" in target_location_lower or "tokyo" in target_location_lower or "kyoto" in target_location_lower or "osaka" in target_location_lower:
        default_local_language = "Japanese"
    elif "france" in target_location_lower or "paris" in target_location_lower:
        default_local_language = "French"
    elif "korea" in target_location_lower or "seoul" in target_location_lower:
        default_local_language = "Korean"
    elif "germany" in target_location_lower or "berlin" in target_location_lower:
        default_local_language = "German"
    elif "spain" in target_location_lower or "madrid" in target_location_lower or "barcelona" in target_location_lower:
        default_local_language = "Spanish"
    elif "italy" in target_location_lower or "rome" in target_location_lower:
        default_local_language = "Italian"


    print(f"Searching for videos related to: {target_location}")
    print(f"Will try to include some videos in: {default_local_language}")

    # Step 1: Discover Videos and get initial info
    discovered_video_info = discover_videos_and_initial_info(target_location, default_local_language)

    if not discovered_video_info:
        print(f"🛑 No video information could be discovered for {target_location}. Exiting.")
        exit()

    print(f"\n✅ Discovered {len(discovered_video_info)} initial video candidates.")
    for i, vid_info in enumerate(discovered_video_info):
        print(f"  {i+1}. URL: {vid_info.get('url','N/A')}, Initial Info: {vid_info.get('info','N/A')}")


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
        file_friendly_location = target_location.replace(', ', '_').replace(' ', '_')
        output_filename = f"{file_friendly_location}_travel_script.txt"
        try:
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(final_script)
            print(f"\n📄 Script also saved to {output_filename}")
        except Exception as e:
            print(f"\n⚠️ Could not save script to file: {e}")
    else:
        print(f"🛑 Failed to generate the final video script for {target_location}.")