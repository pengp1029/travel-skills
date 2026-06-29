#!/usr/bin/env python3
import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)
IMAGE_FIELDS = ("thumbURL", "middleURL", "objURL", "hoverURL", "replaceUrl")
MAGIC_EXTENSIONS = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"RIFF": "webp",
    b"BM": "bmp",
}


def fetch_url(url: str, timeout: int = 15) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": "https://image.baidu.com/",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_json(url: str, timeout: int = 15) -> Dict:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://image.baidu.com/",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def baidu_api_url(keyword: str, page_index: int, page_size: int) -> str:
    query = {
        "tn": "resultjson_com",
        "logid": "",
        "ipn": "rj",
        "ct": "201326592",
        "is": "",
        "fp": "result",
        "fr": "",
        "word": keyword,
        "queryWord": keyword,
        "cl": "2",
        "lm": "-1",
        "ie": "utf-8",
        "oe": "utf-8",
        "adpicid": "",
        "st": "-1",
        "z": "",
        "ic": "0",
        "hd": "",
        "latest": "",
        "copyright": "",
        "s": "",
        "se": "",
        "tab": "",
        "width": "",
        "height": "",
        "face": "0",
        "istype": "2",
        "qc": "",
        "nc": "1",
        "expermode": "",
        "nojc": "",
        "isAsync": "",
        "pn": str(page_index * page_size),
        "rn": str(page_size),
        "gsm": "1e",
    }
    return "https://image.baidu.com/search/acjson?" + urlencode(query)


def normalize_candidate(value) -> Iterable[str]:
    if isinstance(value, str):
        yield value.replace("\\/", "/")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                for key in ("ObjURL", "objURL", "FromURL", "fromURL", "thumbURL"):
                    candidate = item.get(key)
                    if isinstance(candidate, str):
                        yield candidate.replace("\\/", "/")
            elif isinstance(item, str):
                yield item.replace("\\/", "/")


def baidu_mobile_url(keyword: str) -> str:
    query = {
        "pd": "image_content",
        "word": keyword,
    }
    return "https://m.baidu.com/sf/vsearch?" + urlencode(query)


def add_candidate(candidates: List[Dict[str, str]], seen: set, source_url: str, source_field: str, endpoint: str) -> None:
    source_url = html.unescape(source_url).replace("\\/", "/")
    if not source_url.startswith(("http://", "https://")):
        return
    if source_url in seen:
        return
    seen.add(source_url)
    candidates.append({
        "source_field": source_field,
        "source_url": source_url,
        "baidu_endpoint": endpoint,
    })


def collect_api_candidates(keyword: str, pages: int, page_size: int) -> List[Dict[str, str]]:
    seen = set()
    candidates: List[Dict[str, str]] = []
    for page_index in range(pages):
        endpoint = baidu_api_url(keyword, page_index, page_size)
        payload = fetch_json(endpoint)
        for item in payload.get("data", []):
            if not isinstance(item, dict):
                continue
            for field in IMAGE_FIELDS:
                for url in normalize_candidate(item.get(field)):
                    add_candidate(candidates, seen, url, field, endpoint)
    return candidates


def collect_mobile_html_candidates(keyword: str) -> List[Dict[str, str]]:
    endpoint = baidu_mobile_url(keyword)
    request = Request(
        endpoint,
        headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://m.baidu.com/",
        },
    )
    with urlopen(request, timeout=15) as response:
        text = response.read().decode("utf-8", errors="replace")

    seen = set()
    candidates: List[Dict[str, str]] = []
    for img_tag in re.findall(r"<img\b[^>]*>", text, flags=re.I):
        for attr in ("src", "data-src"):
            match = re.search(attr + r"=[\"']([^\"']+)[\"']", img_tag, flags=re.I)
            if not match:
                continue
            source_url = match.group(1)
            host = urlparse(html.unescape(source_url)).netloc.lower()
            if host.endswith("baidu.com") or host.endswith("bcebos.com"):
                add_candidate(candidates, seen, source_url, f"mobile_html:{attr}", endpoint)
    return candidates


def collect_candidates(keyword: str, pages: int, page_size: int) -> List[Dict[str, str]]:
    try:
        candidates = collect_api_candidates(keyword, pages, page_size)
    except Exception:
        candidates = []
    if len(candidates) < 5:
        mobile_candidates = collect_mobile_html_candidates(keyword)
        seen = {candidate["source_url"] for candidate in candidates}
        for candidate in mobile_candidates:
            add_candidate(
                candidates,
                seen,
                candidate["source_url"],
                candidate["source_field"],
                candidate["baidu_endpoint"],
            )
    return candidates


def detect_image_extension(data: bytes, content_type: str, source_url: str) -> Optional[str]:
    for magic, extension in MAGIC_EXTENSIONS.items():
        if data.startswith(magic):
            if magic == b"RIFF" and data[8:12] != b"WEBP":
                continue
            return extension
    content_type = content_type.lower().split(";")[0].strip()
    if content_type == "image/jpeg":
        return "jpg"
    if content_type.startswith("image/"):
        extension = content_type.split("/", 1)[1].replace("jpeg", "jpg")
        if extension in {"jpg", "png", "gif", "webp", "bmp"}:
            return extension
    path_ext = Path(urlparse(source_url).path).suffix.lower().lstrip(".")
    if path_ext in {"jpg", "jpeg", "png", "gif", "webp", "bmp"}:
        return "jpg" if path_ext == "jpeg" else path_ext
    return None


def download_candidate(candidate: Dict[str, str], timeout: int) -> Optional[Dict[str, object]]:
    request = Request(
        candidate["source_url"],
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": "https://image.baidu.com/",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        final_url = response.geturl()
        data = response.read()
    if len(data) < 128:
        return None
    extension = detect_image_extension(data, content_type, candidate["source_url"])
    if not extension:
        return None
    return {
        "data": data,
        "extension": extension,
        "content_type": content_type,
        "final_url": final_url,
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_size": len(data),
    }


def write_manifest(path: Path, records: List[Dict[str, object]]) -> None:
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download the first working Baidu image results for a keyword.")
    parser.add_argument("--keyword", required=True, help="Baidu Images search keyword")
    parser.add_argument("--count", type=int, default=5, help="Number of images to save")
    parser.add_argument("--output-dir", required=True, help="Directory for downloaded images")
    parser.add_argument("--candidate-pages", type=int, default=4, help="Number of Baidu result pages to scan")
    parser.add_argument("--page-size", type=int, default=30, help="Candidates requested per page")
    parser.add_argument("--timeout", type=int, default=15, help="Network timeout in seconds")
    args = parser.parse_args()

    output_dir = Path(os.path.expanduser(args.output_dir)).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    records: List[Dict[str, object]] = []
    try:
        candidates = collect_candidates(args.keyword, args.candidate_pages, args.page_size)
    except Exception as exc:
        print(f"Failed to fetch Baidu image candidates: {exc}", file=sys.stderr)
        return 2

    for candidate in candidates:
        if len(records) >= args.count:
            break
        try:
            downloaded = download_candidate(candidate, args.timeout)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            continue
        if not downloaded:
            continue

        image_index = len(records) + 1
        filename = f"image_{image_index:02d}.{downloaded['extension']}"
        image_path = output_dir / filename
        image_path.write_bytes(downloaded["data"])
        record = {
            "keyword": args.keyword,
            "rank": image_index,
            "file": str(image_path),
            "source_url": candidate["source_url"],
            "source_field": candidate["source_field"],
            "final_url": downloaded["final_url"],
            "baidu_endpoint": candidate["baidu_endpoint"],
            "content_type": downloaded["content_type"],
            "byte_size": downloaded["byte_size"],
            "sha256": downloaded["sha256"],
            "verified_image": True,
        }
        records.append(record)
        print(f"saved {filename} from {candidate['source_url']}")
        time.sleep(0.2)

    manifest_path = output_dir / "manifest.json"
    write_manifest(manifest_path, records)
    print(f"manifest: {manifest_path}")
    print(f"downloaded: {len(records)}/{args.count}")
    if len(records) < args.count:
        print("Not enough valid images were downloaded. Try increasing --candidate-pages.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
