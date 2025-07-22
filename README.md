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

### Running the Main Program
From the project root directory (`autonomous-ui-validator/`), run:

```bash
# Option 1: Using the simple runner script (easiest)
python run.py --url "<target-url>" --prompt-file docs/user_story.txt

# Option 2: Using Python module syntax
python -m src.run_agent --url "<target-url>" --prompt-file docs/user_story.txt

# Option 3: Using direct path
python src/run_agent.py --url "<target-url>" --prompt-file docs/user_story.txt
```

### Example Commands
```bash
# Run with a specific URL and user story (simplest way)
python run.py --url "https://example.com" --prompt-file docs/user_story.txt

# Run with a custom user story file
python run.py --url "https://example.com" --prompt-file path/to/your/story.txt

# Alternative using module syntax
python -m src.run_agent --url "https://example.com" --prompt-file docs/user_story.txt
```

### Output Locations
- **Screenshots**: `data/screenshots/` - Step-by-step screenshots during execution
- **Run Reports**: `data/runs/run_<timestamp>/` - Generated reports, logs, and archives
- **Results**: Each run creates a timestamped folder with:
  - `screenshot.png` - Final page screenshot
  - `result.txt` - AI analysis results
  - `report.html` - Visual HTML report
  - `archive.zip` - Compressed run data
  - `run_log.csv` - Execution log
  - `trace.jsonl` - Detailed trace data

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
