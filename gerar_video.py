import os
import sys
import time
import math
import random
from PIL import Image, ImageDraw, ImageFont

def create_showcase_video():
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VIDEO_DIVULGACAO.mp4")
    print(f"Generating showcase video at: {output_path}")

    width, height = 1280, 720
    fps = 30
    duration_secs = 12
    total_frames = fps * duration_secs

    # Colors
    c_black = (4, 8, 6)
    c_green = (0, 255, 102)
    c_green_dim = (0, 180, 70)
    c_green_dark = (6, 26, 14)
    c_white = (255, 255, 255)
    c_red = (229, 9, 20)
    c_red_dark = (30, 8, 10)
    c_purple = (168, 85, 247)
    c_purple_dark = (24, 10, 36)

    # Try font loading
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 26)
        font_mono = ImageFont.truetype("consola.ttf", 16)
        font_mono_bold = ImageFont.truetype("consolab.ttf", 18)
        font_sub = ImageFont.truetype("consola.ttf", 12)
        font_big = ImageFont.truetype("arialbd.ttf", 32)
    except Exception:
        font_title = ImageFont.load_default()
        font_mono = ImageFont.load_default()
        font_mono_bold = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_big = ImageFont.load_default()

    # Matrix drops state
    columns = width // 16
    drops = [random.randint(-50, 0) for _ in range(columns)]
    chars = "0123456789ABCDEFNETFLIXHBOMAXCONNECTPAIRSTREAM"

    frames = []

    print("Rendering frames...")
    for frame_idx in range(total_frames):
        t = frame_idx / fps  # Current time in seconds

        img = Image.new("RGB", (width, height), (3, 6, 4))
        draw = ImageDraw.Draw(img)

        # 1. Determine state based on timeline
        # 0.0 - 3.5s: Green ROOT_SECURITY login screen
        # 3.5 - 4.2s: Unlock transition
        # 4.2 - 8.0s: Netflix Dashboard with Smart TV pairing
        # 8.0 - 10.0s: Switch to HBO Max
        # 10.0 - 12.0s: Cookie Vault Red Security
        
        is_login = (t < 3.8)
        is_netflix = (3.8 <= t < 8.0)
        is_hbo = (8.0 <= t < 10.0)
        is_cookie = (t >= 10.0)

        # Matrix color
        if is_login:
            m_color = c_green
            m_fade = (0, 0, 0)
        elif is_cookie:
            m_color = c_red
            m_fade = (10, 2, 4)
        elif is_hbo:
            m_color = c_purple
            m_fade = (8, 3, 15)
        else:
            m_color = c_red
            m_fade = (10, 4, 6)

        # Draw Matrix Rain background
        for i in range(columns):
            x = i * 16
            y = drops[i] * 18

            # Draw trail
            for trail_k in range(1, 10):
                ty = y - (trail_k * 18)
                if 0 <= ty < height:
                    char_c = random.choice(chars)
                    alpha_factor = (10 - trail_k) / 10.0
                    r = int(m_color[0] * alpha_factor)
                    g = int(m_color[1] * alpha_factor)
                    b = int(m_color[2] * alpha_factor)
                    draw.text((x, ty), char_c, font=font_sub, fill=(r, g, b))

            # Head char (bright)
            if 0 <= y < height:
                draw.text((x, y), random.choice(chars), font=font_sub, fill=c_white)

            drops[i] += 1
            if drops[i] * 18 > height and random.random() > 0.96:
                drops[i] = 0

        # Draw Overlay Scenes
        if is_login:
            # 🔐 ROOT_SECURITY CARD (CENTERED)
            cx, cy = width // 2, height // 2
            card_w, card_h = 420, 360
            x0, y0 = cx - card_w // 2, cy - card_h // 2
            x1, y1 = cx + card_w // 2, cy + card_h // 2

            # Card background & glowing border
            draw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=c_green_dark, outline=c_green, width=2)

            # Circular Icon Box
            draw.ellipse([cx - 32, y0 + 20, cx + 32, y0 + 84], outline=c_green, width=2, fill=(0, 40, 15))
            draw.text((cx - 10, y0 + 38), "🔒", font=font_title, fill=c_green)

            # Title
            draw.text((cx - 100, y0 + 100), "ROOT_SECURITY", font=font_title, fill=c_white)
            draw.text((cx - 150, y0 + 138), "// ACESSO RESTRITO • PROTOCOLO CRIPTOGRÁFICO", font=font_sub, fill=c_green)

            # Password input box
            pass_y = y0 + 175
            draw.rounded_rectangle([x0 + 30, pass_y, x1 - 30, pass_y + 44], radius=20, fill=(0, 0, 0), outline=c_green, width=1)
            
            # Typing animation
            full_pwd = "CYBER#ROOT@9821$MATRIX*SECURE!2026"
            if t < 1.0:
                typed = ""
                display_txt = "🔒 DIGITE A SENHA MESTRE..."
                txt_col = (0, 180, 80)
            elif t < 3.2:
                chars_to_show = int((t - 1.0) / 2.2 * len(full_pwd))
                typed = "•" * min(chars_to_show, len(full_pwd))
                display_txt = "🔒 " + typed + ("|" if (int(t * 4) % 2 == 0) else "")
                txt_col = c_white
            else:
                typed = "•" * len(full_pwd)
                display_txt = "🔒 " + typed
                txt_col = c_white

            draw.text((x0 + 44, pass_y + 12), display_txt, font=font_mono, fill=txt_col)
            draw.text((x1 - 65, pass_y + 12), "👁️", font=font_mono, fill=c_green)

            # Checkbox
            draw.text((x0 + 45, pass_y + 58), "✔ Lembrar neste dispositivo (Acesso rápido)", font=font_sub, fill=(160, 230, 50))

            # Button
            btn_y = pass_y + 88
            btn_fill = c_green if t < 3.3 else (255, 255, 255)
            draw.rounded_rectangle([x0 + 30, btn_y, x1 - 30, btn_y + 46], radius=24, fill=btn_fill)
            draw.text((cx - 95, btn_y + 14), "DESBLOQUEAR TERMINAL 🔓", font=font_mono_bold, fill=(0, 0, 0))

        else:
            # DASHBOARD HUD (Netflix / HBO Max / Cookie Vault)
            # Top Telemetry Bar
            top_y = 30
            draw.rounded_rectangle([width//2 - 280, top_y, width//2 + 280, top_y + 40], radius=20, fill=(15, 8, 12), outline=(120, 30, 40), width=1)
            draw.ellipse([width//2 - 260, top_y + 14, width//2 - 248, top_y + 26], fill=(0, 255, 100))
            draw.text((width//2 - 240, top_y + 12), "ONLINE", font=font_mono_bold, fill=c_green)
            draw.text((width//2 - 150, top_y + 12), "PING: 18ms", font=font_mono, fill=(200, 200, 200))
            draw.rounded_rectangle([width//2 + 50, top_y + 6, width//2 + 150, top_y + 34], radius=14, fill=(40, 20, 25), outline=c_red)
            draw.text((width//2 + 65, top_y + 10), "🍪 COOKIES", font=font_mono, fill=(255, 215, 0))
            draw.rounded_rectangle([width//2 + 160, top_y + 6, width//2 + 265, top_y + 34], radius=14, fill=(40, 20, 25), outline=c_red)
            draw.text((width//2 + 175, top_y + 10), "🔒 BLOQUEAR", font=font_mono, fill=(255, 255, 255))

            # Service switcher tabs
            tab_y = 85
            if is_hbo:
                # HBO active
                draw.rounded_rectangle([width//2 - 280, tab_y, width//2 - 10, tab_y + 42], radius=18, fill=(20, 10, 15), outline=(60, 20, 30))
                draw.text((width//2 - 190, tab_y + 12), "🔴 NETFLIX", font=font_mono_bold, fill=(180, 120, 130))
                draw.rounded_rectangle([width//2 + 10, tab_y, width//2 + 280, tab_y + 42], radius=18, fill=(80, 20, 120), outline=c_purple, width=2)
                draw.text((width//2 + 90, tab_y + 12), "🟣 HBO MAX", font=font_mono_bold, fill=c_white)
            else:
                # Netflix active
                draw.rounded_rectangle([width//2 - 280, tab_y, width//2 - 10, tab_y + 42], radius=18, fill=(160, 10, 20), outline=c_red, width=2)
                draw.text((width//2 - 190, tab_y + 12), "🔴 NETFLIX", font=font_mono_bold, fill=c_white)
                draw.rounded_rectangle([width//2 + 10, tab_y, width//2 + 280, tab_y + 42], radius=18, fill=(20, 10, 30), outline=(60, 20, 80))
                draw.text((width//2 + 90, tab_y + 12), "🟣 HBO MAX", font=font_mono_bold, fill=(180, 140, 200))

            # Main Card (Active Account & PIN hud)
            card_y = 145
            cur_theme = c_purple if is_hbo else c_red
            cur_fill = c_purple_dark if is_hbo else c_red_dark
            draw.rounded_rectangle([width//2 - 280, card_y, width//2 + 280, card_y + 530], radius=24, fill=cur_fill, outline=cur_theme, width=2)

            # Account Header
            svc_name = "HBO MAX" if is_hbo else "NETFLIX"
            draw.text((width//2 - 255, card_y + 20), f"🔴 CONTA {svc_name} PRONTA PARA ATIVAÇÃO", font=font_mono_bold, fill=cur_theme)
            draw.text((width//2 + 140, card_y + 20), "● SINAL ONLINE", font=font_mono, fill=c_green)

            # Account Boxes
            draw.rounded_rectangle([width//2 - 255, card_y + 55, width//2 - 15, card_y + 115], radius=14, fill=(0, 0, 0), outline=cur_theme)
            draw.text((width//2 - 245, card_y + 65), "// CONTA CONECTADA", font=font_sub, fill=(180, 180, 180))
            draw.text((width//2 - 245, card_y + 88), "[BR] brayanmmello@gmail.com", font=font_mono_bold, fill=c_white)

            draw.rounded_rectangle([width//2 + 5, card_y + 55, width//2 + 255, card_y + 115], radius=14, fill=(0, 0, 0), outline=cur_theme)
            draw.text((width//2 + 15, card_y + 65), "// PLANO DA CONTA", font=font_sub, fill=(180, 180, 180))
            draw.text((width//2 + 15, card_y + 88), "⚡ Premium 4K UHD VIP", font=font_mono_bold, fill=(255, 215, 0))

            # Smart TV Pin HUD
            pin_y = card_y + 145
            draw.text((width//2 - 255, pin_y), f"📺 SMART TV // {svc_name} PAIRING", font=font_mono_bold, fill=c_white)
            draw.text((width//2 + 150, pin_y), "0 / 8 DÍGITOS", font=font_mono_bold, fill=cur_theme)

            # 8 Pin circles
            sample_code = "87419205" if is_netflix else "MAX492"
            typed_len = int((t - 4.5) * 3) if is_netflix and t >= 4.5 else (len(sample_code) if is_hbo else 0)
            typed_len = max(0, min(typed_len, len(sample_code)))

            start_x = width//2 - 240
            for slot_i in range(8):
                sx = start_x + slot_i * 60
                sy = pin_y + 40
                char_val = sample_code[slot_i] if slot_i < typed_len else ""
                slot_fill = (50, 10, 20) if char_val else (0, 0, 0)
                slot_border = cur_theme if char_val else (100, 30, 40)
                draw.ellipse([sx, sy, sx + 50, sy + 50], fill=slot_fill, outline=slot_border, width=2)
                if char_val:
                    draw.text((sx + 16, sy + 12), char_val, font=font_title, fill=c_white)

            # Transmit Button
            btn_tx_y = pin_y + 115
            pulse_color = (255, 40, 50) if is_netflix else (180, 90, 255)
            draw.rounded_rectangle([width//2 - 255, btn_tx_y, width//2 + 255, btn_tx_y + 55], radius=28, fill=pulse_color)
            draw.text((width//2 - 120, btn_tx_y + 16), "EXECUTAR INJEÇÃO DE TOKEN ⚡", font=font_mono_bold, fill=c_white)

            # Lower Deck queue preview
            draw.text((width//2 - 255, btn_tx_y + 75), "🍪 PRÓXIMOS COOKIES NA FILA: 18 CONTAS ATIVAS", font=font_sub, fill=(200, 200, 200))
            for q_idx in range(3):
                qy = btn_tx_y + 100 + q_idx * 40
                draw.rounded_rectangle([width//2 - 255, qy, width//2 + 255, qy + 32], radius=10, fill=(0, 0, 0), outline=(60, 20, 30))
                draw.text((width//2 - 240, qy + 8), f"● Conta VIP #{q_idx+1}: [BR] premium_{q_idx+1}@streaming.com", font=font_mono, fill=(230, 230, 230))
                draw.text((width//2 + 160, qy + 8), "⚡ ONLINE", font=font_mono, fill=c_green)

            # If Cookie Vault scene (10.0s - 12.0s), draw the Red COOKIE_SECURITY modal on top
            if is_cookie:
                cx, cy = width // 2, height // 2
                card_w, card_h = 420, 360
                x0, y0 = cx - card_w // 2, cy - card_h // 2
                x1, y1 = cx + card_w // 2, cy + card_h // 2

                # Dim background
                draw.rectangle([0, 0, width, height], fill=(0, 0, 0, 180))
                # Red Cookie Security Card
                draw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=(20, 6, 8), outline=c_red, width=2)
                draw.ellipse([cx - 32, y0 + 20, cx + 32, y0 + 84], outline=c_red, width=2, fill=(40, 10, 15))
                draw.text((cx - 10, y0 + 38), "🔒", font=font_title, fill=c_red)
                draw.text((cx - 110, y0 + 100), "COOKIE_SECURITY", font=font_title, fill=c_white)
                draw.text((cx - 140, y0 + 138), "// COFRE DE COOKIES • PROTOCOLO CRIPTOGRÁFICO", font=font_sub, fill=c_red)

                pass_y = y0 + 175
                draw.rounded_rectangle([x0 + 30, pass_y, x1 - 30, pass_y + 44], radius=20, fill=(0, 0, 0), outline=c_red, width=1)
                draw.text((x0 + 44, pass_y + 12), "🔒 ••••••••••••••••••••••", font=font_mono, fill=c_white)
                draw.text((x1 - 65, pass_y + 12), "👁️", font=font_mono, fill=c_red)

                btn_y = pass_y + 70
                draw.rounded_rectangle([x0 + 30, btn_y, x1 - 30, btn_y + 46], radius=24, fill=c_red)
                draw.text((cx - 85, btn_y + 14), "DESBLOQUEAR COFRE 🔓", font=font_mono_bold, fill=c_white)

        frames.append(img)
        if frame_idx % 30 == 0:
            print(f"Progress: {frame_idx}/{total_frames} frames rendered ({int(frame_idx/total_frames*100)}%)")

    # Try saving as MP4 or animated WebP/GIF
    print("Exporting video...")
    try:
        import imageio
        imageio.mimsave(output_path, [frame.convert("RGB") for frame in frames], fps=fps)
        print(f"Video successfully exported to {output_path}")
        return output_path
    except Exception as e:
        print(f"imageio mp4 failed ({e}), saving animated WebP and GIF...")
        webp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VIDEO_DIVULGACAO.webp")
        gif_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VIDEO_DIVULGACAO.gif")
        frames[0].save(webp_path, save_all=True, append_images=frames[1:], duration=33, loop=0)
        frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=33, loop=0)
        print(f"Saved animation to {webp_path} and {gif_path}")
        return webp_path

if __name__ == "__main__":
    create_showcase_video()
