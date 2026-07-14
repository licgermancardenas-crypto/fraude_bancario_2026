"""Generate synthetic fraud graph dataset using gen-fraud-graph."""
import argparse
import yaml
from pathlib import Path


def load_config(config_path: str = "config/config.yaml") -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="Generate fraud graph dataset")
    parser.add_argument("--scale", type=float, default=None, help="Scale factor override")
    parser.add_argument("--config", default="config/config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    scale = args.scale or cfg["data"]["scale_factor"]
    output_dir = cfg["data"]["raw_dir"]
    workers = cfg["data"]["workers"]

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    import subprocess
    cmd = [
        "gen-fraud-graph",
        "--scale", str(scale),
        "--workers", str(workers),
        "--output", output_dir,
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print(f"Dataset generated in {output_dir}/")


if __name__ == "__main__":
    main()
