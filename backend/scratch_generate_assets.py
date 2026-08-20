import os
from PIL import Image, ImageDraw

def generate_assets(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Teacher Body/Head
    size = 400
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Head
    draw.ellipse([(100, 50), (300, 250)], fill=(255, 220, 177))
    # Hair
    draw.chord([(90, 40), (310, 260)], start=180, end=360, fill=(80, 40, 10))
    draw.chord([(90, 150), (150, 260)], start=90, end=270, fill=(80, 40, 10))
    draw.chord([(250, 150), (310, 260)], start=270, end=90, fill=(80, 40, 10))
    # Eyes
    draw.ellipse([(150, 120), (170, 140)], fill=(40, 40, 80))
    draw.ellipse([(230, 120), (250, 140)], fill=(40, 40, 80))
    # Glasses
    draw.ellipse([(130, 100), (190, 160)], outline=(40, 40, 40), width=4)
    draw.ellipse([(210, 100), (270, 160)], outline=(40, 40, 40), width=4)
    draw.line([(190, 130), (210, 130)], fill=(40, 40, 40), width=4)
    # Nose
    draw.polygon([(200, 150), (195, 170), (205, 170)], fill=(220, 170, 130))
    
    # Body
    draw.ellipse([(50, 250), (350, 550)], fill=(70, 130, 180))
    draw.rectangle([(170, 250), (230, 320)], fill=(255, 255, 255))
    
    img.save(os.path.join(output_dir, "teacher.png"))

    # 2. Mouth Closed
    img_mc = Image.new("RGBA", (100, 50), (255, 255, 255, 0))
    draw_mc = ImageDraw.Draw(img_mc)
    draw_mc.line([(20, 25), (80, 25)], fill=(150, 40, 40), width=4)
    img_mc.save(os.path.join(output_dir, "mouth_closed.png"))

    # 3. Mouth Open
    img_mo = Image.new("RGBA", (100, 50), (255, 255, 255, 0))
    draw_mo = ImageDraw.Draw(img_mo)
    draw_mo.ellipse([(20, 10), (80, 40)], fill=(150, 40, 40))
    draw_mo.rectangle([(30, 10), (70, 20)], fill=(255, 255, 255)) # Teeth
    img_mo.save(os.path.join(output_dir, "mouth_open.png"))

    # 4. Pointer
    img_p = Image.new("RGBA", (100, 100), (255, 255, 255, 0))
    draw_p = ImageDraw.Draw(img_p)
    # Hand shape
    draw_p.polygon([(40, 20), (60, 20), (60, 60), (80, 60), (80, 80), (50, 100), (30, 100), (20, 80), (20, 50), (40, 50)], fill=(255, 200, 150), outline=(0, 0, 0), width=2)
    # Finger
    draw_p.rectangle([(40, 0), (55, 30)], fill=(255, 200, 150), outline=(0,0,0), width=2)
    img_p.save(os.path.join(output_dir, "pointer.png"))
    img_p.save(os.path.join(output_dir, "hand.png"))
    
    print("Assets generated in", output_dir)

if __name__ == "__main__":
    generate_assets(r"c:\Users\ceran\Downloads\EduGenAI\backend\assets")
