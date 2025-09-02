# Autonomous Visual UI Validation Framework

## Overview
This project is a Visual UI Validation framework that leverages AI agents to autonomously verify user interface requirements. It integrates tools like Playwright for browser automation, Claude-based action planning for intelligent decision-making, and AWS Rekognition and AWS Textract for object detection and OCR text recognition.

## Project Structure
```
autonomous-ui-validator/
├── src/                          # Source code
│   ├── __init__.py
│   ├── run_agent.py             # Main execution script
│   ├── smol_like_agent.py       # AI agent implementation
│   └── tools.py                 # Utility functions
├── data/                         # Data and outputs
│   ├── screenshots/             # Step-by-step screenshots
│   └── runs/                    # Run outputs and logs
├── docs/                         # Documentation
│   ├── README.md                # This file
│   ├── user_story.txt           # Example user story
│   └── Autonomous_UI_Validator_Project.docx
├── requirements.txt              # Python dependencies
└── .git/                         # Git repository
```

## Prerequisites
- Python 3.8 or higher
- Node.js (for Playwright installation)
- AWS credentials configured for Bedrock and Rekognition

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

Run the agent from the project root with a single required parameter:

```bash
python run.py --url "<target>"
```

The script visits the target URL, captures a full-page screenshot, and asks the Claude-powered agent to analyze the page. From the screenshot and DOM the agent proposes UI test-case ideas and, where possible, tries to execute them using Playwright and supporting tools.

Each execution creates a timestamped directory under `data/runs/` containing:

- `screenshot.png` – snapshot of the target page
- `result.txt` – the generated test-case suggestions and their outcomes
- `report.html` – formatted summary of the run
- `archive.zip` – compressed artifacts for sharing
- `run_log.csv` and `trace.jsonl` – detailed logs of the interaction

## Configuration
- **Claude-based Action Planner**:
  Ensure the `MODEL_ID` and `REGION` in `src/run_agent.py` are correctly set for your AWS Bedrock instance.

- **AWS Textract and Rekognition**:
  Ensure the required AWS services are enabled in your account.

## Development

### Running Individual Components
```bash
# Run the agent directly
python -c "from src.smol_like_agent import SmolLikeAgent; print('Agent loaded successfully')"

# Test tools module
python -c "from src.tools import click_buttons_and_search; print('Tools loaded successfully')"
```

### Adding New Features
- Place new source code in the `src/` directory
- Add new documentation in the `docs/` directory
- Store new data files in the appropriate `data/` subdirectory

## Future Enhancements
- Dynamic Playwright script generation.
- Advanced AI-based verification for complex interactions.
- Scalable execution for large-scale testing.

## Troubleshooting
- If Playwright fails to install, ensure Node.js is installed and accessible.
- For AWS-related issues, verify your credentials and permissions.
- If you get import errors, ensure you're running from the project root directory.

## License
This project is licensed under the MIT License.
