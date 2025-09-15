from PIL import Image, ImageDraw
import os

# Create avatars directory if it doesn't exist
os.makedirs('static/img/user_avatar', exist_ok=True)

# Colors from your brand
colors = [
    ('#22d3ee', '#0b1220'),  # Cyan with dark text
    ('#facc15', '#0b1220'),  # Amber with dark text
    ('#0b1220', '#22d3ee'),  # Dark with cyan text
    ('#0b1220', '#facc15'),  # Dark with amber text
    ('#22d3ee', '#facc15'),  # Cyan with amber text
]

# Generate 5 simple geometric avatars
for i, (bg_color, fg_color) in enumerate(colors):
    img = Image.new('RGB', (128, 128), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Draw different shapes for each avatar
    if i == 0:
        # Circle
        draw.ellipse([32, 32, 96, 96], fill=fg_color)
    elif i == 1:
        # Square
        draw.rectangle([32, 32, 96, 96], fill=fg_color)
    elif i == 2:
        # Triangle
        draw.polygon([64, 32, 32, 96, 96, 96], fill=fg_color)
    elif i == 3:
        # Diamond
        draw.polygon([64, 32, 96, 64, 64, 96, 32, 64], fill=fg_color)
    else:
        # Delta shape (like your logo)
        draw.polygon([64, 32, 96, 96, 32, 96], fill=fg_color)

    # Save the image
    img.save(f'static/img/user_avatar/default-avatar-{i}.png')

# Set the first one as the default avatar
if os.path.exists('static/img/user_avatar/default-avatar-0.png'):
    default_avatar = Image.open('static/img/user_avatar/default-avatar-0.png')
    default_avatar.save('static/img/user_avatar/default-avatar.png')

print("Default avatars generated!")