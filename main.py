import os
from dotenv import load_dotenv, dotenv_values 
from openai import OpenAI, AsyncOpenAI, OpenAIError

load_dotenv()

client = OpenAI(
    api_key = os.getenv('OPENAI_API_KEY')
    )