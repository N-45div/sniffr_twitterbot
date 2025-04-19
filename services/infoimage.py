from PIL import Image, ImageDraw, ImageFont
import textwrap
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

def draw_progress_ring(draw, center, radius, thickness, score, color):
    """Draw a circular progress ring for the risk score."""
    start_angle = 90  # Start at the top
    end_angle = 90 - (score / 100 * 360)  # Map score (0-100) to angle (0-360)
    # Background ring (gray)
    draw.arc(
        [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius],
        start=0, end=360, fill=(100, 100, 100), width=thickness
    )
    # Progress ring (colored based on score)
    draw.arc(
        [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius],
        start=start_angle, end=end_angle, fill=color, width=thickness
    )

def create_report_image(report_data, token_address):
    logging.info(f"Creating report image for token: {token_address}")
    try:
        # Base image dimensions
        width = 1200
        min_height = 800
        image = Image.new('RGB', (width, min_height), color=(30, 30, 40))
        draw = ImageDraw.Draw(image)

        # Load fonts with adjusted sizes for better readability
        try:
            title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 50)
            header_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
            normal_font = ImageFont.truetype("DejaVuSans.ttf", 28)
            small_font = ImageFont.truetype("DejaVuSans.ttf", 20)
        except IOError:
            logging.warning("DejaVuSans fonts not found, using default font")
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            normal_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # Modern color palette with better contrast
        white = (240, 240, 240)
        light_gray = (180, 180, 180)
        yellow = (255, 200, 0)
        red = (255, 100, 100)
        green = (100, 200, 150)
        blue = (120, 180, 255)

        # Margins and spacing
        left_margin = 50
        right_margin = 50
        top_margin = 40
        bottom_margin = 40
        vertical_spacing = 15  # Increased for better separation
        content_width = width - left_margin - right_margin

        # Calculate required height dynamically
        y_position = top_margin

        # Title
        title_text = "Token Risk Report"
        bbox = draw.textbbox((0, 0), title_text, font=title_font)
        title_height = bbox[3] - bbox[1]
        y_position += title_height + vertical_spacing

        # Token address (wrapped to fit)
        if len(token_address) > 20:
            short_address = f"{token_address[:6]}...{token_address[-6:]}"
        else:
            short_address = token_address
        address_text = f"Address: {short_address}"
        bbox = draw.textbbox((0, 0), address_text, font=normal_font)
        address_height = bbox[3] - bbox[1]
        y_position += address_height + vertical_spacing

        # Timestamp
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        bbox = draw.textbbox((0, 0), f"Generated: {current_time}", font=small_font)
        timestamp_height = bbox[3] - bbox[1]
        y_position += timestamp_height + vertical_spacing

        # Risk score section
        score = report_data.get("normalized_score", 0)
        circle_radius = 60
        circle_height = circle_radius * 2
        risk_level = "HIGH RISK" if score > 66 else "MEDIUM RISK" if score > 33 else "LOW RISK"
        bbox = draw.textbbox((0, 0), risk_level, font=header_font)
        risk_label_height = bbox[3] - bbox[1]
        y_position += max(circle_height, risk_label_height) + vertical_spacing + 30

        # Risks section
        risks = report_data.get("risks", [])[:3]
        for risk in risks:
            risk_name = risk.get("name", "Unknown Risk")
            risk_level = risk.get("level", "unknown").upper()
            risk_value = risk.get("value", "")
            risk_text = f"Level: {risk_level}"
            if risk_value:
                risk_text += f" ({risk_value})"

            # Risk name (wrapped with dynamic font sizing)
            risk_name_font = normal_font
            wrapped_name = textwrap.wrap(f"{i+1}. {risk_name}", width=int(content_width / 20))
            if len(wrapped_name) > 2:  # If more than 2 lines, reduce font size
                risk_name_font = small_font
                wrapped_name = textwrap.wrap(f"{i+1}. {risk_name}", width=int(content_width / 15))
            for line in wrapped_name:
                bbox = draw.textbbox((0, 0), line, font=risk_name_font)
                y_position += bbox[3] - bbox[1] + 5

            # Risk level
            bbox = draw.textbbox((0, 0), risk_text, font=normal_font)
            y_position += bbox[3] - bbox[1] + 5

            # Score bar
            y_position += 30 + vertical_spacing  # Bar height + spacing

        # Disclaimer
        disclaimer_text = "This report is for informational purposes only. Do your own research."
        wrapped_disclaimer = textwrap.wrap(disclaimer_text, width=int(content_width / 10))
        for line in wrapped_disclaimer:
            bbox = draw.textbbox((0, 0), line, font=small_font)
            y_position += bbox[3] - bbox[1] + 5

        y_position += bottom_margin  # Bottom padding

        # Adjust image height if necessary
        final_height = max(min_height, y_position)
        image = Image.new('RGB', (width, final_height), color=(30, 30, 40))
        draw = ImageDraw.Draw(image)

        # Apply gradient background
        for y in range(final_height):
            r = int(30 + (y / final_height * 20))
            g = int(30 + (y / final_height * 40))
            b = int(40 + (y / final_height * 60))
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Draw border
        draw.rectangle([10, 10, width-10, final_height-10], outline=(255, 255, 255, 50), width=2)

        # Redraw all content
        y_position = top_margin

        # Title with shadow
        draw.text((left_margin + 2, y_position + 2), title_text, font=title_font, fill=(50, 50, 50))
        draw.text((left_margin, y_position), title_text, font=title_font, fill=white)
        y_position += title_height + vertical_spacing

        # Token address
        draw.text((left_margin, y_position), address_text, font=normal_font, fill=light_gray)
        y_position += address_height + vertical_spacing

        # Timestamp (aligned to the right)
        bbox = draw.textbbox((0, 0), f"Generated: {current_time}", font=small_font)
        text_width = bbox[2] - bbox[0]
        draw.text((width - right_margin - text_width, y_position), f"Generated: {current_time}", font=small_font, fill=light_gray)
        y_position += timestamp_height + vertical_spacing

        # Risk score with progress ring
        score_color = red if score > 66 else yellow if score > 33 else green
        circle_center = (left_margin + circle_radius + 20, y_position + circle_radius)
        draw_progress_ring(draw, circle_center, circle_radius, 10, score, score_color)
        score_text = f"{score}"
        bbox = draw.textbbox((0, 0), score_text, font=header_font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text((circle_center[0] - w//2, circle_center[1] - h//2), score_text, font=header_font, fill=score_color)
        draw.text((left_margin + circle_radius * 2 + 60, y_position + circle_radius - risk_label_height//2), risk_level, font=header_font, fill=score_color)
        y_position += circle_height + vertical_spacing + 30

        # Risks section
        draw.text((left_margin, y_position), "Top Risks:", font=header_font, fill=white)
        y_position += risk_label_height + vertical_spacing

        for i, risk in enumerate(risks):
            risk_name = risk.get("name", "Unknown Risk")
            risk_level = risk.get("level", "unknown").upper()
            risk_value = risk.get("value", "")
            risk_score = risk.get("score", 0)
            level_color = red if risk_level == "DANGER" else yellow if risk_level == "WARNING" else blue

            # Risk name (wrapped with dynamic font sizing)
            risk_name_font = normal_font
            wrapped_name = textwrap.wrap(f"{i+1}. {risk_name}", width=int(content_width / 20))
            if len(wrapped_name) > 2:  # If more than 2 lines, reduce font size
                risk_name_font = small_font
                wrapped_name = textwrap.wrap(f"{i+1}. {risk_name}", width=int(content_width / 15))
            for line in wrapped_name:
                draw.text((left_margin + 20, y_position), line, font=risk_name_font, fill=white)
                bbox = draw.textbbox((0, 0), line, font=risk_name_font)
                y_position += bbox[3] - bbox[1] + 5

            # Risk level
            risk_text = f"Level: {risk_level}"
            if risk_value:
                risk_text += f" ({risk_value})"
            draw.text((left_margin + 40, y_position), risk_text, font=normal_font, fill=level_color)
            bbox = draw.textbbox((0, 0), risk_text, font=normal_font)
            y_position += bbox[3] - bbox[1] + 5

            # Score bar
            bar_width = min(content_width - 100, risk_score * 4)
            draw.rounded_rectangle(
                [(left_margin + 40, y_position + 10), (left_margin + 40 + bar_width, y_position + 30)],
                radius=5, fill=level_color
            )
            y_position += 40 + vertical_spacing

        # Disclaimer (aligned to the bottom-right)
        disclaimer_text = "This report is for informational purposes only. Do your own research."
        wrapped_disclaimer = textwrap.wrap(disclaimer_text, width=int(content_width / 10))
        disclaimer_y = final_height - bottom_margin - len(wrapped_disclaimer) * 25
        for line in wrapped_disclaimer:
            bbox = draw.textbbox((0, 0), line, font=small_font)
            text_width = bbox[2] - bbox[0]
            draw.text((width - right_margin - text_width, disclaimer_y), line, font=small_font, fill=light_gray)
            disclaimer_y += 25

        # Watermark ("Powered by Sniffr")
        watermark_text = "Powered by Sniffr"
        bbox = draw.textbbox((0, 0), watermark_text, font=small_font)
        text_width = bbox[2] - bbox[0]
        draw.text((left_margin, final_height - bottom_margin - 20), watermark_text, font=small_font, fill=light_gray)

        # Save the image
        image.save('created_image.png')
        logging.info("Image saved successfully")
        return 'created_image.png'
    except Exception as e:
        logging.error(f"Failed to create image: {e}")
        raise