import os
import subprocess
from collections import OrderedDict
import re
from typing import Pattern
from pathlib import Path

is_debug = False

root = "./"
path = root + "src/"
to_serve = path + "to_serve/"
serve = root + "serve/"
f_temp = open(path + "templates/template.html", "r")
template_content = f_temp.read()
comment_pattern = r'<!--.*-->'

#                                                  BLOG
# Go through draft files and publish/update if ready
blog_paths = [ "blog-dev" ]
for dir_path in blog_paths:
    paths = Path(path + dir_path).iterdir()

    for file in paths:
        f_in = open(str(file), "r").readlines()
        for line in f_in:
            if '<!-- F -->' in line:
                arraypath = str(file).split("/");
                os.system("cp -n " + str(file) + " " + path 
                        + "blog/" + arraypath[len(arraypath)-1])
                break
            if '<!-- U -->' in line:
                arraypath = str(file).split("/");
                print("Updating " + arraypath[len(arraypath)-1])
                os.system("cp -f " + str(file) + " " + path 
                        + "blog/" + arraypath[len(arraypath)-1])
                break
            if '<!-- D -->' in line:
                arraypath = str(file).split("/");
                os.system("rm -f " + path + "blog/" + arraypath[len(arraypath)-1])
                break

# function returns date of the post in UNIX time
# TODO REWRITE IN PYTHON LOL
def sort(file):
    res = int(subprocess.check_output("date -d \"$(cat " + str(file) + 
        " | grep 'Posted:' | awk '{print $2}' | awk 'BEGIN {FS=\".\"};" + 
        " {print $3\"-\"$2\"-\"$1}')\" +%s", shell=True, text=True))    
    return res


# sorted_posts=Path(path + "blog").iterdir()
sorted_posts = sorted(Path(path + "blog").iterdir(), key=sort)[::-1]
sorted_posts_dict = OrderedDict()
for file in sorted_posts:
    sorted_posts_dict[str(file)] = {}

# Store all tags in "tags" variable.
# Create a dictionary with "post: <tags>" entries.
tags = { "art", "personal" }
for file in Path(path + "blog").iterdir():
    thistags=set()
    f_in = open(str(file), "r").readlines()
    is_tags = False
    iterlines = iter(f_in)
    while (1):
        line = ""
        try:
            line = next(iterlines)
        except:
            break
# TITLE
        if '<h3>' in line:
            m = re.match(r'.*>(.*)</', line)
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
    f_tag_out = open(to_serve + "blog/" + tag + ".html", "w")
    text=""
    for file in sorted_posts:
        if tag in sorted_posts_dict[str(file)]["tags"]:
            f_in = open(str(file), "r").read()
            text+="<div class=\"article\">\n" + str(f_in) + "\n</div>\n"
    f_tag_out.write(text)
    f_tag_out.close()


# Put all blogposts in blog.html
f_blog_out = open(to_serve + "blog.html", "w")
content_blog = ""
for file in sorted_posts:
    f_in = open(str(file), "r")
    content_blog += "<div class=\"article\">\n" + f_in.read() + "\n</div>\n"
    # content_blog = re.sub(comment_pattern, '', content_blog)
    f_in.close()
f_blog_out.write(content_blog)
f_blog_out.close()


# For each file in directory to_serve, 
# add a heading etc.
for root, dirs, files in os.walk(to_serve):
    directory = ""
    if dirs:
        directory = "/".join(dirs) + "/"
    for file in files:
        rel_dir = os.path.relpath(root, to_serve)
        rel_file = os.path.join(rel_dir, file)
        f_out = open(serve + rel_file, "w")
        f_in = open(to_serve + rel_file, "r")

        headers = str(open(path + "templates/header_template.html", "r").read()).split("\n")
        # Determine which section of website we are in
        # by checking filename and folder structure for matches
        for file in range(len(headers)-1):
            header = headers[file]
            m = re.match(r'.*> *(\w+)', header)
            if (m != None):
                if (rel_file.find(m.group(1)) != -1):
                    headers[file] = headers[file].replace("> ", " id=\"active\"> ")
                elif (file % 2 == 0):
                    headers[file] = headers[file].replace("> ", " id=\"b2\"> ") 

        content = f_in.read()
        title = "<title>teawhydee | " + os.path.splitext(os.path.basename(f_in.name))[0] + "</title>"
        text = template_content.replace("<!-- CONTENT -->", content)
        text = text.replace("<!-- TITLE -->", title)
        text = text.replace("<!-- HEADER -->", '\n'.join(headers))
            
        # remove all comments
        text = re.sub(comment_pattern, '', text)
        f_out.write(text)

os.system("cp -f " + serve + "home.html " + serve + "index.html")
