import uuid
from google import genai
from google.genai import types
from google.cloud import storage
from google.adk.tools import ToolContext

BUCKET_NAME = "simple-test-agent-assets-597eb"
PROJECT_ID = "qwiklabs-gcp-01-597eb0775984"


async def generate_item_video(item_name: str, tool_context: ToolContext) -> str:
    """Generate a short video for an item in the agent's domain using gemini-omni-flash-preview in the global region.

    Saves the video as a session artifact and uploads it to public Cloud Storage, returning the public HTTPS URL.

    Args:
        item_name: The name of the item, herb, plant, or remedy to generate a video for.
        tool_context: ADK ToolContext for saving artifacts.

    Returns:
        The public Cloud Storage HTTPS URL of the generated video.
    """
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    prompt = f"A detailed, short botanical and natural remedy video showing {item_name} in its natural environment."

    response = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=prompt,
    )

    video_bytes = None
    if getattr(response, "output_video", None) and getattr(response.output_video, "data", None):
        video_bytes = response.output_video.data

    if not video_bytes:
        return "Error: Failed to generate video bytes from gemini-omni-flash-preview."

    filename = f"{item_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}.mp4"

    # 1. Save artifact with tool_context.save_artifact so it shows in Playground Artifacts panel
    if tool_context:
        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload video bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type="video/mp4")

    return f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
