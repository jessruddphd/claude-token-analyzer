"""Command-line interface for token analyzer."""
import argparse
import json
import sys
from pathlib import Path
from typing import Optional, List

from src.models import Conversation
from src.estimators import CharacterBasedEstimator
from src.patterns import PatternDetector
from src.analyzer import ConversationAnalyzer
from src.recommendations import RecommendationGenerator
from src.formatter import ReportFormatter


def load_conversations(filepath: str) -> List[Conversation]:
    """Load conversations from JSON export file.

    Supports both claude.ai and Claude Code/Cursor formats.

    Args:
        filepath: Path to JSON export file.

    Returns:
        List of Conversation objects.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If file format is invalid.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON file: {e}")

    # Parse conversations based on format
    conversations = []

    if isinstance(data, dict):
        if "conversations" in data:
            # claude.ai export format
            for conv_data in data["conversations"]:
                conversations.append(Conversation.from_dict(conv_data))
        elif "messages" in data or "chat_messages" in data:
            # Single conversation in claude.ai format
            conversations.append(Conversation.from_dict(data))
        else:
            raise ValueError("Unknown conversation format")

    elif isinstance(data, list):
        # Claude Code export (flat list of events) or list of conversations
        try:
            convs = Conversation.from_cursor_export(data)
            conversations.extend(convs)
        except (ValueError, KeyError):
            # Try as list of conversation dicts
            for conv_data in data:
                try:
                    conversations.append(Conversation.from_dict(conv_data))
                except (ValueError, KeyError):
                    continue

    if not conversations:
        raise ValueError("No valid conversations found in file")

    return conversations


def main(argv: Optional[List[str]] = None) -> int:
    """Run the token analyzer.

    Args:
        argv: Command-line arguments (default: sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parser = argparse.ArgumentParser(
        description="Analyze Claude conversation exports for token optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.cli --input export.json
  python -m src.cli --input export.json --output analysis.txt
  python -m src.cli --input export.json --quiet
        """,
    )

    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to exported Claude conversation JSON file",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="recommendations.txt",
        help="Output file for recommendations (default: recommendations.txt)",
    )
    parser.add_argument(
        "--metrics",
        "-m",
        default="metrics.json",
        help="Output file for metrics JSON (default: metrics.json)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress console output",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )

    args = parser.parse_args(argv)

    try:
        # Load conversations
        if not args.quiet:
            print("📂 Loading conversations...")
        conversations = load_conversations(args.input)
        if not args.quiet:
            print(f"✓ Loaded {len(conversations)} conversation(s)\n")

        # Analyze
        if not args.quiet:
            print("🔍 Analyzing conversations...")
        estimator = CharacterBasedEstimator()
        detector = PatternDetector()
        analyzer = ConversationAnalyzer(estimator, detector)

        batch_metrics = analyzer.analyze_batch(conversations)
        if not args.quiet:
            print("✓ Analysis complete\n")

        # Generate recommendations
        if not args.quiet:
            print("💡 Generating recommendations...")
        gen = RecommendationGenerator()
        recommendations = gen.generate(batch_metrics)

        # Enhance with examples from conversations
        recommendations = gen.enhance_with_examples(recommendations, conversations)

        ranked_recs = gen.rank(recommendations)
        if not args.quiet:
            print("✓ Recommendations generated\n")

        # Print report
        if not args.quiet:
            formatter = ReportFormatter()
            formatter.print_report(batch_metrics, ranked_recs)

        # Save outputs
        if not args.quiet:
            print("\n📝 Saving outputs...")

        formatter = ReportFormatter()
        formatter.save_recommendations(args.output, ranked_recs)
        formatter.save_metrics(args.metrics, batch_metrics)

        if not args.quiet:
            print(f"✓ Recommendations saved to: {args.output}")
            print(f"✓ Metrics saved to: {args.metrics}")
            print(f"\n✅ Analysis complete!\n")

        return 0

    except FileNotFoundError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
