/**
 * Claude Token Analyzer - Conversation Extractor Bookmarklet
 *
 * Robust extraction that handles virtual scrolling by scrolling through
 * the entire conversation and waiting for all messages to load.
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
    statusEl.textContent = '⏳ Loading entire conversation (this may take a moment)...';
    document.body.appendChild(statusEl);

    // Find and scroll the conversation
    await scrollToLoadAllMessages(statusEl);

    // Extract all messages from the page
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

  async function scrollToLoadAllMessages(statusEl) {
    // Find the main scrollable conversation container
    let container = document.querySelector('[role="main"]');
    if (!container) container = document.querySelector('main');
    if (!container) {
      const all = document.querySelectorAll('div');
      for (let div of all) {
        if (div.scrollHeight > window.innerHeight * 2 && div.clientHeight < div.scrollHeight) {
          container = div;
          break;
        }
      }
    }

    if (!container) {
      throw new Error('Could not find conversation container');
    }

    // Scroll to top first
    container.scrollTop = 0;
    await sleep(1000);

    let previousHeight = 0;
    let noChangeCount = 0;
    const maxNoChangeAttempts = 8;

    // Scroll upward (earlier messages are typically above)
    while (noChangeCount < maxNoChangeAttempts) {
      const currentHeight = container.scrollHeight;

      if (currentHeight === previousHeight) {
        noChangeCount++;
        statusEl.textContent = `⏳ Checking for more messages... (${noChangeCount}/${maxNoChangeAttempts})`;
      } else {
        noChangeCount = 0;
        previousHeight = currentHeight;
        statusEl.textContent = `⏳ Loading messages... (Height: ${Math.round(currentHeight)}px)`;
      }

      // Scroll up aggressively
      container.scrollTop = Math.max(0, container.scrollTop - 2000);
      await sleep(500);
    }

    // Now scroll all the way to bottom
    container.scrollTop = container.scrollHeight;
    await sleep(800);

    // And back to top to make sure everything is loaded
    container.scrollTop = 0;
    await sleep(500);
  }

  function extractConversation() {
    const messages = [];
    const conversationId = extractConversationId();
    const createdAt = new Date().toISOString();

    // Collect ALL potential message elements
    const messageElements = findAllMessageElements();
    const seenMessages = new Set();

    for (const element of messageElements) {
      const role = detectRole(element);
      if (!role) continue;

      const content = extractMessageContent(element);
      if (!content || content.length < 2) continue;

      // Create a signature to avoid duplicates
      const signature = `${role}::${content.substring(0, 100)}`;
      if (seenMessages.has(signature)) continue;
      seenMessages.add(signature);

      messages.push({
        role: role,
        content: content,
        timestamp: new Date().toISOString(),
      });
    }

    return {
      id: conversationId,
      created_at: createdAt,
      messages: messages,
    };
  }

  function findAllMessageElements() {
    const found = [];

    // Strategy 1: Look for elements with data attributes
    const dataAttrElements = document.querySelectorAll('[data-message-id], [data-testid*="message"]');
    for (let el of dataAttrElements) {
      found.push(el);
    }

    // Strategy 2: Look for message-group or message containers
    const messageGroups = document.querySelectorAll('[class*="message-group"], [class*="message-container"]');
    for (let el of messageGroups) {
      // Find actual content within
      const content = el.querySelector('[class*="prose"], [class*="markdown"], p, div');
      if (content) found.push(content);
    }

    // Strategy 3: Main content area
    const main = document.querySelector('[role="main"], main');
    if (main) {
      // Look for divs that are direct children or close to it
      const candidates = main.querySelectorAll('div[class*="message"], div[class*="response"], div[class*="turn"]');
      for (let el of candidates) {
        found.push(el);
      }
    }

    // Strategy 4: Find ANY divs with substantial text (backup)
    const allDivs = document.querySelectorAll('div');
    for (let div of allDivs) {
      const text = div.textContent.trim();
      // Look for divs with actual message-like content
      if (text.length > 50 && text.length < 20000) {
        // Avoid UI elements
        if (!div.querySelector('input, button, textarea, [contenteditable]')) {
          // Check if it contains actual message-like structure
          if (div.children.length < 50) { // Not too many children
            found.push(div);
          }
        }
      }
    }

    // Filter to remove duplicates and very small elements
    const unique = [];
    const textSeen = new Set();

    for (let el of found) {
      const text = el.textContent.trim();
      if (text.length < 2) continue;
      if (textSeen.has(text.substring(0, 200))) continue;
      textSeen.add(text.substring(0, 200));
      unique.push(el);
    }

    return unique;
  }

  function detectRole(element) {
    const classList = (element.className || '').toLowerCase();
    const parent = element.parentElement;
    const parentClass = (parent?.className || '').toLowerCase();

    // Check data attributes
    if (element.dataset.role === 'user') return 'user';
    if (element.dataset.role === 'assistant') return 'assistant';

    // Check classes
    if (classList.includes('user') || classList.includes('from-user') || parentClass.includes('user')) {
      return 'user';
    }
    if (classList.includes('assistant') || classList.includes('from-assistant') || parentClass.includes('assistant')) {
      return 'assistant';
    }

    // Code blocks → likely assistant
    if (element.querySelector('pre, code')) {
      return 'assistant';
    }

    // Check grandparent for role info
    const gp = parent?.parentElement;
    const gpClass = (gp?.className || '').toLowerCase();
    if (gpClass.includes('user')) return 'user';
    if (gpClass.includes('assistant')) return 'assistant';

    // Look at all ancestors for clues
    let current = element;
    for (let i = 0; i < 5; i++) {
      if (!current) break;
      const c = (current.className || '').toLowerCase();
      if (c.includes('user-message') || c.includes('from-user')) return 'user';
      if (c.includes('assistant-message') || c.includes('from-assistant') || c.includes('ai-response')) return 'assistant';
      current = current.parentElement;
    }

    // Default: if we can't determine, skip
    return null;
  }

  function extractMessageContent(element) {
    let text = element.textContent.trim();

    // Remove common UI text
    text = text.replace(/^(User|You|Assistant|Claude|Me):\s*/i, '');
    text = text.replace(/\n\s*(Copy|Copied|Share|Edit|Delete|More|Less|\.{3})\s*$/gm, '');
    text = text.replace(/^\s*(Copy|Copied|Share|Edit|Delete|More|Less|\.{3})\s*\n/gm, '');
    text = text.trim();

    if (text.length < 2 || text.length > 25000) {
      return null;
    }

    return text;
  }

  function extractConversationId() {
    const match = window.location.pathname.match(/\/chat\/([a-f0-9-]+)/);
    if (match) return match[1];

    const hrefMatch = window.location.href.match(/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/);
    if (hrefMatch) return hrefMatch[0];

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

  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
})();
