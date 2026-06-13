from google import genai
import os

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

models = client.models.list()

for m in models:
    print(m.name)
