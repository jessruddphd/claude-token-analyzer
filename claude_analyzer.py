"""
Claude Token Utilization Analyzer
Analyzes exported Claude conversations and provides personalized recommendations
"""
import json
import argparse
import re
from collections import defaultdict, Counter
from datetime import datetime
from typing import List, Dict, Any
import statistics

class ClaudeUsageAnalyzer:
    def __init__(self):
        self.conversations = []
        self.metrics = defaultdict(list)
        self.recommendations = []
        
    def load_conversations(self, filepath: str):
        """Load conversations from exported JSON file.

        Supports two formats:
        1. Claude.ai web export — list of conversation dicts each with a
           ``messages`` key (``[{messages: [{role, content}, ...]}, ...]``)
        2. Claude Code (local) export — flat list of typed event objects
           produced by the claude-vscode / claude-cli entrypoint.  Each
           user/assistant turn is its own top-level object whose content
           lives at ``message.content[].text``.  We reassemble these events
           into a single conversation dict so the rest of the pipeline works
           unchanged.
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, dict):
                if 'conversations' in data:
                    self.conversations = data['conversations']
                elif 'chat_messages' in data:
                    self.conversations = [data]
                else:
                    self.conversations = [data]

            elif isinstance(data, list):
                # Detect Claude Code export: top-level entries have a ``type``
                # field that is one of the known event types rather than being
                # message dicts with a ``role`` field.
                message_like = [
                    item for item in data
                    if isinstance(item, dict) and item.get('type') in ('user', 'assistant')
                ]
                non_message = [
                    item for item in data
                    if isinstance(item, dict) and item.get('type') not in ('user', 'assistant', None)
                ]

                is_claude_code_export = len(non_message) > 0 or (
                    message_like and 'message' in message_like[0]
                )

                if is_claude_code_export:
                    print("  (detected Claude Code / claude-vscode export format)")
                    messages = []
                    for item in message_like:
                        raw_msg = item.get('message', {})
                        role = raw_msg.get('role') or item.get('type', '')
                        content_raw = raw_msg.get('content', '')

                        # content can be a string or a list of typed blocks
                        if isinstance(content_raw, str):
                            text = content_raw
                        elif isinstance(content_raw, list):
                            text = ' '.join(
                                block.get('text', '')
                                for block in content_raw
                                if isinstance(block, dict) and block.get('type') == 'text'
                            )
                        else:
                            text = ''

                        if text:
                            messages.append({'role': role, 'content': text})

                    self.conversations = [{'messages': messages}]
                else:
                    self.conversations = data

            print(f"✓ Loaded {len(self.conversations)} conversation(s)")
            return True
        except Exception as e:
            print(f"✗ Error loading file: {e}")
            return False
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters for English)"""
        if not text:
            return 0
        return len(text) // 4
    
    def classify_message_type(self, text: str) -> str:
        """Classify message as code, question, instruction, etc."""
        text_lower = text.lower()
        
        if re.search(r'```|def |class |function|import |const |let |var ', text):
            return 'code'
        elif text.endswith('?') or text_lower.startswith(('what', 'how', 'why', 'when', 'where', 'can you')):
            return 'question'
        elif re.search(r'\b(create|build|make|generate|write|implement)\b', text_lower):
            return 'instruction'
        elif re.search(r'\b(fix|debug|error|issue|problem)\b', text_lower):
            return 'debugging'
        else:
            return 'other'
    
    def analyze_conversation(self, conversation: Dict) -> Dict:
        """Analyze a single conversation"""
        metrics = {
            'message_count': 0,
            'user_messages': 0,
            'assistant_messages': 0,
            'total_tokens': 0,
            'avg_prompt_length': 0,
            'message_types': Counter(),
            'has_clarifications': False,
            'conversation_length': 0,
            'short_prompts': 0,
            'code_queries': 0
        }
        
        messages = []
        
        # Extract messages from different formats
        if 'messages' in conversation:
            messages = conversation['messages']
        elif 'chat_messages' in conversation:
            messages = conversation['chat_messages']
        elif isinstance(conversation, list):
            messages = conversation
        
        prompt_lengths = []
        prev_was_question = False
        
        for msg in messages:
            role = msg.get('role') or msg.get('sender') or msg.get('type', '')
            content = msg.get('content') or msg.get('text') or msg.get('message', '')
            
            if not content:
                continue
            
            metrics['message_count'] += 1
            tokens = self.estimate_tokens(str(content))
            metrics['total_tokens'] += tokens
            
            if role in ['user', 'human']:
                metrics['user_messages'] += 1
                prompt_lengths.append(len(str(content)))
                
                # Check for short prompts
                if len(str(content)) < 50:
                    metrics['short_prompts'] += 1
                
                # Classify message type
                msg_type = self.classify_message_type(str(content))
                metrics['message_types'][msg_type] += 1
                
                if msg_type == 'code':
                    metrics['code_queries'] += 1
                
                # Detect clarifications (question followed by another question)
                if msg_type == 'question' and prev_was_question:
                    metrics['has_clarifications'] = True
                prev_was_question = (msg_type == 'question')
            
            elif role in ['assistant', 'ai', 'claude']:
                metrics['assistant_messages'] += 1
        
        if prompt_lengths:
            metrics['avg_prompt_length'] = statistics.mean(prompt_lengths)
        
        metrics['conversation_length'] = metrics['message_count']
        
        return metrics
    
    def analyze_all(self):
        """Analyze all loaded conversations"""
        print("\n🔍 Analyzing conversations...\n")
        
        for conv in self.conversations:
            metrics = self.analyze_conversation(conv)
            
            for key, value in metrics.items():
                if key != 'message_types':
                    self.metrics[key].append(value)
                else:
                    # Aggregate message types
                    if 'message_types' not in self.metrics:
                        self.metrics['message_types'] = Counter()
                    self.metrics['message_types'].update(value)
    
    def generate_recommendations(self):
        """Generate personalized recommendations based on analysis"""
        self.recommendations = []
        
        # 1. Long conversation analysis
        long_convos = [c for c in self.metrics['conversation_length'] if c > 40]
        if long_convos:
            avg_long = statistics.mean(long_convos)
            token_waste = sum(self.metrics['total_tokens']) * 0.3  # Rough estimate
            self.recommendations.append({
                'priority': 'HIGH',
                'category': 'Context Management',
                'issue': f"Found {len(long_convos)} conversations with 40+ messages (avg: {avg_long:.0f})",
                'impact': f"Estimated token waste: ~{token_waste:,.0f} tokens",
                'recommendation': "Start new conversations when switching topics. Each message costs tokens for the entire context.",
                'action': "When you see a conversation reaching 30+ messages, ask yourself: 'Is this a new topic?' If yes, start fresh."
            })
        
        # 2. Short prompt analysis
        total_prompts = sum(self.metrics['user_messages'])
        short_prompts = sum(self.metrics['short_prompts'])
        if total_prompts > 0 and (short_prompts / total_prompts) > 0.4:
            self.recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Prompt Quality',
                'issue': f"{short_prompts}/{total_prompts} prompts are very short (<50 chars)",
                'impact': "Short prompts often lead to back-and-forth clarifications, wasting tokens",
                'recommendation': "Add more context upfront: expected format, constraints, examples",
                'action': "Before sending, ask: 'What details would help Claude understand this better?'"
            })
        
        # 3. Clarification pattern
        clarification_convos = sum(1 for x in self.metrics.get('has_clarifications', []) if x)
        if clarification_convos > 0:
            self.recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Communication Efficiency',
                'issue': f"{clarification_convos} conversations show clarification patterns",
                'impact': "Each clarification round doubles your token usage for that query",
                'recommendation': "Structure prompts with: Context → Task → Constraints → Expected Output",
                'action': "Example: Instead of 'optimize this', try 'Optimize this Python function for speed (target <100ms) while maintaining readability. Return documented code.'"
            })
        
        # 4. Message type analysis
        if 'message_types' in self.metrics:
            types = self.metrics['message_types']
            total = sum(types.values())
            
            if total > 0:
                code_ratio = types.get('code', 0) / total
                question_ratio = types.get('question', 0) / total
                
                if code_ratio > 0.5:
                    self.recommendations.append({
                        'priority': 'LOW',
                        'category': 'Tool Optimization',
                        'issue': f"{code_ratio*100:.0f}% of your queries involve code",
                        'impact': "You might benefit from Cursor or Claude in an IDE",
                        'recommendation': "Consider using Cursor for code-heavy workflows (better context management for files)",
                        'action': "Try Cursor for your next coding session and compare"
                    })
                
                if question_ratio > 0.6:
                    self.recommendations.append({
                        'priority': 'LOW',
                        'category': 'Knowledge Management',
                        'issue': f"{question_ratio*100:.0f}% of messages are questions",
                        'impact': "You may be asking similar questions repeatedly",
                        'recommendation': "Build a personal knowledge base or snippet library for common answers",
                        'action': "Save Claude's best answers to frequently asked questions"
                    })
        
        # 5. Overall token usage
        total_tokens = sum(self.metrics['total_tokens'])
        total_convos = len(self.conversations)
        if total_convos > 0:
            avg_tokens_per_convo = total_tokens / total_convos
            self.recommendations.append({
                'priority': 'INFO',
                'category': 'Usage Summary',
                'issue': f"Average {avg_tokens_per_convo:,.0f} tokens per conversation",
                'impact': f"Total analyzed: {total_tokens:,.0f} tokens across {total_convos} conversations",
                'recommendation': "Benchmark: Efficient users average 5,000-10,000 tokens per conversation",
                'action': "If your average is significantly higher, apply the recommendations above"
            })
    
    def print_report(self):
        """Print formatted report to console"""
        print("\n" + "="*70)
        print("📊 CLAUDE TOKEN UTILIZATION REPORT")
        print("="*70 + "\n")
        
        # Summary stats
        print("📈 SUMMARY STATISTICS")
        print("-" * 70)
        print(f"Total Conversations:     {len(self.conversations)}")
        print(f"Total Messages:          {sum(self.metrics['message_count'])}")
        print(f"Total Tokens (est.):     {sum(self.metrics['total_tokens']):,}")
        print(f"Avg Messages/Convo:      {statistics.mean(self.metrics['conversation_length']):.1f}")
        print(f"Avg Prompt Length:       {statistics.mean(self.metrics['avg_prompt_length']):.0f} chars")
        
        if 'message_types' in self.metrics:
            print(f"\n📝 MESSAGE TYPES:")
            for msg_type, count in self.metrics['message_types'].most_common():
                print(f"  {msg_type.capitalize():15s} {count:3d} ({count/sum(self.metrics['message_types'].values())*100:.0f}%)")
        
        print("\n" + "="*70)
        print("💡 PERSONALIZED RECOMMENDATIONS")
        print("="*70 + "\n")
        
        if not self.recommendations:
            print("✓ Great job! No major inefficiencies detected.")
        else:
            for i, rec in enumerate(self.recommendations, 1):
                priority_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢", "INFO": "ℹ️"}
                print(f"{priority_icon.get(rec['priority'], '•')} {rec['priority']} - {rec['category']}")
                print(f"\n   Issue:          {rec['issue']}")
                print(f"   Impact:         {rec['impact']}")
                print(f"   Recommendation: {rec['recommendation']}")
                print(f"   Action:         {rec['action']}")
                print("\n" + "-"*70 + "\n")
    
    def save_recommendations(self, filepath: str):
        """Save recommendations to text file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("CLAUDE TOKEN UTILIZATION - PERSONALIZED RECOMMENDATIONS\n")
                f.write("="*70 + "\n\n")
                
                for i, rec in enumerate(self.recommendations, 1):
                    f.write(f"{i}. {rec['priority']} - {rec['category']}\n")
                    f.write(f"   Issue:          {rec['issue']}\n")
                    f.write(f"   Impact:         {rec['impact']}\n")
                    f.write(f"   Recommendation: {rec['recommendation']}\n")
                    f.write(f"   Action:         {rec['action']}\n\n")
            
            print(f"✓ Recommendations saved to: {filepath}")
            return True
        except Exception as e:
            print(f"✗ Error saving recommendations: {e}")
            return False
    
    def save_metrics(self, filepath: str):
        """Save metrics to JSON file"""
        try:
            # Convert Counter to dict for JSON serialization
            metrics_json = dict(self.metrics)
            if 'message_types' in metrics_json:
                metrics_json['message_types'] = dict(metrics_json['message_types'])
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(metrics_json, f, indent=2)
            
            print(f"✓ Metrics saved to: {filepath}")
            return True
        except Exception as e:
            print(f"✗ Error saving metrics: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(
        description='Analyze Claude conversation exports and get personalized recommendations'
    )
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Path to exported Claude conversation JSON file'
    )
    parser.add_argument(
        '--output', '-o',
        default='recommendations.txt',
        help='Output file for recommendations (default: recommendations.txt)'
    )
    parser.add_argument(
        '--metrics', '-m',
        default='metrics.json',
        help='Output file for metrics JSON (default: metrics.json)'
    )
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = ClaudeUsageAnalyzer()
    
    # Load conversations
    if not analyzer.load_conversations(args.input):
        return 1
    
    # Analyze
    analyzer.analyze_all()
    
    # Generate recommendations
    analyzer.generate_recommendations()
    
    # Print report
    analyzer.print_report()
    
    # Save outputs
    analyzer.save_recommendations(args.output)
    analyzer.save_metrics(args.metrics)
    
    print(f"\n✅ Analysis complete!\n")
    return 0

if __name__ == '__main__':
    exit(main())