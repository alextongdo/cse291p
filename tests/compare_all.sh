#!/bin/bash
# Script to run all test inputs on both implementations and compare outputs

set -e

INPUT_DIR="tests/inputs"
ORIGINAL_OUTPUT_DIR="tests/outputs/original"
REFACTORED_OUTPUT_DIR="tests/outputs/refactored"
COMPARISON_DIR="tests/outputs/comparison"

# Create output directories
mkdir -p "$ORIGINAL_OUTPUT_DIR"
mkdir -p "$REFACTORED_OUTPUT_DIR"
mkdir -p "$COMPARISON_DIR"

echo "=========================================="
echo "Running all test inputs on both implementations"
echo "=========================================="
echo ""

# Function to run original mockdown
run_original() {
    local input_file="$1"
    local output_file="$2"
    local input_name=$(basename "$input_file" .json)
    
    echo "  Running original mockdown on $input_name..."
    cd /Users/xurui/Downloads/FA25/mockdown
    python -m mockdown.cli run "$input_file" "$output_file" \
        --input-format default \
        --numeric-type N \
        --instantiation-method numpy \
        --learning-method noisetolerant \
        --pruning-method baseline \
        2>&1 | grep -v "FutureWarning" || true
}

# Function to run refactored cse291p
run_refactored() {
    local input_file="$1"
    local output_file="$2"
    local input_name=$(basename "$input_file" .json)
    
    echo "  Running refactored cse291p on $input_name..."
    cd /Users/xurui/Downloads/FA25/cse291p
    python -m cse291p.pipeline.run \
        --input-file "$input_file" \
        --input-format default \
        --numeric-type N \
        --instantiation-method numpy \
        --learning-method noisetolerant \
        > "$output_file" 2>&1 || true
}

# Function to compare outputs
compare_outputs() {
    local input_name="$1"
    local original_file="$2"
    local refactored_file="$3"
    local comparison_file="$4"
    
    echo "  Comparing outputs for $input_name..."
    
    # Format both outputs for comparison
    cd /Users/xurui/Downloads/FA25/cse291p
    
    # Format original output
    python -m cse291p.pipeline.output.read_output -i "$original_file" > "${comparison_file}.original.txt" 2>&1 || true
    
    # Format refactored output
    python -m cse291p.pipeline.output.read_output -i "$refactored_file" > "${comparison_file}.refactored.txt" 2>&1 || true
    
    # Show comparison
    echo "" >> "$comparison_file"
    echo "=== ORIGINAL OUTPUT ===" >> "$comparison_file"
    cat "${comparison_file}.original.txt" >> "$comparison_file"
    echo "" >> "$comparison_file"
    echo "=== REFACTORED OUTPUT ===" >> "$comparison_file"
    cat "${comparison_file}.refactored.txt" >> "$comparison_file"
    echo "" >> "$comparison_file"
    echo "=== DIFF ===" >> "$comparison_file"
    diff -u "${comparison_file}.original.txt" "${comparison_file}.refactored.txt" >> "$comparison_file" 2>&1 || true
}

# Process each input file
for input_file in "$INPUT_DIR"/*.json; do
    if [ ! -f "$input_file" ]; then
        continue
    fi
    
    input_name=$(basename "$input_file" .json)
    echo "Processing: $input_name"
    
    original_output="$ORIGINAL_OUTPUT_DIR/${input_name}.json"
    refactored_output="$REFACTORED_OUTPUT_DIR/${input_name}.json"
    comparison_output="$COMPARISON_DIR/${input_name}.txt"
    
    # Run both implementations
    run_original "$input_file" "$original_output"
    run_refactored "$input_file" "$refactored_output"
    
    # Compare outputs
    compare_outputs "$input_name" "$original_output" "$refactored_output" "$comparison_output"
    
    echo "  ✓ Completed $input_name"
    echo ""
done

echo "=========================================="
echo "All tests completed!"
echo "=========================================="
echo ""
echo "Results saved in:"
echo "  Original outputs: $ORIGINAL_OUTPUT_DIR"
echo "  Refactored outputs: $REFACTORED_OUTPUT_DIR"
echo "  Comparisons: $COMPARISON_DIR"
echo ""

