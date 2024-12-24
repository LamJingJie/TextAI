from openai import OpenAI, AsyncOpenAI, OpenAIError
from dotenv import load_dotenv, dotenv_values 
import os

# Initialize openai client
# Use gpt-4o vision model
# Take into account error handling when output is invalid (e.g.)
# Use structured output
# Async programming


# Considerations
# - Using batch processing (Takes up to 24hrs but much cheaper)

async def initialize_openAI():
    client = AsyncOpenAI(
        api_key = os.getenv('OPENAI_API_KEY')
    )
    return client
