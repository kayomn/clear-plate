import datetime
import json
import sys
import os
import re

from gooey import Gooey, GooeyParser
from brother_ql.raster import BrotherQLRaster
from brother_ql.conversion import convert
from brother_ql.backends.helpers import send
from PIL import Image, ImageDraw, ImageFont

def allergen_regex(allergen_list: list[str]) -> re.Pattern:
    patterns = []
    # Sort longest-first so "peanut butter" matches before "peanut"
    sorted_allergens = sorted(allergen_list, key=len, reverse=True)
    
    for term in sorted_allergens:
        escaped_term = re.escape(term)
        
        # If term doesn't already end with 's', allow an optional 's' at the end
        if not term.endswith("s"):
            pattern = rf"\b{escaped_term}s?\b"
        else:
            pattern = rf"\b{escaped_term}\b"
            
        patterns.append(pattern)
        
    # Combine into a single regex engine for fast performance
    combined_pattern = "|".join(patterns)
    return re.compile(combined_pattern, re.IGNORECASE)

UK_14_ALLERGENS_EXPANDED = allergen_regex([
    # Celery
    "celery", "celeriac",

    # Cereals containing gluten
    "cereals containing gluten", "gluten", "wheat", "rye", "barley", "oats", "spelt", "khorasan", "kamut", "triticale",
    "farro", "freekeh", "bulgur", "semolina", "couscous", "einkorn", "emmer",

    # Crustaceans
    "crustacean", "prawn", "shrimp", "crab", "lobster", "crayfish", "langoustine", "scampi",

    # Eggs
    "eggs", "egg", "egg yolk", "egg white", "albumin",

    # Fish
    "fish", "fishes", "anchovy", "anchovies", "isinglass", "tuna", "salmon", "cod", "haddock"

    # Lupin
    "lupin", "lupines", "lupine",

    # Milk / Dairy
    "milk", "butter", "cream", "cheese", "whey", "ghee", "casein", "caseinate", "lactalbumin", "lactoglobulin",
    "lactose", "curd", "curds", "yoghurt", "yogurt",

    # Molluscs
    "molluscs", "mollusc", "mollusk", "mollusks", "mussel", "oyster", "squid", "calamari",
    "snail", "escargot", "clam", "scallop", "octopus", "cuttlefish", "cockles", "whelks",

    # Mustard
    "mustard",

    # Tree Nuts
    "nut", "almond", "hazelnut", "walnut", "cashew", "pecans", "pecan", "pistachio", "macadamia", "marzipan",
    "praline",

    # Peanuts
    "peanut", "groundnut", "peanut butter",

    # Sesame
    "sesame", "tahini",

    # Soy / Soya
    "soy", "soya", "soybean", "edamame", "tofu", "tempeh",

    # Sulphur dioxide / Sulphites
    "sulphur dioxide", "sulfur dioxide", "sulphite", "sulfite", "e220", "e221", "e222", "e223", "e224", "e225", "e226",
    "e227", "e228"
])

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

def is_allergen(ingredient: str) -> bool:
    matches = UK_14_ALLERGENS_EXPANDED.findall(ingredient)

    return len(matches) != 0

def render_label_image(product: dict) -> Image.Image:
    minor_details_font = ImageFont.truetype(get_resource_path("fonts/hyperreadable-regular.ttf"), 32)
    major_details_font = ImageFont.truetype(get_resource_path("fonts/hyperreadable-bold.ttf"), 32)
    regular_font = ImageFont.truetype(get_resource_path("fonts/hyperreadable-regular.ttf"), 64)
    business_font = ImageFont.truetype(get_resource_path("fonts/hyperreadable-bold.ttf"), 96)
    title_font = ImageFont.truetype(get_resource_path("fonts/hyperreadable-bold.ttf"), 80)
    renderer = Renderer()

    renderer.write_centered(business_font, "Profine UK Ltd.")
    renderer.write_centered(title_font, product["Name"])
    renderer.line_break(12)

    if product["Description"]:
        renderer.write_centered(regular_font, product["Description"])
        renderer.line_break(12)

    if product["Ingredients"]:
        renderer.write(major_details_font, "INGREDIENTS: ")

        ingredients_list = [i.strip() for i in product["Ingredients"].split(",") if i.strip()]

        for idx, item in enumerate(ingredients_list):
            is_last = (idx == len(ingredients_list) - 1)
            suffix = "." if is_last else ", "
            font = major_details_font if is_allergen(item) else minor_details_font

            renderer.write(font, item)
            renderer.write(minor_details_font, suffix)

        renderer.line_break(64)

    renderer.write_centered(minor_details_font, "Keep Refrigerated 5°C")

    if product["Expiry"]:
        renderer.write_centered(major_details_font, "Use by: " + product["Expiry"])

    if product["Price"]:
        price = product["Price"]
        renderer.write_centered(regular_font, f"£{(price / 100):.2f}")

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

@Gooey(program_name="Clear Plate", return_to_config=True, default_size=(600, 700), navigation="TABBED", required_cols=1, optional_cols=2)
def main():
    todays_date = datetime.date.today().strftime('%Y-%m-%d')

    parser = GooeyParser(
        description="Natasha's Law-Compliant Label Generator for Brother QL-700",
    )

    sub_parsers = parser.add_subparsers(help="Actions", dest="Action")
    create_command = sub_parsers.add_parser("Create")
    create_command._optionals.title = "Product Details"

    create_command.add_argument("--Name", type=str, default="", help="Product Name (e.g., 'Ham Sandwich').")
    create_command.add_argument("--Description", type=str, default="", help="Short product description.")
    create_command.add_argument("--Ingredients", type=str, default="", metavar="Ingredient List", help="Comma separated list of ingredients.")
    create_command.add_argument("--Price", type=int, default=0, metavar="Price", help="Listed item price in pence.")
    create_command.add_argument("--Expiry", widget="DateChooser", default=todays_date, metavar="Use-By Date", help="Listed item price in pence.")

    create_command.add_argument("Path",
        type=str,
        widget="FileSaver",
        metavar="Save Location",
        gooey_options={"wildcard": "JSON Files (*.json)|*.json"}
    )

    print_command = sub_parsers.add_parser("Print")
    print_command._optionals.title = "Print Label"

    print_command.add_argument("Path", 
        type=str,
        widget="FileChooser",
        metavar="Product File",
        gooey_options={"wildcard": "JSON Files (*.json)|*.json"}
    )

    print_mode = print_command.add_mutually_exclusive_group()

    print_mode.add_argument("--Copies", type=int, default=1, widget="IntegerField", help="Print this many labels.")
    print_mode.add_argument("--Preview", action="store_true", metavar="Preview-Only", help="Save label image to preview.png.")

    args = parser.parse_args()

    match args.Action:
        case "Create":
            with open(args.Path, "w", encoding="utf-8") as file:
                product = dict(vars(args))

                product.pop("Path", None)
                json.dump(product, file, indent=4)

        case "Print":
            with open(args.Path, "r", encoding="utf-8") as file:
                product = json.load(file)
                print(product)
                image = render_label_image(product)

                if args.Preview:
                    image.save("preview.png")
                    print("Label saved to preview.png")

                else:
                    print_label(label, copies=args.Copies)

if __name__ == "__main__":
    main()
