# Mockdown Reimplementation

## Summary

The goal of this summary is to perform a detailed analysis on the Mockdown codebase so that we can gain an in-depth understanding to re-implement it.

### Mockdown

Mockdown is a tool that synthesizes contraint-based visual layouts from examples.

Specifically, given a hierarchial layout JSON that can be mined from a website's HTML, images, or direct-manipulation editor like Figma, Mockdown aims to generate *layout constraints* that generalize to unseen screen sizes.

For example, a hierarchial layout JSON might look like:
```json
{
  "name": "root",
  "rect": [0, 0, 1200, 800],
  "children": [
    {
      "name": "header",
      "rect": [0, 0, 1200, 80],
      "children": []
    },
    {
      "name": "sidebar",
      "rect": [0, 80, 250, 800],
      "children": []
    },
    {
      "name": "main",
      "rect": [250, 80, 1200, 800],
      "children": []
    }
  ]
}
```
Note that this describes a 1200 x 800 webpage, with a 80 height header and 250 width sidebar.

With multiple examples, the complete layout constraints synthesized by Mockdown might look like:

- `header.height = 80`
- `sidebar.width = 250`
- `sidebar.top = header.bottom + 0`
- `main.top = header.bottom + 0`
- `main.left = sidebar.right + 0`

In general, these constraints always conform to the equation $y=a\times x+b$ where $x$, $y$ are anchors like `header.height` and $a$, $b$ are numeric constants.

Mockdown's pipeline is broken down into two major phases: **local inference** and **global inference**.

#### Local Inference

The goal of local inference is to generate a set of candidate constraints matching the provided examples.

In general, all constraints are instaces of the template $y=a\times x+b$.

However, some constraints are considered ill-formed, such as `sidebar.left = a * main.right` or `sidebar.left = main.width + b`. This is because edge ratios and edge-width relations are not considered realistic and discarded.

> Perhaps we can extend these equations to work with something more similar to CSS flexbox. For example, a child width in a row flexbox with 3 children is equal to `(1/3 * parent.width) - (2 * gap)`.

Another optimization used to prune the set of candidate constraints is the **visibility graph**. Intuitively, components of the UI typically are placed in relation to their immediate parents and neigbors. So any constraints where the pair of components are not parent-child or sibling-sibling are discarded. Additionally, any constraints where an uninterrupted line (not passing through any other anchors) cannot be drawn between the two anchors is discarded.

The template instantiation itself into constraint sketches like `header.height = ?` is one following the method from another paper Daikon.