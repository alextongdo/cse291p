#!/usr/bin/env python3
"""
Prune scraped mockdown JSON to keep only a curated set of view names per site.

Usage:
    uv run python3 scripts/prune_views.py data/generated/cnn_mockdown.json --site cnn

If no --site is given, tries to infer from filename prefix before "_mockdown".
Output overwrites the input file by default; use --out to write elsewhere.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Set


SITE_KEEP: Dict[str, Set[str]] = {
    "bbc": {
        "body", "header", "main", "footer", "nav",
        ".gs-container", ".nw-c-top-stories", ".nw-o-news-wide-navigation",
        ".nw-c-nav__wide", ".nw-c-promo", ".nw-c-most-read",
        "section[data-entityid]", "section[role='region']",
    },
    "guardian": {
        "body", "header", "main", "footer", "nav",
        ".pillars", ".content__main", ".content__secondary", ".l-side-margins",
        ".fc-container", ".fc-item", ".fc-item__content", ".fc-item__title",
        ".front-page", "section[id^='news']", "section[id^='most-']",
    },
    "cnn": {
        "body", "header", "main", "footer", "nav",
        ".page", ".l-container", ".container", ".zone", ".zn",
        ".subnav__section", ".subnav__section-link", ".subnav__subsection",
        ".subnav__subsection-link",
        ".cd__wrapper", ".cd__content", ".cd__headline", ".cd__headline-text",
        ".cd__description", ".cd__img", ".media", ".media__image",
        ".card",
        ".container__item", ".container__headline", ".container__headline-text",
        ".container__text", ".container__item-media-wrapper", ".container__item-media",
    },
    "npr": {
        "body", "header", "main", "footer", "nav",
        "section", "article", "aside",
        ".story-wrap", ".story-text", ".bucketwrap",
        ".playlist-item", ".playlist-thumbnail-wrapper",
        ".audio-module", ".imagewrap", ".story-link",
    },
    "nytimes": {
        "body", "header", "main", "footer", "nav", "#site-content",
        "section[name]", "section[data-block-tracking-id]", "article",
        ".story-wrapper", ".css-1ez5fsm", ".css-13mho3u",
        ".css-1l4spti", ".css-kz1pwz", ".container-margin",
    },
    "theverge": {
        "body", "header", "main", "footer", "nav",
        "[class*='duet--layout--river']", "[class*='duet--content-cards']",
        ".duet--content-cards--content-card", ".duet--content-cards--quick-post",
        ".c-entry-box--compact", ".l-col__main", ".l-col__sidebar", ".c-feature-grid",
    },
    "mdn": {
        "body", "header", "main", "footer", "nav",
        ".main-page-content", ".document", "article", ".sidebar", ".toc",
        ".page-header", ".callout", ".code-example", ".card",
    },
    "mozilla": {
        "body", "header", "main", "footer", "nav",
        "#outer-wrapper", "#content", ".mzp-c-hero", ".mzp-c-card",
        ".mzp-c-picto", ".mzp-l-content", ".mzp-l-card-third",
        ".mzp-c-billboard", ".mzp-c-call-out", ".mzp-c-newsletter",
    },
    "hackernews": {
        "body", "#hnmain", "table", "tr.athing", ".title", ".subtext", ".morelink",
    },
    "wikipedia": {
        "body", "header", "main", "footer",
        ".central-textlogo", ".search-container", "#searchInput",
        ".lang-list-container", ".other-projects", ".footer", "form", "button",
        ".central-featured", ".central-featured-lang",
        ".other-projects-list", ".other-projects-list li",
    },
}


def load_examples(path: Path):
    data = json.load(open(path))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "examples" in data:
            return data["examples"]
        if "train" in data:
            return data["train"]
    raise ValueError(f"Unsupported format in {path}")


def save_examples(path: Path, examples):
    with open(path, "w") as f:
        json.dump({"examples": examples}, f, indent=2)
        f.write("\n")


def area(v: dict[str, Any]) -> float:
    l, t, r, b = v.get("rect", [0, 0, 0, 0])
    return max(0.0, r - l) * max(0.0, b - t)


def filter_tree(
    v: dict[str, Any],
    keep: Set[str],
    top_names: Set[str],
    root_area: float,
    min_frac: float,
) -> dict[str, Any] | None:
    name = v.get("name")
    children = v.get("children", []) or []
    kept_children = []
    for c in children:
        fc = filter_tree(c, keep, top_names, root_area, min_frac)
        if fc:
            kept_children.append(fc)
    # keep if name in allow list, or in top_names, or area large enough, or any child kept
    big_enough = area(v) >= min_frac * root_area
    if name in keep or name in top_names or big_enough or kept_children:
        nv = dict(v)
        nv["children"] = kept_children
        return nv
    return None


def infer_site(path: Path) -> str | None:
    stem = path.stem
    if stem.endswith("_mockdown"):
        stem = stem[:-9]
    return stem if stem in SITE_KEEP else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--site", type=str, help="site key for keep list")
    ap.add_argument("--top-k", type=int, default=200, help="force-keep top-k largest views by area")
    ap.add_argument("--min-frac", type=float, default=0.0, help="keep any view with area >= frac*root_area")
    ap.add_argument("--ignore-allow-list", action="store_true", help="ignore SITE_KEEP; keep any name")
    args = ap.parse_args()

    site = args.site or infer_site(args.input)
    if not site or (site not in SITE_KEEP and not args.ignore_allow_list):
        raise SystemExit(f"Unknown site; provide --site. Known: {list(SITE_KEEP)}")
    keep = SITE_KEEP.get(site, set())

    examples = load_examples(args.input)
    pruned = []
    for ex in examples:
        # compute top-k by area
        all_views = []
        stack = [ex]
        while stack:
            v = stack.pop()
            all_views.append(v)
            stack.extend(v.get("children", []) or [])
        top_sorted = sorted(all_views, key=area, reverse=True)[: args.top_k]
        top_names = {v.get("name") for v in top_sorted if v.get("name")}
        if args.ignore_allow_list:
            keep = {v.get("name") for v in all_views if v.get("name")}
        root_a = max(area(ex), 1.0)

        kept = filter_tree(ex, keep, top_names, root_a, args.min_frac)
        if kept:
            pruned.append(kept)
    out_path = args.out or args.input
    save_examples(out_path, pruned)
    print(f"pruned {args.input} -> {out_path} (kept {len(pruned)} examples)")


if __name__ == "__main__":
    main()

