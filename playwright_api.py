import json
from typing import List
from playwright.async_api import async_playwright, Page, BrowserContext, ElementHandle, Browser
from concurrent.futures import ProcessPoolExecutor
import asyncio

# Get relevent data from tldraw
async def get_page_data_playwright(url: str, target: str, processors: ProcessPoolExecutor):
    prj_title = ''
    desc = ''
    date = ''
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                permissions=["clipboard-read", "clipboard-write"],
            )
            page = await context.new_page()
            await page.goto(url)
            await page.wait_for_selector('.tlui-popover')
            await page.click('.tlui-button__menu')
            await page.wait_for_selector('.tlui-page-menu__list')
            dropdown_menu = await page.query_selector_all('.tlui-page-menu__item')

            if not await dropdown_checker(target, dropdown_menu):
                raise Exception(f"Page '{target}' not found") 
        
            await page.wait_for_load_state('load')

            # Click menu btn and copy as JSON
            await page.click("[data-testid = 'main-menu.button']")
            await page.click("[data-testid = 'main-menu-sub.edit-button']")
            await page.click("[data-testid='main-menu-sub.copy as-button']")
            await page.click("[data-testid='main-menu.copy-as-json']")
            clipboard_content = await page.evaluate('navigator.clipboard.readText()')
            json_content = json.loads(clipboard_content)

            # Get prj title
            try:
                prj_title = await page.query_selector('.tlui-top-panel__container')
                prj_title = await prj_title.inner_text()
                prj_title = prj_title.strip().replace('\u00a0', ' ').replace('_','-')
            except AttributeError as a:
                print("Project title not found. Setting it to 'Untitled Project'.")
                prj_title = "Untitled Project"

            await close(context, browser)

            # Clean data in parallel
            future_obj_clean = processors.submit(clean_data, target, json_content['shapes'])
            isCustomTemplatePresent, frame_id, filtered_shapes_data = await asyncio.wrap_future(future_obj_clean)

            # Extract description and date for each page after cleaning
            future_obj_desc_date = processors.submit(get_frame_desc_date, filtered_shapes_data, frame_id)
            frame_desc_date = await asyncio.wrap_future(future_obj_desc_date)

            if "::" in frame_desc_date:
                desc, date = frame_desc_date.split("::")
                desc = desc.strip()
                date = date.strip().replace("<", "").replace(">", "")
            else:
                desc = "desc"
                date = "date"
                print(f"Description and date not found for {target}. Set to default value. Ensure that its in the format '<desc>::<date>'.")

            # Get image tasks to be done in parallel
            if not isCustomTemplatePresent:
                future_obj_task = processors.submit(get_tasks_method1, filtered_shapes_data, frame_id)
            else:
                # Custom template
                future_obj_task = processors.submit(get_tasks_method1, filtered_shapes_data, frame_id)

            tasks = await asyncio.wrap_future(future_obj_task)

            

            # json_content['assets']
            return desc, date, tasks, prj_title, target, tasks
        
    except Exception as e:
        print(e)
        return # None


# DFS algorithm
# No custom template
def get_tasks_method1(shapes: list, frame_id: str, name = None, tasks = None):
    if tasks is None:
        tasks = set()

    for shape in shapes:

        # Stops here when an img is found and adds it to the tasks together with the student name
        if shape['parentId'] == frame_id and shape['type'] == 'image' and name is not None:
            tasks_data = {
                "assetId": shape['props']['assetId'],
                "name": name,
            }
            tasks.add(tasks_data)

        if shape['parentId'] == frame_id and shape['type'] == 'frame':
            name = shape['props']['name'].strip().replace('<', '').replace('>', '')
            sub_tasks = get_tasks_method1(shapes, shape['id'], name, tasks)
            tasks.update(sub_tasks)

            name = None # Reset the name to None after the recursive call

        if shape['parentId'] == frame_id and shape['type'] == 'group':
            sub_tasks = get_tasks_method1(shapes, shape['id'], name, tasks)
            tasks.update(sub_tasks)

    return tasks


def clean_data(target: str, shapes: list):
    isCustomTemplatePresent = False

    # Leave only the necessary shapes (images, text with names, groups and frames with names, submission frame template)
    filtered_shapes_data = []
    target_frameid = ''
    for shape in shapes:
        if (shape['type'] == 'frame' and shape['props'].get('name','').strip() != '') or \
            shape['type'] == 'image' or \
            (shape['type'] == 'text' and shape['props'].get('text','').strip() != '') or \
            shape['type'] == 'group':
                filtered_shapes_data.append(shape)

        elif shape['type'] == 'submission_frame':
            filtered_shapes_data.append(shape)
            isCustomTemplatePresent = True

        if shape['type'] == 'frame' and target == shape['props']['name'].lower().strip() and shape['parentId'].startswith('page:'):
            target_frameid = shape['id']

    if target_frameid == '':
        raise Exception(f"{target} id not found. Ensure that the main frame name matches exactly to the page name.")
 
    return isCustomTemplatePresent, target_frameid, filtered_shapes_data


def get_frame_desc_date(shapes: list, frame_id: str):
    frame_desc = ''

    for shape in shapes:
        # Get the frame description and date
        if shape['parentId'] == frame_id and shape['type'] == 'text' and '::' in shape['props']['text']:
            frame_desc = shape['props']['text']
            
    return frame_desc


async def dropdown_checker(chosen_page, menu: List[ElementHandle]):
    for option in menu:
        value = await option.inner_text()
        value = value.lower().strip()
        if chosen_page == value:
            await option.click()
            return True
    return False


async def get_all_pages_playwright(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            permissions=["clipboard-read", "clipboard-write"],
        )
        
        page = await context.new_page()
        await page.goto(url)
        await page.wait_for_selector('.tlui-popover')
        await page.click('.tlui-button__menu')
        dropdown_menu = await page.query_selector('.tlui-page-menu__list')
        page_list = await dropdown_menu.inner_text()
        await close(context, browser)
        return page_list.lower().split("\n")
    

async def close(context: BrowserContext, browser: Browser):
    await context.close()
    await browser.close()