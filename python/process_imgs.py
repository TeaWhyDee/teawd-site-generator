import os

from bs4 import BeautifulSoup
from PIL import Image


def save_img(img, root_path, filename):
    """
    Returns:
        str: path to file for web server.
    """

    new_root = os.path.join("/", root_path, "compressed/")
    new_save_path = "." + new_root
    os.makedirs(new_save_path, exist_ok=True)

    web_path = os.path.join(new_root, filename)
    rel_save_path = "." + web_path

    if not os.path.exists(rel_save_path):
        print("Saving", rel_save_path)
        img.save(rel_save_path)

    return web_path


def resize_img(
    image,
    original_width,
    original_height,
    new_size,
    filename,
    path_dir,
):
    """
    Args:
        path_dir (str): directory of the image in resources. ex: resources/blog/ssf

    Returns:
        str: web path
    """
    width_new = new_size
    height_new = int(width_new * original_height / original_width)

    filename_new = f"{filename}-{width_new}w.jpg"

    image = image.resize((width_new, height_new))
    web_path = save_img(image, path_dir, filename_new)

    return web_path


def make_source(min_size, max_size, image, path_basename, path_dir):
    orig_w, orig_h = image.size
    webpath_medium = resize_img(
        image, orig_w, orig_h, max_size, path_basename, path_dir
    )
    source_html = f'<source media="(width > {min_size}px) and (width < {max_size}px)" srcset="{webpath_medium}" />'

    return source_html


def generate_picture_element(image_path, output_dir, alt_text, class_name, img_id):
    """
    Args:
        image_path (str): The path to the original image file.
        output_dir (str): The directory to save the resized image files.

    Returns:
        str: The HTML code for the picture element.
    """
    filetype = os.path.splitext(os.path.basename(image_path))[1]
    if filetype != ".png" and filetype != ".jpg":
        return

    try:
        image = Image.open("." + image_path)
        image = image.convert("RGB")
    except Exception as e:
        print(f"Error loading image {image_path}: {e}")
        return

    basename = os.path.splitext(os.path.basename(image_path))[0]  # filename w/o ext
    webpath_root = os.path.dirname(image_path)[1:]
    orig_w, orig_h = image.size

    if orig_w < 400 or class_name == "noresize":
        return

    # Create source elements for the picture tag
    source_els = []

    # compress + resize img
    SIZE_S = 420
    SIZE_M = 1000
    SIZE_H = 2000

    # if orig_w > SIZE_S:
    #     source_els.append(make_source(0, SIZE_S, image, basename, webpath_root))
    if orig_w > SIZE_M:
        source_els.append(make_source(0, SIZE_M, image, basename, webpath_root))
    if orig_w > SIZE_H:
        source_els.append(make_source(SIZE_M, SIZE_H, image, basename, webpath_root))

    # Make jpg version of img
    filename_jpg = f"{basename}.jpg"
    if filetype == ".png":
        webpath_jpg = save_img(image, webpath_root, filename_jpg)
        img_element = f'<img src="{webpath_jpg}" alt="{alt_text}" />'
    else:
        img_element = f'<img src="{image_path}" alt="{alt_text}" />'

    # set class and id
    class_string = f' class="{class_name}"' if class_name else ""
    if img_id:
        class_string += f' id="{img_id}"'

    picture_element = f'<a href="{image_path}">\n\
  <picture{class_string}>\n\
    {"\n    ".join(source_els)}\n    {img_element}\n\
  </picture>\n\
</a>'

    return picture_element


def process_file(html_file):
    with open(html_file, "r") as file:
        text = file.read()

    new_text = process_html_imgs(text, True)

    with open(html_file, "w") as file:
        print("Saving", html_file)
        file.write(new_text)


def process_html_imgs(text, process_a_tags: bool):
    soup = BeautifulSoup(text, "html.parser")

    imgs = soup.find_all("img")

    image_info = []
    for img in imgs:
        src = str(img.get("src"))
        alt = img.get("alt")
        cls = img.get("class") or [None]
        img_id = img.get("id") or None

        res = generate_picture_element(src, "/serve", alt, cls[0], img_id)
        if res:
            img.replace_with(BeautifulSoup(res, "html.parser"))

    if process_a_tags:
        a_tags = soup.find_all("a")
        for a_tag in a_tags:
            href = str(a_tag.get("href"))
            if href.startswith("/") and href.endswith(".html"):
                new_href = href[:-5]  # Remove the ".html" extension
                a_tag.attrs["href"] = new_href

    return str(soup)


if __name__ == "__main__":
    html_file = "./serve/art/all.html"
    process_file(html_file)
