import concurrent.futures
import json
import optparse

import requests
import tqdm
import validators
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import csv

from getsitemap import retrieve_sitemap_urls

parser = optparse.OptionParser()

parser.add_option("-u", "--url", dest="url", help="URL to scrape")
parser.add_option("-t", "--threads", dest="threads", help="Number of threads to use", default=20)

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


def get_image(url: str) -> dict:
    global images_processed
    global failures

    if url in images_processed:
        return {"content-length": int(all_image_sizes[url])}, url

    print(f"Processing {url}")
    try:
        image = requests.head(url, headers={"User-Agent": USER_AGENT})
    except Exception as e:
        print(f"Failed to process {url} due to {e}")
        failures += 1
        return {"content-length": 0}, url
    
    headers = image.headers

    all_image_sizes[url] = int(headers.get("content-length", 1)) / 1024

    print(f"Processed {url} - {all_image_sizes[url]} KB")

    images_processed.add(url)

    image.close()

    return headers, url


def get_all_images(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    images = soup.find_all("img")

    images = [img["src"] for img in images if img.get("src")]

    # canonicalize so domain name is added to relative paths
    images = [urljoin(url, img) for img in images]

    return images


all_urls = list(set(all_urls))

with concurrent.futures.ThreadPoolExecutor(max_workers=int(options.threads)) as executor:
    image_results = list(
        tqdm.tqdm(executor.map(get_all_images, all_urls), total=len(all_urls))
    )

for url, images in zip(all_urls, image_results):
    images_by_page[url] = images

print(f"Found {len(images_by_page)} pages")

for url, images in tqdm.tqdm(images_by_page.items()):
    image_sizes_by_page[url] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=int(options.threads)) as executor:
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

# save images by size in assets_by_size.txt
with open("assets_by_size.csv", "w") as f:
    saved = set()
    writer = csv.writer(f)
    writer.writerow(["image", "size"])

    # sort by size
    assets_by_size = {}

    for url, images in image_sizes_by_page.items():
        for image, size in images.items():
            assets_by_size[image] = size

    assets_by_size = dict(
        sorted(assets_by_size.items(), key=lambda item: item[1], reverse=True)
    )

    for image, size in assets_by_size.items():
        if image not in saved:
            writer.writerow([image, size])
            saved.add(image)

image_use_counts = {}

for url, images in images_by_page.items():
    for image in images:
        if image not in image_use_counts:
            image_use_counts[image] = 1
        else:
            image_use_counts[image] += 1

# save by # of times each image is used
with open("assets_by_use.csv", "w") as f:
    writer = csv.writer(f)
    writer.writerow(["image", "uses"])

    # order desc by uses
    image_use_counts = dict(
        sorted(image_use_counts.items(), key=lambda item: item[1], reverse=True)
    )

    for image, uses in image_use_counts.items():
        writer.writerow([image, uses])

with open("images.json", "w") as f:
    f.write(json.dumps(payload, indent=4))

# make list of urls > 200 kb
# key is image, value is # of times used
large_assets = {}

for url, images in images_by_page.items():
    for image in images:
        if image_sizes_by_page[url][image] > 200:
            large_assets[image] = {
                "uses": image_use_counts[image],
                "size": all_image_sizes[image],
            }

# order large assets by size
large_assets = dict(
    sorted(large_assets.items(), key=lambda item: item[1]["size"], reverse=True)
)

with open("potential_optimizations.csv", "w") as f:
    writer = csv.writer(f)
    writer.writerow(["image", "size", "uses"])

    for image, data in large_assets.items():
        writer.writerow([image, data["size"], data["uses"]])

# create heaviest pages by total asset size
page_sizes = {}

for url, images in image_sizes_by_page.items():
    page_sizes[url] = sum(images.values())

page_sizes = dict(sorted(page_sizes.items(), key=lambda item: item[1], reverse=True))

with open("pages_by_asset_size.csv", "w") as f:
    writer = csv.writer(f)
    writer.writerow(["url", "size"])

    for url, size in page_sizes.items():
        writer.writerow([url, size])

# sparkes emoji
print(f"Done! ✨")