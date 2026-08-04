import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "funnels_config"
TOOLS_DIR = BASE_DIR / "tools"


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def load_config(funnel_id: str) -> dict:
    config_path = CONFIG_DIR / f"{funnel_id}.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    return json.loads(config_path.read_text(encoding="utf-8"))


def main() -> None:
    if len(sys.argv) not in (2, 3):
        print("Usage: python funnel_generator/tools/prepare_funnel_release.py <funnel_id> [--insert-email-config]")
        print("Example: python funnel_generator/tools/prepare_funnel_release.py womensfashion")
        print("Example: python funnel_generator/tools/prepare_funnel_release.py womensfashion --insert-email-config")
        sys.exit(1)

    funnel_id = sys.argv[1].strip()
    insert_email_config = len(sys.argv) == 3 and sys.argv[2] == "--insert-email-config"

    if len(sys.argv) == 3 and not insert_email_config:
        raise ValueError("Unknown option. Use --insert-email-config")

    config = load_config(funnel_id)

    print("Step 1: Generating funnel files...")
    run([sys.executable, str(BASE_DIR / "generate_funnel.py"), funnel_id])

    print()
    print("Step 2: Generating email config block...")
    run([sys.executable, str(TOOLS_DIR / "generate_email_config_block.py"), funnel_id])

    if insert_email_config:
        print()
        print("Step 3: Inserting email config block into local reference config...")
        run([sys.executable, str(TOOLS_DIR / "insert_email_config_block.py"), funnel_id])
    else:
        print()
        print("Step 3 skipped: local email config insertion not requested.")
        print("Use --insert-email-config to insert the block into the local reference config.")

    publish_folder = config.get("publish_folder", f"{funnel_id}_v2")
    server_folder = config.get("server_folder", "")
    landing_public_url = config.get("landing_public_url", "")
    thankyou_public_url = config.get("thankyou_public_url", "")

    landing_filename = config.get("landing_filename", "index.html")
    thankyou_filename = config.get("thankyou_filename", "thank-you.html")
    email_filename = config.get("email_filename", "email.html")
    config_filename = config.get("config_filename", "config_block.php")

    block_path = BASE_DIR / "server_api_reference" / "generated_blocks" / f"{funnel_id}_email_config_block_v2.php"

    print()
    print("Release package ready.")
    print()
    print("Local publish folder:")
    print(f"- funnel_generator/publish/{publish_folder}")
    print()
    print("Email config block:")
    print(f"- {block_path.relative_to(BASE_DIR)}")
    print()
    print("Server folder to create:")
    print(f"- {server_folder}")
    print()
    print("Commands to publish this funnel:")
    print()
    print(f'ssh root@server1.ibcb-s.com "mkdir -p {server_folder}"')
    print()
    print(f"scp funnel_generator/publish/{publish_folder}/{landing_filename} root@server1.ibcb-s.com:{server_folder}/")
    print(f"scp funnel_generator/publish/{publish_folder}/{thankyou_filename} root@server1.ibcb-s.com:{server_folder}/")
    print(f"scp funnel_generator/publish/{publish_folder}/{email_filename} root@server1.ibcb-s.com:{server_folder}/")
    print(f"scp funnel_generator/publish/{publish_folder}/{config_filename} root@server1.ibcb-s.com:{server_folder}/")
    print()
    print("Public URLs to test:")
    print(f"- Landing page: {landing_public_url}")
    print(f"- Thank-you page: {thankyou_public_url}")
    print()
    print("Reminder:")
    print("- Server email sending still requires api/funnel_guides_config_v2.php to contain this funnel block.")
    print("- Then test: lead saved, email received, thank-you redirect, PDFs accessible.")


if __name__ == "__main__":
    main()
