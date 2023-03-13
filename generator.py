from typing import Iterator, List
from cv2 import dnn_superres
from requests import Session, post, get
from ctypes import wintypes
from io import BytesIO
from PIL import Image
import numpy as np
import random
import base64
import sys
import cv2
import os

"""
The wallpaper generator module.

Classes
-------
Generator
    Generator class for generating images from prompts.

Author
------
Tim0-12432 (c) 2023

License
-------
MIT License 2023

Acknowledgements
----------------
Craiyon v2 (https://www.craiyon.com/)
FSRCNN model (https://github.com/Saafke/FSRCNN_Tensorflow)
"""


class Generator:
    """
    Generator class for generating images from prompts.

    Attributes
    ----------
    api_url : str
        URL of the API.
    img_url : str
        URL of the image directory.
    headers : dict
        Headers for the API request.
    sr : DnnSuperResImpl
        Super resolution object.
    version : str
        Version of the API.

    Methods
    -------
    _setup_sr(model: str)
        Sets up the super resolution object.
    _request(prompt: str) -> dict
        Gets the images from the API.
    _clean_dir(path: str) -> int
        Cleans the directory of old images.
    _save_for_wallpaper(image: Image) -> str
        Saves the image for the wallpaper.
    generate(text: str) -> List[Image.Image]
        Generates images from a prompt.
    decode(images: List[Image.Image]) -> Iterator[Image.Image]
        Decodes the images from base64.
    upscale(image: Image, scale: int) -> Image
        Upscales the image.
    set_as_wallpaper(image: Image)
        Sets the image as the wallpaper.
    resize_to_6_to_4(image: Image) -> Image
        Resizes the image to 6:4.
    """

    def __init__(self) -> None:
        """
        Initializes the generator.
        """

        self.api_url = "https://api.craiyon.com/draw"
        self.img_url = "https://img.craiyon.com"
        self.headers = {
            "pragma": "no-cache",
            "cache-control": "no-cache",
            "origin": "https://www.craiyon.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        }
        self.version = "35s5hfwn9n78gb06"
        self._setup_sr("FSRCNN-small_x4")
        sys.stdout.write("Generator initialized.\n")

    def _setup_sr(self, model: str) -> None:
        """
        Sets up the super resolution object.

        Parameters
        ----------
        model : str
            The model to use.
        """

        self.sr = dnn_superres.DnnSuperResImpl_create()
        path = os.path.join(os.path.dirname(__file__), "models", f"{model}.pb")
        self.sr.readModel(path)

    def _request(self, prompt: str) -> List[bytes]:
        """
        Sends a request to the API.

        Parameters
        ----------
        prompt : str
            The prompt to use.

        Returns
        -------
        List[bytes]
            The images from the API.

        Raises
        ------
        Exception
            If the response status code is not 200.
        """

        session = Session()
        data = {"prompt": prompt, "token": None, "version": self.version}
        response = session.post(
            self.api_url,
            headers={
                **self.headers,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=data,
        )
        if response.status_code == 200:
            images = []
            for path in response.json()["images"]:
                img_resp = session.get(
                    self.img_url + "/" + path, headers={**self.headers, "Accept": "*/*"}
                )
                if img_resp.status_code == 200:
                    images.append(base64.b64encode(img_resp.content))
                else:
                    raise Exception(img_resp.text)
            return images
        else:
            raise Exception(response.text)

    def generate(self, text: str) -> List[Image.Image]:
        """
        Generates images from a prompt.

        Parameters
        ----------
        text : str
            The prompt to use.

        Returns
        -------
        List[Image.Image]
            The generated images.
        """

        return self._request(text)

    def decode(self, images: List[bytes]) -> Iterator[Image.Image]:
        """
        Decodes the images from base64.

        Parameters
        ----------
        images : List[bytes]
            The images to decode.

        Yields
        -------
        Iterator[Image.Image]
            The decoded images.
        """

        yield from (Image.open(BytesIO(base64.decodebytes(img))) for img in images)

    def upscale(self, image: Image, scale: int) -> Image:
        """
        Upscales the image.

        Parameters
        ----------
        image : Image
            The image to upscale.
        scale : int
            The scale to use.

        Returns
        -------
        Image
            The upscaled image.
        """

        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        self.sr.setModel("fsrcnn", scale)
        up = self.sr.upsample(img, scale)
        return Image.fromarray(cv2.cvtColor(up, cv2.COLOR_BGR2RGB))

    def _clean_dir(self, path: str) -> int:
        """
        Cleans the directory of old images.

        Parameters
        ----------
        path : str
            The path to the directory.

        Returns
        -------
        int
            The index of the next image.
        """

        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        max_number = 0
        for f in files:
            max_number = (
                int(f.split(".")[0].split("_")[1])
                if int(f.split(".")[0].split("_")[1]) > max_number
                else max_number
            )
        for f in files:
            if int(f.split(".")[0].split("_")[1]) < max_number:
                os.remove(os.path.join(path, f))
        return max_number + 1

    def _save_for_wallpaper(self, image: Image) -> str:
        """
        Saves the image for the wallpaper.

        Parameters
        ----------
        image : Image
            The image to save.

        Returns
        -------
        str
            The path to the image.

        Raises
        ------
        Exception
            If the home directory could not be found.
        """

        if sys.platform == "cygwin":
            home_dir = os.environ["HOME"]
        else:
            home_dir = os.environ["USERPROFILE"] or os.environ["HOME"]
        if home_dir is None:
            raise Exception("Could not find home directory.")
        if not os.path.exists(os.path.join(os.path.normpath(home_dir), "Pictures")):
            os.mkdir(os.path.join(os.path.normpath(home_dir), "Pictures"))
        dir_path = os.path.join(
            os.path.normpath(home_dir), "Pictures", "wallpaper-generator"
        )
        if not os.path.exists(dir_path):
            os.mkdir(dir_path)
        idx = self._clean_dir(dir_path)
        path = os.path.join(
            os.path.normpath(home_dir),
            "Pictures",
            "wallpaper-generator",
            f"wallpaper_{idx}.jpg",
        )
        image.save(path)
        return path

    def set_as_wallpaper(self, image: Image) -> None:
        """
        Sets the image as the wallpaper.

        Parameters
        ----------
        image : Image
            The image to set.

        Raises
        ------
        Exception
            If the platform is not supported.
        """

        if sys.platform in ["win32", "cygwin"]:
            import ctypes

            SPI_SET_DESK_WALLPAPER = 0x14
            SPIF_UPDATE_INI_FILE = 0x1
            SPIF_SEND_WIN_INI_CHANGE = 0x2

            system_params_info = ctypes.windll.user32.SystemParametersInfoW
            system_params_info.argtypes = (
                ctypes.c_uint,
                ctypes.c_uint,
                ctypes.c_void_p,
                ctypes.c_uint,
            )
            system_params_info.restype = wintypes.BOOL

            system_params_info(
                SPI_SET_DESK_WALLPAPER,
                0,
                "",
                SPIF_UPDATE_INI_FILE | SPIF_SEND_WIN_INI_CHANGE,
            )
            img_path = self._save_for_wallpaper(image)
            system_params_info(
                SPI_SET_DESK_WALLPAPER,
                0,
                img_path,
                SPIF_UPDATE_INI_FILE | SPIF_SEND_WIN_INI_CHANGE,
            )
        else:
            raise Exception("Unsupported platform.")

    def resize_to_6_to_4(self, image: Image) -> Image:
        """
        Resizes the image to 6:4.

        Parameters
        ----------
        image : Image
            The image to resize.

        Returns
        -------
        Image
            The resized image.
        """

        orig_width, orig_height = image.size
        if orig_width / orig_height == 6 / 4:
            return image
        elif not orig_width / orig_height == 1:
            image_to_work_with = image.resize((orig_height, orig_height))
        else:
            image_to_work_with = image

        width, height = image_to_work_with.size
        quarter_width = width // 4
        wip_image = Image.new("RGB", (width + width // 2, height))
        wip_image.paste(image_to_work_with, (quarter_width, 0))

        left_img = image_to_work_with.crop((0, 0, quarter_width, height))
        right_img = image_to_work_with.crop((width - quarter_width, 0, width, height))
        left_img = left_img.transpose(Image.FLIP_LEFT_RIGHT)
        right_img = right_img.transpose(Image.FLIP_LEFT_RIGHT)
        wip_image.paste(left_img, (0, 0))
        wip_image.paste(right_img, (width + quarter_width, 0))

        return wip_image


if __name__ == "__main__":
    prompts = [
        "a starwars character in a psychodelic dream, atmospheric, digital art, high definition, realistic, 8k, 85mm, f2.8, star wars",
        "universe, planets, detailed, psychodelic dream, high definition, sharp edges, realistic, 8k, 18mm, f1.4, solar system, milky way",
        "psychodelic dream, digital art, sharp edges, realistic, high definition, 8k, 18mm, f1.4, modern",
        "abstract, sharp edges, detailed, realistic, high definition, 8k, 35mm, f1.4, modern, wall breaking",
        "impressionistic oil painting, by Van Gogh, detailed, high definition, 8k, psychodelic dream, abstract art",
        "cyberpunk, wired, vibrant high contrast, hyperrealistic, photographic, 8k, 85mm, f2.8, octane render, person, spotlight, cyberpunk city, cyberpunk man",
        "hacker, dark, atmospheric, digital art, detailed, high definition, 8k, green bytes floating, zero and ones, hoodie, black",
    ]
    generator = Generator()
    prompt = random.choice(prompts)
    sys.stdout.write(f"Generating image for prompt: {prompt}\n")
    images = generator.generate(prompt)
    sys.stdout.write("Decoding images...\n")
    images = generator.decode(images)
    sys.stdout.write("Upscaling image...\n")
    image = generator.upscale(random.choice([*images]), 4)
    sys.stdout.write("Resizing image...\n")
    image = generator.resize_to_6_to_4(image)
    sys.stdout.write("Setting wallpaper...\n")
    generator.set_as_wallpaper(image)
    sys.stdout.write("Done.\n")
