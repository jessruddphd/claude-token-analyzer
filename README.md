# Claude Token Analyzer

Analyze your Claude conversation usage patterns and get personalized recommendations to optimize token efficiency.

## Features

- **Data Extraction**: Browser bookmarklet to extract conversations from claude.ai (no manual export needed)
- **Pattern Detection**: Identifies inefficient patterns:
  - Long conversations (>40 messages with context overhead)
  - Vague/short prompts requiring clarifications
  - Repetitive questions
  - Poor message structure
- **Token Estimation**: Estimates token usage (1 token ≈ 4 characters)
- **Actionable Recommendations**: Prioritized (HIGH/MEDIUM/LOW) with specific improvement actions
- **Privacy**: All processing happens locally—no data sent to external servers

## Quick Start

### Step 1: Extract Conversation Data

#### Option A: Using the Bookmarklet (Recommended)

1. **Install the bookmarklet**:
   - Open `bookmarklet/claude_extractor_bookmarklet.txt` in this repo
   - Copy the entire content (it's one long line starting with `javascript:`)
   - In your browser:
     - Right-click on Bookmarks → Bookmark Manager (or press `Ctrl+Shift+B`)
     - Click the three dots → Add new bookmark
     - **Name**: "Claude Extractor"
     - **URL**: Paste the entire content from the file
     - Click Save
   
   **Note**: Use the `.txt` file (minified, no comments). The `.js` file has comments that break bookmarklets.

2. **Extract conversation**:
   - Go to any conversation on claude.ai
   - Click the "Claude Extractor" bookmark
   - Conversation downloads as `claude-conversation.json`

#### Option B: Manual Export

If bookmarklet doesn't work:
1. Go to claude.ai conversation
2. Look for export/share options
3. Export as JSON
4. Save to your computer

### Step 2: Analyze the Data

```bash
# Install dependencies (if not already installed)
pip install -r requirements.txt

# Run analysis
python -m src.cli --input claude-conversation.json

# With custom output
python -m src.cli --input claude-conversation.json \
  --output my-recommendations.txt \
  --metrics my-metrics.json
```

### Output

You'll get:
1. **Console Report**: Summary + personalized recommendations
2. **recommendations.txt**: Detailed write-up of each recommendation
3. **metrics.json**: Metrics data for tracking over time

## What the Recommendations Tell You

### HIGH Priority (Act on these first)

**Context Management**: Long conversations burden token limits
- Problem: Each message costs tokens for entire history
- Solution: Start new conversations at topic boundaries

### MEDIUM Priority (Good to address)

**Prompt Quality**: Vague prompts → back-and-forth clarifications
- Problem: "Optimize this?" requires follow-ups, wasting tokens
- Solution: "Optimize this for speed (<100ms) while maintaining readability"

**Communication Efficiency**: Clarification loops detected
- Problem: Structure: Context → Task → Constraints → Output format
- Solution: Prevents miscommunication on first try

### INFO

**Usage Summary**: Your current usage vs. benchmarks

## Installation

### Requirements

- Python 3.9+
- No external API keys needed (all local processing)

### Setup

```bash
# Clone or download this repo
git clone https://github.com/anthropics/claude-token-analyzer.git
cd claude-token-analyzer

# Install dependencies
pip install -r requirements.txt

# Run tests (optional)
pytest tests/unit/
```

## Usage Examples

### Analyze a Single Conversation

```bash
python -m src.cli --input conversation.json
```

### Analyze Multiple Conversations

Export all conversations from claude.ai, then:

```bash
# Create a combined file with all conversations
# Format: {"conversations": [conv1, conv2, ...]}
python -m src.cli --input all-conversations.json
```

### Batch Analysis with Metrics Only

```bash
python -m src.cli --input export.json --quiet \
  --output recs.txt --metrics data.json
```

## How It Works

1. **Load**: Reads conversation JSON (auto-detects format)
2. **Parse**: Extracts messages with role, content, timestamp
3. **Analyze**: Classifies messages (code/question/instruction), detects patterns
4. **Estimate**: Calculates token count (4 chars ≈ 1 token)
5. **Generate**: Creates prioritized recommendations
6. **Report**: Formats and saves output

## Pattern Detection

### Long Conversations
- **Threshold**: >40 messages per conversation
- **Impact**: Context window bloat, 25% token waste on re-reading history
- **Solution**: Split conversations by topic

### Short Prompts
- **Threshold**: <20 character prompts
- **Pattern**: Multiple short prompts + assistant asking for clarification
- **Impact**: 15% token waste on clarification rounds
- **Solution**: Provide context upfront (task, constraints, example output)

### Clarification Loops
- **Pattern**: User asks question → assistant asks for details → repeat
- **Impact**: Doubles tokens for that query
- **Solution**: Structure: "Context. Task. Constraints. Expected output format."

### Repetitive Questions
- **Detection**: Similarity matching on user messages (>80% similar)
- **Impact**: Wasted tokens on repeated analysis
- **Solution**: Save Claude's best answers in a reference document

## Privacy & Security

✅ **All processing is local**
- No conversations sent to external servers
- No cloud processing
- Safe for confidential/proprietary code

✅ **Only metrics are saved**
- Recommendations reference patterns, not content
- No sensitive data in outputs
- Can share reports without revealing conversation text

## Command-Line Options

```
--input FILE, -i FILE          Input JSON export file (required)
--output FILE, -o FILE         Output recommendations file (default: recommendations.txt)
--metrics FILE, -m FILE        Output metrics JSON file (default: metrics.json)
--quiet, -q                    Suppress console output
--verbose, -v                  Show detailed debug output
```

## Supported Formats

- ✅ Claude.ai web export (with "conversations" key)
- ✅ Claude Code / Cursor IDE local export
- ✅ Single conversation JSON files
- ✅ Claude API export formats

## Troubleshooting

### "No conversations found in file"

**Problem**: File format not recognized

**Solutions**:
1. Verify JSON is valid (use `python -m json.tool file.json`)
2. Check file has `conversations` array or `messages` array
3. Ensure messages have `role` and `content` fields

### Bookmarklet Not Working

**Problem**: Blank download or no messages extracted

**Solutions**:
1. Make sure you're on claude.ai (not mobile, not API)
2. Wait for conversation to fully load
3. Check browser console for errors (F12 → Console)
4. Try manual export instead

### Token Estimates Seem Off

**Problem**: Estimated tokens don't match actual

**Reason**: Character-based estimation (4 chars per token) is approximate
- Actual token count varies by content type (code ≠ text)
- Use as relative comparison, not absolute value

**Solution for accuracy**: In Phase 2, we'll add API-based counting

## Contributing

Found a bug? Have a suggestion?

- Report issues: [GitHub Issues](https://github.com/anthropics/claude-token-analyzer/issues)
- Share feedback: Send to AENG team

## Roadmap

### Phase 1 (MVP) ✅ Current
- [x] Bookmarklet data extraction
- [x] Pattern detection
- [x] Recommendation engine
- [x] CLI interface
- [x] Local processing (no external APIs)

### Phase 2 (Full Extension)
- [ ] Browser extension for real-time tracking
- [ ] Dashboard with trends over time
- [ ] Accurate token counting (via Claude API)
- [ ] Weekly usage reports
- [ ] Comparison to team benchmarks

### Phase 3 (Enterprise)
- [ ] Organization-wide analytics
- [ ] Cost optimization per team
- [ ] Integration with billing
- [ ] Custom recommendation rules

## License

MIT

## Support

For questions or issues:
- Check the [Troubleshooting](#troubleshooting) section above
- Review test examples in `tests/fixtures/`
- Run with `--verbose` flag for debug output
