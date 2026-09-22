import uuid
from google import genai
from google.genai import types
from google.cloud import storage
from google.adk.tools import ToolContext

BUCKET_NAME = "simple-test-agent-assets-597eb"
PROJECT_ID = "qwiklabs-gcp-01-597eb0775984"


async def generate_item_image(item_name: str, tool_context: ToolContext) -> str:
    """Generate an image for an item in the agent's domain using gemini-3.1-flash-lite-image in the global region.

    Saves the image as a session artifact and uploads it to public Cloud Storage, returning the public HTTPS URL.

    Args:
        item_name: The name of the item, herb, plant, or remedy to generate an image for.
        tool_context: ADK ToolContext for saving artifacts.

    Returns:
        The public Cloud Storage HTTPS URL of the generated image.
    """
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    prompt = f"A detailed, high quality botanical and natural remedy illustration of {item_name}."

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"]
        ),
    )

    image_bytes = None
    for part in response.candidates[0].content.parts:
        if getattr(part, "inline_data", None) and part.inline_data.data:
            image_bytes = part.inline_data.data
            break

    if not image_bytes:
        return "Error: Failed to generate image bytes."

    filename = f"{item_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}.jpg"

    # 1. Save artifact with tool_context.save_artifact
    if tool_context:
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type="image/jpeg")

    return f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
