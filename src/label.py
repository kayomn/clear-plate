from PIL import Image, ImageFont
from allergens import UK_14
from brother_ql.backends.helpers import send
from brother_ql.conversion import convert
from brother_ql.raster import BrotherQLRaster
from datetime import date
from document import Document
from importlib.resources import as_file, files
from platform import system
from subprocess import run
from tempfile import NamedTemporaryFile
from typing import NamedTuple

LABEL_WIDTH_PX = 696
LABEL_PADDING_PX = 20
LABEL_LINE_WIDTH_PX = LABEL_WIDTH_PX - (LABEL_PADDING_PX * 2)

class Label(NamedTuple):
    name: str = ""
    description: str = ""
    ingredients: set[str] = {}
    price: int = 0
    expiry: date = date.today()

    def to_image(self) -> Image.Image:
        label = Document(width=LABEL_WIDTH_PX, margin=LABEL_PADDING_PX)

        label.write_centered(business_font, "Profine UK Ltd.")
        label.write_centered(title_font, self.name)
        label.line_break(12)

        if self.description:
            label.write_centered(regular_font, self.description)
            label.line_break(12)

        if self.ingredients:
            label.write(major_details_font, "INGREDIENTS: ")

            allergens = []

            for item in self.ingredients:
                is_allergen = UK_14.findall(item)

                if is_allergen:
                    allergens.append(item)
                else:
                    label.write(minor_details_font, f"{item}, ")

            label.line_break(40)
            label.write(major_details_font, "ALLERGENS: ")

            if allergens:
                for item in self.ingredients:
                    if UK_14.findall(item):
                        label.write(major_details_font, f"{item}, ")
            else:
                label.write(minor_details_font, "None.")

            label.line_break(64)

        label.write_centered(minor_details_font, f"Keep Refrigerated 5°C, Use By {self.expiry.strftime("%d/%m/%Y")}")

        if self.price:
            label.write_centered(regular_font, f"£{(self.price / 100):.2f}")

        return label.rasterize()

fonts_dir = files(__name__).joinpath("fonts")

with as_file(fonts_dir / "hyperreadable-regular.ttf") as regular_path, as_file(fonts_dir / "hyperreadable-bold.ttf") as bold_path:
    minor_details_font = ImageFont.truetype(regular_path, 32)
    major_details_font = ImageFont.truetype(bold_path, 32)
    regular_font       = ImageFont.truetype(regular_path, 64)
    business_font      = ImageFont.truetype(bold_path, 96)
    title_font         = ImageFont.truetype(bold_path, 80)

def preview_label(label_image: Image.Image):
    with NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        label_image.save(temp_file.name)

        match system():
            case "Windows":
                from os import startfile

                startfile(temp_file.name)

            case "Darwin":
                run(["open", temp_file.name])

            case "Linux":
                run(["xdg-open", temp_file.name])

def print_label(label_image: Image.Image, copies: int):
	printer = BrotherQLRaster("QL-700")

	printer.exception_on_warning = True
	endless_tape_65mm = "62"

	instructions = convert(
		qlr=printer,
		images=[label_image],
		label=endless_tape_65mm,
		rotate='0',
		threshold=70.0,
		compress=True,
		dither=False,
		cut=True
	)

	for i in range(copies):
		print(f"Printing label {1 + i}")
		send(instructions=instructions, printer_identifier="usb://0x04f9:0x2042", backend_identifier="pyusb", blocking=True)

	print("Print job completed")
