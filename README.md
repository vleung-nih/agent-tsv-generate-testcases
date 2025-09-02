# UI Test Case Generator

## Overview
This project is a simplified UI Test Case Generator that uses Claude 3.5 Sonnet on AWS Bedrock to automatically generate test case suggestions for web pages. It navigates to a URL, clicks the "Continue" button if present, captures a screenshot, and uses AI to suggest relevant UI test cases.

## Project Structure
```
autonomous-ui-validator/
├── src/                          # Source code
│   ├── __init__.py
│   ├── run_agent.py             # Main execution script
│   ├── smol_like_agent.py       # Simplified AI agent
│   └── tools.py                 # Navigation and screenshot utilities
├── data/                         # Data and outputs
│   └── runs/                    # Timestamped run outputs
├── docs/                         # Documentation
│   ├── README.md                # This file
│   └── user_story.txt           # Example requirements
├── requirements.txt              # Python dependencies
└── run.py                       # Simple runner script
```

## Prerequisites
- Python 3.8 or higher
- Node.js (for Playwright installation)
- AWS credentials configured for Bedrock

## Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd autonomous-ui-validator
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Playwright and its browsers:
   ```bash
   playwright install
   ```

4. Configure AWS credentials:
   Ensure your AWS credentials are set up in `~/.aws/credentials` or via environment variables.

## Usage

Run the generator from the project root with a single required parameter:

```bash
python run.py --url "https://example.com"
```

The script will:
1. Navigate to the target URL
2. Click the "Continue" button if present
3. Capture a full-page screenshot
4. Use Claude 3.5 to analyze the page and generate UI test case suggestions

Each execution creates a timestamped directory under `data/runs/` containing:

- `screenshot.png` – snapshot of the target page
- `result.txt` – the generated test case suggestions
- `report.html` – formatted HTML report
- `archive.zip` – compressed artifacts for sharing
- `run_log.csv` – execution log

## Configuration
- **Claude 3.5 Sonnet**:
  Ensure the `MODEL_ID` and `REGION` in `src/run_agent.py` are correctly set for your AWS Bedrock instance.

## Development

### Running Individual Components
```bash
# Test the navigation tool
python -c "from src.tools import navigate_and_capture; print('Navigation tool loaded successfully')"

# Test the agent
python -c "from src.smol_like_agent import SmolLikeAgent; print('Agent loaded successfully')"
```

## Troubleshooting
- If Playwright fails to install, ensure Node.js is installed and accessible.
- For AWS-related issues, verify your credentials and permissions.
- If you get import errors, ensure you're running from the project root directory.

## License
This project is licensed under the MIT License.
