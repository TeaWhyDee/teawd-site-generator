import os
import subprocess
from collections import OrderedDict
import re
from typing import Pattern
from pathlib import Path

is_debug = True
comment_pattern = r'<!--.*-->'

domain = "https://teawide.xyz"
path_root = "./"
path_src = path_root + "src/"
path_to_serve = path_src + "to_serve/"
path_posts = path_to_serve + "blog/post/"
path_serve = path_root + "serve/"
path_blog_rolling = path_to_serve + "blog/all.html"
path_blog_index = path_to_serve + "blog.html"

template_content = open(path_src + "templates/template.html", "r").read()
blog_index_template = open(path_src + "templates/blog_index.html", "r").read()
template_rss = open(path_src + "templates/rss.xml", "r").read()

def html_title(title):
    title = title.replace(" ", "_").replace(":", "")\
            .replace("&", "and").lower() + ".html"
    return title

def rss_title(title):
    title = title.replace("&", "n")
    return title

def create_rss(items, tag):
    rss = template_rss.replace("<!-- CONTENT -->", items)
    rss = rss.replace("<!-- TAG -->", tag)
    return rss

def create_rss_item(title, link, date, content):
    content = content.replace("<code>", "</p><p>")
    content = content.replace("</code>", "</p><p>")
    title = rss_title(title)
    rss_item = f'''<item>
    <title>{title}</title>
    <guid>{link}</guid>
    <link>{link}</link>
    <pubDate>{date}</pubDate>
    <description><![CDATA[{content}
    ]]></description>
    </item>'''
    return rss_item

def rss_date(date):
    fields = date.split(".")
    date = fields[2] + "/" + fields[1] + "/" + fields[0]
    ret = subprocess.check_output(f"TZ=GMT LC_TIME=en_US date \
                                        '+%a, %d %b %Y %H:%M:%S %z'\
                                        -d {date}",
            shell=True, text=True)
    return ret

#                                                  BLOG
# Go through draft files and publish/update if ready
blog_paths = [ "blog-dev" ]
for dir_path in blog_paths:
    paths = Path(path_src + dir_path).iterdir()

    for file in paths:
        text_in = open(str(file), "r").readlines()
        for line in text_in:
            if '<!-- F -->' in line:
                arraypath = str(file).split("/");
                os.system("cp -n " + str(file) + " " + path_src 
                        + "blog/" + arraypath[len(arraypath)-1])
                break
            if '<!-- U -->' in line:
                arraypath = str(file).split("/");
                print("Updating " + arraypath[len(arraypath)-1])
                os.system("cp -f " + str(file) + " " + path_src 
                        + "blog/" + arraypath[len(arraypath)-1])
                break
            if '<!-- D -->' in line:
                arraypath = str(file).split("/");
                os.system("rm -f " + path_src + "blog/" + arraypath[len(arraypath)-1])
                break

# function returns date of the post in UNIX time
# TODO REWRITE IN PYTHON LOL
def sort(file):
    res = int(subprocess.check_output("date -d \"$(cat " + str(file) + 
        " | grep 'Posted:' | awk '{print $2}' | awk 'BEGIN {FS=\".\"};" + 
        " {print $3\"-\"$2\"-\"$1}')\" +%s", shell=True, text=True))    
    return res


# sorted_posts=Path(path + "blog").iterdir()
sorted_posts = sorted(Path(path_src + "blog").iterdir(), key=sort)[::-1]
sorted_posts_dict = OrderedDict()
for file in sorted_posts:
    sorted_posts_dict[str(file)] = {}

# Store all tags in "tags" variable.
# Create a dictionary with each post.
tags = { "all", "art", "personal" }
for file in Path(path_src + "blog").iterdir():
    thistags=set()
    text_in = open(str(file), "r").readlines()
    is_tags = False
    iterlines = iter(text_in)
    while (1):
        line = ""
        try:
            line = next(iterlines)
        except:
            break
# TITLE
        if '</h3>' in line:
            m = re.match(r'(.*)</a', line)
            if (m != None):
                sorted_posts_dict[str(file)]["title"] = m.group(1).strip()
# DATE
        if 'Posted:' in line:
            m = re.match(r'.*Posted:\s*(\S*)', line)
            if (m != None):
                sorted_posts_dict[str(file)]["date"] = m.group(1)
# TAGS
        if '<div class="tags">' in line:
            is_tags = True
        elif tags and 'href' in line:
            m = re.match(r'.*>#(\w+)', line)
            if (m != None):
                tags.add(m.group(1))
                thistags.add(m.group(1))
        elif '/div' in line and is_tags:
            is_tags = False
    sorted_posts_dict[str(file)]["tags"] = thistags
    if is_debug:
        print(sorted_posts_dict[str(file)])


# Create a tag-specific page for each tag.
for tag in tags:
    f_tag_out = open(path_to_serve + "blog/" + tag + ".html", "w")
    this_dict = {}
    text=""
    rss_items = ""
    for file in sorted_posts:
        this_dict = sorted_posts_dict[str(file)]
        text_in = open(str(file), "r").read()
        if tag in this_dict["tags"]:
            text+="<div class=\"article\">\n" + str(text_in) + "\n</div>\n"
            # RSS feeds or each tag
            f_tag_out_rss = open(path_to_serve + "blog/" + tag + ".xml", "w")
            rss_link = domain + "/blog/post/" \
                    + html_title(this_dict["title"])
            rss_items += create_rss_item(this_dict["title"], rss_link, 
                    rss_date(this_dict["date"]), text_in)

    f_tag_out.write(text)
    f_tag_out.close()
    
    f_tag_out_rss.write(create_rss(rss_items, tag))
    f_tag_out_rss.close()



# Put all blogposts in rolling blog page.
f_blog_out = open(path_blog_rolling, "w")
content_blog = ""
for file in sorted_posts_dict:
    f_out = open(path_posts + html_title(sorted_posts_dict[file]["title"]), "w")
    text_in = open(str(file), "r")
    text = text_in.read()
    content_blog += "<div class=\"article\">\n" + text + "\n</div>\n"
    f_out.write("<div class=\"article\">\n" + text + "</div>")
    text_in.close()
f_blog_out.write(content_blog)
f_blog_out.close()


# Put all blogpost titles and links in index blog page.
f_blog_out = open(path_blog_index, "w")
content_blog = blog_index_template
tags_html = ""
for tag in tags:
    tags_html += "<a href=\"/blog/" + tag + ".html\">#" + tag + " </a>"
content_blog = content_blog.replace("<!-- TAGS -->", tags_html)
posts_html = ""
for key in sorted_posts_dict:
    title = html_title(sorted_posts_dict[key]["title"])
    posts_html += sorted_posts_dict[key]["date"] + " - "
    posts_html += "<em><a href=\"/blog/post/" + title +\
            "\"> " + sorted_posts_dict[key]["title"] + "</a></em> | "
    for tag in sorted_posts_dict[key]["tags"]:
        posts_html += "<a href=\"/blog/" + tag + ".html\"> #" + tag + "</a>"
    posts_html += "<br>"
content_blog = content_blog.replace("<!-- POSTS -->", posts_html)
f_blog_out.write(content_blog)
f_blog_out.close()


sections = { "home", "blog", "misc" }
# For each file in directory to_serve, 
# add a heading etc.
for path_root, dirs, files in os.walk(path_to_serve):
    directory = ""
    if dirs:
        directory = "/".join(dirs) + "/"
    for file in files:
        rel_dir = os.path.relpath(path_root, path_to_serve)
        rel_file = os.path.join(rel_dir, file)
        f_out = open(path_serve + rel_file, "w")
        text_in = open(path_to_serve + rel_file, "r")

        section = "misc"
        for i in sections:
            if rel_file.find(i) != -1:
                section = i
                break

        headers = str(open(path_src + "templates/header_template.html", "r").read()).split("\n")
        # Determine which section of website we are in
        # by checking filename and folder structure for matches
        for i in range(len(headers)-1):
            header = headers[i]
            m = re.match(r'.*> *(\w+)', header)
            if (m != None):
                if (headers[i].find("blog") != -1 and 
                        rel_dir == "blog" != -1):
                    headers[i] = headers[i].replace("> blog <", "> blog#" 
                            + file.replace(".html", "") + " <")
                # Cosmetic. <ake odd buttons a little different shade.
                if (rel_file.find(m.group(1)) != -1):
                    headers[i] = headers[i].replace("> ", " id=\"active\"> ")
                elif (i % 2 == 0):
                    headers[i] = headers[i].replace("> ", " id=\"b2\"> ") 

        content = text_in.read()
        # title = "<title>teawd's " + os.path.splitext(os.path.basename(f_in.name))[0] + "</title>"
        title = "<title>teawd's " + section + "</title>"
        text = content
        if (rel_file.find(".html") != -1 ):
            text = template_content.replace("<!-- CONTENT -->", content)
            text = text.replace("<!-- TITLE -->", title)
            text = text.replace("<!-- HEADER -->", '\n'.join(headers))
            
        # remove all comments
        text = re.sub(comment_pattern, '', text)
        f_out.write(text)

# RSS

# print(rss_date)


os.system("cp -f " + path_serve + "home.html " + path_serve + "index.html")
