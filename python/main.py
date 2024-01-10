from collections import OrderedDict
from typing import List, Optional
from pathlib import Path
import os
import shutil
import copy
import re
import toml
import glo as g

from colorutils import Color
import rss

is_debug = False
comment_pattern = r'<!--.*-->'

template_content = open(g.path_templates + "template.html", "r").read()


def html_escape(text):
    return text.replace(" ", "_").replace(":", "").replace("&", "and")\
            .replace("#", "")

def html_title(title):
    title = html_escape(title).lower() + ".html"
    return title


def setup():
    os.chdir(g.path_root)

    try:
        os.remove(os.path.join(g.path_serve, "css/colors.css"),)
    except:
        pass

    to_serve_dirs = [ 'css', 'resources' ]

    if os.path.exists(g.path_serve):
        shutil.rmtree(g.path_serve)
    os.makedirs(g.path_serve)
    for from_path in to_serve_dirs:
        shutil.copytree(from_path, os.path.join(g.path_serve, from_path))

    os.makedirs(g.path_src, exist_ok=True)
    os.makedirs(g.path_templates, exist_ok=True)
    os.makedirs(g.path_processing, exist_ok=True)
    os.makedirs(g.path_processing_sections, exist_ok=True)
    os.makedirs(g.path_to_serve, exist_ok=True)


def compile_site():
    sections = { "home", "blog", "art", "misc" }
    # For each file in directory to_serve, 
    # add a heading etc.

    # TODO REWRITE
    for path_root, dirs, files in os.walk("./.websitegen/html_content/"):
        for file in files:
            rel_dir = os.path.relpath(path_root, g.path_cache)
            rel_file = str(os.path.join(rel_dir, file))
            if (rel_file.find(".html") == -1 ):
                continue
            f_out = open(g.path_serve + rel_file, "w")
            content = open(g.path_cache + rel_file, "r").read()

            section = "misc"
            root_dir = os.path.dirname(rel_file).split("/")[0]
            for i in sections:
                if root_dir == ".":
                    if os.path.splitext(rel_file)[0][2:] == i:
                        section = i
                        break
                else:
                    if root_dir == i:
                        section = i
                        break

            headers = str(open(g.path_templates + "header_template.html", "r").read())\
                    .split("\n")

            # Determine which section of website we are in
            # by checking filename and folder structure for matches
            for i in range(len(headers)-1):
                header = headers[i]
                m = re.match(r'.*> *(\w+)', header)
                if (m != None):
                    # Cosmetic. make odd buttons a little different shade.
                    if (section == m.group(1)):
                        headers[i] = headers[i].replace("> ", " id=\"active\"> ")
                    elif (i % 2 == 0):
                        headers[i] = headers[i].replace("> ", " id=\"b2\"> ") 

            title = "<title>teawd's " + section + "</title>"
            text = template_content.replace("<!-- CONTENT -->", content)
            text = text.replace("<!-- TITLE -->", title)
            text = text.replace("<!-- HEADER -->", '\n'.join(headers))

            # remove all comments
            text = re.sub(comment_pattern, '', text)
            f_out.write(text)
        for file in files:
            rel_dir = os.path.relpath(path_root, g.path_to_serve)
            rel_file = str(os.path.join(rel_dir, file))
            if (rel_file.find(".xml") == -1 ):
                continue
            f_out = open(g.path_serve + rel_file, "w")
            content = open(g.path_to_serve + rel_file, "r").read()
            f_out.write(content)
            f_out.close()

    cmd = "cp -f " + g.path_serve + "home.html " + g.path_serve + "index.html"
    os.system(cmd)


def get_tags_html(tags, colors, section_name: str, default_col = "", use_all = True):
    html = ""
    for tag in tags:
        if tag == "all" and not use_all:
            continue
        # col = "col"+colors[tag] if tag in colors else default_col
        col = colors[tag] if tag in colors else default_col
        html += get_tag_html(tag, col=col, section_name=section_name)
    return html


def get_tag_html(tag: str, section_name: str, col: Optional[str] = None, bold = False):
    col = f'class="col{col}"' if col else ""
    tag_text = f"{'<em>' if bold else ''} #{tag} {'</em>' if bold else ''}"
    return f"<a {col} href=\"/{section_name}/" + tag + ".html\">" + tag_text + "</a>"


def compile_section(section_name: str, is_blog: bool = False):
    if not is_blog:
        index_content = open(g.path_src + section_name + ".html").read()
        index_out = open(g.path_cache + section_name + ".html", "w")
        index_out.write(index_content)
        return

    os.makedirs(g.path_cache + section_name, exist_ok=True)
    os.makedirs(g.path_cache + f"{section_name}/post", exist_ok=True)
    os.makedirs(g.path_to_serve + section_name, exist_ok=True)
    os.makedirs(g.path_to_serve + f"{section_name}/post", exist_ok=True)
    os.makedirs(g.path_serve + section_name, exist_ok=True)
    os.makedirs(g.path_serve + f"{section_name}/post", exist_ok=True)

    template_dir = g.path_templates + f"{section_name}/"
    section_index_template = open(template_dir + "index.html", "r").read()
    default_post_template = open(template_dir + "post.html", "r").read()
    index_post_template = open(template_dir + "index_post.html", "r").read()
    section_toml = toml.loads(open(g.path_src + f"{section_name}.toml", "r").read())

    map_tag_posts = {}
    posts_all: OrderedDict = OrderedDict(section_toml['posts'])
    posts: OrderedDict = OrderedDict()
    for post_name in posts_all:
        post = posts_all[post_name]

        if not "visible" in posts_all[post_name]:
            posts_all[post_name]["visible"] = True
        if post["visible"]:
            posts[post_name] = posts_all[post_name]

    config = section_toml['settings']
    tag_colors = config["tag_colors"]

    # get all tags
    tags_unsorted: OrderedDict = OrderedDict()
    for post_name in posts:
        post = posts[post_name]
        # if post["visible"]:
        post["tags"].append("all")

        for tag in post['tags']:
            if not tag in tags_unsorted:
                tags_unsorted[tag] = { "count": 1 }
            else:
                tags_unsorted[tag]["count"] += 1

    tags: OrderedDict = OrderedDict(sorted(tags_unsorted.items(), key = lambda x: x[1]["count"], reverse=True))

    for tag in tags:
        map_tag_posts[tag] = []
    for post_name in posts:
        for tag in posts[post_name]['tags']:
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
        color_hover = Color(hex=color)
        mul = 0.25
        add = 10
        color_add = Color((
                int(color_hover.red * mul + add), 
                int(color_hover.green * mul + add), 
                int(color_hover.blue * mul + add))
        )
        color_hover += color_add

        color_css_text += f"""
        .col{color} {{
            color: #{color}
        }}

        .col{color}:hover {{
            color: {color_hover.hex}
        }}
        """
    
    css_f.write(color_css_text)

    # ========== INDEX PAGE ==========
    out_blog_index = open(g.path_cache + f"{section_name}.html", "w")
    tags_html_all = get_tags_html(tags, config["tag_colors"], section_name=section_name, use_all=True)

    posts_html = ""
    for key in posts:
        post = posts[key]
        if not post["visible"]:
            continue
        posts_html += index_post_template\
                .replace("<!-- POST_LINK -->", f"/{section_name}/post/{key}.html")\
                .replace("<!-- POST_TITLE -->", post["title"])\
                .replace("<!-- POST_NAME -->", key)\
                .replace("<!-- POST_DATE -->", post["date"])\
                .replace("<!-- POST_TAGS -->", get_tags_html(post["tags"],
                                                        config["tag_colors"],
                                                        section_name=section_name,
                                                        default_col="blues",
                                                        use_all=False)
                                                        )

    index_content = section_index_template.replace("<!-- POSTS -->", posts_html)
    index_content = index_content.replace("<!-- TAGS -->", tags_html_all)

    out_blog_index.write(index_content)


    # ========== POST PAGES ==========
    for post_name in posts:
        if "filename" in posts[post_name]:
            post_content = open(f'{g.path_src}{section_name}/{posts[post_name]["filename"]}.html').read()
            posts[post_name]["content"] = post_content

    for i in range(len(posts)):
        post_name = list(posts.keys())[i]
        post_next = list(posts.keys())[i+1] if i < len(posts)-1 else None
        post_prev = list(posts.keys())[i-1] if i > 0 else None

        post = posts[post_name]
        path = g.path_cache + f"{section_name}/post/{post_name}.html"
        f_out = open(path, "w")

        tags_html = get_tags_html(post["tags"], config["tag_colors"], section_name=section_name, use_all=False)

        content = default_post_template
        if "template" in post.keys():
            template_text = open(template_dir + f"post_{post['template']}.html", "r").read()
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
            text = text.replace("{title}", post["title"])
            content = content.replace(f"<!-- {field.upper()} -->", text)
            
        post["content"] = content

        # Content exclusive to post pages
        if post_next:
            next_link = f'<a class="next_link" href="/{section_name}/post/{post_next}.html"> older post → </a>'
            content = content.replace("<!-- NEXT -->", next_link)
        if post_prev:
            prev_link = f'<a href="/{section_name}/post/{post_prev}.html"> ← newer post </a>'
            content = content.replace("<!-- PREVIOUS -->", prev_link)

        f_out.write(content)
        f_out.close()


    # ========== TAG PAGES ===========
    path_tag_template = os.path.join(g.path_templates, f"{section_name}/tag.html")

    for tag in map_tag_posts:
        path = g.path_cache + f"{section_name}/{tag}.html"
        f_tag_out = open(path, "w")

        other_tags = copy.deepcopy(tags)
        other_tags.pop(tag)

        color = tag_colors[tag] if tag in tag_colors else ""
        tags_html_current = get_tag_html(tag, section_name=section_name, col=color)
        tags_html_other = get_tags_html(other_tags, config["tag_colors"], section_name=section_name, use_all=True)
        tags_html_all = get_tags_html(tags, config["tag_colors"], section_name=section_name, use_all=True)

        rss_link = f"/{section_name}/{tag}.xml"

        if os.path.exists(path_tag_template):
            content = open(path_tag_template, "r").read()
            content = content.replace("<!-- TAGS -->", tags_html_other)
            content = content.replace("<!-- TAGS_ALL -->", tags_html_all)
            content = content.replace("<!-- CURRENT_TAG -->", tags_html_current)
            content = content.replace("<!-- RSS_LINK -->", rss_link)
        else:
            content = ""

    # ========== TAG RSS ==========
        rss_items = ""
        for post_name in map_tag_posts[tag]:
            post = posts[post_name]
            rss_link = g.domain + f"/{section_name}/post/" + post_name
            rss_items += rss.create_rss_item(post["title"], rss_link, rss.rss_date(post["date"]), post["content"])

            if posts[post_name]["visible"]:
                post_content = posts[post_name]["content"]
                content += post_content

        rss_title = f"teawd's blog#{tag}"
        rss_desc = f"Full size posts from teawide.xyz/{section_name}/{tag}"
        rss_link = f"{section_name}/{tag}"
        f_tag_rss = open(g.path_serve + f"{section_name}/{tag}.xml", "w")
        f_tag_rss.write(rss.create_rss(rss_title, rss_desc, rss_link, rss_items))
        f_tag_rss.close()

        f_tag_out.write(content)
        f_tag_out.close()

    # backwards compatibility :))))))))
    cmd = "cp -f " + g.path_serve + f"{section_name}/all.xml " + g.path_serve + f"{section_name}.xml"
    os.system(cmd)


def main():
    config_toml = toml.loads(open(g.path_src + "config.toml").read())
    config_sections = config_toml['sections']
    for section in config_sections:
        c_section = config_sections[section]
        if c_section["visible"]:
            # compile_section(section, c_section['blog'])
            compile_section(section, c_section['blog'])

    index = open(g.path_cache + config_toml["config"]["index"]).read()
    index_out = open(g.path_cache + "index.html", "w")
    index_out.write(index)

    compile_site()


if __name__ == "__main__":
    setup()
    main()
