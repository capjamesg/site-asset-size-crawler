import concurrent.futures
import json
import optparse

import requests
import tqdm
import validators
from bs4 import BeautifulSoup

from .getsitemap import retrieve_sitemap_urls

parser = optparse.OptionParser()

parser.add_option("-u", "--url", dest="url", help="URL to scrape")

(options, args) = parser.parse_args()

if not options.url:
    parser.error("URL is required")

url = options.url

ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png", "gif", "svg", "mov", "mp4", "webm"]
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

all_urls = retrieve_sitemap_urls(url)

images_by_page = {}
image_sizes_by_page = {}
failures = 0

images_processed = set()
all_image_sizes = {}


def get_image(url):
    global images_processed

    if url in images_processed:
        return {"content-length": all_image_sizes[url]}, url

    print(f"Processing {url}")
    image = requests.head(url, headers={"User-Agent": USER_AGENT})
    headers = image.headers

    all_image_sizes[url] = headers.get("content-length")

    images_processed.add(url)

    image.close()

    return headers, url


def get_all_images(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    images = soup.find_all("img")

    return [img["src"] for img in images if img.get("src")]


all_urls = list(set(all_urls))

with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    image_results = list(
        tqdm.tqdm(executor.map(get_all_images, all_urls), total=len(all_urls))
    )

for url, images in zip(all_urls, image_results):
    images_by_page[url] = images

print(f"Found {len(images_by_page)} pages")

for url, images in tqdm.tqdm(images_by_page.items()):
    image_sizes_by_page[url] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        image_results = executor.map(
            get_image, list(set([img for img in images if url and validators.url(img)]))
        )

    for result in image_results:
        try:
            headers, page = result
            image_sizes_by_page[url][page] = (
                int(headers.get("content-length", 0)) / 1024
            )
        except Exception as e:
            print(f"Failed to process {url} due to {e}")
            failures += 1

print(f"Processed {len(images_processed)} images, {failures} failures")

payload = {
    "images": image_sizes_by_page,
    "urls": all_urls,
    "images_by_page": images_by_page,
}

with open("images.json", "w") as f:
    f.write(json.dumps(payload, indent=4))

oversized = {}

with open("images.json", "r") as f:
    data = json.loads(f.read())

    images = data["images"]

    for url, image_sizes in images.items():
        for image, size in image_sizes.items():
            if size > 100:
                oversized[image] = size

oversized = dict(sorted(oversized.items(), key=lambda item: item[1], reverse=True))

with open("oversized_images.txt", "w") as f:
    for image, size in oversized.items():
        f.write(f"{image} - {size}KB\n")

image_pages = {}

for url, images in data["images_by_page"].items():
    for image in images:
        if image in oversized:
            if image in image_pages:
                image_pages[image] += 1
            else:
                image_pages[image] = 1

with open("oversized_by_page.txt", "w") as f:
    for image, size in oversized.items():
        if image_pages[image] > 4:
            f.write(f"{image} - {size}KB\n")

print(f"Done! ✨")
