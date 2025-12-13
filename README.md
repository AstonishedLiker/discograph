# Discograph

Discograph turns review data from ReviewDB into an interactive network that shows how people might be connected. It crawls from a seed Discord user ID, builds a graph, finds groups, and exports an HTML view you can open in a browser.

## Features

- Fast async crawl from a seed user
- Clear NetworkX graph of connections
- Group detection with the Louvain algorithm
- Shareable HTML view
- Visuals that show clusters and bridges

## Requirements

- Python 3.13+ (recommended)
- [Poetry](https://python-poetry.org/)

Install dependencies via [Poetry](https://python-poetry.org/):

```bash
poetry install
```

## Usage

Run from the project root:

```bash
poetry run python src --userid <DISCORD_USER_ID> --depth <CRAWL_DEPTH> --show-cross-communities
```

This will generate a file named `discograph.html` in the project directory. Open it in your browser.

### Syntax help

- `-cross` or `--show-cross-communities` _(Optional)_
    - Shows interactions between communities.
    - Disable for large graphs to reduce lag and improve readability.

- `--userid` or `-id`
    - The root Discord user ID to start the crawl from.
    - Example: `--userid 233958408179417089`

- `--depth` or `-d`
    - How many layers to crawl outward from the root user.
    - Use small numbers (e.g., 1–3) for faster runs.
    - Example: `--depth 2`

Examples:

```bash
poetry run python src -id 233958408179417089 -d 2
poetry run python src --userid 704017415432044544 --depth 3 --show-cross-communities
```

## Output

- `discograph.html`: interactive network view
    - Nodes colored by detected communities
    - Box nodes represent community hubs
    - Solid edges within communities, dashed gray edges between communities

Open `discograph.html` (if not done automatically) in any modern browser.

## Feedback

If you are interested in social graphs or visualization, I would be glad to hear your thoughts and suggestions.