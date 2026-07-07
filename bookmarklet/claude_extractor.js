/**
 * Claude Token Analyzer - Conversation Extractor Bookmarklet
 *
 * Extracts conversation data from claude.ai and exports as JSON
 * Usage: Create bookmark with javascript: code from claude_extractor_bookmarklet.txt
 *
 * Multiple extraction strategies to handle various DOM structures:
 * 1. Data attributes (most reliable)
 * 2. Class name patterns
 * 3. Element positioning heuristics
 * 4. Conversation thread parsing
 * 5. Full page text fallback
 */

(async function() {
  try {
    const statusEl = document.createElement('div');
    statusEl.id = 'claude-extractor-status';
    statusEl.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #4F46E5;
      color: white;
      padding: 16px 24px;
      border-radius: 8px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
      z-index: 10000;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    `;
    statusEl.textContent = '⏳ Extracting conversation...';
    document.body.appendChild(statusEl);

    const conversationData = extractConversation();

    if (!conversationData || conversationData.messages.length === 0) {
      throw new Error('No conversation found. Make sure you\'re on a claude.ai conversation page.');
    }

    statusEl.textContent = `✓ Extracted ${conversationData.messages.length} messages`;
    statusEl.style.background = '#10B981';

    downloadJSON(conversationData, 'claude-conversation.json');

    setTimeout(() => {
      statusEl.textContent = '✓ Conversation exported! Check your Downloads folder.';
      setTimeout(() => statusEl.remove(), 3000);
    }, 500);

  } catch (error) {
    console.error('Extraction failed:', error);
    const statusEl = document.getElementById('claude-extractor-status');
    if (statusEl) {
      statusEl.textContent = `✗ Error: ${error.message}`;
      statusEl.style.background = '#EF4444';
      setTimeout(() => statusEl.remove(), 4000);
    } else {
      alert(`Extraction failed: ${error.message}`);
    }
  }

  function extractConversation() {
    const messages = [];
    const conversationId = extractConversationId();
    const createdAt = new Date().toISOString();

    // Strategy 1: Look for message container elements with data attributes
    let messageElements = Array.from(document.querySelectorAll('[data-message-id], [data-testid*="message"], [class*="message-group"]'));

    if (messageElements.length === 0) {
      // Strategy 2: Look for prose/text content containers
      messageElements = Array.from(document.querySelectorAll('[class*="prose"], [class*="markdown"], [role="article"]'));
    }

    if (messageElements.length === 0) {
      // Strategy 3: Look in main content area
      const mainContent = document.querySelector('[role="main"], main, [class*="chat"], [class*="conversation"]');
      if (mainContent) {
        messageElements = Array.from(mainContent.querySelectorAll('[class*="message"], [class*="Message"], [class*="response"]'));
      }
    }

    if (messageElements.length === 0) {
      // Strategy 4: Get all divs with substantial text content
      const allDivs = Array.from(document.querySelectorAll('div'));
      messageElements = allDivs.filter(div => {
        const text = div.textContent;
        return text && text.length > 30 && text.length < 10000 && !div.querySelector('input, button, [role="button"]');
      });
    }

    // Extract messages from elements
    for (const el of messageElements) {
      const role = detectRole(el);
      if (!role) continue;

      const content = extractMessageContent(el);
      if (content && content.trim().length > 0) {
        // Check if we already have this message (avoid duplicates)
        const isDuplicate = messages.some(m => m.content === content && m.role === role);
        if (!isDuplicate) {
          messages.push({
            role: role,
            content: content,
            timestamp: new Date().toISOString(),
          });
        }
      }
    }

    // If extraction still minimal, try parsing the visible conversation thread
    if (messages.length < 2) {
      messages.length = 0;
      messages.push(...extractFromConversationThread());
    }

    // If still nothing, try extracting from structured data
    if (messages.length === 0) {
      messages.push(...extractFromPageText());
    }

    return {
      id: conversationId,
      created_at: createdAt,
      messages: messages,
    };
  }

  function detectRole(element) {
    const classList = element.className.toLowerCase();

    // Check data attributes first
    if (element.dataset.role === 'user' || element.getAttribute('data-role') === 'user') {
      return 'user';
    }
    if (element.dataset.role === 'assistant' || element.getAttribute('data-role') === 'assistant') {
      return 'assistant';
    }

    // Check text and class indicators
    if (classList.includes('user') || classList.includes('from-user')) {
      return 'user';
    }
    if (classList.includes('assistant') || classList.includes('from-assistant') || classList.includes('ai-response')) {
      return 'assistant';
    }

    // Heuristic: code blocks typically from assistant
    if (element.querySelector('pre, code')) {
      return 'assistant';
    }

    // Heuristic: right-aligned or specific styling typically user
    const styles = window.getComputedStyle(element);
    if (styles.marginLeft === 'auto' || styles.marginInlineStart === 'auto' || styles.float === 'right') {
      return 'user';
    }

    // Check if parent has role indicators
    const parent = element.parentElement;
    if (parent) {
      const parentClass = parent.className.toLowerCase();
      if (parentClass.includes('user') || parentClass.includes('from-user')) return 'user';
      if (parentClass.includes('assistant') || parentClass.includes('from-assistant')) return 'assistant';
    }

    return null;
  }

  function extractMessageContent(element) {
    let content = element.textContent.trim();

    // Remove common UI artifacts
    content = content.replace(/^(User|Claude|Assistant|You|Me):\s*/i, '');
    content = content.replace(/^\s*(Copy|Copied|Share|Copy to clipboard|\.{3}|More|Less)\s*$/gim, '');
    content = content.replace(/\n(Copy|Copied|Share|Copy to clipboard|\.{3})\s*$/i, '');
    content = content.trim();

    if (content.length < 1) return null;

    return content;
  }

  function extractFromConversationThread() {
    const messages = [];

    const chatContainers = Array.from(document.querySelectorAll(
      '[class*="chat"], [class*="conversation"], [role="region"]'
    ));

    for (const container of chatContainers) {
      const potentialMessages = Array.from(container.children).filter(child => {
        const text = child.textContent;
        return text && text.length > 20 && text.length < 20000;
      });

      for (const msg of potentialMessages) {
        const role = detectRole(msg);
        if (!role) continue;

        const content = extractMessageContent(msg);
        if (content && content.length > 1) {
          const isDuplicate = messages.some(m => m.content === content);
          if (!isDuplicate) {
            messages.push({
              role: role,
              content: content,
              timestamp: new Date().toISOString(),
            });
          }
        }
      }

      if (messages.length > 0) break;
    }

    return messages;
  }

  function extractFromPageText() {
    const messages = [];
    const pageText = document.body.innerText;
    const lines = pageText.split('\n').filter(l => l.trim().length > 0);

    let currentRole = null;
    let currentContent = [];

    for (let i = 0; i < lines.length; i++) {
      const trimmed = lines[i].trim();
      const lower = trimmed.toLowerCase();

      if (lower.match(/^(user|you|me)[\s:]*$/) && i + 1 < lines.length) {
        if (currentContent.length > 0) {
          messages.push({
            role: currentRole || 'assistant',
            content: currentContent.join('\n').trim(),
            timestamp: new Date().toISOString(),
          });
          currentContent = [];
        }
        currentRole = 'user';
      } else if (lower.match(/^(claude|assistant|ai)[\s:]*$/) && i + 1 < lines.length) {
        if (currentContent.length > 0) {
          messages.push({
            role: currentRole || 'user',
            content: currentContent.join('\n').trim(),
            timestamp: new Date().toISOString(),
          });
          currentContent = [];
        }
        currentRole = 'assistant';
      } else if (trimmed.length > 0 && currentRole) {
        if (!trimmed.match(/^(copy|copied|share|\.{3}|more|less)$/i)) {
          currentContent.push(trimmed);
        }
      }
    }

    if (currentContent.length > 0) {
      messages.push({
        role: currentRole || 'assistant',
        content: currentContent.join('\n').trim(),
        timestamp: new Date().toISOString(),
      });
    }

    return messages;
  }

  function extractConversationId() {
    const urlMatch = window.location.pathname.match(/\/chat\/([a-f0-9-]+)/);
    if (urlMatch) return urlMatch[1];

    const href = window.location.href;
    if (href.includes('claude.ai')) {
      const idMatch = href.match(/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/);
      if (idMatch) return idMatch[0];
    }

    return `conv_${Date.now()}`;
  }

  function downloadJSON(data, filename) {
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
})();
