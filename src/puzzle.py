import discord
import base64
# selenium requires installation of https://github.com/mozilla/geckodriver/releases and add path/to/executable to $PATH
from selenium import webdriver
import selenium
from selenium.webdriver.chrome.options import Options
from PIL import Image
from io import BytesIO
import time
from typing import Optional


async def show_puzzle(message: discord.message.Message, puzzle_id: Optional[str] = '') -> None:
    # Create a headless instance of a web browser
    options = Options()
    options.headless = True
    fox = webdriver.Chrome(options=options)

    try:
        # Get a puzzle image
        fox.get(f'https://lichess.org/training/{puzzle_id}')

        element = fox.find_element_by_class_name('main-board')
        location = element.location
        size = element.size
        time.sleep(.8)  # wait for the last move to play out
        img = Image.open(BytesIO(base64.b64decode(fox.get_screenshot_as_base64())))  # take screenshot of page
        fox.quit()  # quit the connection
    except selenium.common.exceptions.NoSuchElementException:
        await message.channel.send(f"I can't find a puzzle with puzzle id '{puzzle_id}'")
        fox.quit()
        return

    # Crop image to only the board
    left = location['x']
    top = location['y']
    right = location['x'] + size['width']
    bottom = location['y'] + size['height']
    im = img.crop((left, top, right, bottom))

    im.save('../media/puzzle.png')

    await message.channel.send("Solve this!")
    with open('../media/puzzle.png', 'rb') as f:
        puzzle = discord.File(f)
        await message.channel.send(file=puzzle)
