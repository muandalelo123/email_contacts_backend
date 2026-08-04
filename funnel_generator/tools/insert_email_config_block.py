import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_REFERENCE = BASE_DIR / "server_api_reference" / "funnel_guides_config_v2.php"
BLOCKS_DIR = BASE_DIR / "server_api_reference" / "generated_blocks"


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python funnel_generator/tools/insert_email_config_block.py <funnel_id>")
        print("Example: python funnel_generator/tools/insert_email_config_block.py womensfashion")
        sys.exit(1)

    funnel_id = sys.argv[1].strip()

    config_path = CONFIG_REFERENCE
    block_path = BLOCKS_DIR / f"{funnel_id}_email_config_block_v2.php"

    if not config_path.exists():
        raise FileNotFoundError(f"Reference config file not found: {config_path}")

    if not block_path.exists():
        raise FileNotFoundError(
            f"Email config block not found: {block_path}. "
            f"Run generate_email_config_block.py first."
        )

    config_text = config_path.read_text(encoding="utf-8")
    block_text = block_path.read_text(encoding="utf-8").strip()

    funnel_key = f"'{funnel_id}'"

    if funnel_key in config_text:
        print(f"{funnel_id} already exists in funnel_guides_config_v2.php. No insertion done.")
        return

    marker = "];"
    idx = config_text.rfind(marker)

    if idx == -1:
        raise RuntimeError("Final closing array marker ]; not found.")

    new_text = config_text[:idx].rstrip() + "\n\n" + block_text + "\n\n" + config_text[idx:]

    config_path.write_text(new_text, encoding="utf-8")

    print("Email config block inserted successfully.")
    print(f"- Funnel ID: {funnel_id}")
    print(f"- Updated file: {config_path.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
