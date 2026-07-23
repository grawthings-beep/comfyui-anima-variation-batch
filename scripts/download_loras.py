#!/usr/bin/env python3
import argparse
import json
import pathlib
import subprocess
import tempfile
from urllib.parse import unquote, urlsplit


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "config" / "anima-loras.json"


def load_manifest(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def select_loras(entries, selected_ids):
    if not selected_ids:
        return entries
    wanted = {value.casefold() for value in selected_ids}
    selected = [entry for entry in entries if entry["id"].casefold() in wanted]
    missing = wanted - {entry["id"].casefold() for entry in selected}
    if missing:
        raise ValueError(f"unknown LoRA id(s): {', '.join(sorted(missing))}")
    return selected


def parse_hf_resolve_url(url):
    path = unquote(urlsplit(url).path).strip("/").split("/")
    if len(path) < 5 or path[2:4] != ["resolve", "main"]:
        raise ValueError(f"unsupported Hugging Face resolve URL: {url}")
    return "/".join(path[:2]), "/".join(path[4:])


def verify_hf_login():
    try:
        subprocess.run(
            ["hf", "auth", "whoami"],
            check=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            "The hf command was not found. Install huggingface_hub, "
            "then run: hf auth login"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            "Hugging Face authentication is required. Run: hf auth login"
        ) from exc


def cleanup_legacy_paths(entry, root, output):
    if not output.exists():
        return

    root = root.resolve()
    output = output.resolve()
    for value in entry.get("legacy_paths", []):
        legacy = (root / value).resolve()
        if legacy == output:
            continue
        try:
            legacy.relative_to(root)
        except ValueError:
            print(f"WARN: refusing legacy path outside root: {legacy}")
            continue
        if legacy.is_file():
            legacy.unlink()
            print(f"REMOVE legacy: {entry['id']} -> {legacy}")


def download(entry, root):
    output = root / entry["path"]
    minimum = int(entry.get("min_bytes") or 0)
    if output.exists() and output.stat().st_size >= minimum:
        print(f"SKIP existing: {entry['id']} -> {output}")
        cleanup_legacy_paths(entry, root, output)
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    repo_id, filename = parse_hf_resolve_url(entry["url"])
    print(f"DOWNLOAD: {entry['id']} (trigger: {entry['trigger']})")
    with tempfile.TemporaryDirectory(
        prefix=f".{entry['id']}-",
        dir=output.parent,
    ) as temporary_directory:
        subprocess.run(
            [
                "hf",
                "download",
                repo_id,
                filename,
                "--repo-type",
                "model",
                "--local-dir",
                temporary_directory,
            ],
            check=True,
        )
        temporary = pathlib.Path(temporary_directory) / filename
        if not temporary.is_file():
            raise RuntimeError(f"hf download did not create: {temporary}")
        size = temporary.stat().st_size
        if size < minimum:
            raise RuntimeError(
                f"downloaded file is too small: {size} bytes"
            )
        temporary.replace(output)
    cleanup_legacy_paths(entry, root, output)


def main():
    parser = argparse.ArgumentParser(
        description="Download private Anima character LoRAs from the project manifest."
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument(
        "--root",
        default="/workspace/comfyui",
        help="ComfyUI root containing the models directory.",
    )
    parser.add_argument(
        "--id",
        action="append",
        dest="selected_ids",
        help="Download only this manifest id. Repeat for multiple LoRAs.",
    )
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    entries = select_loras(manifest.get("loras", []), args.selected_ids)
    if args.list:
        for entry in entries:
            print(f"{entry['id']:20} trigger={entry['trigger']:12} {entry['path']}")
        return

    verify_hf_login()
    root = pathlib.Path(args.root)
    failures = []
    for entry in entries:
        try:
            download(entry, root)
        except Exception as exc:
            failures.append((entry["id"], exc))
            print(f"ERROR: {entry['id']}: {exc}")

    if failures:
        raise SystemExit(f"{len(failures)} LoRA download(s) failed")


if __name__ == "__main__":
    main()
