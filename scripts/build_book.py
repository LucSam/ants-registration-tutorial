#!/usr/bin/env python3
"""Export all six notebook chapters as one HTML reading copy."""
from html import escape, unescape
import os
from pathlib import Path
import re
import shutil
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import nbformat
from nbconvert import HTMLExporter
from traitlets.config import Config

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'ants_registration_tutorial.ipynb'
TUTORIAL = 'ants_registration_tutorial.html'
DATA_SOURCE = ROOT / 'DATA.md'
DOCS = ROOT / 'docs'

STYLE = '''
<style id="tutorial-book-style">
:root { color-scheme: light; --book-ink: #253340; --book-accent: #245c72; }
html { scroll-behavior: smooth; scroll-padding-top: 24px; }
body.jp-Notebook { margin: 0; padding: 0; max-width: none; background: #fff; color: var(--book-ink); }
#book-nav { position: fixed; inset: 0 auto 0 0; width: 258px; box-sizing: border-box;
  padding: 28px 22px; background: #f4f6f7; border-right: 1px solid #e0e5e8;
  overflow-y: auto; font: 14px/1.5 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
#book-nav .book-title { display: block; font-size: 19px; line-height: 1.35; margin-bottom: 22px; }
#book-nav ol { list-style: none; margin: 0; padding: 0; }
#book-nav .chapters > li { margin-bottom: 14px; }
#book-nav .subtopics { margin: 7px 0 0; padding-left: 12px; border-left: 1px solid #dce2e5; }
#book-nav .subtopics li { margin-bottom: 5px; font-size: 12px; line-height: 1.45; }
#book-nav a { color: #314f60; text-decoration: none; }
#book-nav a:hover, #book-nav a:focus { text-decoration: underline; }
#book-nav a[aria-current="page"] { text-decoration: underline; text-underline-offset: 4px; }
main { width: calc(100% - 258px); max-width: 1000px; box-sizing: border-box;
  margin: 0 auto 0 max(258px, calc((100vw - 1000px + 258px) / 2)); padding: 38px 48px 80px; }
.jp-MarkdownOutput { font: 16px/1.72 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color: var(--book-ink); overflow-wrap: break-word; }
.jp-MarkdownOutput h1 { font-size: 34px; line-height: 1.2; font-weight: 650; margin: 0 0 22px; }
.jp-MarkdownOutput h2 { font-size: 26px; line-height: 1.3; margin-top: 48px; padding-top: 20px;
  border-top: 1px solid #dde4e8; }
.jp-MarkdownOutput h3 { font-size: 20px; line-height: 1.4; margin-top: 30px; }
.jp-MarkdownOutput h4 { font-size: 17px; line-height: 1.4; margin-top: 26px; }
.jp-MarkdownOutput p { margin: 0 0 16px; }
.jp-MarkdownOutput a { color: var(--book-accent); }
.jp-MarkdownOutput table { font-size: 14px; line-height: 1.5; width: 100%; margin: 20px 0; }
.jp-MarkdownOutput th, .jp-MarkdownOutput td { padding: 10px 12px; text-align: left; vertical-align: top; }
.jp-MarkdownOutput th { background: #edf2f4; }
.jp-MarkdownOutput code { font-size: 0.88em; }
.jp-MarkdownOutput td code { overflow-wrap: anywhere; white-space: normal; }
.jp-InputPrompt, .jp-OutputPrompt { display: none !important; }
.jp-CodeCell { margin: 12px 0 24px; }
.jp-InputArea { border: 1px solid #dce3e7; border-radius: 5px; background: #f7f9fa; }
.jp-InputArea-editor { padding: 12px 14px; background: transparent !important; }
.jp-InputArea pre { white-space: pre-wrap !important; overflow-wrap: anywhere; font-size: 12px; line-height: 1.55; }
.jp-OutputArea { margin-top: 12px; }
.jp-OutputArea pre { font-size: 12px; line-height: 1.5; }
.jp-OutputArea img { max-width: 100%; height: auto; }
@media (max-width: 850px) {
  #book-nav { position: static; width: auto; padding: 22px; border-right: 0; border-bottom: 1px solid #dde4e8; }
  #book-nav .chapters { columns: 2; column-gap: 22px; }
  #book-nav .chapters > li { break-inside: avoid; }
  #book-nav .subtopics { columns: 1; }
  #book-nav .book-title { margin-bottom: 16px; }
  main { width: 100%; margin: 0; padding: 24px 18px 50px; }
  .jp-MarkdownOutput h1 { font-size: 28px; }
}
@media (max-width: 480px) { #book-nav .chapters { columns: 1; } }
@media print {
  #book-nav { display: none; }
  main { width: 100%; max-width: none; margin: 0; padding: 0; }
  .jp-CodeCell, .jp-OutputArea { break-inside: avoid; }
}
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
</style>
'''


def chapters(notebook):
    """Use explicit notebook anchors so chapter labels have one source."""
    result = []
    pattern = re.compile(r'<a id="([^"]+)"></a>\s*\n(#{2,3}) ([^\n]+)')
    for cell in notebook.cells:
        if cell.cell_type != 'markdown':
            continue
        for anchor, heading, title in pattern.findall(cell.source):
            item = {'anchor': anchor, 'title': title, 'children': []}
            if heading == '##':
                result.append(item)
            elif result:
                result[-1]['children'].append(item)
    return result


def navigation(toc):
    def link(title, anchor):
        return f'<a href="#{escape(anchor, quote=True)}">{escape(title)}</a>'

    items = []
    for chapter in toc:
        children = ''.join('<li>' + link(item['title'], item['anchor']) + '</li>'
                           for item in chapter['children'])
        sublist = f'<ol class="subtopics">{children}</ol>' if children else ''
        items.append('<li>' + link(chapter['title'], chapter['anchor']) + sublist + '</li>')
    return ('<aside id="book-nav" aria-label="Tutorial navigation">'
            '<a class="book-title" href="#top">ANTs registration<br>tutorial</a>'
            '<ol class="chapters">' + ''.join(items) + '</ol></aside>')


def resolve_links(content, destination):
    """Resolve links written relative to the project root from the HTML directory."""
    def replace(match):
        original = unescape(match.group(1))
        parts = urlsplit(original)
        if parts.scheme or parts.netloc or not parts.path:
            return match.group(0)
        source_path = unquote(parts.path)
        if source_path == 'DATA.md':
            anchor = parts.fragment or 'data-and-attribution'
            return f'href="#{escape(anchor, quote=True)}"'
        if destination.parent == DOCS and source_path.startswith('licenses/'):
            target = source_path
        else:
            target = Path(os.path.relpath(ROOT / source_path, destination.parent)).as_posix()
        resolved = urlunsplit(('', '', quote(target, safe='/'), parts.query, parts.fragment))
        return f'href="{escape(resolved, quote=True)}"'
    return re.sub(r'href="([^"]*)"', replace, content)


def export_page(notebook, destination, title, toc):
    config = Config()
    config.TagRemovePreprocessor.enabled = True
    config.TagRemovePreprocessor.remove_all_outputs_tags = {'interactive-only'}
    exporter = HTMLExporter(template_name='lab', config=config)
    content, _ = exporter.from_notebook_node(notebook, resources={'metadata': {'name': title}})
    content = resolve_links(content, destination)
    content = content.replace('</head>', STYLE + '</head>')
    body_start = content.index('>', content.index('<body')) + 1
    content = content[:body_start] + '<a id="top"></a>' + navigation(toc) + content[body_start:]
    destination.write_text(content)
    return destination


def sync_data_chapter(notebook):
    """Keep the notebook's final chapter in sync with its attribution source."""
    source = re.sub(r'^(#{1,3}) ', r'#\1 ', DATA_SOURCE.read_text(), flags=re.MULTILINE)
    data_cell = nbformat.v4.new_markdown_cell(
        source, id='data-attribution', metadata={'tags': ['data-chapter']},
    )
    cells = [cell for cell in notebook.cells
             if 'data-chapter' not in cell.metadata.get('tags', [])]
    footer_index = next((i for i, cell in enumerate(cells)
                         if 'tutorial-footer' in cell.metadata.get('tags', [])), len(cells))
    cells.insert(footer_index, data_cell)
    changed = cells != notebook.cells
    notebook.cells = cells
    return changed


def main():
    notebook = nbformat.read(SOURCE, as_version=4)
    changed = sync_data_chapter(notebook)
    nbformat.validate(notebook)
    if changed:
        nbformat.write(notebook, SOURCE)
    toc = chapters(notebook)
    case_id = notebook.metadata.get('tutorial_case', 'UCSF-PDGM-0033')
    output_dir = ROOT / 'outputs' / case_id
    output_dir.mkdir(parents=True, exist_ok=True)
    path = export_page(notebook, output_dir / TUTORIAL, 'ANTs registration tutorial', toc)
    (output_dir / 'data.html').unlink(missing_ok=True)
    print(path)
    DOCS.mkdir(exist_ok=True)
    (DOCS / 'licenses').mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'licenses/FSL.txt', DOCS / 'licenses/FSL.txt')
    (DOCS / '.nojekyll').touch()
    print(export_page(notebook, DOCS / 'index.html', 'ANTs registration tutorial', toc))


if __name__ == '__main__':
    main()
