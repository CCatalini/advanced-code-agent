import os
from dotenv import load_dotenv
from anthropic import Anthropic

# File to test the connection to the Anthropic API
load_dotenv()
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

response = client.messages.create(
    model=os.environ["ANTHROPIC_MODEL"],
    max_tokens=200,
    messages=[{"role": "user", "content": "Decime hola en una frase"}]
)
print(response.content[0].text)
