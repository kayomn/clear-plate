import datetime
import sys
import os
import libusb
import pkg_about

from gooey import Gooey, GooeyParser
from brother_ql.raster import BrotherQLRaster
from brother_ql.conversion import convert
from brother_ql.backends.helpers import send
from PIL import Image, ImageDraw, ImageFont

UK_14_ALLERGENS = [
    "celery", "cereals containing gluten", "wheat", "rye", "barley", "oats",
    "spelt", "khorasan", "crustacean", "crustaceans", "prawns", "crabs", "lobster",
    "crayfish", "eggs", "egg", "fish", "lupin", "milk", "butter", "cream", "cheese",
    "whey", "molluscs", "mollusc", "mussels", "oysters", "squid", "snails", "mustard",
    "nuts", "almonds", "hazelnuts", "walnuts", "cashews", "pecans", "brazil nuts",
    "pistachios", "macadamia", "peanuts", "sesame", "sesame seeds", "soy",
    "soya", "soybean", "soy beans", "soy bean", "soybeans", "sulphur dioxide",
    "sulphites", "sulfites"
]

LABEL_WIDTH_PX = 696
LABEL_HEIGHT_PX = 342
LABEL_PADDING_PX = 20
LABEL_LINE_WIDTH_PX = LABEL_WIDTH_PX - (LABEL_PADDING_PX * 2)

LABEL_WIDTH_PX = 696
LABEL_PADDING_PX = 20
LABEL_LINE_WIDTH_PX = LABEL_WIDTH_PX - (LABEL_PADDING_PX * 2)

class Renderer:
    def __init__(self, width=LABEL_WIDTH_PX, padding=LABEL_PADDING_PX):
        self.width = width
        self.padding = padding
        self.max_x = width - padding

        self.draw_calls = []
        self.cursor_x = self.padding
        self.cursor_y = self.padding

    def write(self, font: ImageFont.ImageFont, text: str):
        ascent, descent = font.getmetrics()
        line_height = ascent + descent 
        
        words = text.split(" ")
        for idx, word in enumerate(words):
            if word:
                is_last_word = (idx == len(words) - 1)
                # Only add space BETWEEN words inside this specific text call, not at the end
                padding = "" if is_last_word else " "
                word_to_draw = word + padding
                
                word_width = font.getlength(word_to_draw)

                if self.cursor_x + word_width > self.max_x:
                    self.line_break(line_height)

                self.draw_calls.append(("text", (self.cursor_x, self.cursor_y), word, font))
                self.cursor_x += word_width

    def write_centered(self, font: ImageFont.ImageFont, text: str):
        ascent, descent = font.getmetrics()
        line_height = ascent + descent

        if self.cursor_x > self.padding:
            self.line_break(line_height)

        usable_width = self.max_x - self.padding
        words = text.split(" ")
        current_line = []

        for word in words:
            if not word:
                continue

            test_line = " ".join(current_line + [word])
            line_width = font.getlength(test_line)

            if line_width <= usable_width or not current_line:
                current_line.append(word)
            else:
                # Draw current accumulated line centered
                line_str = " ".join(current_line)
                w = font.getlength(line_str) # We only need the width now

                start_x = self.padding + (usable_width - w) / 2
                self.draw_calls.append(("text", (start_x, self.cursor_y), line_str, font))

                # Advance by the uniform line height
                self.cursor_y += line_height
                current_line = [word]

        if current_line:
            line_str = " ".join(current_line)
            w = font.getlength(line_str)

            start_x = self.padding + (usable_width - w) / 2
            self.draw_calls.append(("text", (start_x, self.cursor_y), line_str, font))

            self.cursor_y += line_height

        self.cursor_x = self.padding

    def line_break(self, line_height: int = 20): # Added a default so line_rule() works
        self.cursor_x = self.padding
        self.cursor_y += line_height

    def line_rule(self):
        if self.cursor_x > self.padding:
            self.line_break()
        
        self.cursor_y += 5
        self.draw_calls.append(("line", (self.padding, self.cursor_y, self.max_x, self.cursor_y)))
        self.cursor_y += 15

    def render(self) -> Image.Image:
        height = self.cursor_y + LABEL_PADDING_PX
        image = Image.new("RGB", (self.width, height), "white")
        draw = ImageDraw.Draw(image)

        for kind, coords, content, *extra in self.draw_calls:
            if kind == "text":
                draw.text(coords, content, fill="black", font=extra[0])
            elif kind == "line":
                draw.line(coords, fill="black", width=2)

        return image

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def is_allergen(word: str) -> bool:
    return word.lower().strip() in UK_14_ALLERGENS

def render_label_image(name: str, description: str, ingredients: str, price_pence: int, expiry: str) -> Image.Image:
    regular_font = ImageFont.truetype(get_resource_path("fonts/hyperreadable-regular.ttf"), 64)
    bold_font = ImageFont.truetype(get_resource_path("fonts/hyperreadable-bold.ttf"), 64)
    business_font = ImageFont.truetype(get_resource_path("fonts/hyperreadable-bold.ttf"), 128)
    title_font = ImageFont.truetype(get_resource_path("fonts/hyperreadable-bold.ttf"), 96)
    renderer = Renderer()

    renderer.write_centered(business_font, "Profine UK Ltd.")
    renderer.write_centered(title_font, name)
    renderer.line_break(12)

    if description:
        renderer.write_centered(regular_font, description)
        renderer.line_break(12)

    if ingredients:
        renderer.write(bold_font, "INGREDIENTS: ")

        ingredients_list = [i.strip() for i in ingredients.split(",") if i.strip()]

        for idx, item in enumerate(ingredients_list):
            is_last = (idx == len(ingredients_list) - 1)
            suffix = "." if is_last else ", "
            font = bold_font if is_allergen(item) else regular_font
            renderer.write(font, item)
            renderer.write(regular_font, suffix)

        renderer.line_break(64)

    renderer.write(regular_font, "Keep Refrigerated 5°C | Use by: ")
    renderer.write(bold_font, expiry)

    if price_pence:
        renderer.write_centered(regular_font, f"£{(price_pence / 100):.2f}")

    return renderer.render()

def print_label(image: Image.Image, copies: int):
    qlr = BrotherQLRaster('QL-700')
    qlr.exception_on_warning = True

    # 62mm endless tape identifier is '62'
    instructions = convert(
        qlr=qlr,
        images=[image] * copies,  # Print requested number of copies
        label='62',
        rotate='0',
        threshold=70.0,
        dither=False,
        cut=True # Cut after the batch/label
    )

    print(f"Sending {copies} label(s) to printer...")
    send(instructions=instructions, printer_identifier="usb://0x04f9:0x2042", backend_identifier="pyusb", blocking=True)
    print("Done!")

@Gooey(program_name="Clear Plate", return_to_config=True, default_size=(600, 600))
def main():
    todays_date = datetime.date.today().strftime('%Y-%m-%d')

    parser = GooeyParser(
        prog="ClearPlate",
        description="Natasha's Law-Compliant Label Generator for Brother QL-700",
    )

    parser.add_argument("--name", required=True, metavar="Name", help="Product Name (e.g., 'Ham & Cheese Sandwich').")
    parser.add_argument("--description", default="", metavar="Description", help="Short product description.")
    parser.add_argument("--ingredients", required=True, metavar="Ingredient List", help="Comma separated list of ingredients.")
    parser.add_argument("--price", default=0, metavar="Price", help="Listed item price in pence.")
    parser.add_argument("--expiry", widget="DateChooser", default=todays_date, metavar="Use By Date", help="Listed item price in pence.")
    parser.add_argument("--copies", type=int, default=1, metavar="Copies", help="Number of labels to print.")
    parser.add_argument("--preview", action="store_true", help="Save label image to preview.png instead of printing")

    args = parser.parse_args()
    label = render_label_image(str(args.name), str(args.description), str(args.ingredients), int(args.price), args.expiry)

    if args.preview:
        label.save("preview.png")
        print("Label saved to preview.png")
    else:
        print_label(label, copies=args.copies)

if __name__ == "__main__":
    main()
