# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types


from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from app.a2ui_utils import a2ui_callback
from app.firestore_tools import get_item_by_id, read_items, write_item
from app.image_tools import generate_item_image
from app.maps_tools import geocode_address, search_nearby_places
from app.rag_tools import consult_herbal_corpus
from app.video_tools import generate_item_video


async def generate_memories_callback(callback_context: CallbackContext):
    if hasattr(callback_context, "events") and callback_context.events:
        await callback_context.add_events_to_memory(events=callback_context.events)
    await callback_context.add_session_to_memory()
    return None


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


import json
import urllib.parse
import urllib.request


def get_live_weather_and_aqi(location: str) -> str:
    """Gets real-time live weather and air quality index (AQI) for a given location using the Open-Meteo API.

    Args:
        location: City or location name (e.g. 'San Francisco', 'New York', 'Tokyo').

    Returns:
        A formatted string summarizing live weather, temperature, humidity, wind, and US Air Quality Index.
    """
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(location)}&count=1"
        req = urllib.request.Request(geo_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            geo_data = json.loads(response.read().decode("utf-8"))

        if not geo_data.get("results"):
            return f"Could not find coordinates for location: {location}"

        res = geo_data["results"][0]
        lat, lon = res["latitude"], res["longitude"]
        city_name = res.get("name", location)
        country = res.get("country", "")

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        req = urllib.request.Request(weather_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            weather_data = json.loads(response.read().decode("utf-8"))

        aqi_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=us_aqi"
        req = urllib.request.Request(aqi_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            aqi_data = json.loads(response.read().decode("utf-8"))

        curr_weather = weather_data.get("current", {})
        curr_aqi = aqi_data.get("current", {})

        temp_c = curr_weather.get("temperature_2m", "N/A")
        temp_f = round(temp_c * 9 / 5 + 32, 1) if isinstance(temp_c, (int, float)) else "N/A"
        humidity = curr_weather.get("relative_humidity_2m", "N/A")
        wind_kmh = curr_weather.get("wind_speed_10m", "N/A")
        aqi = curr_aqi.get("us_aqi", "N/A")

        return (
            f"Live Weather & Air Quality for {city_name}, {country}:\n"
            f"- Temperature: {temp_c}°C ({temp_f}°F)\n"
            f"- Humidity: {humidity}%\n"
            f"- Wind Speed: {wind_kmh} km/h\n"
            f"- Air Quality Index (US AQI): {aqi}"
        )
    except Exception as e:
        return f"Error fetching live weather for {location}: {e}"


def get_wikipedia_summary(topic: str) -> str:
    """Fetches a concise real-world Wikipedia summary for a given topic, food item, or health condition.

    Args:
        topic: The topic, item, or term to research (e.g. 'Peanut allergy', 'Quinoa', 'Artificial intelligence').

    Returns:
        A formatted string summary and reference URL.
    """
    import os
    api_key = os.getenv("WIKIPEDIA_API_KEY", "")
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(topic)}"
        headers = {"User-Agent": "AntigravityAgent/1.0 (contact@example.com)"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))

        title = data.get("title", topic)
        extract = data.get("extract", "No summary available.")
        content_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")

        return f"Wikipedia Summary for '{title}':\n{extract}\nReference URL: {content_url}"
    except Exception as e:
        return f"Error fetching Wikipedia summary for '{topic}': {e}"


code_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name="projects/934521868830/locations/us-east1/reasoningEngines/3944636503111499776/sandboxEnvironments/122529575799357440",
    agent_engine_resource_name="projects/934521868830/locations/us-east1/reasoningEngines/3944636503111499776",
)

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are 'Culpeper Herbalist Agent' (also known as Culpeper Herbal AI), a specialized herbalist and domain assistant. "
        "Your official name is 'Culpeper Herbalist Agent'. "
        "When asked about your name, who you are, or what your work is, state clearly: 'My name is Culpeper Herbalist Agent' "
        "and explain that your work is to consult 'Culpeper's Complete Herbal' (1653) to provide authentic historical herbal remedies, "
        "medicinal plant virtues, manage domain items in your database, generate images for domain items, and assist with related location queries. "
        "STRICT TOPIC BOUNDARY: You MUST strictly keep the conversation focused on your domain data (Culpeper's herbal remedies, medicinal plants, domain items, and related plant/location tools). "
        "If a user asks about completely out-of-scope topics (e.g. pop culture, sports, financial advice, or unrelated programming), politely explain that as Culpeper Herbalist Agent, your work is strictly dedicated to herbal remedies and domain knowledge."
    ),
    workflow_description=(
        "Analyze the user request, call tools as needed (`consult_herbal_corpus`, `generate_item_image`, `generate_item_video`, "
        "`geocode_address`, `search_nearby_places`, `get_live_weather_and_aqi`, `read_items`, `write_item`), "
        "and return structured A2UI UI when appropriate."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=code_executor,
    instruction=instruction,
    tools=[
        consult_herbal_corpus,
        generate_item_image,
        generate_item_video,
        geocode_address,
        search_nearby_places,
        get_live_weather_and_aqi,
        get_wikipedia_summary,
        get_weather,
        get_current_time,
        read_items,
        get_item_by_id,
        write_item,
        PreloadMemoryTool(),
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
