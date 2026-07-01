---
name: baidu-image-downloader
description: Use this skill whenever the user wants to download images from Baidu search or Baidu Images by keyword, especially requests like “下载百度图片前几张”, “按搜索关键词保存图片到本地”, “download the first N Baidu image results”, or “用百度搜索图片并落盘”. This skill provides a deterministic script that searches Baidu Images, downloads the first available image results to a local folder, writes a manifest, and verifies the saved files.
---

# Baidu Image Downloader

## Environment

At the start of every skill run, load environment variables from `$OPENCLAW_HOME/.env` (defaults to `~/.openclaw/.env`) if the file exists, before running any bundled script, CLI, browser automation, or network request. Do not print secret values.

Use this skill to turn a search keyword into local image files from Baidu Images. Prefer the bundled script over hand-written ad hoc scraping because Baidu image pages often contain escaped JSON, multiple URL fields, and anti-hotlink behavior; the script handles retries, file type detection, and verification consistently.

## Workflow

1. Choose the keyword from the user prompt.
2. Choose an output directory. If the user did not specify one, use a clear local directory such as `~/Downloads/baidu-image-downloads/<keyword-slug>/`.
3. Run the bundled downloader:

```bash
python $HOME/.comate/skills/baidu-image-downloader/scripts/baidu_image_downloader.py \
  --keyword "<keyword>" \
  --count 5 \
  --output-dir "<output-dir>"
```

4. Inspect the terminal output. A successful run reports downloaded files and a `manifest.json` path.
5. Verify the saved files exist and are images. The script already does magic-byte verification; for extra confirmation you can run a platform image/file check when useful.
6. Tell the user the output directory and the downloaded image filenames.

## Output Files

The script writes:

- `image_01.<ext>` through `image_05.<ext>` when five images are available.
- `manifest.json` with keyword, Baidu endpoint, source URL, final URL, local path, content type, byte size, and verification status.

## Notes

- Baidu may return duplicate or temporarily blocked image links. The script scans more candidates than requested and only counts files that download and pass image verification.
- If fewer than the requested count are saved, rerun once with a larger `--candidate-pages` value before reporting failure.
- Do not download images for unlawful, private, or harmful surveillance purposes. For normal public web image search and local reference downloads, proceed.

## Examples

Download the first five Baidu image results for West Lake:

```bash
python $HOME/.comate/skills/baidu-image-downloader/scripts/baidu_image_downloader.py --keyword "西湖" --count 5 --output-dir "$HOME/Downloads/baidu-image-downloads/xihu"
```

Download eight robot images:

```bash
python $HOME/.comate/skills/baidu-image-downloader/scripts/baidu_image_downloader.py --keyword "机器人" --count 8 --output-dir "$HOME/Downloads/baidu-image-downloads/robot"
```
