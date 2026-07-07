/**
 * Claude Token Analyzer - Conversation Extractor Bookmarklet
 *
 * Extracts conversation data from claude.ai and exports as JSON
 * Usage: Drag this to bookmarks bar, click while on claude.ai conversation
 */

(async function() {
  try {
    // Show loading message
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

    // Extract conversation data from DOM
    const conversationData = extractConversation();

    if (!conversationData || conversationData.messages.length === 0) {
      throw new Error('No conversation found. Make sure you\'re on a claude.ai conversation page.');
    }

    // Update status
    statusEl.textContent = `✓ Extracted ${conversationData.messages.length} messages`;
    statusEl.style.background = '#10B981';

    // Download as JSON
    downloadJSON(conversationData, 'claude-conversation.json');

    // Show success message
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

    // Try multiple selectors for message containers (claude.ai may vary)
    const messageSelectors = [
      '[data-testid="message"]',
      '[class*="message"]',
      '[class*="Message"]',
      '.prose', // Common for text content
      '[role="article"]',
    ];

    let messageElements = [];
    for (const selector of messageSelectors) {
      messageElements = Array.from(document.querySelectorAll(selector));
      if (messageElements.length > 0) break;
    }

    // If still no messages, try alternative approach: look for message containers
    if (messageElements.length === 0) {
      const mainContent = document.querySelector('[role="main"]') || document.querySelector('main');
      if (mainContent) {
        messageElements = Array.from(mainContent.children).filter(
          el => el.textContent && el.textContent.length > 0
        );
      }
    }

    // Extract message content
    for (const el of messageElements) {
      const role = detectRole(el);
      if (!role) continue;

      const content = extractMessageContent(el);
      if (content && content.trim().length > 0) {
        messages.push({
          role: role,
          content: content,
          timestamp: new Date().toISOString(),
        });
      }
    }

    // If extraction still failed, try parsing visible text
    if (messages.length === 0) {
      messages.push(...extractFromVisibleText());
    }

    return {
      id: conversationId,
      created_at: createdAt,
      messages: messages,
    };
  }

  function detectRole(element) {
    const html = element.outerHTML.toLowerCase();
    const text = element.textContent.toLowerCase();

    // Check for user indicators
    if (html.includes('user') || text.includes('you:') || element.className.includes('user')) {
      return 'user';
    }

    // Check for assistant indicators
    if (html.includes('assistant') || html.includes('claude') || text.includes('claude:')) {
      return 'assistant';
    }

    // Heuristic: if it has code blocks, likely assistant
    if (element.querySelector('code') || element.querySelector('pre')) {
      return 'assistant';
    }

    // Heuristic: check visual styling for user (often right-aligned or different bg)
    const styles = window.getComputedStyle(element);
    if (styles.marginLeft === 'auto' || styles.float === 'right') {
      return 'user';
    }

    return null;
  }

  function extractMessageContent(element) {
    // Get text content
    let content = element.textContent.trim();

    // Clean up common artifacts
    content = content.replace(/^(User|Claude|Assistant|You):\s*/i, '');
    content = content.replace(/^(Copy|Copied|Share|...)/i, '');
    content = content.trim();

    return content;
  }

  function extractFromVisibleText() {
    const messages = [];
    const text = document.body.innerText;
    const lines = text.split('\n').filter(l => l.trim());

    let currentRole = null;
    let currentContent = [];

    for (const line of lines) {
      const trimmed = line.trim();

      if (trimmed.toLowerCase().startsWith('user') || trimmed.toLowerCase().startsWith('you')) {
        if (currentContent.length > 0) {
          messages.push({
            role: currentRole || 'assistant',
            content: currentContent.join('\n').trim(),
            timestamp: new Date().toISOString(),
          });
          currentContent = [];
        }
        currentRole = 'user';
      } else if (trimmed.toLowerCase().startsWith('claude') ||
                 trimmed.toLowerCase().startsWith('assistant')) {
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
        currentContent.push(trimmed);
      }
    }

    // Push last message
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
    // Try to get from URL
    const urlMatch = window.location.pathname.match(/\/chat\/([a-f0-9-]+)/);
    if (urlMatch) return urlMatch[1];

    // Fallback to timestamp
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
