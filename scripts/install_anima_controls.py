#!/usr/bin/env python3
"""Install the Anima Pose/Depth workflow and its external assets."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import sysconfig
import tempfile


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "config" / "anima-controls.json"
DEFAULT_WORKFLOW = (
    REPO_ROOT
    / "example_workflows"
    / "anima_hiresfix_esrgan_pose_depth.json"
)
COMMON_COMFY_ROOTS = (
    pathlib.Path("/workspace/ComfyUI"),
    pathlib.Path("/workspace/comfyui"),
    pathlib.Path("/opt/ComfyUI"),
    pathlib.Path("/opt/comfyui"),
    pathlib.Path("/opt/comfyui-baked"),
)


class InstallError(RuntimeError):
    """Raised when the requested installation cannot be completed safely."""


def load_manifest(path: os.PathLike[str] | str) -> dict:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def is_comfyui_root(path: pathlib.Path) -> bool:
    return (
        path.is_dir()
        and (path / "models").is_dir()
        and (path / "custom_nodes").is_dir()
    )


def discover_comfyui_root(explicit: str | None = None) -> pathlib.Path:
    candidates: list[pathlib.Path] = []
    if explicit:
        candidates.append(pathlib.Path(explicit).expanduser())
    env_root = os.environ.get("COMFYUI_ROOT")
    if env_root:
        candidates.append(pathlib.Path(env_root).expanduser())

    for parent in REPO_ROOT.parents:
        candidates.append(parent)
    candidates.extend(COMMON_COMFY_ROOTS)

    seen: set[pathlib.Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if is_comfyui_root(resolved):
            return resolved

    if explicit:
        raise InstallError(f"not a ComfyUI root: {pathlib.Path(explicit)}")
    raise InstallError(
        "could not find ComfyUI; pass --root /path/to/ComfyUI or set "
        "COMFYUI_ROOT"
    )


def run(command: list[str], *, dry_run: bool = False) -> None:
    print("RUN:", " ".join(command))
    if not dry_run:
        subprocess.run(command, check=True)


def install_node_dependency(
    root: pathlib.Path,
    settings: dict,
    *,
    label: str,
    install_python_deps: bool,
    dry_run: bool,
) -> pathlib.Path:
    destination = root / settings["path"]

    if destination.exists():
        if not (destination / "__init__.py").is_file():
            raise InstallError(
                f"refusing to replace invalid {label} path: {destination}"
            )
        print(f"KEEP existing {label}: {destination}")
    else:
        run(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                settings["repository"],
                str(destination),
            ],
            dry_run=dry_run,
        )
        run(
            [
                "git",
                "-C",
                str(destination),
                "fetch",
                "--depth",
                "1",
                "origin",
                settings["commit"],
            ],
            dry_run=dry_run,
        )
        run(
            [
                "git",
                "-C",
                str(destination),
                "checkout",
                "--detach",
                settings["commit"],
            ],
            dry_run=dry_run,
        )

    marker = destination / f".anima-deps-{settings['commit'][:12]}"
    if install_python_deps and not marker.is_file():
        requirements = destination / "requirements.txt"
        if dry_run or requirements.is_file():
            run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    str(requirements),
                ],
                dry_run=dry_run,
            )
            if not dry_run:
                marker.touch()
        else:
            print(f"No Python requirements for {label}: {destination}")

    return destination


def install_controlnet_aux(
    root: pathlib.Path,
    manifest: dict,
    *,
    install_python_deps: bool,
    dry_run: bool,
) -> pathlib.Path:
    return install_node_dependency(
        root,
        manifest["controlnet_aux"],
        label="ControlNet Aux",
        install_python_deps=install_python_deps,
        dry_run=dry_run,
    )


def install_anima_lllite_node(
    root: pathlib.Path,
    manifest: dict,
    *,
    dry_run: bool,
) -> pathlib.Path:
    return install_node_dependency(
        root,
        manifest["anima_lllite_node"],
        label="Anima LLLite compatibility node",
        install_python_deps=False,
        dry_run=dry_run,
    )


def find_hf_command() -> str:
    command = shutil.which("hf")
    if command:
        return command

    executable_dir = pathlib.Path(sys.executable).resolve().parent
    script_directories = (
        pathlib.Path(sysconfig.get_path("scripts")),
        executable_dir,
        executable_dir / "Scripts",
        executable_dir / "bin",
    )
    for directory in script_directories:
        for name in ("hf", "hf.exe", "hf.cmd"):
            candidate = directory / name
            if candidate.is_file():
                return str(candidate)

    raise InstallError(
        "the Hugging Face 'hf' command was not found; install it with "
        f"'{sys.executable} -m pip install -U huggingface_hub'"
    )


def download_artifact(
    root: pathlib.Path,
    entry: dict,
    hf_command: str,
    *,
    force: bool,
    dry_run: bool,
) -> None:
    output = root / entry["path"]
    minimum = int(entry.get("min_bytes") or 0)
    if not force and output.is_file() and output.stat().st_size >= minimum:
        print(f"SKIP existing: {entry['id']} -> {output}")
        return

    print(f"DOWNLOAD: {entry['id']} -> {output}")
    if dry_run:
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{entry['id']}-",
        dir=output.parent,
    ) as temporary_directory:
        run(
            [
                hf_command,
                "download",
                entry["repo_id"],
                entry["filename"],
                "--repo-type",
                "model",
                "--local-dir",
                temporary_directory,
            ]
        )
        temporary = pathlib.Path(temporary_directory) / entry["filename"]
        if not temporary.is_file():
            raise InstallError(f"hf download did not create: {temporary}")
        if temporary.stat().st_size < minimum:
            raise InstallError(
                f"downloaded file is too small: {temporary.stat().st_size} bytes"
            )
        os.replace(temporary, output)


def install_workflow(
    root: pathlib.Path,
    workflow: pathlib.Path,
    workflow_dir: str | None,
    *,
    dry_run: bool,
) -> pathlib.Path:
    if not workflow.is_file():
        raise InstallError(f"workflow is missing from this repository: {workflow}")

    destination_dir = (
        pathlib.Path(workflow_dir).expanduser().resolve()
        if workflow_dir
        else root / "user" / "default" / "workflows"
    )
    destination = destination_dir / workflow.name
    print(f"INSTALL workflow: {destination}")
    if not dry_run:
        destination_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(workflow, destination)
    return destination


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Install Anima LLLite Pose/Depth support, ControlNet Aux "
            "preprocessors, and the ready-to-load ComfyUI workflow."
        )
    )
    parser.add_argument("--root", help="ComfyUI root containing models/ and custom_nodes/")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--workflow", default=str(DEFAULT_WORKFLOW))
    parser.add_argument(
        "--workflow-dir",
        help="Override the destination (default: user/default/workflows)",
    )
    parser.add_argument(
        "--skip-anima-node",
        action="store_true",
        help="Do not install the baked-ComfyUI-compatible Anima LLLite node",
    )
    parser.add_argument(
        "--skip-controlnet-aux",
        action="store_true",
        help="Do not clone the Pose/Depth preprocessor node pack",
    )
    parser.add_argument(
        "--skip-python-deps",
        action="store_true",
        help="Do not pip-install ControlNet Aux requirements",
    )
    parser.add_argument(
        "--skip-preprocessor-models",
        action="store_true",
        help="Let ControlNet Aux download its ~742 MB preprocessors on first use",
    )
    parser.add_argument(
        "--skip-workflow",
        action="store_true",
        help="Download assets without copying the workflow into the user folder",
    )
    parser.add_argument("--force", action="store_true", help="Redownload existing assets")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        root = discover_comfyui_root(args.root)
        manifest = load_manifest(args.manifest)
        print(f"ComfyUI root: {root}")

        if not args.skip_anima_node:
            install_anima_lllite_node(
                root,
                manifest,
                dry_run=args.dry_run,
            )

        if not args.skip_controlnet_aux:
            install_controlnet_aux(
                root,
                manifest,
                install_python_deps=not args.skip_python_deps,
                dry_run=args.dry_run,
            )

        hf_command = find_hf_command()
        entries = list(manifest["lllite_models"])
        entries.extend(manifest.get("upscale_models", []))
        if not args.skip_preprocessor_models:
            entries.extend(manifest["preprocessor_models"])
        for entry in entries:
            download_artifact(
                root,
                entry,
                hf_command,
                force=args.force,
                dry_run=args.dry_run,
            )

        if not args.skip_workflow:
            install_workflow(
                root,
                pathlib.Path(args.workflow),
                args.workflow_dir,
                dry_run=args.dry_run,
            )
    except (InstallError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc

    print("Done. Load anima_hiresfix_esrgan_pose_depth.json after ComfyUI starts.")
    print("Pose/Depth LLLite weights inherit Anima's non-commercial model license.")


if __name__ == "__main__":
    main()
