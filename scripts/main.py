import logging
import tech
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_subdirectory(sub_name: str) -> None:
    """Process a subdirectory based on its config.json."""
    sub_path = Path("data") / sub_name
    config_path = sub_path / "config.json"
    
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        return

    config = tech.load_json(config_path)
    display_name = config.get("name", sub_name)
    logger.info(f"== Processing Category: {display_name} ==")
    
    files_to_process = config.get("file", [])
    completed_files = set(config.get("completed", []))
    
    for file_name in files_to_process:
        if file_name not in completed_files:
            file_path = sub_path / file_name
            if file_path.exists():
                tech.action(str(file_path))
                completed_files.add(file_name)
            else:
                logger.warning(f"File listed in config but not found: {file_path}")
    
    # Update and save config
    config["completed"] = sorted(list(completed_files))
    tech.write_json(config_path, config)

def main() -> None:
    """Main entry point for the script."""
    root_config_path = Path("data/config.json")
    if not root_config_path.exists():
        logger.error(f"Root config not found: {root_config_path}")
        return

    root_config = tech.load_json(root_config_path)
    subdirectories = root_config.get("file", [])
    
    for sub in subdirectories:
        process_subdirectory(sub)

if __name__ == "__main__":
    main()
