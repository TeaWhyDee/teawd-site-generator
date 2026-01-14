import re
import subprocess

import glo as g

template_rss = open(g.path_templates + "rss.xml", "r").read()


def rss_title(title):
    title = title.replace("&", "n")
    return title


def create_rss(config, title, desc, link, items):
    link_full = config["config"]["domain"] + link

    rss = (
        template_rss.replace("<!-- CONTENT -->", items)
        .replace("<!-- TITLE -->", title)
        .replace("<!-- DESC -->", desc.strip())
        .replace("<!-- LINK -->", link_full)
    )
    return rss


def create_rss_item(config, title, link, date, content):
    content = content.replace("<code>", "</p><p>")
    content = content.replace("</code>", "</p><p>").strip()
    title = rss_title(title)
    rss_item = f"""<item>
    <title>{title}</title>
    <guid>{link}</guid>
    <link>{link}</link>
    <pubDate>{date}</pubDate>
    <description><![CDATA[ {content} ]]></description>
    </item>"""

    pattern = r'(href|src)="(?!https://)([^"]+)"'
    rss_item = re.sub(
        pattern,
        lambda m: f'{m.group(1)}="{config["config"]["domain"]}{m.group(2)}"',
        rss_item,
    )

    return rss_item


def rss_date(date):
    fields = date.split(".")
    date = fields[2] + "/" + fields[1] + "/" + fields[0]
    ret = subprocess.check_output(
        f"TZ=GMT LC_TIME=en_US date \
                                        '+%a, %d %b %Y %H:%M:%S %z'\
                                        -d {date}",
        shell=True,
        text=True,
    ).strip()
    return ret
