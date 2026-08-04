import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "funnels_config"
OUTPUT_DIR = BASE_DIR / "server_api_reference" / "generated_blocks"


def php_escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


def build_block(config: dict) -> str:
    funnel_id = php_escape(config.get("funnel_id", ""))
    label = php_escape(config.get("guide_title", config.get("funnel_name", "")))
    brand = php_escape(config.get("brand_name", "iBCB"))
    accent = php_escape(config.get("primary_color", "#0B3D91"))
    dark = "#1F2937"

    pdf_en = php_escape(config.get("pdf_en_url", ""))
    pdf_fr = php_escape(config.get("pdf_fr_url", ""))
    product_url = php_escape(config.get("product_category_url", ""))
    utm_campaign = php_escape(config.get("utm_campaign", ""))

    subject_en = php_escape(config.get("email_subject_en", f"Your Free {label}"))
    subject_fr = php_escape(config.get("email_subject_fr", f"Votre guide gratuit {label}"))

    body_en = php_escape(config.get("email_body_en", "Thank you for requesting your free guide. You can download it using the link below."))
    body_fr = php_escape(config.get("email_body_fr", "Merci d’avoir demandé votre guide gratuit. Vous pouvez le télécharger avec le lien ci-dessous."))

    return f"""  '{funnel_id}' => [
    'label' => '{label}',
    'brand' => '{brand}',
    'from_email' => 'no-reply@ibcb-s.com',
    'from_name'  => '{brand}',
    'reply_to'   => 'support@ibcb-s.com',
    'accent_color' => '{accent}',
    'dark_color'   => '{dark}',
    'pdf' => [
      'EN' => '{pdf_en}',
      'FR' => '{pdf_fr}',
    ],
    'product_url'  => '{product_url}',
    'utm_campaign' => '{utm_campaign}',
    'subject' => [
      'EN' => '{subject_en}',
      'FR' => '{subject_fr}',
    ],
    'body' => [
      'EN' => '{body_en}',
      'FR' => '{body_fr}',
    ],
  ],"""


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python funnel_generator/tools/generate_email_config_block.py <funnel_id>")
        print("Example: python funnel_generator/tools/generate_email_config_block.py womensfashion")
        sys.exit(1)

    funnel_id = sys.argv[1].strip()
    config_path = CONFIG_DIR / f"{funnel_id}.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    block = build_block(config)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR / f"{funnel_id}_email_config_block_v2.php"
    output_path.write_text(block + "\n", encoding="utf-8")

    print("Email config block generated successfully.")
    print(f"- {output_path.relative_to(BASE_DIR)}")
    print()
    print(block)


if __name__ == "__main__":
    main()
