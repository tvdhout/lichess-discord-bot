import base64
# selenium requires installation of https://github.com/mozilla/geckodriver/releases and add path/to/executable to $PATH
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
from io import BytesIO
import time


options = Options()
options.headless = True
fox = webdriver.Chrome(options=options)
fox.get('https://lichess.org/training/')

element = fox.find_element_by_class_name('main-board')
location = element.location
size = element.size
time.sleep(.8)
img = Image.open(BytesIO(base64.b64decode(fox.get_screenshot_as_base64())))

pixel_ratio = fox.execute_script("return window.devicePixelRatio")

fox.quit()
left = location['x']*pixel_ratio
top = location['y']*pixel_ratio
right = location['x']*pixel_ratio + size['width']*pixel_ratio
bottom = location['y']*pixel_ratio + size['height']*pixel_ratio

im = img.crop((left, top, right, bottom))  # defines crop points
im.save('../media/screenshot.png')  # saves new cropped image
