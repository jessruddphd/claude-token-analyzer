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


def engineer_prompt_command(args) -> int:
    """Handle engineer-prompt subcommand.

    Args:
        args: Parsed arguments from subcommand.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    try:
        from src.gemma_engineer import PromptEngineer

        try:
            engineer = PromptEngineer()
        except ConnectionError as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            return 1

        # Mode 1: Improve a single prompt
        if args.prompt:
            if not args.quiet:
                print("🔧 Analyzing prompt with Gemma...\n")

            analysis = engineer.improve_prompt(args.prompt)

            print("=" * 70)
            print("📝 PROMPT ANALYSIS")
            print("=" * 70 + "\n")

            print(f"Original:  {analysis.original_prompt}\n")
            print(f"Improved:  {analysis.improved_prompt}\n")

            if analysis.issues_found:
                print("Issues found:")
                for i, issue in enumerate(analysis.issues_found, 1):
                    print(f"  {i}. {issue}")
                print()

            if analysis.reasoning:
                print(f"Why it's better: {analysis.reasoning}\n")

            # Ask follow-up questions if requested
            if args.ask_questions:
                if not args.quiet:
                    print("💭 Asking clarifying questions...\n")

                questions = engineer.ask_followup_questions(args.prompt, analysis)

                print("Clarifying questions to refine further:")
                for i, q in enumerate(questions, 1):
                    print(f"  {i}. {q}")
                print()

            print("=" * 70)
            print(
                "✅ Use the improved prompt above in Claude before wasting tokens!\n"
            )
            return 0

        # Mode 2: Analyze vague prompts from history
        elif args.history:
            if not args.quiet:
                print("📂 Loading conversations...")
            conversations = load_conversations(args.history)
            if not args.quiet:
                print(f"✓ Loaded {len(conversations)} conversation(s)\n")

            if not args.quiet:
                print("🔍 Finding vague prompts...")
            analyses = engineer.analyze_vague_prompts(conversations, max_to_analyze=5)

            if not analyses:
                print("✓ No vague prompts found in conversation history!")
                return 0

            if not args.quiet:
                print(f"✓ Found {len(analyses)} vague prompt(s) to improve\n")

            # Print analyses
            print("=" * 70)
            print("📝 VAGUE PROMPT IMPROVEMENTS")
            print("=" * 70 + "\n")

            for i, analysis in enumerate(analyses, 1):
                print(f"{i}. ORIGINAL PROMPT")
                print(f"   {analysis.original_prompt}\n")

                print(f"   IMPROVED")
                print(f"   {analysis.improved_prompt}\n")

                if analysis.reasoning:
                    print(f"   Why: {analysis.reasoning}\n")

                print("-" * 70 + "\n")

            # Save to output directory if specified
            if args.output_dir:
                output_dir = Path(args.output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = output_dir / "engineered_prompts.jsonl"

                mode = "w" if args.fresh else "a"
                with open(output_file, mode, encoding="utf-8") as f:
                    for analysis in analyses:
                        record = {
                            "original": analysis.original_prompt,
                            "improved": analysis.improved_prompt,
                            "issues": analysis.issues_found,
                            "reasoning": analysis.reasoning,
                            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
                        }
                        f.write(json.dumps(record) + "\n")

                if not args.quiet:
                    print(f"✓ Saved to: {output_file}\n")

            return 0

        else:
            print("✗ Error: Use --prompt or --history", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """Run the token analyzer or prompt engineer.

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
  python -m src.cli analyze --input export.json
  python -m src.cli engineer-prompt --prompt "How do I optimize this?"
  python -m src.cli engineer-prompt --history export.json --ask-questions
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Analyze subcommand
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze conversations for token usage patterns"
    )
    analyze_parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to exported Claude conversation JSON file",
    )
    analyze_parser.add_argument(
        "--output-dir",
        "-o",
        default="output",
        help="Output directory for recommendations and metrics (default: output/)",
    )
    analyze_parser.add_argument(
        "--fresh",
        "-f",
        action="store_true",
        help="Start fresh - overwrite existing metrics/recommendations files",
    )
    analyze_parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress console output",
    )
    analyze_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )

    # Engineer-prompt subcommand
    engineer_parser = subparsers.add_parser(
        "engineer-prompt", help="Use local Gemma to improve prompts"
    )
    engineer_parser.add_argument(
        "--prompt",
        "-p",
        help="Prompt to improve",
    )
    engineer_parser.add_argument(
        "--history",
        help="Conversation file to analyze for vague prompts",
    )
    engineer_parser.add_argument(
        "--ask-questions",
        action="store_true",
        help="Ask clarifying questions to refine the prompt",
    )
    engineer_parser.add_argument(
        "--output-dir",
        "-o",
        help="Output directory for engineered prompts",
    )
    engineer_parser.add_argument(
        "--fresh",
        "-f",
        action="store_true",
        help="Overwrite existing engineered prompts file",
    )
    engineer_parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress console output",
    )
    engineer_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )

    args = parser.parse_args(argv)

    # Handle no command (default to analyze for backwards compatibility)
    if not args.command:
        # Check if old-style arguments were used
        if hasattr(args, "input") and args.input:
            args.command = "analyze"
        else:
            parser.print_help()
            return 0

    # Dispatch to command handler
    if args.command == "engineer-prompt":
        return engineer_prompt_command(args)

    # Analyze command (default or explicit)
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

        # Set analysis_id on all recommendations to tie them to metrics
        for rec in recommendations:
            rec.analysis_id = batch_metrics.analysis_id

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

        # Create output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        recommendations_file = output_dir / "recommendations.jsonl"
        metrics_file = output_dir / "metrics.jsonl"

        formatter = ReportFormatter()
        formatter.save_recommendations_append(
            recommendations_file, ranked_recs, fresh=args.fresh
        )
        formatter.save_metrics_append(metrics_file, batch_metrics, fresh=args.fresh)

        if not args.quiet:
            print(f"✓ Recommendations appended to: {recommendations_file}")
            print(f"✓ Metrics appended to: {metrics_file}")
            print(f"✅ Analysis complete! (ID: {batch_metrics.analysis_id})\n")

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
