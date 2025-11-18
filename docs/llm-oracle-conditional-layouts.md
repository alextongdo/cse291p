# LLM Oracle for Non-Linear Conditional Layouts

## Overview

This document describes a proposed approach to extend Mockdown's constraint synthesis to handle **non-linear conditional layouts** using Large Language Models (LLMs) as heuristic oracles. The system learns responsive breakpoints (e.g., 3-column vs. 2-column layouts based on screen size) and synthesizes conditional constraint systems on a per-view basis.

## Problem Statement

### Current Limitations

Mockdown's current implementation only handles **linear constraints** of the form `y = a·x + b`:
- Constant constraints: `header.height = 80`
- Linear constraints: `child.left = parent.left + 10`
- Multiplicative constraints: `child.width = 0.5 * parent.width`

### Non-Linear Conditional Layouts

Real-world responsive layouts often require:

1. **Breakpoint-Based Structures**: 
   - Desktop (width > 1200px): 3-column layout
   - Tablet (600px < width ≤ 1200px): 2-column layout
   - Mobile (width ≤ 600px): 1-column layout

2. **Conditional Constraints**:
   - `IF root.width > 1200 THEN column1.width = root.width / 3`
   - `IF root.width ≤ 1200 AND root.width > 600 THEN column1.width = root.width / 2`
   - `IF root.width ≤ 600 THEN column1.width = root.width`

3. **Non-Linear Relationships**:
   - Piecewise linear: Different linear constraints in different ranges
   - Threshold-based: Constraints that activate/deactivate at breakpoints
   - View-dependent: Different constraint systems for different view structures

### Challenge

Synthesizing conditional layouts requires:
1. **Breakpoint Detection**: Learning thresholds where layout structure changes
2. **Structure Grouping**: Identifying isomorphic view groups (same structure)
3. **Conditional Constraint Synthesis**: Learning different constraint sets per group
4. **Non-Linear Approximation**: Handling relationships that aren't globally linear

## Proposed Solution: LLM Oracle Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Input: Multiple Examples                  │
│         (Different screen sizes, different structures)      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Step 1: LLM-Guided Breakpoint Detection       │
│  - Analyze view hierarchies across examples               │
│  - Identify structural differences (2-col vs 3-col)       │
│  - Suggest breakpoint thresholds                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         Step 2: Structure Grouping (Isomorphic Sets)       │
│  - Group examples by isomorphic structure                  │
│  - Use existing group_by_isomorphic_structure()            │
│  - Validate LLM-suggested groupings                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│      Step 3: LLM-Guided Constraint Pattern Detection       │
│  - For each structure group, analyze layout patterns       │
│  - Suggest constraint templates (linear, piecewise)     │
│  - Identify view-specific constraint relationships         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│        Step 4: Conditional Constraint Synthesis            │
│  - Learn constraints per structure group                   │
│  - Use existing Bayesian learning for linear parts         │
│  - Use LLM for non-linear approximations                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         Step 5: Max-SMT with Conditional Constraints       │
│  - Encode conditional constraints: IF structure THEN ...  │
│  - Use existing HierarchicalPruner with modifications     │
│  - Solve for each structure group separately              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Output: Conditional Constraint System         │
│  - Breakpoint thresholds                                   │
│  - Per-structure constraint sets                           │
│  - Conditional activation rules                           │
└─────────────────────────────────────────────────────────────┘
```

## Detailed Component Design

### Component 1: LLM-Guided Breakpoint Detection

#### How It Works

The LLM analyzes view hierarchies across examples to identify breakpoint thresholds:

```python
class LLMBreakpointDetector:
    def __init__(self, model="gpt-4"):
        self.model = model
    
    def detect_breakpoints(self, examples: List[IView[NT]]) -> List[Breakpoint]:
        """Detect screen size breakpoints where layout structure changes.
        
        Args:
            examples: List of view hierarchies at different screen sizes
            
        Returns:
            List of Breakpoint objects with threshold values
        """
        # Extract view structure and screen sizes
        example_data = []
        for ex in examples:
            example_data.append({
                'width': ex.width,
                'height': ex.height,
                'structure': self._extract_structure(ex),
                'num_children': len(ex.children),
                'child_names': [c.name for c in ex.children]
            })
        
        # Build prompt for LLM
        prompt = self._build_breakpoint_prompt(example_data)
        
        # Call LLM
        response = self._call_llm(prompt)
        
        # Parse breakpoints from response
        breakpoints = self._parse_breakpoints(response)
        
        # Validate breakpoints against examples
        validated = self._validate_breakpoints(breakpoints, examples)
        
        return validated
    
    def _extract_structure(self, view: IView[NT]) -> Dict:
        """Extract structural signature of view hierarchy."""
        def recurse(v: IView[NT]) -> Dict:
            return {
                'name': v.name,
                'num_children': len(v.children),
                'children': [recurse(c) for c in v.children]
            }
        return recurse(view)
    
    def _build_breakpoint_prompt(self, example_data: List[Dict]) -> str:
        """Build prompt for LLM breakpoint detection."""
        return f"""
You are analyzing responsive layout examples to detect breakpoint thresholds.

Given these layout examples at different screen sizes:
{json.dumps(example_data, indent=2)}

Identify breakpoint thresholds where the layout structure changes significantly.
For example:
- Desktop: width > 1200px (3 columns)
- Tablet: 600px < width ≤ 1200px (2 columns)  
- Mobile: width ≤ 600px (1 column)

Consider:
1. Changes in number of children (columns, rows)
2. Changes in view hierarchy structure
3. Common responsive design breakpoints (768px, 1024px, 1200px)

Return JSON array of breakpoints:
[
  {{"threshold": 1200, "dimension": "width", "direction": ">", "structure": "3-column"}},
  {{"threshold": 600, "dimension": "width", "direction": ">", "structure": "2-column"}}
]
"""
```

#### Why It Works

1. **Pattern Recognition**: LLMs excel at recognizing patterns in structured data
2. **Domain Knowledge**: LLMs have knowledge of common responsive design patterns
3. **Contextual Analysis**: Can analyze multiple examples simultaneously to find patterns
4. **Heuristic Guidance**: Provides initial breakpoint guesses that can be refined

#### Integration with Existing Code

- **Input**: Uses existing `IView[NT]` structure
- **Output**: `Breakpoint` objects that can be used for grouping
- **Validation**: Validates against actual examples to ensure correctness

---

### Component 2: Structure Grouping with LLM Validation

#### How It Works

Extend existing `group_by_isomorphic_structure()` to use LLM for validation and refinement:

```python
class LLMStructureGrouper:
    def __init__(self, model="gpt-4"):
        self.model = model
    
    def group_with_llm_validation(self, examples: List[IView[NT]], 
                                   breakpoints: List[Breakpoint]) -> List[List[IView[NT]]]:
        """Group examples by structure with LLM validation.
        
        Uses existing group_by_isomorphic_structure() but validates
        and refines groupings using LLM analysis.
        """
        # Use existing grouping function
        initial_groups = group_by_isomorphic_structure(examples)
        
        # LLM validates and refines groups
        for group_idx, group in enumerate(initial_groups):
            # Extract group characteristics
            group_data = self._analyze_group(group)
            
            # LLM checks if grouping makes sense
            prompt = self._build_validation_prompt(group_data, breakpoints)
            validation = self._call_llm(prompt)
            
            if not validation['is_valid']:
                # LLM suggests corrections
                corrected = self._apply_corrections(group, validation['suggestions'])
                initial_groups[group_idx] = corrected
        
        return initial_groups
    
    def _analyze_group(self, group: List[IView[NT]]) -> Dict:
        """Analyze characteristics of a structure group."""
        return {
            'size': len(group),
            'screen_sizes': [(ex.width, ex.height) for ex in group],
            'structure': self._extract_structure(group[0]),
            'variations': self._find_variations(group)
        }
    
    def _build_validation_prompt(self, group_data: Dict, breakpoints: List[Breakpoint]) -> str:
        """Build prompt for LLM validation."""
        return f"""
You are validating structure groupings for responsive layouts.

Group characteristics:
{json.dumps(group_data, indent=2)}

Breakpoints:
{json.dumps([bp.to_dict() for bp in breakpoints], indent=2)}

Does this grouping make sense? Consider:
1. Do all examples in the group have the same structure?
2. Are screen sizes consistent with breakpoints?
3. Are there examples that should be in different groups?

Return JSON:
{{"is_valid": true/false, "suggestions": ["move example X to group Y", ...]}}
"""
```

#### Why It Works

1. **Validation**: LLM can catch grouping errors that pure isomorphism might miss
2. **Context Awareness**: Considers screen sizes and breakpoints, not just structure
3. **Refinement**: Suggests corrections for misgrouped examples
4. **Hybrid Approach**: Combines algorithmic grouping with LLM validation

#### Integration with Existing Code

- **Uses Existing Function**: Calls `group_by_isomorphic_structure()` from `evaluation/metrics.py`
- **Extends Functionality**: Adds validation and refinement layer
- **Preserves Interface**: Returns same format (List[List[IView[NT]]])

---

### Component 3: LLM-Guided Constraint Pattern Detection

#### How It Works

For each structure group, the LLM analyzes layout patterns and suggests constraint templates:

```python
class LLMConstraintPatternDetector:
    def __init__(self, model="gpt-4"):
        self.model = model
    
    def detect_patterns(self, group: List[IView[NT]], 
                        breakpoint: Breakpoint) -> List[ConstraintPattern]:
        """Detect constraint patterns for a structure group.
        
        Args:
            group: Examples with same structure
            breakpoint: Breakpoint threshold for this group
            
        Returns:
            List of suggested constraint patterns
        """
        # Analyze layout relationships in group
        analysis = self._analyze_layout_relationships(group)
        
        # Build prompt for LLM
        prompt = self._build_pattern_prompt(analysis, breakpoint)
        
        # Call LLM
        response = self._call_llm(prompt)
        
        # Parse constraint patterns
        patterns = self._parse_patterns(response)
        
        return patterns
    
    def _analyze_layout_relationships(self, group: List[IView[NT]]) -> Dict:
        """Analyze spatial relationships in layout examples."""
        relationships = []
        
        for ex in group:
            # Extract key relationships
            rels = {
                'parent_child': self._extract_parent_child_rels(ex),
                'sibling': self._extract_sibling_rels(ex),
                'alignment': self._extract_alignment_rels(ex),
                'spacing': self._extract_spacing_rels(ex)
            }
            relationships.append(rels)
        
        return {
            'relationships': relationships,
            'common_patterns': self._find_common_patterns(relationships)
        }
    
    def _build_pattern_prompt(self, analysis: Dict, breakpoint: Breakpoint) -> str:
        """Build prompt for LLM pattern detection."""
        return f"""
You are analyzing layout patterns to suggest constraint templates.

Layout relationships:
{json.dumps(analysis, indent=2)}

Breakpoint: {breakpoint.threshold}px ({breakpoint.structure})

Suggest constraint patterns that govern this layout. Consider:

1. **Linear Constraints** (y = a*x + b):
   - Constant: header.height = 80
   - Offset: child.left = parent.left + 10
   - Proportional: child.width = 0.5 * parent.width

2. **Piecewise Linear** (different linear constraints in different ranges):
   - IF width > 1000: column.width = width / 3
   - IF width ≤ 1000: column.width = width / 2

3. **Conditional Constraints** (activate based on conditions):
   - IF width > breakpoint: use 3-column layout
   - IF width ≤ breakpoint: use 2-column layout

4. **View-Specific Constraints**:
   - Different constraints for different view types
   - Container views vs. content views

Return JSON array of constraint patterns:
[
  {{
    "type": "linear",
    "template": "column1.width = root.width / 3",
    "views": ["column1", "root"],
    "confidence": 0.9
  }},
  {{
    "type": "piecewise",
    "condition": "root.width > 1200",
    "then": "column1.width = root.width / 3",
    "else": "column1.width = root.width / 2",
    "confidence": 0.8
  }}
]
"""
```

#### Why It Works

1. **Pattern Recognition**: LLMs can identify common layout patterns (grids, flexbox-like, etc.)
2. **Template Suggestion**: Suggests constraint templates that match observed patterns
3. **Non-Linear Handling**: Can suggest piecewise linear and conditional constraints
4. **Confidence Scores**: Provides confidence scores for suggested patterns

#### Integration with Existing Code

- **Input**: Uses existing `IView[NT]` structure
- **Output**: `ConstraintPattern` objects that can be converted to `IConstraint` templates
- **Compatibility**: Patterns can be fed into existing Bayesian learning pipeline

---

### Component 4: Conditional Constraint Synthesis

#### How It Works

Synthesize constraints for each structure group, then combine into conditional system:

```python
class ConditionalConstraintSynthesizer:
    def __init__(self, llm_oracle: LLMConstraintPatternDetector):
        self.llm_oracle = llm_oracle
    
    def synthesize_conditional(self, 
                               structure_groups: List[List[IView[NT]]],
                               breakpoints: List[Breakpoint]) -> ConditionalConstraintSystem:
        """Synthesize conditional constraint system.
        
        Args:
            structure_groups: Groups of examples with same structure
            breakpoints: Breakpoint thresholds
            
        Returns:
            ConditionalConstraintSystem with per-group constraints
        """
        conditional_constraints = []
        
        for group_idx, group in enumerate(structure_groups):
            breakpoint = breakpoints[group_idx] if group_idx < len(breakpoints) else None
            
            # Get LLM-suggested patterns
            patterns = self.llm_oracle.detect_patterns(group, breakpoint)
            
            # Convert patterns to constraint templates
            templates = self._patterns_to_templates(patterns)
            
            # Use existing Bayesian learning for linear constraints
            from cse291p.pipeline.bayes.noisetolerant import NoiseTolerantLearning
            learner = NoiseTolerantLearning(templates=templates, samples=group, config=...)
            candidates = learner.learn()
            
            # Use existing Max-SMT solving
            from cse291p.pipeline.hierarchical_decomp import HierarchicalPruner
            pruner = HierarchicalPruner(group, bounds=..., solve_unambig=False)
            constraints = pruner(candidates)[0]
            
            # Create conditional constraint set
            conditional_set = ConditionalConstraintSet(
                condition=breakpoint.to_condition(),
                constraints=constraints,
                structure_group=group_idx
            )
            conditional_constraints.append(conditional_set)
        
        return ConditionalConstraintSystem(
            breakpoints=breakpoints,
            constraint_sets=conditional_constraints
        )
    
    def _patterns_to_templates(self, patterns: List[ConstraintPattern]) -> List[IConstraint]:
        """Convert LLM-suggested patterns to constraint templates."""
        templates = []
        
        for pattern in patterns:
            if pattern.type == "linear":
                # Convert to existing IConstraint template
                template = self._parse_linear_template(pattern.template)
                templates.append(template)
            elif pattern.type == "piecewise":
                # Create conditional template
                template = self._create_piecewise_template(pattern)
                templates.append(template)
            # ... handle other pattern types ...
        
        return templates
```

#### Why It Works

1. **Reuses Existing Pipeline**: Uses existing Bayesian learning and Max-SMT solving
2. **LLM Guides Template Generation**: LLM suggests patterns, existing code learns parameters
3. **Per-Group Synthesis**: Each structure group gets its own constraint set
4. **Conditional Combination**: Combines groups into conditional system

#### Integration with Existing Code

- **Uses Existing Learners**: `NoiseTolerantLearning` for parameter inference
- **Uses Existing Pruners**: `HierarchicalPruner` for Max-SMT solving
- **Extends Output**: Adds conditional structure to constraint system

---

### Component 5: Max-SMT with Conditional Constraints

#### How It Works

Extend existing Max-SMT solving to handle conditional constraints:

```python
class ConditionalMaxSMTSolver:
    def solve_conditional(self, 
                         conditional_system: ConditionalConstraintSystem,
                         target_view: IView[NT]) -> List[IConstraint]:
        """Solve Max-SMT with conditional constraints.
        
        Encodes: IF structure_group THEN constraints
        """
        from z3 import z3
        
        solver = z3.Optimize()
        
        # For each structure group, create conditional constraints
        for group_idx, constraint_set in enumerate(conditional_system.constraint_sets):
            # Create boolean variable for group activation
            group_active = z3.Bool(f"group_{group_idx}_active")
            
            # Encode breakpoint condition
            breakpoint = conditional_system.breakpoints[group_idx]
            condition = self._breakpoint_to_z3(breakpoint, target_view)
            
            # IF condition THEN group_active
            solver.add(z3.Implies(condition, group_active))
            
            # IF group_active THEN constraints
            for constraint in constraint_set.constraints:
                constraint_expr = constraint_to_z3_expr(constraint, 0)
                solver.add(z3.Implies(group_active, constraint_expr))
        
        # Solve Max-SMT (maximize number of satisfied constraints)
        # ... existing Max-SMT logic ...
        
        return solved_constraints
    
    def _breakpoint_to_z3(self, breakpoint: Breakpoint, view: IView[NT]) -> z3.BoolRef:
        """Convert breakpoint condition to Z3 expression."""
        if breakpoint.dimension == "width":
            var = anchor_id_to_z3_var(view.width_anchor.id, 0)
        else:  # height
            var = anchor_id_to_z3_var(view.height_anchor.id, 0)
        
        if breakpoint.direction == ">":
            return var > breakpoint.threshold
        else:  # <=
            return var <= breakpoint.threshold
```

#### Why It Works

1. **Z3 Supports Conditionals**: Z3 can encode `IF condition THEN constraint`
2. **Max-SMT Handles Soft Constraints**: Can maximize satisfied constraints across groups
3. **Breakpoint Encoding**: Breakpoints become Z3 conditions on view dimensions
4. **Reuses Existing Logic**: Extends existing Z3 integration

#### Integration with Existing Code

- **Uses Existing Z3 Integration**: `constraint_to_z3_expr()` from `integration/z3.py`
- **Extends Solver**: Adds conditional encoding to existing Max-SMT
- **Compatible Output**: Returns same `List[IConstraint]` format

---

## Example: 3-Column to 2-Column Responsive Layout

### Input Examples

```python
examples = [
    # Desktop: 1920x1080, 3 columns
    View(name="root", rect=[0, 0, 1920, 1080], children=[
        View(name="col1", rect=[0, 0, 640, 1080], children=[]),
        View(name="col2", rect=[640, 0, 1280, 1080], children=[]),
        View(name="col3", rect=[1280, 0, 1920, 1080], children=[])
    ]),
    # Tablet: 768x1024, 2 columns
    View(name="root", rect=[0, 0, 768, 1024], children=[
        View(name="col1", rect=[0, 0, 384, 1024], children=[]),
        View(name="col2", rect=[384, 0, 768, 1024], children=[])
    ]),
    # Mobile: 375x667, 1 column
    View(name="root", rect=[0, 0, 375, 667], children=[
        View(name="col1", rect=[0, 0, 375, 667], children=[])
    ])
]
```

### LLM Analysis

1. **Breakpoint Detection**:
   - LLM identifies: `width > 1200` → 3 columns, `width ≤ 1200 AND width > 600` → 2 columns, `width ≤ 600` → 1 column

2. **Structure Grouping**:
   - Group 0: Desktop example (3 columns)
   - Group 1: Tablet example (2 columns)
   - Group 2: Mobile example (1 column)

3. **Pattern Detection**:
   - Group 0: `col1.width = root.width / 3`, `col2.left = col1.right`, etc.
   - Group 1: `col1.width = root.width / 2`, `col2.left = col1.right`, etc.
   - Group 2: `col1.width = root.width`

### Synthesized Conditional Constraints

```python
conditional_system = ConditionalConstraintSystem(
    breakpoints=[
        Breakpoint(threshold=1200, dimension="width", direction=">", structure="3-column"),
        Breakpoint(threshold=600, dimension="width", direction=">", structure="2-column")
    ],
    constraint_sets=[
        ConditionalConstraintSet(
            condition="root.width > 1200",
            constraints=[
                LinearConstraint(y_id="col1.width", x_id="root.width", a=1/3, b=0),
                LinearConstraint(y_id="col2.left", x_id="col1.right", a=1, b=0),
                # ... more constraints
            ]
        ),
        ConditionalConstraintSet(
            condition="root.width > 600 AND root.width <= 1200",
            constraints=[
                LinearConstraint(y_id="col1.width", x_id="root.width", a=1/2, b=0),
                LinearConstraint(y_id="col2.left", x_id="col1.right", a=1, b=0),
                # ... more constraints
            ]
        ),
        ConditionalConstraintSet(
            condition="root.width <= 600",
            constraints=[
                LinearConstraint(y_id="col1.width", x_id="root.width", a=1, b=0),
                # ... more constraints
            ]
        )
    ]
)
```

---

## Why This Approach Works

### LLM Strengths

1. **Pattern Recognition**: LLMs excel at recognizing layout patterns across examples
2. **Domain Knowledge**: Have knowledge of responsive design patterns
3. **Heuristic Guidance**: Provide good initial guesses for breakpoints and patterns
4. **Non-Linear Handling**: Can suggest piecewise linear and conditional constraints

### Hybrid Approach Benefits

1. **LLM for Heuristics**: LLM provides initial guesses and pattern suggestions
2. **Existing Code for Precision**: Existing Bayesian learning and Max-SMT provide precise parameter inference
3. **Best of Both Worlds**: Combines LLM creativity with algorithmic precision

### Safety and Correctness

1. **Validation**: LLM suggestions are validated against examples
2. **Fallback**: Can fall back to existing linear synthesis if LLM fails
3. **Incremental**: Can enable LLM features gradually
4. **Compatible**: Output format compatible with existing evaluation

---

## Integration Points

### Existing Code Reused

1. **Structure Grouping**: `group_by_isomorphic_structure()` from `evaluation/metrics.py`
2. **Bayesian Learning**: `NoiseTolerantLearning` from `pipeline/bayes/noisetolerant/`
3. **Max-SMT Solving**: `HierarchicalPruner` and `BlackBoxPruner` from `pipeline/hierarchical_decomp/`
4. **Z3 Integration**: `constraint_to_z3_expr()` from `pipeline/integration/z3.py`
5. **Evaluation**: `evaluate_layouts()` from `evaluation/metrics.py` (already supports conditional)

### New Components

1. **LLMBreakpointDetector**: Detects breakpoint thresholds
2. **LLMStructureGrouper**: Validates and refines structure groupings
3. **LLMConstraintPatternDetector**: Suggests constraint patterns
4. **ConditionalConstraintSynthesizer**: Synthesizes conditional constraint system
5. **ConditionalMaxSMTSolver**: Solves Max-SMT with conditional constraints

---

## Expected Benefits

### Capabilities

1. **Responsive Layouts**: Handles breakpoint-based responsive designs
2. **Non-Linear Constraints**: Supports piecewise linear and conditional constraints
3. **Structure Variations**: Handles layouts with different structures at different screen sizes

### Quality

1. **LLM Guidance**: LLM provides good initial guesses, reducing search space
2. **Precise Learning**: Existing Bayesian learning provides precise parameter inference
3. **Validation**: LLM suggestions validated against examples

### Runtime

1. **Reduced Search Space**: LLM guidance reduces constraint candidate space
2. **Parallel Processing**: Can process structure groups in parallel
3. **Early Termination**: Can terminate early if LLM confidence is high

---

## Implementation Strategy

### Phase 1: LLM Oracle Infrastructure

1. Create `LLMBreakpointDetector` class
2. Create `LLMStructureGrouper` class
3. Create `LLMConstraintPatternDetector` class
4. Add LLM API integration (OpenAI, Anthropic, etc.)

### Phase 2: Conditional Synthesis

1. Create `ConditionalConstraintSynthesizer` class
2. Extend existing learners to handle conditional templates
3. Add conditional constraint data structures

### Phase 3: Conditional Max-SMT

1. Create `ConditionalMaxSMTSolver` class
2. Extend Z3 integration for conditional constraints
3. Update `HierarchicalPruner` to handle conditionals

### Phase 4: Evaluation and Tuning

1. Test on responsive layout examples
2. Measure accuracy vs. existing linear synthesis
3. Tune LLM prompts and validation logic

---

## Summary

This approach extends Mockdown to handle **non-linear conditional layouts** by:

1. **Using LLMs as Heuristic Oracles**: LLMs provide initial guesses for breakpoints, patterns, and groupings
2. **Reusing Existing Pipeline**: Existing Bayesian learning and Max-SMT solving provide precise inference
3. **Hybrid Approach**: Combines LLM creativity with algorithmic precision
4. **Incremental Integration**: Can be added gradually without breaking existing functionality

The key insight: **LLMs excel at pattern recognition and heuristic guidance**, while **existing algorithms excel at precise parameter inference**, so combining them provides the best of both worlds for handling complex responsive layouts.

