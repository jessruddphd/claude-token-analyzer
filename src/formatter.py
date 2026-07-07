"""Report formatting and output."""
import json
from typing import List

from src.analyzer import BatchMetrics
from src.recommendations import Recommendation, RecommendationPriority


class ReportFormatter:
    """Format and output analysis reports."""

    def print_report(self, metrics: BatchMetrics, recommendations: List[Recommendation]) -> None:
        """Print formatted report to console.

        Args:
            metrics: Batch metrics from analysis.
            recommendations: List of recommendations.
        """
        print("\n" + "=" * 70)
        print("📊 CLAUDE TOKEN UTILIZATION REPORT")
        print("=" * 70 + "\n")

        # Summary statistics
        print("📈 SUMMARY STATISTICS")
        print("-" * 70)
        print(f"Total Conversations:     {metrics.total_conversations}")
        print(f"Total Messages:          {metrics.total_messages}")
        print(f"Total Tokens (est.):     {metrics.total_tokens:,}")
        print(f"Avg Messages/Convo:      {metrics.avg_messages_per_conversation:.1f}")
        print(f"Avg Tokens/Convo:        {metrics.avg_tokens_per_conversation:,.0f}")

        print("\n" + "=" * 70)
        print("💡 PERSONALIZED RECOMMENDATIONS")
        print("=" * 70 + "\n")

        if not recommendations:
            print("✓ Great job! No major inefficiencies detected.")
        else:
            for i, rec in enumerate(recommendations, 1):
                priority_icon = {
                    RecommendationPriority.HIGH: "🔴",
                    RecommendationPriority.MEDIUM: "🟡",
                    RecommendationPriority.LOW: "🟢",
                    RecommendationPriority.INFO: "ℹ️",
                }
                icon = priority_icon.get(rec.priority, "•")

                print(f"{icon} {rec.priority.value} - {rec.category}")
                print(f"\n   Issue:          {rec.issue}")
                print(f"   Impact:         {rec.impact}")
                print(f"   Recommendation: {rec.recommendation}")
                print(f"   Action:         {rec.action}")

                # Show example if available
                if rec.example:
                    print(f"\n   📝 EXAMPLE FROM YOUR CONVERSATION:")
                    print(f"      Current:  \"{rec.example.current}\"")
                    print(f"      Improved: \"{rec.example.improved}\"")

                print("\n" + "-" * 70 + "\n")

    def save_recommendations(self, filepath: str, recommendations: List[Recommendation]) -> None:
        """Save recommendations to text file.

        Args:
            filepath: Output file path.
            recommendations: List of recommendations.
        """
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("CLAUDE TOKEN UTILIZATION - PERSONALIZED RECOMMENDATIONS\n")
            f.write("=" * 70 + "\n\n")

            for i, rec in enumerate(recommendations, 1):
                f.write(f"{i}. {rec.priority.value} - {rec.category}\n")
                f.write(f"   Issue:          {rec.issue}\n")
                f.write(f"   Impact:         {rec.impact}\n")
                f.write(f"   Recommendation: {rec.recommendation}\n")
                f.write(f"   Action:         {rec.action}\n\n")

    def save_metrics(self, filepath: str, metrics: BatchMetrics) -> None:
        """Save metrics to JSON file.

        Args:
            filepath: Output file path.
            metrics: Batch metrics to save.
        """
        metrics_dict = {
            "total_conversations": metrics.total_conversations,
            "total_messages": metrics.total_messages,
            "total_tokens": metrics.total_tokens,
            "avg_messages_per_conversation": metrics.avg_messages_per_conversation,
            "avg_tokens_per_conversation": metrics.avg_tokens_per_conversation,
            "conversations_with_clarifications": metrics.conversations_with_clarifications,
            "conversations_with_long_chains": metrics.conversations_with_long_chains,
            "conversations_with_short_prompts": metrics.conversations_with_short_prompts,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metrics_dict, f, indent=2)
