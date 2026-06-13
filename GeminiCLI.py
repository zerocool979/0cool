from google import genai
import os

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

response = client.models.generate_content(
    model="models/gemini-2.5-flash",
    contents="Jawab dengan singkat: Bagaimana cara mmengubur ayam seberat 70kg?)")

print(response.text)
