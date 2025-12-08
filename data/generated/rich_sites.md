# Rich Layout URLs for Conditional Scraping

These 10 URLs produced multi-element layouts across 6 viewports (3 wide, 3 thin) using `layout_scraper/config_rich.json`. Each example had at least 6 child elements (see min_children below).

1. https://www.wikipedia.org — min_children: 11
2. https://developer.mozilla.org/en-US/ — min_children: 13
3. https://news.ycombinator.com — min_children: 6
4. https://www.bbc.com — min_children: 8
5. https://www.theguardian.com/international — min_children: 11
6. https://www.cnn.com — min_children: 11
7. https://www.theverge.com — min_children: 6
8. https://www.nytimes.com — min_children: 11
9. https://www.mozilla.org — min_children: 7
10. https://www.npr.org — min_children: 13

Generated data (raw + Mockdown format) live in `data/generated/*_{raw,mockdown}.json`, and combined results in `data/generated/all_sites.json`.

## Pipeline compatibility summary
- Works on our pipeline but fails on original Mockdown:
  - bbc (Mockdown crashes on missing anchors; our pipeline succeeds)
  - guardian (Mockdown crashes on missing anchors; our pipeline succeeds)
  - mozilla (Mockdown crashes on missing anchors; our pipeline succeeds)
  - npr (Mockdown crashes on missing anchors; our pipeline succeeds)

- Fails on our pipeline (MaxSMT pruning) — investigate/fallback needed:
  - wikipedia_home (`MaxSMT pruner could not solve for horizontal dimension`)
  - wikipedia (`MaxSMT pruner could not solve for horizontal dimension`)

