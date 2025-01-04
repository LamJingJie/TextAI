from dotenv import load_dotenv, dotenv_values 
import asyncio
from app.openai.main import initialize_openAI, AsyncOpenAI, get_openai_response
from app.playwright.main import get_page_data_playwright, get_all_pages_playwright
from multiprocessing import Lock, Pool, Manager, cpu_count, Queue
from concurrent.futures import ProcessPoolExecutor, Future, wait
import base64
from requests import Response
import requests
from yarl import URL
from PIL import Image, ImageFile
from io import BytesIO
import json
import sys
import threading
import time

# *Main Flow*
# 1. Load environment variables (done)
# 2. Add client input functuionality (done)
# 3. Initialize openai client (Done)
# 4. retrieve json data from tldraw using playwright (Done)
# 5. Get relevent data from json (Done)
# 5. Send data to openai (URL or Base64) (Resize them before sending) (DONE)
# 6. Get response from openai (DONE)
# 7. Process response (figure out how to store the desc and keywords for each of the img) (DONE)

# *Considerations*
# - Add error handling


# Use async programming and multi-processing


# Example: https://www.tldraw.com/r/fOZmgi9MQzQc-rrXnpAz6?v=-167,-196,5343,2630&p=HGtpLC0ipiTvgK6awql7m


async def main(processors: ProcessPoolExecutor):
    pages_json_content: list = []
    client: AsyncOpenAI = await initialize_openAI()
    targets, url = await cmd_user_input()

    stop_loading_success = threading.Event()
    stop_loading_failure = threading.Event()
    loading_thread = threading.Thread(target=loading_screen, args = (stop_loading_success, stop_loading_failure))
    loading_thread.start()

    # Get relevent JSON data from tldraw
    for target in targets:
        pages_json_content.append(get_page_data_playwright(url, target, processors))
    
    # None value = error occured and should be ignored

    # Wait for all pages to be processed and returns back an array
    pages_json_content = await asyncio.gather(*pages_json_content)
    pages_json_content = [data for data in pages_json_content if data is not None]

    # If all pages are invalid, exit program
    if len(pages_json_content) == 0:
        stop_loading_failure.set()
        loading_thread.join()
        return None


    # Process imgs in each page
    futures: list[Future] = []
    for page in pages_json_content:
        for img in page['all_student_imgs']:
            # Transform all imgs seperately, in PARALLEL (multi-processing)
            future = processors.submit(process_img, img[0], page['assets'], img[1], page['target'], page['prj_title'], page['date'], page['desc'])
            futures.append(future)
    

    # Wait for all images to be processed
    done, notdone = wait(futures, return_when="ALL_COMPLETED")
    done = [future for future in done if future.result() is not None]

    # If all images are invalid, exit program
    if len(done) == 0:
        stop_loading_failure.set()
        loading_thread.join()
        return None

    
    # Array of processed imgs from selected pages
    openai_img_output: dict = {}
    tasks: list = []
    for future in done:
        new_img, student_name, curr_page, prj_title, submission_date, desc, student_img_id = future.result()

        # Send img to openAI 4o vision model asynchronously
        tasks.append(get_openai_response(client, new_img, student_name, curr_page, prj_title, submission_date, desc, student_img_id, openai_img_output))


    # Wait for all imgs to be processed by openAI, returns back an array[obj]
    await asyncio.gather(*tasks)


    # If all images are unable to be processed by openAI, exit program
    if len(openai_img_output.keys()) == 0:
        stop_loading_failure.set()
        return None
    

    try:
        # save output to a json file
        with open('output.json', 'w') as opt:
            json.dump(openai_img_output, opt, indent=4)
    except Exception as e:
        print(f"\rError saving output to file: {e}\n")
        stop_loading_failure.set()
        loading_thread.join()
        return None

    stop_loading_success.set()
    loading_thread.join()



# General loading screen for the entire program
def loading_screen(stop_loading_success: threading.Event, stop_loading_failure: threading.Event):
    position = 0
    sys.stdout.write("\n")
    while not stop_loading_success.is_set() and not stop_loading_failure.is_set():
        line = '.' * (position % 10 + 1)
        sys.stdout.write(f"\rLoading{line}{' ' * (10 - len(line))}") # Clear the remaining lines
        sys.stdout.flush()
        position += 1
        time.sleep(0.1)

    if stop_loading_success.is_set():
        print("\rProgram Completed")
    elif stop_loading_failure.is_set():
        print("\rProgram Failed")
    


# Process 1 image at a time
def process_img(student_img_id: str, assets, student_name, curr_page, prj_title, submission_date, desc) -> tuple:
    try:

        for asset in assets:
            if student_img_id == asset['id']:
                new_img: str = resize_img(asset['props']['src'])
                
                # student_img_id = student_img_id[student_img_id.find(":") + 1:]
                student_img_id = student_img_id[len("asset:"):]
                return new_img, student_name, curr_page, prj_title, submission_date, desc, student_img_id
            
    except Exception as e:
        print(f"Error processing image {student_img_id} for {student_name} at {curr_page}: {e}")
        return None


# Resize img to fit openAI vision model specs
def resize_img(img_data: str | URL) -> str:

    # Check if url or base64 and get the raw bytes data
    if img_data.startswith('data:image') and img_data.find('base64,') != -1:
        # Is base64
        base64_index = img_data.find('base64,') + len('base64,')
        img_data = base64.b64decode(img_data[base64_index:]) # raw bytes data
    else:
        # is URL
        response: Response = requests.get(img_data)
        if response.status_code == 200:
            img_data = response.content # raw bytes data
        else:
            Exception("Unable to retrieve img data (bytes) from url")
    
    # Convert raw byte into file-like object to be opened by PIL as an image
    image = Image.open(BytesIO(img_data))
    max_res_horizontal: tuple = (768, 2048)
    max_res_vertical: tuple = (2048, 768)
    buffered = BytesIO()

    # Resize img for 'high res' mode. Short side <= 768px and Long side <= 2048
    image.thumbnail(max_res_horizontal, Image.LANCZOS) if image.size[0] < image.size[1] else image.thumbnail(max_res_vertical, Image.LANCZOS)
    image.save(buffered, format="PNG", quality = 95, subsampling = 0) # 0 = highest quality slowest, 2 = lowest quality but fastest
    img_bytes: bytes = buffered.getvalue()
    return base64.b64encode(img_bytes).decode('utf-8')
        
    

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
    # Initializing loading screen
    
    # Load the environment variables from .env file
    load_dotenv()

    # Initialize mp
    manager = Manager()
    processors = ProcessPoolExecutor(max_workers=12)

    asyncio.run(main(processors))
    processors.shutdown()
    manager.shutdown()


