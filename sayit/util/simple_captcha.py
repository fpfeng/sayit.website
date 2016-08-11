from flask import current_app
from random import randint
from PIL import Image, ImageDraw, ImageFont


def get_captcha():
    size = (80, 30)
    img = Image.new('RGB', size, (255, 255, 255))
    font = ImageFont.truetype(current_app.config['FONT_PATH'], 22)
    draw = ImageDraw.Draw(img)
    numbers = random_numbers()
    for i, num in enumerate(numbers):  # offset x,y
        draw.text((i * 15 + 1, 3), num, font=font, fill=random_rgb())
    return img, numbers


def random_numbers():
    nums = ''
    for i in range(5):
        nums += str(randint(0, 9))
    return nums


def random_rgb():
    start = 0
    end = 255
    return (randint(start, end), randint(start, end), randint(start, end))
