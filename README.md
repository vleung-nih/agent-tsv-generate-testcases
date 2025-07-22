# Autonomous Visual UI Validation Framework

## Overview
This project is a Visual UI Validation framework that leverages AI agents to autonomously verify user interface requirements. It integrates tools like Playwright for browser automation, Claude-based action planning for intelligent decision-making, and AWS Rekognition and AWS Textract for object detectition and OCR text recognition.

## Prerequisites
- Python 3.8 or higher
- Node.js (for Playwright installation)
- AWS credentials configured for Bedrock and Rekognition

## Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-folder>
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
1. Run the main script with a URL and user story file:
   ```bash
   python run_agent.py --url "<target-url>" --prompt-file user_story.txt
   ```

2. View the generated reports in the `run_<timestamp>` folder.

## Configuration
- **Claude-based Action Planner**:
  Ensure the `MODEL_ID` and `REGION` in the code are correctly set for your AWS Bedrock instance.

- **AWS Textract and Rekognition**:
  Ensure the required AWS services are enabled in your account.

## Future Enhancements
- Dynamic Playwright script generation.
- Advanced AI-based verification for complex interactions.
- Scalable execution for large-scale testing.

## Troubleshooting
- If Playwright fails to install, ensure Node.js is installed and accessible.
- For AWS-related issues, verify your credentials and permissions.

## License
This project is licensed under the MIT License.
