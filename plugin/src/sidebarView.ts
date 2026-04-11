import { ItemView, WorkspaceLeaf } from "obsidian";

export const LLM_KB_LOG_VIEW = "llm-kb-log-view";

/**
 * Sidebar view that streams the output of the latest compile / lint run.
 * The plugin pushes lines into it via `append()` from its subprocess handlers.
 */
export class LlmKbLogView extends ItemView {
  private logEl: HTMLElement | null = null;

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
    const container = this.containerEl.children[1] as HTMLElement;
    container.empty();
    container.createEl("h3", { text: "LLM-KB log" });
    this.logEl = container.createEl("pre", {
      cls: "llm-kb-log",
      attr: { style: "white-space:pre-wrap; font-size:0.85em;" },
    });
  }

  append(text: string): void {
    if (!this.logEl) return;
    this.logEl.appendText(text);
    this.logEl.scrollIntoView({ block: "end" });
  }

  clear(): void {
    if (!this.logEl) return;
    this.logEl.empty();
  }

  async onClose(): Promise<void> {
    // no-op
  }
}
