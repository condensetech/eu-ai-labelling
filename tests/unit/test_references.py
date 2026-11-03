"""`label_tool references`: where a project uses an image that now has a Labelled Copy.

Each test builds a project on disk, with the original image, its Labelled
Copy next to it and pages that use it, runs `references <image> --root
<project>` as a subprocess and reads the JSON. The tool only finds and
classifies references: it reports each one it can update (with the
replacement and, for an image tag, its current alt text) and each one it
can't, with the reason. Without `--apply` it never edits a file; with it,
it points each reference to the copy and, with `--alt-mention`, adds the
mention to the alt text, changing nothing else (see the end of this file).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from conftest import run_label_tool
from helpers import sha256


def write(project: Path, relative: str, text: str) -> Path:
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def image(project: Path, relative: str, labelled: bool = True) -> Path:
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (60, 40), (200, 220, 240)).save(path)
    if labelled:
        Image.new("RGB", (60, 40), (0, 0, 0)).save(path.with_name(f"{path.stem}.ai-label{path.suffix}"))
    return path


@pytest.fixture
def project(tmp_path) -> Path:
    root = tmp_path / "site"
    root.mkdir()
    return root


def references(project: Path, original: Path, *extra: str):
    return run_label_tool("references", original, "--root", project, *extra, cwd=project)


def found(result, key: str = "updatable") -> list[tuple[str, int, str]]:
    return [(r["file"], r["line"], r["reference"]) for r in result.json[key]]


# --- Updatable references -----------------------------------------------------


def test_finds_a_markdown_image_reference_with_its_alt_text(project):
    original = image(project, "images/hero.png")
    write(project, "content/post.md", "# Trails\n\nIntro.\n\n![A trail among larches](../images/hero.png)\n")

    result = references(project, original)

    assert result.returncode == 0, result.json
    assert result.json["original"] == str(original)
    assert result.json["labelled_copy"] == str(project / "images" / "hero.ai-label.png")
    assert result.json["updatable"] == [
        {
            "file": "content/post.md",
            "line": 5,
            "kind": "markdown-image",
            "reference": "../images/hero.png",
            "replacement": "../images/hero.ai-label.png",
            "alt": "A trail among larches",
            "alt_expression": None,
        }
    ]
    assert result.json["not_updatable"] == []


def test_finds_an_html_img_with_a_root_relative_path_served_from_public(project):
    original = image(project, "public/images/hero.png")
    write(
        project,
        "index.html",
        '<main>\n  <img class="hero"\n       src="/images/hero.png?v=2"\n       alt="Larches in autumn">\n</main>\n',
    )

    result = references(project, original)

    assert result.json["updatable"] == [
        {
            "file": "index.html",
            "line": 3,
            "kind": "html-img",
            "reference": "/images/hero.png?v=2",
            "replacement": "/images/hero.ai-label.png?v=2",
            "alt": "Larches in autumn",
            "alt_expression": None,
        }
    ]


def test_finds_references_in_source_and_style_files(project):
    original = image(project, "src/assets/hero.png")
    write(project, "src/App.jsx", 'import hero from "./assets/hero.png";\n\nexport const App = () => <img src={hero} alt="Larches" />;\n')
    write(project, "src/styles/site.css", ".banner {\n  background: url('../assets/hero.png') no-repeat;\n}\n")

    result = references(project, original)

    assert sorted((r["file"], r["line"], r["kind"], r["replacement"], r["alt"]) for r in result.json["updatable"]) == [
        ("src/App.jsx", 1, "other", "./assets/hero.ai-label.png", None),
        ("src/styles/site.css", 2, "other", "../assets/hero.ai-label.png", None),
    ]


def test_tells_an_alt_expression_apart_from_a_missing_alt(project):
    original = image(project, "src/img/hero.png")
    write(
        project,
        "src/Hero.jsx",
        'export const A = () => <img src="img/hero.png" alt={title} />;\n'
        'export const B = () => <img src="img/hero.png" alt={`${title} photo`} />;\n'
        'export const C = () => <img src="img/hero.png" />;\n'
        'export const D = () => <img src="img/hero.png" alt="" />;\n',
    )
    write(project, "src/page.html", "<img src=img/hero.png alt=Larches>\n")

    result = references(project, original)

    assert sorted((r["file"], r["line"], r["alt"], r["alt_expression"]) for r in result.json["updatable"]) == [
        ("src/Hero.jsx", 1, None, "{title}"),
        ("src/Hero.jsx", 2, None, "{`${title} photo`}"),
        ("src/Hero.jsx", 3, None, None),
        ("src/Hero.jsx", 4, "", None),
        ("src/page.html", 1, "Larches", None),
    ]


def alts(result) -> list[tuple[int, str | None, str | None]]:
    return [(r["line"], r["alt"], r["alt_expression"]) for r in result.json["updatable"]]


@pytest.mark.parametrize(
    ("tag", "alt", "alt_expression"),
    [
        ("<img src=images/hero.png>", None, None),
        ("<img src='images/hero.png' alt='Larches in autumn'>", "Larches in autumn", None),
        ('<img src="images/hero.png" alt={"Larches in autumn"} />', "Larches in autumn", None),
    ],
    ids=["no alt", "single-quoted alt", "JSX string alt"],
)
def test_reports_the_alt_text_of_an_img_tag(project, tag, alt, alt_expression):
    original = image(project, "images/hero.png")
    write(project, "page.jsx", f"{tag}\n")

    assert alts(references(project, original)) == [(1, alt, alt_expression)]


@pytest.mark.parametrize(
    ("tag", "alt", "alt_expression"),
    [
        ('<img src="images/hero.png" data-alt="zz">', None, None),
        ('<img src="images/hero.png" alt="x" data-alt="zz">', "x", None),
        ('<img src="images/hero.png" data-alt="zz" alt="x">', "x", None),
        ('<img src="images/hero.png" title="alt=zz" alt="x">', "x", None),
        ('<img src="images/hero.png" :alt="t">', None, '"t"'),
        ('<img src="images/hero.png" v-bind:alt="caption + \'!\'">', None, '"caption + \'!\'"'),
        ("<img src=\"images/hero.png\" alt={title} />", None, "{title}"),
        ("<img src=\"images/hero.png\" onLoad={() => go()} alt={title} />", None, "{title}"),
        ("<img src=\"images/hero.png\" onLoad={() => go()} alt=\"Larches\" />", "Larches", None),
        ("<img onLoad={() => go()} src=\"images/hero.png\" alt=\"Larches\" />", "Larches", None),
    ],
    ids=[
        "data-alt only", "alt then data-alt", "data-alt then alt", "alt= inside another value",
        "Vue :alt", "Vue v-bind:alt", "JSX alt prop", "arrow function before a computed alt",
        "arrow function before a literal alt", "arrow function before src",
    ],
)
def test_reads_the_alt_attribute_itself_across_the_whole_tag(project, tag, alt, alt_expression):
    original = image(project, "images/hero.png")
    write(project, "page.vue", f"{tag}\n")

    result = references(project, original)

    assert [(r["kind"], r["alt"], r["alt_expression"]) for r in result.json["updatable"]] == [("html-img", alt, alt_expression)]


def test_a_reference_style_image_reports_the_definition_and_each_image_using_it(project):
    original = image(project, "docs/img/hero.png")
    write(
        project,
        "docs/a.md",
        "# Trails\n\n"
        "![Trail][r]\n"
        "Some text, [see the trail][map].\n"
        "![Larches in autumn][R]\n"
        "![hero][]\n"
        "![hero]\n\n"
        "[r]: img/hero.png\n"
        "[hero]: <img/hero.png> \"Hero\"\n",
    )

    result = references(project, original)

    assert result.json["updatable"] == [
        {
            "file": "docs/a.md",
            "line": 9,
            "kind": "markdown-definition",
            "reference": "img/hero.png",
            "replacement": "img/hero.ai-label.png",
            "alt": None,
            "alt_expression": None,
            "images": [{"line": 3, "alt": "Trail"}, {"line": 5, "alt": "Larches in autumn"}],
        },
        {
            "file": "docs/a.md",
            "line": 10,
            "kind": "markdown-definition",
            "reference": "img/hero.png",
            "replacement": "img/hero.ai-label.png",
            "alt": None,
            "alt_expression": None,
            "images": [{"line": 6, "alt": "hero"}, {"line": 7, "alt": "hero"}],
        },
    ]


def test_a_link_to_the_image_is_reported_as_a_link(project):
    original = image(project, "docs/img/hero.png")
    write(
        project,
        "docs/a.md",
        "[full size](img/hero.png)\n"
        "[download][d]\n\n"
        "[d]: img/hero.png\n",
    )
    write(project, "docs/b.html", '<a class="zoom" href="img/hero.png">Full size</a>\n')

    result = references(project, original)

    assert sorted((r["file"], r["line"], r["kind"], r["alt"]) for r in result.json["updatable"]) == [
        ("docs/a.md", 1, "link", None),
        ("docs/a.md", 4, "link", None),
        ("docs/b.html", 1, "link", None),
    ]


def test_a_linked_image_whose_link_points_to_the_original_reports_the_link(project):
    original = image(project, "docs/img/hero.png")
    image(project, "docs/other.png")
    write(
        project,
        "docs/a.md",
        "[![a](img/hero.png)](https://example.com)\n"
        "[![b](other.png)](img/hero.png)\n",
    )

    result = references(project, original)

    assert sorted((r["line"], r["kind"], r["alt"]) for r in result.json["updatable"]) == [
        (1, "markdown-image", "a"),
        (2, "link", None),
    ]

def test_a_picture_source_is_updatable_and_has_no_alt(project):
    original = image(project, "images/hero.png")
    write(
        project,
        "index.html",
        "<picture>\n"
        '  <source srcset="images/hero.png 1x" type="image/png">\n'
        '  <img src="images/hero.jpg" alt="Larches">\n'
        "</picture>\n",
    )

    result = references(project, original)

    assert [(r["line"], r["kind"], r["replacement"], r["alt"], r["alt_expression"]) for r in result.json["updatable"]] == [
        (2, "html-source", "images/hero.ai-label.png", None, None)
    ]


def test_ignores_other_images_that_only_share_or_contain_the_name(project):
    original = image(project, "images/hero.png")
    image(project, "drafts/hero.png", labelled=False)
    write(
        project,
        "post.md",
        "# Post\n\n"
        "![Draft](drafts/hero.png)\n"
        "![Other](images/superhero.png)\n"
        "![Already labelled](images/hero.ai-label.png)\n"
        "![The one](images/hero.png)\n",
    )

    result = references(project, original)

    assert found(result) == [("post.md", 6, "images/hero.png")]
    assert result.json["not_updatable"] == []


def test_an_angle_bracket_destination_is_one_path_even_with_spaces(project):
    original = image(project, "docs/img/hero.png")
    spaced = image(project, "docs/img/my hero.png")
    write(project, "docs/a.md", "![x](<img/my hero.png>)\n![y](<img/hero.png>)\n")

    assert found(references(project, original)) == [("docs/a.md", 2, "img/hero.png")]
    assert references(project, original).json["not_updatable"] == []
    spaced_result = references(project, spaced)
    assert [(r["line"], r["kind"], r["replacement"], r["alt"]) for r in spaced_result.json["updatable"]] == [
        (1, "markdown-image", "img/my hero.ai-label.png", "x")
    ]


def test_a_plain_text_file_reports_only_paths_not_a_file_name_in_prose(project):
    original = image(project, "docs/img/hero.png")
    write(project, "CREDITS.txt", "Photo credit: see hero.png in docs\nFile: docs/img/hero.png\nOld: docs/old/hero.png\n")

    result = references(project, original)

    assert found(result) == [("CREDITS.txt", 2, "docs/img/hero.png")]
    assert found(result, "not_updatable") == [("CREDITS.txt", 3, "docs/old/hero.png")]


@pytest.mark.parametrize("source", ["m.py", "m.rb", "m.go", "M.java", "m.rs", "m.php", "M.cs"])
def test_finds_references_in_common_source_languages(project, source):
    original = image(project, "src/img/hero.png")
    write(project, f"src/{source}", 'hero = "img/hero.png"\n')

    result = references(project, original)

    assert [(r["file"], r["kind"], r["replacement"]) for r in result.json["updatable"]] == [
        (f"src/{source}", "other", "img/hero.ai-label.png")
    ]


def test_skips_dependencies_build_output_and_hidden_folders(project):
    original = image(project, "images/hero.png")
    for folder in ("node_modules/theme", "dist", ".git"):
        write(project, f"{folder}/page.html", '<img src="/images/hero.png" alt="x">\n')
    write(project, "page.html", '<img src="/images/hero.png" alt="x">\n')

    result = references(project, original)

    assert found(result) == [("page.html", 1, "/images/hero.png")]


def test_keeps_a_query_or_fragment_and_decodes_an_encoded_folder(project):
    original = image(project, "img/my dir/hero.png")
    write(project, "a.md", "![a](img/my%20dir/hero.png#zoom)\n")

    result = references(project, original)

    assert [(r["reference"], r["replacement"]) for r in result.json["updatable"]] == [
        ("img/my%20dir/hero.png#zoom", "img/my%20dir/hero.ai-label.png#zoom")
    ]


def test_finds_a_reference_whose_file_name_is_url_encoded(project):
    original = image(project, "img/my hero.png")
    write(project, "a.md", "![a](img/my%20hero.png)\n")

    result = references(project, original)

    assert found(result) == [("a.md", 1, "img/my%20hero.png")]
    assert result.json["updatable"][0]["replacement"] == "img/my%20hero.ai-label.png"


def test_a_page_linked_from_outside_the_project_is_not_scanned(project, tmp_path):
    original = image(project, "hero.png")
    outside = tmp_path / "elsewhere.md"
    outside.write_text("![Mountain](hero.png)\n")
    (project / "page.md").symlink_to(outside)

    assert found(references(project, original)) == []


@pytest.mark.parametrize("served", ["public", "static"])
def test_resolves_a_root_relative_path_from_the_folder_the_site_serves(project, served):
    original = image(project, f"{served}/images/hero.png")
    write(project, "index.html", '<img src="/images/hero.png" alt="Hero">\n')

    assert found(references(project, original)) == [("index.html", 1, "/images/hero.png")]


def test_skips_files_too_large_or_not_utf8_without_failing(project):
    original = image(project, "images/hero.png")
    write(project, "big.md", "![Hero](images/hero.png)\n" + "x" * 2_100_000 + "\n")
    (project / "latin1.html").write_bytes('<p>Caf\xe9</p><img src="images/hero.png">\n'.encode("latin-1"))
    write(project, "post.md", "![Hero](images/hero.png)\n")

    result = references(project, original)

    assert result.returncode == 0, result.json
    assert found(result) == [("post.md", 1, "images/hero.png")]


def test_searches_the_current_folder_when_no_root_is_given(project):
    original = image(project, "images/hero.png")
    write(project, "post.md", "![Hero](images/hero.png)\n")

    result = run_label_tool("references", "images/hero.png", cwd=project)

    assert result.returncode == 0, result.json
    assert result.json["root"] == str(project.resolve())
    assert result.json["original"] == str(original.resolve())
    assert found(result) == [("post.md", 1, "images/hero.png")]


def test_changes_no_file(project):
    original = image(project, "images/hero.png")
    page = write(project, "post.md", "![Hero](images/hero.png)\n")
    before = {p: sha256(p) for p in project.rglob("*") if p.is_file()}

    result = references(project, original)

    assert result.returncode == 0 and found(result)
    assert {p: sha256(p) for p in project.rglob("*") if p.is_file()} == before
    assert page.read_text() == "![Hero](images/hero.png)\n"


# --- References the tool can't update -------------------------------------------


def test_reports_dynamic_external_and_unresolved_references_as_not_updatable(project):
    original = image(project, "public/images/hero.png")
    write(
        project,
        "src/Hero.jsx",
        "const base = import.meta.env.BASE_URL;\n"
        "export const a = `${base}/images/hero.png`;\n"
        'export const b = base + "/images/hero.png";\n'
        'export const c = "https://cdn.example.com/images/hero.png";\n'
        'import d from "@/images/hero.png";\n',
    )
    write(project, "layouts/post.njk", '<img src="{{ site.baseurl }}/images/hero.png" alt="Hero">\n')

    result = references(project, original)

    assert result.returncode == 0, result.json
    assert result.json["updatable"] == []
    reasons = sorted((r["file"], r["line"], r["reference"], r["reason"]) for r in result.json["not_updatable"])
    assert reasons == [
        ("layouts/post.njk", 1, "/images/hero.png", "dynamic"),
        ("src/Hero.jsx", 2, "/images/hero.png", "dynamic"),
        ("src/Hero.jsx", 3, "/images/hero.png", "dynamic"),
        ("src/Hero.jsx", 4, "https://cdn.example.com/images/hero.png", "external"),
        ("src/Hero.jsx", 5, "@/images/hero.png", "unresolved"),
    ]


def test_a_reference_that_resolves_to_the_original_and_one_that_does_not(project):
    original = image(project, "images/hero.png")
    write(project, "a.md", "![Hero](images/hero.png)\n![Moved](img/hero.png)\n")

    result = references(project, original)

    assert found(result) == [("a.md", 1, "images/hero.png")]
    assert found(result, "not_updatable") == [("a.md", 2, "img/hero.png")]
    assert result.json["not_updatable"][0]["reason"] == "unresolved"


# --- Errors ---------------------------------------------------------------------


def error_code(result) -> str:
    assert result.returncode != 0, result.json
    return result.json["error"]["code"]


def test_refuses_before_the_labelled_copy_exists(project):
    original = image(project, "images/hero.png", labelled=False)
    write(project, "post.md", "![Hero](images/hero.png)\n")

    assert error_code(references(project, original)) == "no_labelled_copy"


def test_refuses_a_labelled_copy_in_place_of_the_original(project):
    original = image(project, "images/hero.png")

    assert error_code(references(project, original.with_name("hero.ai-label.png"))) == "labelled_copy"


def test_refuses_a_missing_image_and_an_image_outside_the_project(project, tmp_path):
    assert error_code(references(project, project / "images" / "missing.png")) == "not_found"
    outside = image(tmp_path, "elsewhere/hero.png")
    assert error_code(references(project, outside)) == "outside_project"


# --- --apply and --alt-mention: the edits themselves -------------------------

MENTION = "Image generated with AI"


def apply(project: Path, original: Path, *mentions: str):
    extra = ["--apply"] + [arg for m in mentions for arg in ("--alt-mention", m)]
    result = references(project, original, *extra)
    assert result.returncode == 0, result.json
    return result.json


@pytest.mark.parametrize("before, after", [
    ("![A trail](../images/hero.png)", "![A trail (Image generated with AI)](../images/hero.ai-label.png)"),
    ("![](../images/hero.png)", "![Image generated with AI](../images/hero.ai-label.png)"),
    ('<img src="../images/hero.png" alt="A trail">', '<img src="../images/hero.ai-label.png" alt="A trail (Image generated with AI)">'),
    ("<img alt='A trail' src=\"../images/hero.png\">", '<img alt="A trail (Image generated with AI)" src="../images/hero.ai-label.png">'),
    ('<img src="../images/hero.png">', '<img alt="Image generated with AI" src="../images/hero.ai-label.png">'),
    ('<img src="../images/hero.png" alt={"A trail"} />', '<img src="../images/hero.ai-label.png" alt="A trail (Image generated with AI)" />'),
    ("![A trail][r]\n\n[r]: ../images/hero.png", "![A trail (Image generated with AI)][r]\n\n[r]: ../images/hero.ai-label.png"),
    ("![trail]\n\n[trail]: ../images/hero.png", "![trail (Image generated with AI)][trail]\n\n[trail]: ../images/hero.ai-label.png"),
], ids=["markdown", "markdown, empty alt", "html", "html, single quotes", "html, no alt", "jsx literal alt",
        "reference-style", "collapsed reference-style"])
def test_apply_points_to_the_copy_and_adds_the_mention(project, before, after):
    original = image(project, "images/hero.png")
    page = write(project, "content/post.md", f"# Trails\n\n{before}\n\nThe end.\n")

    report = apply(project, original, MENTION)

    assert page.read_text() == f"# Trails\n\n{after}\n\nThe end.\n"
    assert report["applied"] and report["alt_updated"] and not report["needs_hand_edit"]


@pytest.mark.parametrize("before, after", [
    ('<img src="hero.png" alt="hero.png">', '<img src="hero.ai-label.png" alt="hero.png (Image generated with AI)">'),
    ('<img src="hero.png" title="hero.png">', '<img alt="Image generated with AI" src="hero.ai-label.png" title="hero.png">'),
    ("![hero.png](hero.png)", "![hero.png (Image generated with AI)](hero.ai-label.png)"),
], ids=["html alt", "html title", "markdown alt"])
def test_apply_treats_a_file_name_in_alt_text_as_text(project, before, after):
    """The image's name written in its alt or title is not a second reference to it."""
    original = image(project, "hero.png")
    page = write(project, "page.md", f"{before}\n")

    report = apply(project, original, MENTION)

    assert page.read_text() == f"{after}\n"
    assert len(report["applied"]) == 1


def test_apply_leaves_a_link_to_the_original_alone(project):
    original = image(project, "images/hero.png")
    page = write(project, "content/post.md", "![A trail](../images/hero.png)\n[full size](../images/hero.png)\n")

    apply(project, original, MENTION)

    assert page.read_text() == (
        "![A trail (Image generated with AI)](../images/hero.ai-label.png)\n[full size](../images/hero.png)\n"
    )


def test_apply_without_a_mention_is_refused_and_changes_nothing(project):
    """The alt mention is half of the step: --apply without --wording or
    --alt-mention would leave every alt silently unchanged."""
    original = image(project, "images/hero.png")
    page = write(project, "content/post.md", "![A trail](../images/hero.png)\n")

    result = references(project, original, "--apply")

    assert result.returncode != 0
    assert result.json["error"]["code"] == "usage"
    assert "--wording" in result.json["error"]["message"] and "--alt-mention" in result.json["error"]["message"]
    assert page.read_text() == "![A trail](../images/hero.png)\n"


def test_a_mention_per_page_wins_over_the_default(project):
    original = image(project, "images/hero.png")
    english = write(project, "en/post.md", "![A trail](../images/hero.png)\n")
    italian = write(project, "it/post.md", "![Un sentiero](../images/hero.png)\n")

    apply(project, original, MENTION, "it/post.md=Immagine generata con IA")

    assert english.read_text() == "![A trail (Image generated with AI)](../images/hero.ai-label.png)\n"
    assert italian.read_text() == "![Un sentiero (Immagine generata con IA)](../images/hero.ai-label.png)\n"


def test_an_alt_that_already_says_ai_is_left_alone(project):
    original = image(project, "images/hero.png")
    page = write(project, "content/post.md", "![An AI illustration of a trail](../images/hero.png)\n")

    report = apply(project, original, MENTION)

    assert page.read_text() == "![An AI illustration of a trail](../images/hero.ai-label.png)\n"
    assert [r["alt"] for r in report["alt_unchanged"]] == ["An AI illustration of a trail"]


@pytest.mark.parametrize("relative, text, kind", [
    ("src/Hero.jsx", 'export const Hero = () => <img src="../images/hero.png" alt={title} />;\n', "html-img"),
    ("index.html", '<picture><source srcset="images/hero.png"><img src="x.png" alt="x"></picture>\n', "html-source"),
], ids=["computed alt", "picture source"])
def test_alts_the_tool_cannot_edit_are_left_to_the_agent(project, relative, text, kind):
    original = image(project, "images/hero.png")
    page = write(project, relative, text)

    report = apply(project, original, MENTION)

    assert [(r["file"], r["kind"]) for r in report["needs_hand_edit"]] == [(relative, kind)]
    assert "hero.ai-label.png" in page.read_text()
    assert MENTION not in page.read_text()


def test_apply_keeps_windows_line_endings(project):
    original = image(project, "images/hero.png")
    page = project / "content" / "post.md"
    page.parent.mkdir(parents=True)
    page.write_bytes(b"# Trails\r\n\r\n![A trail](../images/hero.png)\r\n")

    apply(project, original, MENTION)

    assert page.read_bytes() == b"# Trails\r\n\r\n![A trail (Image generated with AI)](../images/hero.ai-label.png)\r\n"


def test_an_alt_mention_without_apply_is_a_usage_error(project):
    original = image(project, "images/hero.png")
    write(project, "content/post.md", "![A trail](../images/hero.png)\n")

    result = references(project, original, "--alt-mention", MENTION)

    assert result.returncode != 0 and result.json["error"]["code"] == "usage"


def test_a_definition_an_image_and_a_link_share_is_not_updated(project):
    """Pointing it to the copy would make the download link serve the copy too."""
    original = image(project, "hero.png")
    text = "![Photo][hero]\n\n[Download the original][hero]\n\n[hero]: hero.png\n"
    page = write(project, "post.md", text)

    report = apply(project, original, MENTION)

    assert [(r["line"], r["reason"]) for r in report["not_updatable"]] == [(5, "shared")]
    assert page.read_text() == text


def test_a_reference_in_a_markdown_code_block_is_an_example(project):
    original = image(project, "hero.png")
    text = "```markdown\n![Photo](hero.png)\n```\n"
    page = write(project, "post.md", text)

    report = apply(project, original, MENTION)

    assert report["updatable"] == [] and report["not_updatable"] == []
    assert page.read_text() == text


def test_a_custom_element_named_like_a_tag_is_not_a_link(project):
    original = image(project, "hero.png")
    write(project, "page.html", '<a-frame src="hero.png"></a-frame>\n')

    assert [r["kind"] for r in references(project, original).json["updatable"]] == ["other"]


@pytest.mark.parametrize("relative, text", [
    ("src/styles.css", ".hero { background: url(../images/hero.png); }\n"),
    ("src/Hero.jsx", 'import hero from "../images/hero.png";\n'),
    ("notes.md", "The source is images/hero.png, kept for the record.\n"),
], ids=["css url", "import", "prose"])
def test_apply_leaves_other_references_to_the_agent_unchanged(project, relative, text):
    """The tool can't tell whether they show the image (ticket 57)."""
    original = image(project, "images/hero.png")
    page = write(project, relative, text)

    report = apply(project, original, MENTION)

    assert page.read_text() == text
    assert not report["applied"]
    assert [(r["file"], r["kind"]) for r in report["needs_hand_edit"]] == [(relative, "other")]
    assert report["needs_hand_edit"][0]["replacement"].endswith("hero.ai-label.png")
