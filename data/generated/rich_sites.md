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

## Latest conditional results (manual_cnn.json, Desktop Standard removed)
- Avg RMSD: 0.7810
- Avg ACC: 0.4000
- Per-view RMSD/ACC:
  - Desktop Large: 0.0000 / 1.0000
  - Tablet Landscape: 0.6847 / 0.2500
  - Desktop Large Copy: 0.0000 / 1.0000
  - Tablet Landscape Copy: 0.6847 / 0.2500
  - Mobile Large: 1.2809 / 0.2500
  - Mobile Medium: 1.2809 / 0.2500
  - Mobile Small: 1.2809 / 0.2500
  - Mobile Large Variant: 0.4146 / 0.3750
  - Mobile Medium Variant: 0.9843 / 0.1250
  - Mobile Small Variant: 1.1990 / 0.2500

## Prepared local HTML set (current selection)
- arcgis.com (`arcgis_prepared.json`)
- bestbuy.com (`bestbuy_prepared.json`)
- bluehost.com (`bluehost_prepared.json`)
- epicgames.com (`epicgames_prepared.json`)
- gmail.com (`gmail_prepared.json`)
- google.com (`google_prepared.json`)
- openx.com (`openx_prepared.json`)
- shutterstock.com (`shutterstock_prepared.json`)
- manual CNN reference (`manual_cnn.json`) — unchanged reference set

## Latest evaluation (train: h0,h1,v0,v1; val: h2,v2; depth 4, no jitter)
Average over 9 sites:
- Mockdown — avg RMSD 182.83, avg ACC 0.428
- Conditional Mockdown — avg RMSD 2.826, avg ACC 0.700

Per-site (val RMSD / ACC):
- arcgis: Mockdown 132.70 / 0.714, Conditional 0.453 / 0.857
- bestbuy: Mockdown 123.14 / 0.444, Conditional 0.161 / 1.000
- bluehost: Mockdown 200.10 / 0.417, Conditional 0.235 / 1.000
- epicgames: Mockdown 82.31 / 0.889, Conditional 0.299 / 1.000
- gmail: Mockdown 292.37 / 0.444, Conditional 0.241 / 0.778
- google: Mockdown 183.44 / 0.154, Conditional 13.889 / 0.500
- manual_cnn: Mockdown 276.62 / 0.325, Conditional 0.781 / 0.400
- openx: Mockdown 118.49 / 0.000, Conditional 8.986 / 0.000
- shutterstock: Mockdown 236.33 / 0.462, Conditional 0.385 / 0.769

