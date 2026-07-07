/**
 * Claude Token Analyzer - Conversation Extractor Bookmarklet
 *
 * Extracts COMPLETE conversation data from claude.ai by scrolling through
 * the entire conversation to load all messages (handles virtual scrolling)
 *
 * Key improvement: Scrolls to load all messages before extraction
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
    statusEl.textContent = '⏳ Loading entire conversation...';
    document.body.appendChild(statusEl);

    // Step 1: Scroll to load all messages
    await loadAllMessages(statusEl);

    // Step 2: Extract conversation data
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

  async function loadAllMessages(statusEl) {
    // Find the scrollable conversation container
    const conversationContainer = findConversationContainer();
    if (!conversationContainer) {
      throw new Error('Could not find conversation container');
    }

    // Scroll to top first to start from beginning
    conversationContainer.scrollTop = 0;
    await new Promise(resolve => setTimeout(resolve, 500));

    // Keep track of previously loaded message count
    let previousMessageCount = 0;
    let unchangedChecks = 0;
    const maxUnchangedChecks = 5;

    // Scroll through entire conversation to load all messages
    while (unchangedChecks < maxUnchangedChecks) {
      const currentMessageCount = countVisibleMessages();

      if (currentMessageCount === previousMessageCount) {
        unchangedChecks++;
      } else {
        unchangedChecks = 0;
        previousMessageCount = currentMessageCount;
      }

      statusEl.textContent = `⏳ Loading... (${currentMessageCount} messages loaded)`;

      // Scroll up to load earlier messages
      conversationContainer.scrollTop -= 1000;
      await new Promise(resolve => setTimeout(resolve, 300));
    }

    // Now scroll to bottom to ensure we captured everything
    conversationContainer.scrollTop = conversationContainer.scrollHeight;
    await new Promise(resolve => setTimeout(resolve, 500));

    // Final scroll to top and back to ensure all content is loaded
    conversationContainer.scrollTop = 0;
    await new Promise(resolve => setTimeout(resolve, 300));
  }

  function findConversationContainer() {
    // Try multiple selectors for the scrollable container
    const selectors = [
      '[class*="conversation"]',
      '[class*="chat-container"]',
      '[class*="messages"]',
      '[role="main"]',
      'main',
    ];

    for (const selector of selectors) {
      const el = document.querySelector(selector);
      if (el && isScrollable(el)) {
        return el;
      }
    }

    // Fallback: find any scrollable div with significant height
    const allDivs = Array.from(document.querySelectorAll('div'));
    return allDivs.find(div => {
      return isScrollable(div) && div.scrollHeight > window.innerHeight * 2;
    });
  }

  function isScrollable(element) {
    return element.scrollHeight > element.clientHeight;
  }

  function countVisibleMessages() {
    const selectors = [
      '[data-message-id]',
      '[class*="message-group"]',
      '[class*="prose"][class*="message"]',
      '[role="article"]',
    ];

    for (const selector of selectors) {
      const count = document.querySelectorAll(selector).length;
      if (count > 0) return count;
    }

    return 0;
  }

  function extractConversation() {
    const messages = [];
    const conversationId = extractConversationId();
    const createdAt = new Date().toISOString();

    // Collect all message elements from the page
    const allMessages = collectAllMessageElements();

    // Extract and deduplicate messages
    const seenContent = new Set();

    for (const { element, role } of allMessages) {
      if (!role) continue;

      const content = extractMessageContent(element);
      if (!content || content.length < 1) continue;

      // Deduplicate
      if (seenContent.has(content)) continue;
      seenContent.add(content);

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

  function collectAllMessageElements() {
    const messagesByRole = [];

    // Strategy 1: Data attributes
    const dataAttrMessages = Array.from(document.querySelectorAll('[data-message-id], [data-testid*="message"]'));
    for (const el of dataAttrMessages) {
      const role = detectRole(el);
      if (role) messagesByRole.push({ element: el, role });
    }

    if (messagesByRole.length > 0) return messagesByRole;

    // Strategy 2: Class-based message containers
    const classMessages = Array.from(document.querySelectorAll('[class*="message-group"], [class*="prose"][class*="message"]'));
    for (const el of classMessages) {
      const role = detectRole(el);
      if (role) messagesByRole.push({ element: el, role });
    }

    if (messagesByRole.length > 0) return messagesByRole;

    // Strategy 3: Look in main content area
    const mainContent = document.querySelector('[role="main"], main');
    if (mainContent) {
      const messageContainers = Array.from(mainContent.querySelectorAll('[class*="message"], [class*="Message"], div[class*="rounded"]'));
      for (const el of messageContainers) {
        const role = detectRole(el);
        if (role) messagesByRole.push({ element: el, role });
      }
    }

    if (messagesByRole.length > 0) return messagesByRole;

    // Strategy 4: All divs with substantial text
    const allDivs = Array.from(document.querySelectorAll('div')).filter(div => {
      const text = div.textContent;
      return text && text.length > 40 && text.length < 15000 && !div.querySelector('input, button');
    });

    for (const el of allDivs) {
      const role = detectRole(el);
      if (role) messagesByRole.push({ element: el, role });
    }

    return messagesByRole;
  }

  function detectRole(element) {
    const classList = element.className.toLowerCase();

    // Check data attributes
    if (element.dataset.role === 'user' || element.getAttribute('data-role') === 'user') {
      return 'user';
    }
    if (element.dataset.role === 'assistant' || element.getAttribute('data-role') === 'assistant') {
      return 'assistant';
    }

    // Check class names
    if (classList.includes('user') || classList.includes('from-user') || classList.includes('user-message')) {
      return 'user';
    }
    if (classList.includes('assistant') || classList.includes('from-assistant') || classList.includes('assistant-message') || classList.includes('ai-response')) {
      return 'assistant';
    }

    // Code blocks usually from assistant
    if (element.querySelector('pre, code, [class*="codeblock"]')) {
      return 'assistant';
    }

    // Check positioning (user messages often right-aligned)
    const styles = window.getComputedStyle(element);
    if (styles.marginLeft === 'auto' || styles.marginInlineStart === 'auto') {
      return 'user';
    }

    // Check parent class
    const parent = element.parentElement;
    if (parent) {
      const parentClass = parent.className.toLowerCase();
      if (parentClass.includes('user')) return 'user';
      if (parentClass.includes('assistant')) return 'assistant';
    }

    return null;
  }

  function extractMessageContent(element) {
    let content = element.textContent.trim();

    // Remove role prefixes
    content = content.replace(/^(User|Claude|Assistant|You|Me|You said):\s*/i, '');

    // Remove UI elements and buttons
    content = content.replace(/^\s*(Copy|Copied|Share|Copy to clipboard|Edit|Delete|More|Less|\.{3})\s*$/gim, '');
    content = content.replace(/\n(Copy|Copied|Share|Copy to clipboard|Edit|Delete|\.{3})\s*$/i, '');

    content = content.trim();

    // Ensure meaningful content
    if (content.length < 1 || content.length > 20000) return null;

    return content;
  }

  function extractConversationId() {
    // Try URL patterns
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
