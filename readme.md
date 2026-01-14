
Mainly for personal use.

See https://teawide.xyz/ for an example of a website generated with this scripr.

Refer to https://teawide.xyz/blog/post/updating_the_website for extra info.

## Principle
This is a blog-style static site generator with tagging support, post templates and macros.
Site content is defined in html files and toml configs.
The script generates a tree of html pages, each one containing a header and content.
Blog sections have rolling and index pages (for all posts and for each tag).

It generates the following end-points and files:
- `/resources/`   (media)
- `/section-name/`     (pages of a section, section-name is user defined)
- `/section-name.html` (index page of a section)
- `/index.html`   (copy of selected section)
- `/css/`

End-points are called 'sections'.
tea-sitegen allows for two types of sections:
- Blog section.
- Single page section (an html file to which a header is added).

Generation pipeline:
1. Process macros in section definitions.
2. Substitute values in posts, apply tags.
3. Generate pages.
4. Add headers and styling to pages.


### Blog sections
All blog sections automatically generate the following pages:
1. Index page with post titles and links.
3. Rolling pages for each tag (including #all tag which contains all visible posts).
4. Individual post pages.

Post content is the html content of a specific post excluding metadata (tags, etc.).
Post content can either be an html file or an html-formatted string value inside the section config (see usage).

Post content is put inside an `html template`.
All the section pages are then populated with those templated posts.

A section is defined with:
- Index page html file.
- Configuration file.
- Templates (index, post templates).
- Posts (defined in the config file and optionally html files).

Posts are defined using:
- An entry inside a section toml file (path: `src/section.html`).
- An html template (path: `templates/section/post.html`).
- Optional .html file (`src/section/post_filename.html`)

Posts have the following settings:
- `Visible` (wether or not the post should show up in the index and #all pages).

## Usage
The only config file necessary to run the script is config.toml, it defines the index page and sections.

Edit `src/config.toml` and define at least one section:
```toml
[sections]
    [sections.blog]
    visible = true   # false hides the section from the header.
    blog = true      # wether the section should be a blog-section.
```

Section config consists of:
- Tags, tag colors.
- Macros (html strings with substitutable values defined in post definitions)

Defite the config for the section `src/blog.toml`:
```
[settings]
    [settings.tag_colors]
    some = "dddddd"
    tag = "dd9ace"
    all = "6bb28c"  # always present tag

    [settings.fields]
    macro = '<div class="macro"> {} </div>'

[posts]
    [posts.post1]
    title = "post with html file content"
    filename = "content_file"
    visible = true
    tags = [ "some", "tag" ]
    date = "01.01.2026"
    macro = "i am a macro value"
```


Put media into `resources`.

Check src folder for example config files.

Run:
```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python python/main.py
```


## Code
All code is stored in the `python` folder.
Files:
- `main.py` - site generation code.
- `glo.py` - Path definitions for generation.
- `rss.py` - rss feed generation code.

# Example

```python
cd example
python ../python/main.py
```

Generated code will be located in `./serve`

Use `./serve.sh` to automatically open it in a browser, or
you can simply open the files created in `./serve`.

