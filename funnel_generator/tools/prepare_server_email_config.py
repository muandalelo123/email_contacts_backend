import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

REFERENCE_CONFIG = BASE_DIR / "server_api_reference" / "funnel_guides_config_v2.php"
GENERATED_BLOCKS_DIR = BASE_DIR / "server_api_reference" / "generated_blocks"
DEPLOY_READY_DIR = BASE_DIR / "server_api_reference" / "deploy_ready"
DEPLOY_READY_CONFIG = DEPLOY_READY_DIR / "funnel_guides_config_v2.php"


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python funnel_generator/tools/prepare_server_email_config.py <funnel_id>")
        print("Example: python funnel_generator/tools/prepare_server_email_config.py womensfashion")
        sys.exit(1)

    funnel_id = sys.argv[1].strip()
    block_path = GENERATED_BLOCKS_DIR / f"{funnel_id}_email_config_block_v2.php"

    if not REFERENCE_CONFIG.exists():
        raise FileNotFoundError(f"Reference config not found: {REFERENCE_CONFIG}")

    if not block_path.exists():
        raise FileNotFoundError(
            f"Generated block not found: {block_path}. "
            f"Run prepare_funnel_release.py first."
        )

    config_text = REFERENCE_CONFIG.read_text(encoding="utf-8")
    block_text = block_path.read_text(encoding="utf-8").strip()

    funnel_key = f"'{funnel_id}'"

    if funnel_key in config_text:
        print(f"{funnel_id} already exists in the reference config.")
        print("Deploy-ready config will be created from the current reference file.")
        new_text = config_text
    else:
        idx = config_text.rfind("];")

        if idx == -1:
            raise RuntimeError("Final closing array marker ]; not found.")

        new_text = config_text[:idx].rstrip() + "\n\n" + block_text + "\n\n" + config_text[idx:]

    DEPLOY_READY_DIR.mkdir(parents=True, exist_ok=True)
    DEPLOY_READY_CONFIG.write_text(new_text, encoding="utf-8")

    print("Deploy-ready server email config prepared.")
    print(f"- {DEPLOY_READY_CONFIG.relative_to(BASE_DIR)}")
    print()
    print("Next commands:")
    print()
    print("php -l funnel_generator/server_api_reference/deploy_ready/funnel_guides_config_v2.php")
    print()
    print("scp funnel_generator/server_api_reference/deploy_ready/funnel_guides_config_v2.php root@server1.ibcb-s.com:/home/ibcbquil/public_html/api/funnel_guides_config_v2.php")


if __name__ == "__main__":
    main()
