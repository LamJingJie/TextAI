from openai import OpenAI, AsyncOpenAI, OpenAIError
from dotenv import load_dotenv, dotenv_values 
import os
import base64
import json

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


async def get_openai_response(client: AsyncOpenAI, new_img: str,  student_name: str, curr_page: str, prj_title: str, submission_date: str, desc: str, img_id: str, output: dict):
    content = {
        "desc": "",
        "keywords": []
    }

    completion = await client.chat.completions.create(
        model="gpt-4o-2024-11-20",
        messages = [
            {
                "role": "developer",
                "content": [
                    {
                        "type": "text",
                        "text": """Interpret the hidden meanings, emotions, and messages conveyed by the abstract image. Provide a detailed explanation, including any possible symbolic or metaphorical interpretations. 
                                    Provide a list of keywords and a description. If the image contains text, return the text as the description and extract keywords from it. 
                                    Minimum 1 keyword, maximum 5 keywords. Minimum 40 description words.""",
                    },
                    {
                        "type": "context",
                        "context": f"Consider the following context: Student: {student_name}, Project title: {prj_title}, Page: {curr_page}, Context of the image: {desc}",
                    }
                ],

                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{new_img}",
                            "detail": "high", # 768 x 2048, expensive but btr quality output
                        }
                    }
                ]
            },
        ],

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "image_content",
                "strict": True, # Enforce the response schema strictly
                "schema": {
                    "type": "object",
                    "properties": {
                        "desc": {
                            "description": "Description of the abstract image",
                            "type": "string"
                        },

                        "keywords": {
                            "description": "Keywords of the abstract image",
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                        }
                    },
                    "required": ["desc", "keywords"],
                    "additionalProperties": False # Disallow properties not defined in the schema
                }
            }
        },

        max_tokens=3000,
    )
    # Convert json str to dict
    response_data: dict = json.loads(completion.choices[0].message.content)
    content["desc"] = response_data["desc"]
    content["keywords"] = response_data["keywords"]
    key = f"{prj_title}__{curr_page}__{submission_date}__{student_name}__{img_id}"
    output[key] = content