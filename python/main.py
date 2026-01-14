import argparse
import copy
import os
import re
import shutil
from collections import OrderedDict
from pathlib import Path
from typing import List, Optional

import glo as g
import rss
import toml
from PIL import ImageColor
from process_imgs import process_html_imgs

is_debug = False
comment_pattern = r"<!--.*-->"

template_content = open(g.path_templates + "template.html", "r").read()

global_config: dict = {
    "sitemap_rel": [],
    "files": {},
}


def get_color_css(color):
    r, g, b = ImageColor.getrgb("#" + color)[:3]

    mul = 0.25
    add = 10

    add_r = int(r * mul + add)
    add_g = int(g * mul + add)
    add_b = int(b * mul + add)

    hr = min(255, r + add_r)
    hg = min(255, g + add_g)
    hb = min(255, b + add_b)

    color_hover = f"#{hr:02x}{hg:02x}{hb:02x}"

    return f"""
.col{color} {{
    color: #{color};
}}

.col{color}:hover {{
    color: {color_hover};
}}
"""


def html_escape(text):
    return text.replace(" ", "_").replace(":", "").replace("&", "and").replace("#", "")


def html_title(title):
    title = html_escape(title).lower() + ".html"
    return title


def setup():
    # set up cache dirs
    os.chdir(g.path_root)

    pwd = os.getcwd()
    g.path_root = pwd

    if os.path.exists(g.path_serve):
        shutil.rmtree(g.path_serve)

    os.makedirs(g.path_serve)

    # copy css and resources to serve
    to_serve_dirs = ["css", "resources"]

    for from_path in to_serve_dirs:
        target_path = os.path.join(g.path_serve, from_path)
        if not os.path.exists(target_path):
            shutil.copytree(from_path, target_path)

    os.makedirs(g.path_src, exist_ok=True)
    os.makedirs(g.path_templates, exist_ok=True)
    os.makedirs(g.path_processing, exist_ok=True)
    os.makedirs(g.path_processing_sections, exist_ok=True)
    os.makedirs(g.path_to_serve, exist_ok=True)

    config_toml = toml.loads(open(g.path_src + "config.toml").read())
    config_sections = config_toml["sections"]

    # section cache dirs
    for section in config_sections:
        c_section = config_sections[section]
        if c_section["visible"]:
            section_name = section

            if c_section["blog"]:
                os.makedirs(g.path_cache + section_name, exist_ok=True)
                os.makedirs(g.path_to_serve + section_name, exist_ok=True)
                os.makedirs(g.path_serve + section_name, exist_ok=True)
                os.makedirs(g.path_cache + f"{section_name}/post", exist_ok=True)
                os.makedirs(g.path_to_serve + f"{section_name}/post", exist_ok=True)
                os.makedirs(g.path_serve + f"{section_name}/post", exist_ok=True)


def generate_headers(section) -> List[str]:
    headers = str(open(g.path_templates + "header_template.html", "r").read()).split(
        "\n"
    )

    for i in range(len(headers) - 1):
        header = headers[i]
        m = re.match(r".*> *(\w+)", header)
        if m is not None:
            # Cosmetic. make odd buttons a little different shade.
            if section == m.group(1):
                headers[i] = headers[i].replace("> ", ' id="active"> ')
            elif i % 2 == 0:
                headers[i] = headers[i].replace("> ", ' id="b2"> ')

    return headers


def compile_site():
    sections = {"home", "blog", "art", "misc"}
    # final step
    # For each file in directory to_serve,
    # add a heading etc.

    print("Compiling website...")
    for path_root, dirs, files in os.walk(g.path_cache):
        # Serve HTML
        for file in files:
            rel_dir = os.path.relpath(path_root, g.path_cache)
            rel_file = str(os.path.join(rel_dir, file))
            if rel_file.find(".html") == -1:
                continue
            content = open(g.path_cache + rel_file, "r").read()

            section = "misc"  # for other content, set section as misc
            root_dir = os.path.dirname(rel_file).split("/")[0]
            # Determine which section of website we are in
            # by checking filename and folder structure for matches
            for i in sections:
                if root_dir == ".":
                    if os.path.splitext(rel_file)[0][2:] == i:
                        section = i
                        break
                else:
                    if root_dir == i:
                        section = i
                        break

            headers = generate_headers(section)

            # extract titles, descriptions, keywords
            title_str_prefix = ""
            meta_str = None
            keywords = []

            if "meta_keywords" in global_config["config"]["config"]:
                keywords.extend(global_config["config"]["config"]["meta_keywords"])

            if "meta_description" in global_config[section]["settings"]:
                meta_str = global_config[section]["settings"]["meta_description"]

            if rel_file in global_config["files"]:
                if "meta_description" in global_config["files"][rel_file]:
                    meta_str = global_config["files"][rel_file]["meta_description"]

                if "title" in global_config["files"][rel_file]:
                    title_str_prefix = global_config["files"][rel_file]["title"] + ": "

                if "tags" in global_config["files"][rel_file]:
                    keywords.extend(global_config["files"][rel_file]["tags"])

                if "meta_keywords" in global_config["files"][rel_file]:
                    keywords.extend(global_config["files"][rel_file]["meta_keywords"])

            title = f"<title>{title_str_prefix}teawd's " + section + "</title>"

            meta_str = meta_str or ""
            meta_desc = f'<meta name="description" content="{meta_str}">'

            keywords_str = ", ".join(keywords)
            if keywords_str != "":
                meta_keywords = f'<meta name="keywords" content="{keywords_str}">'
                meta_desc += f"\n{meta_keywords}"

            canonical_url = os.path.splitext(file)[0]
            meta_canonical = f'<link rel="canonical" href="{canonical_url}" >'
            meta_desc += "\n" + meta_canonical

            # generate final html text
            text = template_content.replace("<!-- CONTENT -->", content)
            text = text.replace("<!-- TITLE -->", title)
            text = text.replace("<!-- HEADER -->", "\n".join(headers))
            text = text.replace("<!-- META -->", meta_desc)
            text = re.sub(comment_pattern, "", text)

            if global_config["args"].process_imgs:
                content = process_html_imgs(text, global_config["args"].process_a_tags)
            else:
                content = text

            f_out_path = g.path_serve + rel_file
            f_out = open(f_out_path, "w")
            f_out.write(content)
            f_out.close()

        # Serve XML
        for file in files:
            rel_dir = os.path.relpath(path_root, g.path_to_serve)
            rel_file = str(os.path.join(rel_dir, file))
            if rel_file.find(".xml") == -1:
                continue
            content = open(g.path_to_serve + rel_file, "r").read()

            f_out = open(g.path_serve + rel_file, "w")
            f_out.write(content)
            f_out.close()

    # Generate sitemap
    sitemap_string = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for sitemap_link in global_config["sitemap_rel"]:
        sitemap_link = sitemap_link[:-5]
        sitemap_string += f"\
    <url>\n\
        <loc> {g.domain}/{sitemap_link} </loc>\n\
    </url>\n"
    sitemap_string += "</urlset>"

    path_sm = g.path_serve + "sitemap.xml"
    sm_f_out = open(path_sm, "w")
    sm_f_out.write(sitemap_string)
    sm_f_out.close()

    cmd = "cp -f " + g.path_serve + "home.html " + g.path_serve + "index.html"
    os.system(cmd)


def get_tags_html(
    tags,
    colors,
    section_name: str,
    default_col="",
    use_all=True,
    tabindex=True,
):
    # get html of all tags (excluding #all).
    html = ""
    for tag in tags:
        if tag == "all" and not use_all:
            continue
        # col = "col"+colors[tag] if tag in colors else default_col
        col = colors[tag] if tag in colors else default_col
        html += get_tag_html(tag, col=col, section_name=section_name, tabindex=tabindex)
    return html


def get_tag_html(
    tag: str,
    section_name: str,
    col: Optional[str] = None,
    bold=False,
    tabindex=True,
):
    # get html of a post tag (with a link to the rolling page of the tag).
    col = f'class="col{col}"' if col else 'class="tag"'
    tag_text = f"{'<em>' if bold else ''} #{tag} {'</em>' if bold else ''}"
    tabindex_html = "" if tabindex else 'tabindex="-1"'
    tag_html = (
        f'<a {tabindex_html} {col} href="/{section_name}/{tag}.html">'
        + tag_text
        + "</a>"
    )
    return tag_html


def compile_section(section_name: str, is_blog: bool = False):
    print(f"Processing {section_name}...")
    section_toml_path = g.path_src + f"{section_name}.toml"
    if os.path.exists(section_toml_path):
        section_toml = toml.loads(open(section_toml_path, "r").read())
    else:
        section_toml = {}

    global_config[section_name] = section_toml

    # NON-BLOG SECTIONS
    if not is_blog:
        index_content = open(g.path_src + section_name + ".html").read()
        index_out = open(g.path_cache + section_name + ".html", "w")
        index_out.write(index_content)

        # copy all html files in section src folder.
        walk_path = os.path.join(g.path_src, section_name)
        if os.path.exists(walk_path):
            for root, dirs, files in os.walk(walk_path):
                for d in dirs:
                    out_dir_path = os.path.join(g.path_cache, section_name, d)
                    serve_dir_path = os.path.join(g.path_serve, section_name, d)
                    os.makedirs(out_dir_path, exist_ok=True)
                    os.makedirs(serve_dir_path, exist_ok=True)

                for file in files:
                    src_file_path = os.path.join(root, file)
                    file_content = open(src_file_path).read()
                    src_file_path_rel = os.path.relpath(src_file_path, walk_path)

                    out_file_path = os.path.join(
                        g.path_cache, section_name, src_file_path_rel
                    )
                    file_out = open(out_file_path, "w")
                    file_out.write(file_content)

            os.chdir(g.path_root)

        return

    # BLOG SECTIONS
    template_dir = g.path_templates + f"{section_name}/"
    section_index_template = open(template_dir + "index.html", "r").read()
    default_post_template = open(template_dir + "post.html", "r").read()
    index_post_template = open(template_dir + "index_post.html", "r").read()

    map_tag_posts = {}
    posts_all: OrderedDict = OrderedDict(section_toml["posts"])
    posts: OrderedDict = OrderedDict()
    for post_name in posts_all:
        post = posts_all[post_name]

        if "visible" not in posts_all[post_name]:
            posts_all[post_name]["visible"] = True
        if post["visible"]:
            posts[post_name] = posts_all[post_name]

    config = section_toml["settings"]
    tag_colors = config["tag_colors"]

    # get all tags
    tags_unsorted: OrderedDict = OrderedDict()
    for post_name in posts:
        post = posts[post_name]
        # if post["visible"]:
        post["tags"].append("all")

        for tag in post["tags"]:
            if tag not in tags_unsorted:
                tags_unsorted[tag] = {"count": 1}
            else:
                tags_unsorted[tag]["count"] += 1

    tags: OrderedDict = OrderedDict(
        sorted(tags_unsorted.items(), key=lambda x: x[1]["count"], reverse=True)
    )

    for tag in tags:
        map_tag_posts[tag] = []
    for post_name in posts:
        for tag in posts[post_name]["tags"]:
            map_tag_posts[tag].append(post_name)

    # Generate (color) styles for tags
    try:
        css_f = open(os.path.join(g.path_serve, "css/colors.css"), "r")
        color_css_text = css_f.read()
        css_f.close()
    except:
        color_css_text = ""

    css_f = open(os.path.join(g.path_serve, "css/colors.css"), "w")

    for tag, color in tag_colors.items():
        color_css_text += get_color_css(color)

    css_f.write(color_css_text)

    # ========== INDEX PAGE ==========
    out_blog_path_rel = f"{section_name}.html"
    out_blog_index = open(g.path_cache + out_blog_path_rel, "w")

    global_config["sitemap_rel"].append(out_blog_path_rel)

    tags_html_all = get_tags_html(
        tags, config["tag_colors"], section_name=section_name, use_all=True
    )

    posts_html = ""
    for key in posts:
        post = posts[key]
        if not post["visible"]:
            continue
        posts_html += (
            index_post_template.replace(
                "<!-- POST_LINK -->", f"/{section_name}/post/{key}.html"
            )
            .replace("<!-- POST_TITLE -->", post["title"])
            .replace("<!-- POST_NAME -->", key)
            .replace("<!-- POST_DATE -->", post["date"])
            .replace(
                "<!-- POST_TAGS -->",
                get_tags_html(
                    post["tags"],
                    config["tag_colors"],
                    section_name=section_name,
                    # default_col="blues",
                    use_all=False,
                    tabindex=False,
                ),
            )
        )

    # TODO: add subheaders for years

    index_content = section_index_template.replace("<!-- POSTS -->", posts_html)
    index_content = index_content.replace("<!-- TAGS -->", tags_html_all)

    out_blog_index.write(index_content)

    # ========== POST PAGES ==========
    for post_name in posts:
        if "filename" in posts[post_name]:
            post_content = open(
                f'{g.path_src}{section_name}/{posts[post_name]["filename"]}.html'
            ).read()
            posts[post_name]["content"] = post_content

    for i in range(len(posts)):
        post_name = list(posts.keys())[i]
        post_next = list(posts.keys())[i + 1] if i < len(posts) - 1 else None
        post_prev = list(posts.keys())[i - 1] if i > 0 else None

        post = posts[post_name]
        path_rel = f"{section_name}/post/{post_name}.html"
        path = g.path_cache + path_rel
        f_out = open(path, "w")

        global_config["sitemap_rel"].append(path_rel)

        tags_html = get_tags_html(
            post["tags"],
            config["tag_colors"],
            section_name=section_name,
            use_all=False,
        )

        tags_html_all = get_tags_html(
            tags, config["tag_colors"], section_name=section_name, use_all=True
        )

        content = default_post_template
        if "template" in post.keys():
            template_text = open(
                template_dir + f"post_{post['template']}.html", "r"
            ).read()
            content = template_text

        content = content.replace("<!-- TAGS -->", tags_html)
        content = content.replace("<!-- NAME -->", post_name)

        for field in post:
            value = post[field]
            if field in ["visible", "tags"]:
                continue

            # normal fields
            if field not in config["fields"]:
                if isinstance(post[field], str):
                    content = content.replace(f"<!-- {field.upper()} -->", value)
                    continue

            # special fields
            if not field in config["fields"]:
                continue

            special_field = config["fields"][field]
            if isinstance(special_field, list):
                text = special_field[0]
                special_field = special_field[1]
            else:
                text = ""

            if isinstance(post[field], dict):
                for key in post[field]:
                    val = post[field][key]
                    text += special_field.replace("{key}", key).replace("{value}", val)
            elif isinstance(post[field], list):
                for val in post[field]:
                    text += special_field.replace("{}", val)
            elif isinstance(post[field], str):
                text = special_field.replace("{}", value)

            text = text.replace("{name}", post_name)
            replace_strings = ["title", "source_extra"]
            for rep_str in replace_strings:
                text = text.replace(
                    "{" + rep_str + "}", post[rep_str] if rep_str in post else ""
                )

            content = content.replace(f"<!-- {field.upper()} -->", text)

        post["content"] = content

        # Content exclusive to post pages
        content = content.replace("<!-- MAIN_BEGIN -->", "<main>")
        content = content.replace("<!-- MAIN_END -->", "</main>")
        if post_next:
            next_link = f'<a class="next_link" href="/{section_name}/post/{post_next}.html"> older post → </a>'
            content = content.replace("<!-- NEXT -->", next_link)
        if post_prev:
            prev_link = (
                f'<a href="/{section_name}/post/{post_prev}.html"> ← newer post </a>'
            )
            content = content.replace("<!-- PREVIOUS -->", prev_link)

        tags_html_all = (
            '<div class="article"> <p class="centered">'
            + tags_html_all
            + "</p> </div> "
        )
        content = content.replace("<!-- TAGS_ALL -->", tags_html_all)

        clean_tags = post["tags"]
        if "all" in clean_tags:
            clean_tags.remove("all")

        # save post config
        global_config["files"][path_rel] = {
            "title": post["title"],
            "meta_description": (
                post["meta_description"] if "meta_description" in post else None
            ),
            "meta_keywords": (post["meta_keywords"] if "meta_keywords" in post else []),
            "tags": clean_tags,
            "visible": post["visible"],
        }

        f_out.write(content)
        f_out.close()

    # ========== TAG (ROLLING/FEED) PAGES ===========
    path_tag_template = os.path.join(g.path_templates, f"{section_name}/tag.html")

    for tag in map_tag_posts:
        path = g.path_cache + f"{section_name}/{tag}.html"
        f_tag_out = open(path, "w")

        other_tags = copy.deepcopy(tags)
        other_tags.pop(tag)

        color = tag_colors[tag] if tag in tag_colors else ""
        tags_html_current = get_tag_html(tag, section_name=section_name, col=color)
        tags_html_other = get_tags_html(
            other_tags,
            config["tag_colors"],
            section_name=section_name,
            use_all=True,
        )
        tags_html_all = get_tags_html(
            tags, config["tag_colors"], section_name=section_name, use_all=True
        )

        rss_link = f"/{section_name}/{tag}.xml"

        if os.path.exists(path_tag_template):
            content = open(path_tag_template, "r").read()
            content = content.replace("<!-- TAGS -->", tags_html_other)
            content = content.replace("<!-- TAGS_ALL -->", tags_html_all)
            content = content.replace("<!-- CURRENT_TAG -->", tags_html_current)
            content = content.replace("<!-- RSS_LINK -->", rss_link)
        else:
            content = ""

        # Add posts to content
        content += "<main>"
        for post_name in map_tag_posts[tag]:
            if posts[post_name]["visible"]:
                post_content = posts[post_name]["content"]
                content += post_content
        content += "</main>"

        # Write feed pages
        f_tag_out.write(content)
        f_tag_out.close()

        # ========== TAG RSS ==========
        rss_items = ""
        for post_name in map_tag_posts[tag]:
            post = posts[post_name]
            rss_link = g.domain + f"/{section_name}/post/" + post_name

            post_content = re.sub(comment_pattern, "", post["content"])

            rss_items += rss.create_rss_item(
                post["title"],
                rss_link,
                rss.rss_date(post["date"]),
                post_content,
            )

        rss_title = f"teawd's blog#{tag}"
        rss_desc = f"Full size posts from teawide.xyz/{section_name}/{tag}"
        rss_link = f"/{section_name}/{tag}"
        f_tag_rss = open(g.path_serve + f"{section_name}/{tag}.xml", "w")
        f_tag_rss.write(rss.create_rss(rss_title, rss_desc, rss_link, rss_items))
        f_tag_rss.close()

    # backwards compatibility :))))))))
    cmd = (
        "cp -f "
        + g.path_serve
        + f"{section_name}/all.xml "
        + g.path_serve
        + f"{section_name}.xml"
    )
    os.system(cmd)


def main():
    config_toml = toml.loads(open(g.path_src + "config.toml").read())
    config_sections = config_toml["sections"]
    global_config["config"] = config_toml

    # How-to add new section:
    # 1 Add into src/config.toml
    # 2 Add into the list in compile_site()
    # 3 Add a button in templates/header_template.html

    for section in config_sections:
        c_section = config_sections[section]
        if c_section["visible"]:
            # compile_section(section, c_section['blog'])
            compile_section(section, c_section["blog"])

    index = open(g.path_cache + config_toml["config"]["index"]).read()
    index_out = open(g.path_cache + "index.html", "w")
    index_out.write(index)

    compile_site()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate static site.")
    parser.add_argument(
        "--process_imgs",
        action="store_true",
        help='Generate smaller images and replace img tags (except tags with "noresize" class)',
    )

    # parser.add_argument(
    #     "--keep_resources",
    #     action="store_true",
    #     help="Do not clear resources directory",
    # )

    parser.add_argument(
        "--process_a_tags",
        action="store_true",
        help="Remove .html suffix from internal links",
    )

    args = parser.parse_args()
    global_config["args"] = args

    setup()
    main()
