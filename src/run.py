import time
from rich import print

from src.evaluation import calculate_rmsd
from src.instantiation import ConditionalTemplateInstantiator
from src.learning import ConditionalBayesianLearning
from src.logging import setup_logging
from src.pruning import ConditionalHierarchicalPruner
from src.types import View

setup_logging(debug=False)

examples = [
    {
        "name": "root",
        "rect": [0, 0, 1200, 870],
        "children": [
            {
                "name": "authors",
                "rect": [0, 435, 1200, 870],
                "children": [
                    {"name": "author1", "rect": [60, 540, 400, 840]},
                    {"name": "author2", "rect": [430, 540, 770, 840]},
                    {"name": "author3", "rect": [800, 540, 1140, 840]},
                ],
            },
        ],
    },
    # {
    #     "name": "root",
    #     "rect": [0, 0, 1600, 870],
    #     "children": [
    #         {
    #             "name": "authors",
    #             "rect": [0, 435, 1600, 870],
    #             "children": [
    #                 {"name": "author1", "rect": [60, 540, 533.33, 840]},
    #                 {"name": "author2", "rect": [563.33, 540, 1036.66, 840]},
    #                 {"name": "author3", "rect": [1066.66, 540, 1539.99, 840]},
    #             ],
    #         },
    #     ],
    # },
    {
        "name": "root",
        "rect": [0, 0, 500, 1530],
        "children": [
            {
                "name": "authors",
                "rect": [0, 510, 500, 1530],
                "children": [
                    {"name": "author1", "rect": [60, 540, 440, 840]},
                    {"name": "author2", "rect": [60, 870, 440, 1170]},
                    {"name": "author3", "rect": [60, 1200, 440, 1500]},
                ],
            },
        ],
    },
    {
        "name": "root",
        "rect": [0, 0, 400, 1470],
        "children": [
            {
                "name": "authors",
                "rect": [0, 510, 400, 1470],
                "children": [
                    {"name": "author1", "rect": [10, 525, 390, 825]},
                    {"name": "author2", "rect": [10, 840, 390, 1140]},
                    {"name": "author3", "rect": [10, 1155, 390, 1455]},
                ],
            },
        ],
    },
]

views = [View(**example) for example in examples]

# Overall runtime measurement
overall_start = time.perf_counter()

# 1. Conditional Template Instantiation (Conditional Local Inference)
instantiation_start = time.perf_counter()
example_idxs_to_templates_map = ConditionalTemplateInstantiator(
    examples=views
).instantiate()
instantiation_time = time.perf_counter() - instantiation_start

# print(repr(example_idxs_to_templates_map))
print({ind: len(lst) for ind, lst in example_idxs_to_templates_map.items()})

# Debug: Check vertical templates for group (1,2)
if (1, 2) in example_idxs_to_templates_map:
    print("\n=== TEMPLATES FOR GROUP (1,2) ===")
    vertical_templates = [
        t for t in example_idxs_to_templates_map[(1, 2)]
        if t.y.is_vertical() and (t.x is None or t.x.is_vertical())
    ]
    print(f"Total templates: {len(example_idxs_to_templates_map[(1, 2)])}")
    print(f"Vertical templates: {len(vertical_templates)}")
    
    # Check specifically for author top/bottom templates
    author_top_bottom_templates = [
        t for t in vertical_templates
        if 'author' in t.y.view.name and ('top' in t.y.type or 'bottom' in t.y.type)
    ]
    print(f"Author top/bottom templates: {len(author_top_bottom_templates)}")
    print("All author top/bottom templates:")
    for t in author_top_bottom_templates:
        print(f"  {t}")
    
    print("\nSample vertical templates:")
    for t in vertical_templates[:10]:
        print(f"  {t}")

# 2. Conditional Bayesian Learning (Local Inference)
# Debug: Check what happens to author top/bottom templates during learning
if (1, 2) in example_idxs_to_templates_map:
    from src.learning import BayesianLearning
    from collections import defaultdict
    import numpy as np
    
    author_top_bottom_templates = [
        t for t in example_idxs_to_templates_map[(1, 2)]
        if t.y.is_vertical() and (t.x is None or t.x.is_vertical())
        and 'author' in t.y.view.name and ('top' in t.y.type or 'bottom' in t.y.type)
    ]
    
    print("\n=== DEBUGGING AUTHOR TOP/BOTTOM TEMPLATE LEARNING ===")
    set_examples = [views[i] for i in (1, 2)]
    
    # Extract data for one template
    if author_top_bottom_templates:
        template = author_top_bottom_templates[0]
        print(f"\nTemplate: {template}")
        
        anchor_to_data_map = defaultdict(list)
        for example in set_examples:
            for view in example._flattened_views_in_subtree:
                anchor_to_data_map[f"{view.name}.width"].append(view.width)
                anchor_to_data_map[f"{view.name}.height"].append(view.height)
                anchor_to_data_map[f"{view.name}.left"].append(view.left)
                anchor_to_data_map[f"{view.name}.right"].append(view.right)
                anchor_to_data_map[f"{view.name}.top"].append(view.top)
                anchor_to_data_map[f"{view.name}.bottom"].append(view.bottom)
                anchor_to_data_map[f"{view.name}.center_x"].append(view.center_x)
                anchor_to_data_map[f"{view.name}.center_y"].append(view.center_y)
        
        y_data = np.array(
            anchor_to_data_map[f"{template.y.view.name}.{template.y.type}"],
            dtype=float,
        )
        if template.x is None:
            x_data = None
        else:
            x_data = np.array(
                anchor_to_data_map[f"{template.x.view.name}.{template.x.type}"],
                dtype=float,
            )
        
        print(f"Y data: {y_data}")
        if x_data is not None:
            print(f"X data: {x_data}")
        else:
            print("X data: None (constant constraint)")
        
        # Try to learn this template
        from src.learning import TemplateBayesianLinearModel
        from src.config import LearningConfig
        max_dim = max(max(root.width, root.height) for root in set_examples)
        config = LearningConfig(max_offset=int(max_dim) + 10)
        
        try:
            model = TemplateBayesianLinearModel(
                template=template, config=config, y_data=y_data, x_data=x_data
            )
            print(f"Should reject: {model.should_reject()}")
            candidates = model.filter_candidates()
            print(f"Number of candidates: {len(candidates)}")
            if len(candidates) > 0:
                learned = model.learn()
                print(f"Number of learned constraints: {len(learned)}")
                if learned:
                    print(f"Best constraint: {learned[0]}")
            else:
                print("No candidates found in confidence intervals")
        except Exception as e:
            print(f"Error during learning: {e}")
            import traceback
            traceback.print_exc()

learning_start = time.perf_counter()
example_idxs_to_constrs_map = ConditionalBayesianLearning(
    examples=views, seed=42
).learn(example_idxs_to_templates_map)
learning_time = time.perf_counter() - learning_start

# print(repr(example_idxs_to_constrs_map))
print({ind: len(lst) for ind, lst in example_idxs_to_constrs_map.items()})

# Debug: Check vertical constraints for group (1,2) BEFORE pruning
if (1, 2) in example_idxs_to_constrs_map:
    print("\n=== LEARNED CONSTRAINTS FOR GROUP (1,2) (BEFORE PRUNING) ===")
    vertical_constrs = [
        c for c in example_idxs_to_constrs_map[(1, 2)]
        if c.y.is_vertical() and (c.x is None or c.x.is_vertical())
    ]
    print(f"Total constraints: {len(example_idxs_to_constrs_map[(1, 2)])}")
    print(f"Vertical constraints: {len(vertical_constrs)}")
    print("All vertical constraints:")
    for c in vertical_constrs:
        print(f"  {c}")
    
    # Check specifically for author top/bottom constraints
    author_vertical = [
        c for c in vertical_constrs
        if 'author' in c.y.view.name and ('top' in c.y.type or 'bottom' in c.y.type)
    ]
    print(f"\nAuthor top/bottom constraints: {len(author_vertical)}")
    for c in author_vertical:
        print(f"  {c}")

# 3. Conditional Hierarchical Pruning (Global Inference)
pruning_start = time.perf_counter()
outputs = ConditionalHierarchicalPruner(examples=views).prune(
    example_idxs_to_constrs_map
)
pruning_time = time.perf_counter() - pruning_start

# Debug: Check vertical constraints for group (1,2) AFTER pruning
if (1, 2) in outputs:
    print("\n=== PRUNED CONSTRAINTS FOR GROUP (1,2) (AFTER PRUNING) ===")
    vertical_constrs = [
        c for c in outputs[(1, 2)]
        if c.y.is_vertical() and (c.x is None or c.x.is_vertical())
    ]
    print(f"Total constraints: {len(outputs[(1, 2)])}")
    print(f"Vertical constraints: {len(vertical_constrs)}")
    print("All vertical constraints:")
    for c in vertical_constrs:
        print(f"  {c}")
    
    # Check specifically for author top/bottom constraints
    author_vertical = [
        c for c in vertical_constrs
        if 'author' in c.y.view.name and ('top' in c.y.type or 'bottom' in c.y.type)
    ]
    print(f"\nAuthor top/bottom constraints: {len(author_vertical)}")
    for c in author_vertical:
        print(f"  {c}")
    
    # Compare what was pruned
    before = set(example_idxs_to_constrs_map.get((1, 2), []))
    after = set(outputs.get((1, 2), []))
    pruned_vertical = [
        c for c in (before - after)
        if c.y.is_vertical() and (c.x is None or c.x.is_vertical())
        and 'author' in c.y.view.name and ('top' in c.y.type or 'bottom' in c.y.type)
    ]
    print(f"\nPruned author top/bottom constraints: {len(pruned_vertical)}")
    for c in pruned_vertical[:10]:
        print(f"  {c}")

overall_time = time.perf_counter() - overall_start

# Print timing information
print("\n" + "="*60)
print("LATENCY MEASUREMENTS")
print("="*60)
print(f"Overall runtime: {overall_time:.4f}s")
print(f"  - Conditional Local Inference (Template Instantiation): {instantiation_time:.4f}s")
print(f"  - Local Inference (Bayesian Learning): {learning_time:.4f}s")
print(f"  - Global Inference (Hierarchical Pruning): {pruning_time:.4f}s")
print("="*60)

print("\n" + repr(outputs))

# Calculate and print RMSD
rmsd = calculate_rmsd(views, outputs, debug=True)
print("\n" + "="*60)
print("EVALUATION")
print("="*60)
print(f"RMSD: {rmsd:.4f}")
print("="*60)
