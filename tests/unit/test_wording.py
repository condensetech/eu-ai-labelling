"""The text-label wording comes from label_tool's own table.

`wording` prints the phrases for one language and wording; `snippet` and
`references --apply` use the same table, so the agent never copies a phrase
by hand. The language is what the user asked for (`--lang`), else the
document's declared language. With neither, the agent judges it from context,
asks the user or uses English; with a language outside the table, it writes
the text label itself.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from PIL import Image

from conftest import run_label_tool

TABLE = {
    # language: (document label generated, modified, image generated, modified, icon name)
    "en": ("Generated with AI", "Modified with AI", "Image generated with AI", "Image modified with AI", "AI"),
    "it": ("Generato con IA", "Modificato con IA", "Immagine generata con IA", "Immagine modificata con IA", "IA"),
    "fr": ("Généré par IA", "Modifié par IA", "Image générée par IA", "Image modifiée par IA", "IA"),
    "es": ("Generado con IA", "Modificado con IA", "Imagen generada con IA", "Imagen modificada con IA", "IA"),
    "de": ("Mit KI erstellt", "Mit KI bearbeitet", "Bild mit KI erstellt", "Bild mit KI bearbeitet", "KI"),
}


def wording(*args, cwd: Path | None = None):
    return run_label_tool("wording", *args, cwd=cwd)


@pytest.mark.parametrize("lang", sorted(TABLE))
def test_wording_prints_each_phrase_of_a_listed_language(lang):
    gen, mod, image_gen, image_mod, icon = TABLE[lang]
    for word, label, image_phrase in (("generated", gen, image_gen), ("modified", mod, image_mod)):
        result = wording("--wording", word, "--lang", lang)

        assert result.returncode == 0, result.json
        assert result.json == {
            "language": lang, "language_from": "lang", "wording": word,
            "label": label, "image": image_phrase, "icon_name": icon,
        }


@pytest.mark.parametrize("lang", sorted(TABLE))
def test_every_phrase_uses_its_languages_word_for_ai(lang):
    *phrases, icon = TABLE[lang]
    assert all(re.search(rf"\b{icon}\b", p) for p in phrases)


def test_a_regional_code_uses_its_language():
    assert wording("--wording", "generated", "--lang", "it-IT").json["label"] == "Generato con IA"


def document(folder: Path, name: str, text: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(text)
    return path


@pytest.mark.parametrize("name, text, lang", [
    ("page.html", '<!doctype html>\n<html lang="fr">\n<body><h1>Titre</h1></body></html>\n', "fr"),
    ("post.md", "---\ntitle: Bericht\nlang: de\n---\n\n# Bericht\n", "de"),
    ("post.md", "---\nlanguage: es-ES\n---\n\n# Informe\n", "es"),
], ids=["html lang", "front matter lang", "front matter language"])
def test_the_documents_declared_language_is_used(tmp_path, name, text, lang):
    page = document(tmp_path, name, text)

    result = wording("--wording", "generated", "--document", page)

    assert result.json["language"] == lang
    assert result.json["language_from"] == "document"


def test_what_the_user_asked_for_wins_over_the_document(tmp_path):
    page = document(tmp_path / "content", "page.html", '<html lang="fr"><body></body></html>')

    result = wording("--wording", "generated", "--document", page, "--lang", "es")

    assert (result.json["language"], result.json["language_from"]) == ("es", "lang")


def test_an_unknown_language_asks_for_lang(tmp_path):
    page = document(tmp_path, "post.md", "# Notes\n\nSome text.\n")

    result = wording("--wording", "generated", "--document", page)

    assert result.returncode != 0
    assert result.json["error"]["code"] == "language_unknown"
    message = result.json["error"]["message"]
    assert "--lang" in message and "--label" not in message  # `wording` has no --label
    assert "ask the user" in message and "--lang en" not in message
    assert "textLabelLanguage" not in message


def test_a_language_outside_the_table_asks_for_the_agents_own_translation():
    result = wording("--wording", "generated", "--lang", "pt")

    assert result.returncode != 0
    assert result.json["error"]["code"] == "language_not_listed"
    assert "--label" in result.json["error"]["message"]


# --- snippet: the phrase comes from the table -----------------------------------


def snippet(*args, cwd=None):
    result = run_label_tool("snippet", *args, cwd=cwd)
    assert result.returncode == 0, result.json
    return result.json


def test_a_document_label_takes_the_documents_language(tmp_path):
    page = document(tmp_path, "post.md", "---\nlang: it\n---\n\n# Orari\n")

    result = snippet("--format", "markdown", "--wording", "generated", "--document", page)

    assert result["snippet"].endswith("![IA](assets/ai-basic-black.svg) Generato con IA")
    assert (result["label"], result["language"], result["language_from"]) == ("Generato con IA", "it", "document")


def test_a_caption_uses_the_image_phrasing():
    caption = snippet("--format", "markdown", "--as", "caption", "--wording", "modified", "--lang", "fr")

    assert caption["snippet"].endswith("![IA](assets/ai-basic-black.svg) Image modifiée par IA")


def test_a_caption_in_html_is_a_paragraph_or_a_figcaption_like_a_label():
    caption = snippet("--format", "html", "--as", "caption", "--wording", "generated", "--lang", "en", "--figcaption")

    assert '<figcaption class="eu-ai-label"' in caption["snippet"]
    assert "<span>Image generated with AI</span>" in caption["snippet"]


def test_a_free_text_label_takes_its_icon_name_from_the_table_when_the_language_is_known(tmp_path):
    page = document(tmp_path, "post.md", "---\nlang: it\n---\n\n# Rapporto\n")

    result = snippet("--format", "markdown", "--wording", "generated", "--document", page,
                     "--label", "Questa sezione è generata con IA")

    assert result["snippet"].endswith("![IA](assets/ai-basic-black.svg) Questa sezione è generata con IA")
    assert result["language_from"] == "label"


def test_a_free_text_label_in_another_language_still_needs_its_icon_name():
    ok = snippet("--format", "markdown", "--wording", "generated", "--label", "Gerado com IA", "--icon-name", "IA")
    missing = run_label_tool("snippet", "--format", "markdown", "--wording", "generated", "--label", "Gerado com IA")

    assert ok["snippet"].endswith("![IA](assets/ai-basic-black.svg) Gerado com IA")
    assert missing.returncode != 0 and "--icon-name" in missing.json["error"]["message"]


def test_a_snippet_with_no_language_and_no_label_is_refused(tmp_path):
    result = run_label_tool("snippet", "--format", "html", "--wording", "generated", cwd=tmp_path)

    assert result.returncode != 0
    assert result.json["error"]["code"] == "language_unknown"


# --- references --apply: each page's mention in its own language ----------------


def test_apply_writes_each_pages_mention_in_that_pages_language(tmp_path):
    original = tmp_path / "images" / "hero.png"
    original.parent.mkdir(parents=True)
    Image.new("RGB", (60, 40), (200, 220, 240)).save(original)
    Image.new("RGB", (60, 40), (0, 0, 0)).save(original.with_name("hero.ai-label.png"))
    italian = document(tmp_path / "it", "index.html", '<html lang="it"><body><img src="../images/hero.png" alt="Un sentiero"></body></html>\n')
    german = document(tmp_path / "de", "post.md", "---\nlang: de\n---\n\n![Ein Weg](../images/hero.png)\n")
    unknown = document(tmp_path / "notes", "post.md", "![A trail](../images/hero.png)\n")

    result = run_label_tool("references", original, "--root", tmp_path, "--apply", "--wording", "generated", cwd=tmp_path)

    assert result.returncode == 0, result.json
    assert 'alt="Un sentiero (Immagine generata con IA)"' in italian.read_text()
    assert "![Ein Weg (Bild mit KI erstellt)](../images/hero.ai-label.png)" in german.read_text()
    # Its language is unknown: the path changes, the alt is left for the agent.
    assert unknown.read_text() == "![A trail](../images/hero.ai-label.png)\n"
    hand = [(h["file"], h["reason"]) for h in result.json["needs_hand_edit"]]
    assert len(hand) == 1 and hand[0][0] == "notes/post.md" and "--alt-mention" in hand[0][1]


def test_apply_with_lang_uses_it_for_every_page(tmp_path):
    original = tmp_path / "hero.png"
    Image.new("RGB", (60, 40), (200, 220, 240)).save(original)
    Image.new("RGB", (60, 40), (0, 0, 0)).save(tmp_path / "hero.ai-label.png")
    page = document(tmp_path, "post.md", "![A trail](hero.png)\n")

    run_label_tool("references", original, "--root", tmp_path, "--apply", "--wording", "modified", "--lang", "en", cwd=tmp_path)

    assert page.read_text() == "![A trail (Image modified with AI)](hero.ai-label.png)\n"


def test_an_alt_mention_for_a_page_wins_over_the_table(tmp_path):
    original = tmp_path / "hero.png"
    Image.new("RGB", (60, 40), (200, 220, 240)).save(original)
    Image.new("RGB", (60, 40), (0, 0, 0)).save(tmp_path / "hero.ai-label.png")
    page = document(tmp_path, "post.md", "![Um caminho](hero.png)\n")

    run_label_tool("references", original, "--root", tmp_path, "--apply", "--wording", "generated", "--lang", "en",
                   "--alt-mention", "post.md=Imagem gerada com IA", cwd=tmp_path)

    assert page.read_text() == "![Um caminho (Imagem gerada com IA)](hero.ai-label.png)\n"
