import webbrowser
from pathlib import Path

import distinctipy
from jinja2 import Template

from src.types import View

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Layout</title>
    <style>
        body {
            margin: 0;
            padding: 16px;
            font-family: monospace;
        }
        .labels {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 16px;
        }
        .label {
            padding: 4px 8px;
            border: 1px solid #333;
            border-radius: 4px;
            cursor: pointer;
            user-select: none;
            font-size: 12px;
        }
        .label:hover {
            background: #eee;
        }
        .viewport {
            position: relative;
            background: #fafafa;
            border: 1px solid #ccc;
        }
        .view {
            position: absolute;
            box-sizing: border-box;
            border: 1px solid #333;
            transition: background-color 0.15s;
        }
    </style>
</head>
<body>
    <div class="labels">
        {% for view in views %}
        <div class="label"
             data-view="{{ view.name }}"
             data-color="{{ view.color }}">
            {{ view.name }}
        </div>
        {% endfor %}
    </div>
    <div class="viewport" style="width: {{ width }}px; height: {{ height }}px;">
        {% for view in views %}
        <div class="view"
             data-name="{{ view.name }}"
             data-color="{{ view.color }}"
             style="left: {{ view.left }}px; 
                    top: {{ view.top }}px; 
                    width: {{ view.width }}px; 
                    height: {{ view.height }}px;">
        </div>
        {% endfor %}
    </div>
    <script>
        document.querySelectorAll('.label').forEach(label => {
            const viewName = label.dataset.view;
            const color = label.dataset.color;
            const viewEl = document.querySelector(`.view[data-name="${viewName}"]`);

            label.addEventListener('mouseenter', () => {
                label.style.backgroundColor = color;
                if (viewEl) viewEl.style.backgroundColor = color;
            });

            label.addEventListener('mouseleave', () => {
                label.style.backgroundColor = '';
                if (viewEl) viewEl.style.backgroundColor = '';
            });
        });
    </script>
</body>
</html>
"""


def visualize(
    layout: View | dict[str, tuple[float, float, float, float]],
    *,
    root_name: str | None = None,
) -> None:
    """
    Visualize a layout by rendering views as HTML and opening in browser.

    Args:
        layout: Either:
            - A View object (root of hierarchy, uses rects from flattened subtree)
            - A dict mapping view name to rect tuple (left, top, right, bottom)
        root_name: Required when layout is a dict. Identifies which view is the root
                   for determining viewport dimensions.
    """
    view_list: list[dict] = []

    if isinstance(layout, View):
        # View hierarchy - use root's dimensions for viewport
        width = int(layout.width)
        height = int(layout.height)
        views = layout._flattened_views_in_subtree
        colors = distinctipy.get_colors(len(views), pastel_factor=0.7)
        for view, color in zip(views, colors, strict=True):
            r, g, b = [int(c * 255) for c in color]
            view_list.append(
                {
                    "name": view.name,
                    "left": view.left,
                    "top": view.top,
                    "width": view.width,
                    "height": view.height,
                    "color": f"rgb({r}, {g}, {b})",
                }
            )
    else:
        # Dict mapping name -> (left, top, right, bottom)
        if root_name is None:
            raise ValueError("root_name is required when layout is a dict")
        root_rect = layout[root_name]
        width = int(root_rect[2] - root_rect[0])  # right - left
        height = int(root_rect[3] - root_rect[1])  # bottom - top
        colors = distinctipy.get_colors(len(layout), pastel_factor=0.7)
        for (name, rect), color in zip(layout.items(), colors, strict=True):
            left, top, right, bottom = rect
            r, g, b = [int(c * 255) for c in color]
            view_list.append(
                {
                    "name": name,
                    "left": left,
                    "top": top,
                    "width": right - left,
                    "height": bottom - top,
                    "color": f"rgb({r}, {g}, {b})",
                }
            )

    # Render HTML
    template: Template = Template(HTML_TEMPLATE)
    html = template.render(width=width, height=height, views=view_list)

    # Create tmp directory if it doesn't exist
    tmp_dir = Path("tmp_html")
    tmp_dir.mkdir(exist_ok=True)

    # Write to local tmp file and open in browser
    output_path = tmp_dir / "layout_visualization.html"
    output_path.write_text(html)

    print(f"Opening visualization at: {output_path.absolute()}")
    webbrowser.open(f"file://{output_path.absolute()}")
