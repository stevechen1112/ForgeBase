#!/usr/bin/env python3
import argparse
import base64
import json
import mimetypes
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = PACKAGE_ROOT / ".env.gemini"
DEFAULT_MANIFEST = PACKAGE_ROOT / "assets" / "generation-jobs.minimum-demo.json"
API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(
            f"Env file not found: {path}. Copy .env.gemini.example to .env.gemini and set GEMINI_API_KEY first."
        )

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_output_dir(raw_path: str) -> Path:
    output_dir = Path(raw_path)
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def resolve_manifest(path_arg: str | None) -> Path:
    if not path_arg:
        return DEFAULT_MANIFEST
    manifest_path = Path(path_arg)
    if not manifest_path.is_absolute():
        manifest_path = REPO_ROOT / manifest_path
    return manifest_path


def validate_api_key(api_key: str) -> None:
    if not api_key or api_key == "your-gemini-api-key-here":
        raise RuntimeError("GEMINI_API_KEY is missing. Set it in demo/handtool-company/.env.gemini.")


def build_request(job: dict, model: str, include_thoughts: bool, thinking_level: str):
    generation_config = {
        "responseModalities": ["IMAGE"],
        "imageConfig": {
            "aspectRatio": job["aspect_ratio"],
            "imageSize": job["image_size"],
        },
    }

    if "gemini-3" in model:
        generation_config["thinkingConfig"] = {
            "includeThoughts": include_thoughts,
            "thinkingLevel": thinking_level,
        }

    return {
        "contents": [
            {
                "parts": [
                    {
                        "text": job["prompt"],
                    }
                ]
            }
        ],
        "generationConfig": generation_config,
    }


def call_gemini(api_key: str, model: str, payload: dict) -> dict:
    endpoint = f"{API_BASE}/models/{model}:generateContent?key={urllib.parse.quote(api_key)}"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(f"Gemini API error {exc.code}: {body}") from exc


def extract_first_image(response: dict) -> tuple[bytes, str]:
    for candidate in response.get("candidates", []):
        parts = candidate.get("content", {}).get("parts", [])
        for part in parts:
            inline_data = part.get("inlineData") or part.get("inline_data")
            if not inline_data:
                continue
            mime_type = inline_data.get("mimeType") or inline_data.get("mime_type")
            data = inline_data.get("data")
            if mime_type and mime_type.startswith("image/") and data:
                return base64.b64decode(data), mime_type
    raise RuntimeError("No image payload found in Gemini response.")


def select_jobs(manifest: dict, requested_ids: set[str] | None, limit: int | None) -> list[dict]:
    jobs = manifest["jobs"]
    if requested_ids:
        jobs = [job for job in jobs if job["id"] in requested_ids]
    if limit is not None:
        jobs = jobs[:limit]
    return jobs


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate NorthForge demo images with Gemini.")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE), help="Path to local env file.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to generation manifest JSON.")
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N jobs.")
    parser.add_argument("--only", default="", help="Comma-separated job IDs to generate.")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and list jobs without calling Gemini.")
    args = parser.parse_args()

    env_file = Path(args.env_file)
    if not env_file.is_absolute():
        env_file = REPO_ROOT / env_file
    manifest_path = resolve_manifest(args.manifest)

    env = load_env_file(env_file)
    model = env.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image-preview")
    output_dir = resolve_output_dir(env.get("GEMINI_IMAGE_OUTPUT_DIR", "demo/handtool-company/assets/generated"))
    include_thoughts = env.get("GEMINI_IMAGE_ENABLE_THOUGHTS", "false").lower() == "true"
    thinking_level = env.get("GEMINI_IMAGE_THINKING_LEVEL", "MINIMAL").upper()
    manifest = load_json(manifest_path)

    requested_ids = {item.strip() for item in args.only.split(",") if item.strip()} or None
    jobs = select_jobs(manifest, requested_ids, args.limit)
    if not jobs:
        raise RuntimeError("No jobs selected from the manifest.")

    print(f"env file: {env_file}")
    print(f"manifest: {manifest_path}")
    print(f"output dir: {output_dir}")
    print(f"model: {model}")
    print(f"jobs: {len(jobs)}")
    for job in jobs:
        print(f"- {job['id']} -> {job['filename']} [{job['aspect_ratio']} {job['image_size']}]")

    if args.dry_run:
        return 0

    api_key = env.get("GEMINI_API_KEY", "")
    validate_api_key(api_key)

    for index, job in enumerate(jobs, start=1):
        print(f"[{index}/{len(jobs)}] generating {job['id']}...")
        payload = build_request(job, model, include_thoughts, thinking_level)
        response = call_gemini(api_key, model, payload)
        image_bytes, mime_type = extract_first_image(response)
        extension = mimetypes.guess_extension(mime_type) or ".png"
        image_path = output_dir / job["filename"]
        if image_path.suffix != extension:
            image_path = image_path.with_suffix(extension)
        image_path.write_bytes(image_bytes)

        metadata_path = image_path.with_suffix(image_path.suffix + ".json")
        metadata = {
            "job": job,
            "model": model,
            "mime_type": mime_type,
            "response_id": response.get("responseId"),
            "model_version": response.get("modelVersion"),
            "usage_metadata": response.get("usageMetadata"),
        }
        metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"saved: {image_path.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)