from PIL import Image, ImageDraw, ImageFont
import re
import os

WIDTH = 400
HEIGHT = 600

def create_card_images(md_file, output_dir):
    """
    Reads a markdown file with card data and creates an image for each card.

    Args:
        md_file (str): Path to the markdown file.
        output_dir (str): Directory to save the generated images.
    """
    width, height = WIDTH, HEIGHT
    text_box_height = int(height * 0.2)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        font = ImageFont.load_default()

    with open(md_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('-'):
                print("Skipping line:", line)
                continue

            match = re.match(r'- (\w+) -> (.+)', line)
            if not match:
                continue

            card_id, card_name = match.groups()
            
            img = Image.new('RGB', (width, height), color = 'white')
            draw = ImageDraw.Draw(img)

            # Draw text box background
            draw.rectangle([0, 0, width, text_box_height], fill='lightgrey')

            # Draw text
            text_bbox = draw.textbbox((0, 0), card_name, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            text_x = (width - text_width) / 2
            text_y = (text_box_height - text_height) / 2
            draw.text((text_x, text_y), card_name, fill='black', font=font)

            # Save image
            output_filename = os.path.join(output_dir, f"{card_id}.webp")
            img.save(output_filename, 'WEBP')
            print(f"Created {output_filename}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    md_file_path = os.path.join(script_dir, 'tmp.md')
    create_card_images(md_file_path, script_dir)
