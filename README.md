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
- **Prompt Engineering** (Optional): Use local Gemma 4 to improve prompts before sending to Claude
  - Improve a single prompt with AI suggestions
  - Get clarifying questions to refine prompts
  - Batch analyze past vague prompts from your history
  - Requires local Ollama installation (free, runs on MacBook Pro)
- **Privacy**: All processing happens locally—no data sent to external servers

## Quick Start

### Step 1: Extract Conversation Data

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

### Step 2: Analyze the Data

```bash
# Install dependencies (if not already installed)
pip install -e .

# Run analysis (default command)
python -m src.cli analyze --input claude-conversation.json

# With custom output directory
python -m src.cli analyze --input claude-conversation.json --output-dir ./my-results

# Start fresh (overwrite previous results)
python -m src.cli analyze --input claude-conversation.json --fresh
```

### Output

You'll get:
1. **Console Report**: Summary + personalized recommendations
2. **output/recommendations.jsonl**: JSONL file with timestamped recommendations
3. **output/metrics.jsonl**: JSONL file with timestamped metrics (append mode by default)

Files are stored in `output/` directory and append on each run, allowing you to track changes over time.

### (Optional) Step 3: Engineer Your Prompts with Gemma

Before sending prompts to Claude, use local Gemma to improve them for free:

```bash
# Improve a single prompt
python -m src.cli engineer-prompt --prompt "How do I optimize this?"

# Get clarifying questions to refine the prompt
python -m src.cli engineer-prompt --prompt "..." --ask-questions

# Analyze past vague prompts from your conversation history
python -m src.cli engineer-prompt --history claude-conversation.json
```

**This feature requires Ollama with Gemma installed locally** (see [Prompt Engineering Setup](#prompt-engineering-setup) below).

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
- Optional: Ollama (for prompt engineering feature)

### Setup

```bash
# Clone or download this repo
git clone https://github.com/anthropics/claude-token-analyzer.git
cd claude-token-analyzer

# Install the package with dependencies
pip install -e .

# Run tests (optional)
pytest tests/unit/
```

## Prompt Engineering Setup

⚠️ **FanDuel Note**: Ollama and Gemma 4 are currently under security review. This feature is **not yet available for use on FanDuel machines**. Check with your security team for availability updates.

The `engineer-prompt` subcommand uses **local Gemma 4** (via Ollama) to improve prompts before you send them to Claude. This is completely optional—you can use the analyzer without it.

### Why Use This?

- **Free prompt improvement**: Uses Gemma instead of your Claude tokens
- **Clarifying questions**: Get 2-3 follow-up questions to refine before sending
- **History analysis**: Find and improve vague prompts from past conversations
- **Local only**: No data sent anywhere, runs on your machine

### Installing Ollama + Gemma

1. **Install Ollama** (macOS, Linux, or Windows):
   - Go to [https://ollama.ai](https://ollama.ai)
   - Download and install Ollama
   - Start Ollama: `ollama serve` (runs on `http://localhost:11434`)

2. **Pull Gemma 4 model**:

   ```bash
   ollama pull gemma:latest
   ```

   This downloads ~9GB model (one time only). On a MacBook Pro M1/M2/M3:
   - Download: ~5-10 minutes (depends on internet)
   - First run: ~30 seconds (model loads into memory)
   - Subsequent runs: ~5 seconds (cached)

3. **Verify setup**:

   ```bash
   # Check Ollama is running
   curl http://localhost:11434/api/tags

   # Should show gemma in the list
   ```

### Using Prompt Engineering

Once Ollama is running with Gemma:

```bash
# Improve a single prompt
python -m src.cli engineer-prompt --prompt "How do I optimize this?"

# Ask clarifying questions
python -m src.cli engineer-prompt --prompt "My code is slow" --ask-questions

# Batch analyze vague prompts from your history
python -m src.cli engineer-prompt --history claude-conversation.json

# Save results to a file
python -m src.cli engineer-prompt --history export.json --output-dir ./engineered
```

### Troubleshooting Prompt Engineering

#### Error: "Cannot connect to Ollama"

- Make sure Ollama is running: `ollama serve` in another terminal
- Check it's accessible: `curl http://localhost:11434/api/tags`

#### "Gemma model not found"

- Install it: `ollama pull gemma:latest`
- Wait for download to complete

#### Slow responses

- Gemma 4 is large (~9GB), runs best on M1/M2/M3 Macs
- First request: ~30 seconds (model loading)
- Subsequent: ~5 seconds (cached)
- If too slow, try a smaller model: `ollama pull gemma:7b`

#### Want to use a different model?

- Pull another model: `ollama pull mistral` or `ollama pull neural-chat`
- Then: `python -m src.cli engineer-prompt --prompt "..."` will auto-detect available models

## Usage Examples

### Analyze a Single Conversation

```bash
python -m src.cli analyze --input conversation.json
```

### Analyze Multiple Conversations

Export all conversations from claude.ai, then:

```bash
# Create a combined file with all conversations
# Format: {"conversations": [conv1, conv2, ...]}
python -m src.cli analyze --input all-conversations.json
```

### Analyze with Custom Output Directory

```bash
python -m src.cli analyze --input export.json --output-dir ./my-analysis --fresh
```

### Engineer a Prompt (Requires Ollama + Gemma)

```bash
# Improve a single prompt
python -m src.cli engineer-prompt --prompt "How do I optimize this?"

# Get clarifying questions
python -m src.cli engineer-prompt --prompt "My code is slow" --ask-questions

# Analyze vague prompts from history
python -m src.cli engineer-prompt --history export.json --output-dir ./engineered
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

### analyze (Default)

```
--input FILE, -i FILE          Input JSON export file (required)
--output-dir DIR, -o DIR       Output directory (default: output/)
--fresh, -f                    Overwrite existing files (default: append)
--quiet, -q                    Suppress console output
--verbose, -v                  Show detailed debug output
```

### engineer-prompt (Optional, requires Ollama)

```
--prompt TEXT, -p TEXT         Prompt to improve
--history FILE                 Conversation file to analyze for vague prompts
--ask-questions                Ask 2-3 clarifying questions (with --prompt)
--output-dir DIR, -o DIR       Save engineered prompts to directory
--fresh, -f                    Overwrite existing prompts file
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
- [x] Recommendation engine with examples
- [x] CLI interface with subcommands
- [x] Local processing (no external APIs)
- [x] Prompt engineering with local Gemma (optional)
- [x] Timestamped JSONL output for trend tracking
- [x] Append mode for historical analysis

### Phase 2 (Full Extension)
- [ ] Browser extension for real-time tracking
- [ ] Dashboard with trends over time
- [ ] Accurate token counting (via Claude API)
- [ ] Weekly usage reports
- [ ] Comparison to team benchmarks
- [ ] Support for additional local models (Mistral, Neural Chat, etc.)

### Phase 3 (Enterprise)
- [ ] Organization-wide analytics
- [ ] Cost optimization per team
- [ ] Integration with billing
- [ ] Custom recommendation rules
- [ ] Team prompt engineering guidelines

## License

MIT

## Support

For questions or issues:
- Check the [Troubleshooting](#troubleshooting) section above
- Review test examples in `tests/fixtures/`
- Run with `--verbose` flag for debug output
