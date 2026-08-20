import os
from pathlib import Path
from huggingface_hub import snapshot_download
import urllib.request

def download_file(url, dest_path):
    print(f"Downloading {url}...")
    urllib.request.urlretrieve(url, dest_path)
    print(f"Downloaded to {dest_path}")

def main():
    sadtalker_dir = Path("sadtalker")
    checkpoints_dir = sadtalker_dir / "checkpoints"
    gfpgan_weights_dir = sadtalker_dir / "gfpgan" / "weights"

    # Create directories if they don't exist
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    gfpgan_weights_dir.mkdir(parents=True, exist_ok=True)

    print("Downloading SadTalker checkpoints from HuggingFace Hub...")
    # This downloads the checkpoints directly into the checkpoints folder
    snapshot_download(
        repo_id="vinthony/SadTalker",
        local_dir=checkpoints_dir,
        allow_patterns=["*.safetensors", "*.tar", "*.json"],
        local_dir_use_symlinks=False
    )
    print("SadTalker checkpoints downloaded successfully!")

    # 2. Download GFPGAN weights
    gfpgan_file = gfpgan_weights_dir / "alignment_WFLW_4_landmarks.pth"
    if not gfpgan_file.exists():
        download_file(
            "https://github.com/xinntao/facexlib/releases/download/v0.1.0/alignment_WFLW_4_landmarks.pth",
            gfpgan_weights_dir / "alignment_WFLW_4_landmarks.pth"
        )
        download_file(
            "https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth",
            gfpgan_weights_dir / "detection_Resnet50_Final.pth"
        )
        download_file(
            "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
            gfpgan_weights_dir / "GFPGANv1.4.pth"
        )
        download_file(
            "https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth",
            gfpgan_weights_dir / "parsing_parsenet.pth"
        )
    else:
        print("GFPGAN weights already exist, skipping.")

if __name__ == "__main__":
    main()
