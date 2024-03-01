<img width="1009" alt="example" src="https://github.com/capjamesg/site-asset-size-crawler/assets/37276661/f6584c28-bf71-4ab8-9788-4de7ee6f67ae">

# site-asset-size-crawler

Measure the size of different assets (i.e. PNG, GIF, MP4) across your entire website.

The `analyze.py` script in this project takes a URL, downloads the associated sitemap, then crawls all pages in the sitemap to find the file sizes of image and video assets. You can use this to find assets that are larger than they should be, and how many times those assets are referenced on your website. 

You can also measure the total weight of image and video assets referenced on each page, allowing you to find pages that may load slowly due to the number of assets referenced.

This tool sends `HEAD` requests to each asset URL to get the file size from a `Content-Length` header. This means that you can measure file sizes without having to download them.

## Installation

To get started, clone this project repository and install the required dependencies:

```
git clone https://github.com/capjamesg/site-asset-size-crawler
cd site-asset-size-crawler
pip3 install -r requirements.txt
```

## Usage

To analyze your site, run:

```
python3 analyze.py --url https://example.com
```

Where `https://example.com` is either:

1. Your root site, or
2. A specific sitemap on which you want to run an analysis.

The script creates a few files.

- `assets_by_size.csv`: A list of images and videos found, listed in descending order by file size.
- `assets_by_use.csv`: A list of images and videos found, listed in descending order of the number of pages on which the image was referenced.
- `potential_optimizations.csv`: A list of images and videos > 200 KB in size.
- `pages_by_asset_size.csv`: A list of pages, listed in descending order by the total size of assets referenced on the page.
- `results.json`: Stores the URLs analyzed and asset sizes by page as a JSON file.

## License

This project is licensed under an [MIT license](LICENSE).

## Contributing

Have an idea on how this software can be improved? Create an Issue in the project GitHub repository! Found a bug? If you would like to, feel free to file a PR to help make the software better!
