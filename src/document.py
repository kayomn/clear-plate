from PIL import Image, ImageDraw, ImageFont

class Document:
    def __init__(self, width: int, margin: int):
        self.width = width
        self.margin = margin
        self.max_x = width - margin
        self.draw_calls = []
        self.cursor_x = self.margin
        self.cursor_y = self.margin

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

        if self.cursor_x > self.margin:
            self.line_break(line_height)

        usable_width = self.max_x - self.margin
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

                start_x = self.margin + (usable_width - w) / 2
                self.draw_calls.append(("text", (start_x, self.cursor_y), line_str, font))

                # Advance by the uniform line height
                self.cursor_y += line_height
                current_line = [word]

        if current_line:
            line_str = " ".join(current_line)
            w = font.getlength(line_str)

            start_x = self.margin + (usable_width - w) / 2
            self.draw_calls.append(("text", (start_x, self.cursor_y), line_str, font))

            self.cursor_y += line_height

        self.cursor_x = self.margin

    def line_break(self, line_height: int = 20):
        self.cursor_x = self.margin
        self.cursor_y += line_height

    def line_rule(self):
        if self.cursor_x > self.margin:
            self.line_break()

        self.cursor_y += 5
        self.draw_calls.append(("line", (self.margin, self.cursor_y, self.max_x, self.cursor_y)))
        self.cursor_y += 15

    def rasterize(self) -> Image.Image:
        height = self.cursor_y + self.margin
        image = Image.new("1", (self.width, height), "white")
        draw = ImageDraw.Draw(image)

        for kind, coords, content, *extra in self.draw_calls:
            if kind == "text":
                draw.text(coords, content, fill="black", font=extra[0])
            elif kind == "line":
                draw.line(coords, fill="black", width=2)

        return image
