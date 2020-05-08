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

BASE_DIR = '/home/thijs/Lichess-discord-bot'
answer = None


async def show_puzzle(message: discord.message.Message, puzzle_id: Optional[str] = '') -> None:
    # Create a headless instance of a web browser
    options = Options()
    options.headless = True
    fox = webdriver.Chrome(options=options)

    try:
        # Get a puzzle image
        fox.get(f'https://lichess.org/training/{puzzle_id}')

        if puzzle_id == '':
            puzzle_id = fox.current_url.split('/')[-1]

        board = fox.find_element_by_class_name('puzzle__board')
        time.sleep(.8)  # wait for the last move to play out
        im = Image.open(BytesIO(base64.b64decode(board.screenshot_as_base64)))  # take screenshot of page

        im.save(f'{BASE_DIR}/media/puzzle.png')

        # #Get answer
        # solution_button = fox.find_element_by_class_name("view_solution")
        # fox.execute_script("arguments[0].setAttribute('class','view_solution show')", solution_button)
        # solution_event = fox.find_elements_by_class_name("button")[-1]
        # print(solution_button)
        # solution_event.click()
        # time.sleep(.1)
        # moves = fox.find_element_by_class_name('good')
        # print(moves)

        fox.quit()  # quit the connection
    except selenium.common.exceptions.NoSuchElementException:
        await message.channel.send(f"I can't find a puzzle with puzzle id '{puzzle_id}'")
        fox.quit()
        return

    im.save(f'{BASE_DIR}/media/puzzle.png')

    embed = discord.Embed(title=f"Solve this! (puzzle {puzzle_id})",
                          url=f'https://lichess.org/training/{puzzle_id}',
                          colour=0x00ffff
                          )

    puzzle = discord.File(f'{BASE_DIR}/media/puzzle.png', filename="puzzle.png")
    embed.set_image(url="attachment://puzzle.png")
    embed.add_field(name="Answer with !answer", value="Use the standard algebraic notation, e.g. Qxb7")
    await message.channel.send(file=puzzle, embed=embed)
