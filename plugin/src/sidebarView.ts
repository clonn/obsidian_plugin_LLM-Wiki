import { ItemView, WorkspaceLeaf } from "obsidian";

export const LLM_KB_LOG_VIEW = "llm-kb-log-view";

/**
 * Sidebar view for LLM-KB output.
 *
 * Two modes:
 *   1. Log mode  — streaming pre-formatted text from CLI tools
 *   2. Search mode — structured results with clickable file links
 *
 * Follows Obsidian plugin guidelines:
 *   - Uses contentEl (not containerEl.children[1])
 *   - Builds DOM via createEl / createDiv (never innerHTML)
 *   - CSS classes for styling (no inline styles)
 */
export class LlmKbLogView extends ItemView {
  private bodyEl!: HTMLElement;

  constructor(leaf: WorkspaceLeaf) {
    super(leaf);
  }

  getViewType(): string {
    return LLM_KB_LOG_VIEW;
  }

  getDisplayText(): string {
    return "LLM-KB Log";
  }

  getIcon(): string {
    return "scroll-text";
  }

  async onOpen(): Promise<void> {
    const container = this.contentEl;
    container.empty();
    container.addClass("llm-kb-view");

    container.createEl("h4", { text: "LLM-KB", cls: "llm-kb-view__title" });
    this.bodyEl = container.createDiv({ cls: "llm-kb-view__body" });
  }

  // ── Log mode helpers ──────────────────────────────────────

  /** Append plain text (streaming CLI output). */
  append(text: string): void {
    if (!this.bodyEl) return;
    // Ensure a <pre> block exists for log output
    let pre = this.bodyEl.querySelector<HTMLPreElement>(".llm-kb-log");
    if (!pre) {
      pre = this.bodyEl.createEl("pre", { cls: "llm-kb-log" });
    }
    pre.appendText(text);
    pre.scrollIntoView({ block: "end" });
  }

  // ── Search mode helpers ───────────────────────────────────

  /** Render a search result card with clickable file link + context. */
  addSearchResult(opts: {
    rank: number;
    score: string;
    filePath: string;
    title: string;
    context: string;
  }): void {
    if (!this.bodyEl) return;

    const card = this.bodyEl.createDiv({ cls: "llm-kb-result" });

    // Header row: rank + score badge
    const header = card.createDiv({ cls: "llm-kb-result__header" });
    header.createSpan({ text: `${opts.rank}.`, cls: "llm-kb-result__rank" });
    header.createSpan({ text: opts.score, cls: "llm-kb-result__score" });

    // Clickable file link — uses Obsidian's openLinkText
    const link = card.createEl("a", {
      text: opts.filePath,
      cls: "llm-kb-result__link internal-link",
      attr: { "data-href": opts.filePath },
    });
    this.registerDomEvent(link, "click", (e: MouseEvent) => {
      e.preventDefault();
      const target = opts.filePath.replace(/\.md$/, "");
      this.app.workspace.openLinkText(target, "", true);
    });

    // Title
    if (opts.title) {
      card.createDiv({ text: opts.title, cls: "llm-kb-result__title" });
    }

    // Context snippet
    if (opts.context) {
      card.createEl("small", {
        text: opts.context,
        cls: "llm-kb-result__context",
      });
    }
  }

  /** Show a heading for the search results section. */
  addSearchHeading(query: string, count: number): void {
    if (!this.bodyEl) return;
    const heading = this.bodyEl.createDiv({ cls: "llm-kb-search-heading" });
    heading.createEl("strong", { text: `"${query}"` });
    heading.createSpan({ text: ` — ${count} results` });
  }

  // ── Common ────────────────────────────────────────────────

  clear(): void {
    if (!this.bodyEl) return;
    this.bodyEl.empty();
  }

  async onClose(): Promise<void> {
    this.contentEl.empty();
  }
}
