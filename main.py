import os
from dotenv import load_dotenv, dotenv_values 
import asyncio
from app.openai.main import initialize_openAI
from app.playwright.main import get_page_data_playwright, get_all_pages_playwright
from multiprocessing import Lock, Pool, Manager, cpu_count, Queue
from concurrent.futures import ProcessPoolExecutor
import base64
from requests import Response
import requests
from yarl import URL
from PIL import Image

# *Main Flow*
# 1. Load environment variables (done)
# 2. Add client input functuionality (done)
# 3. Initialize openai client (Done)
# 4. retrieve json data from tldraw using playwright (Done)
# 5. Get relevent data from json (Done)
# 5. Send data to openai (URL or Base64) (Resize them before sending)
# 6. Get response from openai
# 7. Process response (figure out how to store the desc and keywords for each of the img)

# Use async programming and multi-processing


# Example: https://www.tldraw.com/r/fOZmgi9MQzQc-rrXnpAz6?v=-167,-196,5343,2630&p=HGtpLC0ipiTvgK6awql7m


async def main(processors: ProcessPoolExecutor):
    pages_json_content: list = []
    client = await initialize_openAI()
    # await get_page_data_playwright()
    targets, url = await cmd_user_input()

    # Get relevent JSON data from tldraw
    for target in targets:
        pages_json_content.append(get_page_data_playwright(url, target, processors))
    
    # None value = error occured and should be ignored

    # Wait for all pages to be processed and returns back an array
    pages_json_content = await asyncio.gather(*pages_json_content)

    
    for page in pages_json_content:
        for img in page['all_student_imgs']:
            #Find img in assets
            processors.submit(process_img_openai, img[0], page['assets'], img[1])


# abit CPU-intensive :> (TMR TASKS)------
# Tasks:
# a) Resize img to fit openAI vision model specs
# b) Send img to openAI
# c) Get response (desc n keywords)
# d) Store response and that img name, along with student name. Store as JSON file
def process_img_openai(student_img_id, assets, student_name):
    for asset in assets:
        if student_img_id == asset['id']:
            resize_img(asset['props']['src'])
            print('Found img for', student_name)


def resize_img(img_data: str | URL):
    # get raw img data (bytes)
    if img_data.startswith('data:image') and img_data.find('base64,') != -1:
        # Is base64 data
        base64_index = img_data.find('base64,') + len('base64,')
        img_data = base64.b64decode(img_data[base64_index:])
    else:
        # is URL
        response: Response = requests.get(img_data)
        if response.status_code == 200:
            img_data = response.content
        else:
            # Unable to retrieve img data (bytes) from url
            print("Fail")
            return
    print("Success")
    image = Image.open(img_data)

    # Resize img for 'high res' mode. Short side <= 768px and Long side <= 2000px

    

# What the user will see
async def cmd_user_input():
    url = ""
    targets = []

    while url == "":
        url = input("Tldraw project url: ").strip()
    
    print("\nType 'ALL' to extract all pages. Otherwise, type the page name(s) u wish to extract.\nWhen finished type 'DONE'.\n")
    while True:
        val = input("::").lower().strip()

        if len(targets) == 0 and val == "all":
            # Extract all pages
            try:
                targets = await get_all_pages_playwright(url)
            except Exception as e:
                print(e)
                exit()
            break

        # Done adding pages
        if val == "done": break

        if val != "": targets.append(val)

    return targets, url


if __name__ == "__main__":
    # Load the environment variables from .env file
    load_dotenv()

    # Initialize mp
    manager = Manager()
    processors = ProcessPoolExecutor(max_workers=10)

    asyncio.run(main(processors))


