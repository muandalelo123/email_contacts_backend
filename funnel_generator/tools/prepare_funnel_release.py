import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "funnels_config"
TOOLS_DIR = BASE_DIR / "tools"


ALLOWED_OPTIONS = {
    "--insert-email-config",
    "--prepare-server-config",
}


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def load_config(funnel_id: str) -> dict:
    config_path = CONFIG_DIR / f"{funnel_id}.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    return json.loads(config_path.read_text(encoding="utf-8"))


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python funnel_generator/tools/prepare_funnel_release.py <funnel_id> [options]")
        print("Options:")
        print("  --insert-email-config")
        print("  --prepare-server-config")
        print()
        print("Example:")
        print("  python funnel_generator/tools/prepare_funnel_release.py womensfashion --insert-email-config --prepare-server-config")
        sys.exit(1)

    funnel_id = sys.argv[1].strip()
    options = set(sys.argv[2:])

    unknown_options = options - ALLOWED_OPTIONS
    if unknown_options:
        raise ValueError("Unknown option(s): " + ", ".join(sorted(unknown_options)))

    insert_email_config = "--insert-email-config" in options
    prepare_server_config = "--prepare-server-config" in options

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

    if prepare_server_config:
        print()
        print("Step 4: Preparing deploy-ready server email config...")
        run([sys.executable, str(TOOLS_DIR / "prepare_server_email_config.py"), funnel_id])
    else:
        print()
        print("Step 4 skipped: deploy-ready server config not requested.")
        print("Use --prepare-server-config to prepare deploy_ready/funnel_guides_config_v2.php.")

    publish_folder = config.get("publish_folder", f"{funnel_id}_v2")
    server_folder = config.get("server_folder", "")
    landing_public_url = config.get("landing_public_url", "")
    thankyou_public_url = config.get("thankyou_public_url", "")

    landing_filename = config.get("landing_filename", "index.html")
    thankyou_filename = config.get("thankyou_filename", "thank-you.html")
    email_filename = config.get("email_filename", "email.html")
    config_filename = config.get("config_filename", "config_block.php")

    block_path = BASE_DIR / "server_api_reference" / "generated_blocks" / f"{funnel_id}_email_config_block_v2.php"
    deploy_ready_path = BASE_DIR / "server_api_reference" / "deploy_ready" / "funnel_guides_config_v2.php"

    print()
    print("Release package ready.")
    print()
    print("Local publish folder:")
    print(f"- funnel_generator/publish/{publish_folder}")
    print()
    print("Email config block:")
    print(f"- {block_path.relative_to(BASE_DIR)}")

    if prepare_server_config:
        print()
        print("Deploy-ready server config:")
        print(f"- {deploy_ready_path.relative_to(BASE_DIR)}")

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

    if prepare_server_config:
        print()
        print("Commands to validate and deploy server email config:")
        print()
        print("scp funnel_generator/server_api_reference/deploy_ready/funnel_guides_config_v2.php root@server1.ibcb-s.com:/home/ibcbquil/public_html/api/funnel_guides_config_v2_test.php")
        print('ssh root@server1.ibcb-s.com "php -l /home/ibcbquil/public_html/api/funnel_guides_config_v2_test.php"')
        print('ssh root@server1.ibcb-s.com "cp /home/ibcbquil/public_html/api/funnel_guides_config_v2.php /home/ibcbquil/public_html/api/funnel_guides_config_v2.php.bak_$(date +%Y%m%d_%H%M%S)"')
        print("scp funnel_generator/server_api_reference/deploy_ready/funnel_guides_config_v2.php root@server1.ibcb-s.com:/home/ibcbquil/public_html/api/funnel_guides_config_v2.php")
        print('ssh root@server1.ibcb-s.com "php -l /home/ibcbquil/public_html/api/funnel_guides_config_v2.php"')

    print()
    print("Public URLs to test:")
    print(f"- Landing page: {landing_public_url}")
    print(f"- Thank-you page: {thankyou_public_url}")
    print()
    print("Final test checklist:")
    print("- lead saved")
    print("- email received")
    print("- thank-you redirect works")
    print("- PDF EN accessible")
    print("- PDF FR accessible")


if __name__ == "__main__":
    main()
