#!/bin/bash
# print_structure.sh - Print directory tree structure (Bash version)

# Colors (optional)
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Directories to skip
SKIP_DIRS=".git .github __pycache__ node_modules .venv venv build dist .cache pacman-cache .idea .vscode"

# Function to check if directory should be skipped
should_skip() {
    local dir="$1"
    for skip in $SKIP_DIRS; do
        if [[ "$dir" == "$skip" ]]; then
            return 0
        fi
    done
    return 1
}

# Function to print tree structure recursively
print_tree() {
    local dir="$1"
    local prefix="$2"
    local show_size="$3"
    
    # Get all entries, sorted
    local entries=()
    while IFS= read -r entry; do
        entries+=("$entry")
    done < <(ls -A "$dir" 2>/dev/null | sort)
    
    # Filter out hidden files and skip directories
    local filtered=()
    for entry in "${entries[@]}"; do
        # Skip hidden files unless -a flag is set
        if [[ "$SHOW_HIDDEN" != "true" && "$entry" =~ ^\. ]]; then
            continue
        fi
        
        # Skip certain directories
        if should_skip "$entry"; then
            continue
        fi
        
        filtered+=("$entry")
    done
    
    # Separate directories and files
    local dirs=()
    local files=()
    
    for entry in "${filtered[@]}"; do
        local path="$dir/$entry"
        if [[ -d "$path" ]]; then
            dirs+=("$entry")
        else
            files+=("$entry")
        fi
    done
    
    # Combine: directories first, then files
    local all_entries=("${dirs[@]}" "${files[@]}")
    local total=${#all_entries[@]}
    
    # Print each entry
    for i in "${!all_entries[@]}"; do
        local entry="${all_entries[$i]}"
        local path="$dir/$entry"
        local is_last=false
        
        if [[ $((i + 1)) -eq $total ]]; then
            is_last=true
        fi
        
        # Choose tree characters
        if $is_last; then
            local connector="└── "
            local extension="    "
        else
            local connector="├── "
            local extension="│   "
        fi
        
        # Print entry
        if [[ -d "$path" ]]; then
            if [[ "$USE_COLOR" == "true" ]]; then
                echo -e "${prefix}${connector}${BLUE}${entry}/${NC}"
            else
                echo "${prefix}${connector}${entry}/"
            fi
            
            # Recursively print subdirectory
            print_tree "$path" "${prefix}${extension}" "$show_size"
        else
            # Print file
            if [[ "$show_size" == "true" ]]; then
                local size=$(du -h "$path" 2>/dev/null | cut -f1)
                if [[ "$USE_COLOR" == "true" ]]; then
                    echo -e "${prefix}${connector}${GREEN}${entry}${NC} (${size})"
                else
                    echo "${prefix}${connector}${entry} (${size})"
                fi
            else
                if [[ "$USE_COLOR" == "true" ]]; then
                    echo -e "${prefix}${connector}${GREEN}${entry}${NC}"
                else
                    echo "${prefix}${connector}${entry}"
                fi
            fi
        fi
    done
}

# Function to print statistics
print_stats() {
    local dir="$1"
    
    echo ""
    echo "=================================================="
    
    # Count files and directories
    local file_count=0
    local dir_count=0
    local total_size=0
    
    while IFS= read -r line; do
        ((dir_count++))
    done < <(find "$dir" -type d ! -path "*/.git/*" ! -path "*/node_modules/*" ! -path "*/build/*" 2>/dev/null)
    
    while IFS= read -r line; do
        ((file_count++))
    done < <(find "$dir" -type f ! -path "*/.git/*" ! -path "*/node_modules/*" ! -path "*/build/*" 2>/dev/null)
    
    total_size=$(du -sh "$dir" 2>/dev/null | cut -f1)
    
    echo "Total Directories: $((dir_count - 1))"  # Subtract 1 for root
    echo "Total Files: $file_count"
    echo "Total Size: $total_size"
    echo "=================================================="
}

# Main function
main() {
    local directory="."
    local show_size=false
    local show_stats=false
    SHOW_HIDDEN=false
    USE_COLOR=true
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s|--size)
                show_size=true
                shift
                ;;
            -a|--all)
                SHOW_HIDDEN=true
                shift
                ;;
            --stats)
                show_stats=true
                shift
                ;;
            --no-color)
                USE_COLOR=false
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS] [DIRECTORY]"
                echo ""
                echo "Options:"
                echo "  -s, --size        Show file sizes"
                echo "  -a, --all         Show hidden files"
                echo "  --stats           Show statistics"
                echo "  --no-color        Disable colors"
                echo "  -h, --help        Show this help"
                echo ""
                echo "Examples:"
                echo "  $0                    # Basic tree"
                echo "  $0 -s                 # Show sizes"
                echo "  $0 -a --stats         # Show hidden + stats"
                echo "  $0 /path/to/dir       # Specific directory"
                exit 0
                ;;
            *)
                directory="$1"
                shift
                ;;
        esac
    done
    
    # Check if directory exists
    if [[ ! -d "$directory" ]]; then
        echo "Error: '$directory' is not a valid directory"
        exit 1
    fi
    
    # Print header
    echo ""
    echo "=================================================="
    echo "Directory Structure: $(cd "$directory" && pwd)"
    echo "=================================================="
    echo ""
    
    # Print root
    local root_name=$(basename "$(cd "$directory" && pwd)")
    if [[ "$USE_COLOR" == "true" ]]; then
        echo -e "${BLUE}${root_name}/${NC}"
    else
        echo "${root_name}/"
    fi
    
    # Print tree
    print_tree "$directory" "" "$show_size"
    
    # Print stats if requested
    if [[ "$show_stats" == "true" ]]; then
        print_stats "$directory"
    fi
    
    echo ""
}

# Run main function
main "$@"