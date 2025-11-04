"""Script to parse and display synthesis output.

Reimplements:
- Utility for reading and displaying synthesis results from JSON output
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click


def format_constraint(c: Dict[str, str]) -> str:
    """Format a constraint dictionary into a human-readable string."""
    y = c.get('y', '')
    op = c.get('op', '=')
    kind = c.get('kind', 'unknown')
    
    # Constant constraint: y = b
    if 'x' not in c or not c.get('x'):
        b = c.get('b', '0')
        return f"{y} {op} {b}  [{kind}]"
    
    # Linear constraint: y = a * x + b
    a = c.get('a', '1')
    x = c.get('x', '')
    b = c.get('b', '0')
    
    # Format multiplier
    if a == '1':
        a_str = ''
    elif '/' in a:
        # Rational number
        a_str = f"{a} * "
    else:
        a_str = f"{a} * "
    
    # Format constant
    if b == '0':
        b_str = ''
    elif b.startswith('-'):
        b_str = f" - {b[1:]}"
    else:
        b_str = f" + {b}"
    
    # Build expression
    if a_str and b_str:
        expr = f"{a_str}{x}{b_str}"
    elif a_str:
        expr = f"{a_str}{x}"
    elif b_str:
        expr = f"{x}{b_str}"
    else:
        expr = x
    
    strength = c.get('strength', 'required')
    return f"{y} {op} {expr}  [{kind}, {strength}]"


def parse_output(output_data: Dict[str, Any]) -> None:
    """Parse and display synthesis output."""
    constraints = output_data.get('constraints', [])
    axioms = output_data.get('axioms', [])
    valuations_min = output_data.get('valuations_min', {})
    valuations_max = output_data.get('valuations_max', {})
    
    print("=" * 80)
    print("SYNTHESIS OUTPUT")
    print("=" * 80)
    
    # Display constraints
    if constraints:
        print(f"\nConstraints ({len(constraints)}):")
        print("-" * 80)
        for i, c in enumerate(constraints, 1):
            print(f"{i:3d}. {format_constraint(c)}")
    else:
        print("\nNo constraints synthesized.")
    
    # Display axioms if present
    if axioms:
        print(f"\nAxioms ({len(axioms)}):")
        print("-" * 80)
        for i, axiom in enumerate(axioms, 1):
            print(f"{i:3d}. {axiom}")
    
    # Display valuations if present
    if valuations_min or valuations_max:
        print("\nModel Valuations:")
        print("-" * 80)
        
        # Get all anchor IDs
        all_anchors = set(valuations_min.keys()) | set(valuations_max.keys())
        
        if all_anchors:
            print(f"{'Anchor':<30} {'Min':<20} {'Max':<20}")
            print("-" * 80)
            for anchor in sorted(all_anchors):
                min_val = valuations_min.get(anchor, 'N/A')
                max_val = valuations_max.get(anchor, 'N/A')
                print(f"{anchor:<30} {min_val:<20} {max_val:<20}")
    
    print("\n" + "=" * 80)


def read_output_file(file_path: Path) -> Dict[str, Any]:
    """Read synthesis output from a JSON file."""
    try:
        with file_path.open('r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def read_output_stdin() -> Dict[str, Any]:
    """Read synthesis output from stdin."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON from stdin: {e}", file=sys.stderr)
        sys.exit(1)


@click.command()
@click.option('--input-file', '-i', type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help='Path to JSON output file. If not provided, reads from stdin.')
@click.option('--output-file', '-o', type=click.Path(dir_okay=False, path_type=Path),
              help='Path to write formatted output. If not provided, writes to stdout.')
@click.option('--json', 'output_json', is_flag=True, default=False,
              help='Output as JSON instead of formatted text.')
def main(input_file: Optional[Path], output_file: Optional[Path], output_json: bool) -> None:
    """Parse and display synthesis output from JSON.
    
    Reads synthesis output (constraints, valuations) from a JSON file or stdin
    and displays it in a human-readable format.
    
    Examples:
    
        # Read from file
        python -m cse291p.pipeline.output.read_output -i output.json
    
        # Read from stdin
        cat output.json | python -m cse291p.pipeline.output.read_output
    
        # Output as JSON
        python -m cse291p.pipeline.output.read_output -i output.json --json
    """
    # Read input
    if input_file:
        output_data = read_output_file(input_file)
    else:
        output_data = read_output_stdin()
    
    # Validate structure
    if not isinstance(output_data, dict):
        print("Error: Output must be a JSON object", file=sys.stderr)
        sys.exit(1)
    
    # Output
    if output_json:
        output_text = json.dumps(output_data, indent=2)
        if output_file:
            output_file.write_text(output_text)
        else:
            print(output_text)
    else:
        # Format output
        if output_file:
            with output_file.open('w') as f:
                import sys
                old_stdout = sys.stdout
                sys.stdout = f
                try:
                    parse_output(output_data)
                finally:
                    sys.stdout = old_stdout
        else:
            parse_output(output_data)


if __name__ == '__main__':
    main()

