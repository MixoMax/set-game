from PIL import Image, ImageDraw, ImageFont
import re
import os
from balatro_set_core import JOKER_DATABASE, TAROT_DATABASE

WIDTH = 400
HEIGHT = 600
TITLE_FONT_SIZE = 52
DESCRIPTION_FONT_SIZE = 36


def wrap_text(text, font, max_width, draw):
    """Wraps text to fit within a maximum width."""
    if not text:
        return ""
    
    lines = []
    # Preserve existing newlines
    for paragraph in text.split('\n'):
        words = paragraph.split(' ')
        if not words:
            lines.append('')
            continue

        current_line = words[0]
        for word in words[1:]:
            # Check width of the current line with the new word
            if draw.textbbox((0, 0), current_line + " " + word, font=font)[2] <= max_width:
                current_line += " " + word
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
    
    return "\n".join(lines)


def create_card_image(card_id, card_name, description, output_dir):
    width, height = WIDTH, HEIGHT
    text_box_height = int(height * 0.2)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        title_font = ImageFont.truetype("arial.ttf", TITLE_FONT_SIZE)
        description_font = ImageFont.truetype("arial.ttf", DESCRIPTION_FONT_SIZE)
    except IOError:
        title_font = ImageFont.load_default()
        description_font = ImageFont.load_default()

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    # Draw text box background
    draw.rectangle([0, 0, width, text_box_height], fill="lightgrey")

    # Wrap and draw title
    wrapped_title = wrap_text(card_name, title_font, width - 20, draw)
    title_bbox = draw.textbbox((0, 0), wrapped_title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    title_x = (width - title_width) / 2
    title_y = (text_box_height - title_height) / 2
    draw.text((title_x, title_y), wrapped_title, fill="black", font=title_font, align="center")

    # Wrap and draw description
    wrapped_description = wrap_text(description, description_font, width - 20, draw)
    desc_bbox = draw.textbbox((0, 0), wrapped_description, font=description_font)
    desc_width = desc_bbox[2] - desc_bbox[0]
    desc_height = desc_bbox[3] - desc_bbox[1]
    desc_x = (width - desc_width) / 2
    desc_y = text_box_height + (height - text_box_height - desc_height) / 2
    draw.text((desc_x, desc_y), wrapped_description, fill="black", font=description_font, align="center")

    # Save image
    output_filename = os.path.join(output_dir, f"{card_id}.webp")
    image.save(output_filename, "WEBP")
    print(f"Created {output_filename}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    img_dir = os.path.join(script_dir, "static", "images")
    for card_id, card_data in JOKER_DATABASE.items():
        create_card_image(card_id, card_data.name, card_data.description, img_dir)
    for card_id, card_data in TAROT_DATABASE.items():
        create_card_image(card_id, card_data.name, card_data.description, img_dir)

