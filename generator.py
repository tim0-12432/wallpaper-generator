from typing import Iterator, List
from cv2 import dnn_superres
from requests import post
from io import BytesIO
from PIL import Image
import numpy as np
import random
import base64
import sys
import cv2
import os

class Generator:
    def __init__(self) -> None:
        self.url = 'https://backend.craiyon.com/generate'
        self.headers = {'Content-Type': 'application/json'}
        self._setup_sr("FSRCNN-small_x4")
        sys.stdout.write("Generator initialized.\n")

    def _setup_sr(self, model: str) -> None:
        self.sr = dnn_superres.DnnSuperResImpl_create()
        self.sr.readModel(f'./models/{model}.pb')

    def _request(self, prompt: str) -> dict:
        data = '{' + f'"prompt": "{prompt}<br>"' + '}'
        response = post(self.url, headers=self.headers, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(response.text)

    def generate(self, text: str) -> List[Image.Image]:
        result = self._request(text)
        images = result['images']
        return images

    def decode(self, images: List[Image.Image]) -> Iterator[Image.Image]:
        yield from (Image.open(BytesIO(base64.decodebytes(img.encode("utf-8")))) for img in images)

    def upscale(self, image: Image, scale: int) -> Image:
        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        self.sr.setModel('fsrcnn', scale)
        up = self.sr.upsample(img, scale)
        return Image.fromarray(cv2.cvtColor(up, cv2.COLOR_BGR2RGB))

    def _save_for_wallpaper(self, image: Image) -> str:
        if sys.platform == 'cygwin':
            home_dir = os.environ['HOME']
        else:
            home_dir = os.environ['USERPROFILE'] or os.environ['HOME']
        if home_dir is None:
            raise Exception("Could not find home directory.")
        if not os.path.exists(os.path.join(os.path.normpath(home_dir), 'Pictures')):
            os.mkdir(os.path.join(os.path.normpath(home_dir), 'Pictures'))
        path = os.path.join(os.path.normpath(home_dir), 'Pictures', 'wallpaper.png')
        image.save(path)
        return path

    def set_as_wallpaper(self, image: Image) -> None:
        if sys.platform in ['win32', 'cygwin']:
            import ctypes
            img_path = self._save_for_wallpaper(image)
            SPI_SETDESKWALLPAPER = 0x14
            SPIF_UPDATEINIFILE = 0x2
            ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, img_path, SPIF_UPDATEINIFILE)
        else:
            raise Exception("Unsupported platform.")


if __name__ == '__main__':
    prompts = [
        "a starwars character in a psychodelic dream, digital art, sharp edges, realistic, 4k, 85mm, f2.8, star wars",
        "universe, planets, psychodelic dream, digital art, sharp edges, realistic, 4k, 18mm, f1.4, solar system, milky way",
        "psychodelic dream, digital art, sharp edges, realistic, 4k, 18mm, f1.4, modern",
        "abstract, digital art, sharp edges, realistic, 4k, 35mm, f1.4, modern, wall breaking"
    ]
    generator = Generator()
    prompt = random.choice(prompts)
    sys.stdout.write(f"Generating image for prompt: {prompt}\n")
    images = generator.generate(prompt)
    sys.stdout.write("Decoding images...\n")
    images = generator.decode(images)
    sys.stdout.write("Upscaling image...\n")
    image = generator.upscale(random.choice([*images]), 4)
    sys.stdout.write("Setting wallpaper...\n")
    image.show()
    generator.set_as_wallpaper(image)
    sys.stdout.write("Done.\n")
