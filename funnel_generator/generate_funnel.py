import json
import re
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

CONFIG_DIR = BASE_DIR / "funnels_config"
TEMPLATE_DIR = BASE_DIR / "templates"
GENERATED_DIR = BASE_DIR / "generated"
PUBLISH_DIR = BASE_DIR / "publish"

REQUIRED_FIELDS = [
    "funnel_id",
    "funnel_name",
    "category_name",
    "guide_title",
    "headline",
    "subtitle",
    "cta_text",
    "pdf_en_url",
    "pdf_fr_url",
    "product_category_url",
    "primary_color",
    "secondary_color",
    "utm_campaign",
]


TEMPLATE_FILES = {
    "index.html": "landing_template.html",
    "thank-you.html": "thankyou_template.html",
    "email.html": "email_template.html",
    "config_block.php": "config_template.php",
}


PUBLISH_FILE_KEYS = {
    "index.html": "landing_filename",
    "thank-you.html": "thankyou_filename",
    "email.html": "email_filename",
    "config_block.php": "config_filename",
}


def load_config(funnel_id: str) -> dict:
    config_path = CONFIG_DIR / f"{funnel_id}.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_funnel_id(funnel_id: str) -> None:
    if not re.fullmatch(r"[a-z0-9_-]+", funnel_id):
        raise ValueError(
            "Invalid funnel_id. Use lowercase letters, numbers, hyphens, or underscores only."
        )


def validate_config(config: dict) -> None:
    missing_fields = [field for field in REQUIRED_FIELDS if not config.get(field)]

    if missing_fields:
        raise ValueError(
            "Missing required field(s): " + ", ".join(missing_fields)
        )

    validate_funnel_id(config["funnel_id"])


def build_featured_products_html(config: dict) -> str:
    products = config.get("featured_products", [])

    if not products:
        return ""

    cards = []

    for product in products[:4]:
        title = product.get("title", "")
        description = product.get("description", "")
        image_url = product.get("image_url", "")
        product_url = product.get("product_url", config.get("product_category_url", "#"))

        image_html = ""
        if image_url:
            image_html = f'<img src="{image_url}" alt="{title}" />'
        else:
            image_html = '<div class="product-image-placeholder">Home & Garden</div>'

        cards.append(f"""
          <article class="product-card">
            <div class="product-image">
              {image_html}
            </div>
            <div class="product-content">
              <h3>{title}</h3>
              <p>{description}</p>
              <a href="{product_url}" target="_blank" rel="noopener">View product</a>
            </div>
          </article>
        """)

    return "\n".join(cards)


def build_replacements(config: dict) -> dict:
    return {
        "{{FEATURED_SECTION_TITLE}}": config.get("featured_section_title", "Featured Picks"),
        "{{FEATURED_SECTION_SUBTITLE}}": config.get("featured_section_subtitle", ""),
        "{{FEATURED_PRODUCTS_HTML}}": build_featured_products_html(config),
        "{{FUNNEL_ID}}": config.get("funnel_id", ""),
        "{{FUNNEL_NAME}}": config.get("funnel_name", ""),
        "{{CATEGORY_NAME}}": config.get("category_name", ""),
        "{{GUIDE_TITLE}}": config.get("guide_title", ""),
        "{{HEADLINE}}": config.get("headline", ""),
        "{{SUBTITLE}}": config.get("subtitle", ""),
        "{{CTA_TEXT}}": config.get("cta_text", ""),
        "{{PDF_EN_URL}}": config.get("pdf_en_url", ""),
        "{{PDF_FR_URL}}": config.get("pdf_fr_url", ""),
        "{{PRODUCT_CATEGORY_URL}}": config.get("product_category_url", ""),
        "{{PRIMARY_COLOR}}": config.get("primary_color", ""),
        "{{SECONDARY_COLOR}}": config.get("secondary_color", ""),
        "{{HERO_IMAGE}}": config.get("hero_image", ""),
        "{{EMAIL_SUBJECT_EN}}": config.get("email_subject_en", ""),
        "{{EMAIL_SUBJECT_FR}}": config.get("email_subject_fr", ""),
        "{{EMAIL_BODY_EN}}": config.get("email_body_en", ""),
        "{{EMAIL_BODY_FR}}": config.get("email_body_fr", ""),
        "{{UTM_CAMPAIGN}}": config.get("utm_campaign", ""),
        "{{LANGUAGE_DEFAULT}}": config.get("language_default", "en"),
        "{{STATUS}}": config.get("status", "draft"),
        "{{LEAD_CAPTURE_URL}}": config.get("lead_capture_url", ""),
        "{{THANKYOU_URL}}": config.get("thankyou_url", ""),
        "{{BRAND_NAME}}": config.get("brand_name", "iBCB"),
        "{{LOGO_URL}}": config.get("logo_url", ""),
        "{{HERO_IMAGE_URL}}": config.get("hero_image_url", ""),
        "{{GUIDE_COVER_URL}}": config.get("guide_cover_url", ""),
    }


def render_template(template_content: str, replacements: dict) -> str:
    rendered = template_content

    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, str(value))

    return rendered


def render_file(template_filename: str, output_path: Path, replacements: dict) -> None:
    template_path = TEMPLATE_DIR / template_filename

    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    template_content = template_path.read_text(encoding="utf-8")
    rendered_content = render_template(template_content, replacements)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered_content, encoding="utf-8")


def generate_funnel(funnel_id: str) -> None:
    config = load_config(funnel_id)
    validate_config(config)

    funnel_id = config["funnel_id"]
    replacements = build_replacements(config)

    output_dir = GENERATED_DIR / funnel_id
    assets_dir = output_dir / "assets"

    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    generated_files = []

    for output_filename, template_filename in TEMPLATE_FILES.items():
        output_path = output_dir / output_filename
        render_file(template_filename, output_path, replacements)
        generated_files.append(output_path)

    publish_folder = config.get("publish_folder", f"{funnel_id}_v2")
    publish_dir = PUBLISH_DIR / publish_folder

    publish_files = []

    for default_output_filename, template_filename in TEMPLATE_FILES.items():
        filename_key = PUBLISH_FILE_KEYS[default_output_filename]
        publish_filename = config.get(filename_key, default_output_filename)
        publish_path = publish_dir / publish_filename

        render_file(template_filename, publish_path, replacements)
        publish_files.append(publish_path)

    print("Funnel generated successfully.")
    print()
    print(f"Funnel ID: {config['funnel_id']}")
    print(f"Funnel name: {config['funnel_name']}")
    print(f"Status: {config.get('status', 'draft')}")
    print()
    print("Generated files:")

    for file_path in generated_files:
        print(f"- {file_path.relative_to(BASE_DIR)}")

    print()
    print("Publish-ready files:")

    for file_path in publish_files:
        print(f"- {file_path.relative_to(BASE_DIR)}")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python funnel_generator/generate_funnel.py <funnel_id>")
        print("Example: python funnel_generator/generate_funnel.py homegarden")
        sys.exit(1)

    funnel_id = sys.argv[1].strip()
    generate_funnel(funnel_id)


if __name__ == "__main__":
    main()
