import os
from dotenv import load_dotenv, dotenv_values 
from openai import OpenAI, AsyncOpenAI, OpenAIError
import asyncio
from openai_api import initialize_openAI
from playwright_api import get_page_data_playwright, get_all_pages_playwright
from playwright.async_api import async_playwright, Page, BrowserContext, ElementHandle, Browser
from multiprocessing import Lock, Pool, Manager, cpu_count, Queue
from concurrent.futures import ProcessPoolExecutor

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


# TASKS:
            # Get img using the assetId
            # Resize the img to fit openAI vision model - high quality
            # Send the img to openAI


# Example: https://www.tldraw.com/r/fOZmgi9MQzQc-rrXnpAz6?v=-167,-196,5343,2630&p=HGtpLC0ipiTvgK6awql7m


async def main(processors: ProcessPoolExecutor):
    pages_json_content = []
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


# abit CPU-intensive :>
# Tasks:
# a) Resize img to fit openAI vision model specs
# b) Send img to openAI
# c) Get response (desc n keywords)
# d) Store response and that img name, along with student name. Store as JSON file
def process_img_openai(student_img_id, assets, student_name):
    for asset in assets:
        if student_img_id == asset['id']:
            print('Found img for', student_name)



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


