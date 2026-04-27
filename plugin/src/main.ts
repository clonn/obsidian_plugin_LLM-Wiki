import {
  App,
  Modal,
  Notice,
  Plugin,
  TFile,
  WorkspaceLeaf,
} from "obsidian";
import {
  DEFAULT_SETTINGS,
  LlmKbSettings,
  LlmKbSettingTab,
} from "./settings";
import { LLM_KB_LOG_VIEW, LlmKbLogView } from "./sidebarView";
import { runStreaming } from "./runner";

/**
 * Karpathy's 4-phase knowledge-base loop:
 *   1. Ingest  — Clippings/ + vault root → raw/, then auto-link
 *   2. Compile — emit prompt for Claude Code to write wiki articles
 *   3. Query   — ask the wiki (mode picked in modal)
 *   4. Lint    — find contradictions / dead links / gaps
 *
 * https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
 */
export default class LlmKbPlugin extends Plugin {
  settings!: LlmKbSettings;
  statusBarEl!: HTMLElement;

  async onload(): Promise<void> {
    await this.loadSettings();

    this.registerView(
      LLM_KB_LOG_VIEW,
      (leaf: WorkspaceLeaf) => new LlmKbLogView(leaf),
    );

    this.statusBarEl = this.addStatusBarItem();
    this.statusBarEl.createEl("span", { text: "LLM-KB", cls: "llm-kb-status" });
    this.refreshStatusBar();
    this.registerInterval(
      window.setInterval(() => this.refreshStatusBar(), 30_000),
    );

    // ── Karpathy's 4 phases ───────────────────────────────

    this.addCommand({
      id: "llm-kb-ingest",
      name: "1. Ingest — pipeline (Clippings → raw/) + autolink",
      callback: () => this.runIngestChain(),
    });

    this.addCommand({
      id: "llm-kb-compile",
      name: "2. Compile — generate wiki prompt for Claude Code",
      callback: () => this.runTool("compile.compile", ["--incremental"]),
    });

    this.addCommand({
      id: "llm-kb-query",
      name: "3. Query — ask the wiki",
      callback: () => {
        new QueryModal(this.app, (q, mode) =>
          this.runTool("query.query", ["--mode", mode, q]),
        ).open();
      },
    });

    this.addCommand({
      id: "llm-kb-lint",
      name: "4. Lint — check vault integrity",
      callback: () => this.runTool("lint.lint", []),
    });

    // ── Navigation ────────────────────────────────────────

    this.addCommand({
      id: "llm-kb-open-index",
      name: "Open index.md",
      callback: async () => {
        const file = this.app.vault.getAbstractFileByPath("index.md");
        if (file instanceof TFile) {
          await this.app.workspace.getLeaf(true).openFile(file);
        } else {
          new Notice("index.md not found.");
        }
      },
    });

    this.addCommand({
      id: "llm-kb-open-log-view",
      name: "Open log sidebar",
      callback: () => this.activateLogView(),
    });

    this.addSettingTab(new LlmKbSettingTab(this.app, this));

    // ── Auto-run ingest on startup ────────────────────────
    if (this.settings.autoRunPipelineOnLoad) {
      this.app.workspace.onLayoutReady(() => {
        if (!this.settings.toolsPath) {
          new Notice(
            "LLM-KB: auto-ingest skipped — set Tools path in settings.",
          );
          return;
        }
        this.runIngestChain();
      });
    }
  }

  onunload(): void {
    this.app.workspace.detachLeavesOfType(LLM_KB_LOG_VIEW);
  }

  async loadSettings(): Promise<void> {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
  }

  // ── Helpers ─────────────────────────────────────────────

  private vaultPath(): string {
    // @ts-expect-error — getBasePath is implemented by FileSystemAdapter
    return this.app.vault.adapter.getBasePath?.() ?? "";
  }

  private refreshStatusBar(): void {
    const all = this.app.vault.getMarkdownFiles();
    let raw = 0;
    let wiki = 0;
    for (const f of all) {
      if (f.path.startsWith("raw/")) raw++;
      else if (f.path.startsWith("wiki/")) wiki++;
    }
    this.statusBarEl.empty();
    this.statusBarEl.createEl("span", {
      text: `raw:${raw} · wiki:${wiki}`,
      cls: "llm-kb-status",
    });
  }

  private async activateLogView(): Promise<LlmKbLogView> {
    const { workspace } = this.app;
    let leaf = workspace.getLeavesOfType(LLM_KB_LOG_VIEW)[0];
    if (!leaf) {
      leaf = workspace.getRightLeaf(false)!;
      await leaf.setViewState({ type: LLM_KB_LOG_VIEW, active: true });
    }
    workspace.revealLeaf(leaf);
    return leaf.view as LlmKbLogView;
  }

  /** Phase 1: pipeline (Clippings → raw/) → autolink. */
  private async runIngestChain(): Promise<void> {
    await this.runTool("pipeline.pipeline", ["--apply"]);
    await this.runTool("link.autolink", ["--apply"]);
  }

  /** Spawn `uv run python -m <module>` and stream output to the log view. */
  private async runTool(module: string, extraArgs: string[]): Promise<number> {
    const vault = this.vaultPath();
    if (!vault) {
      new Notice("Cannot determine vault path.");
      return -1;
    }
    if (!this.settings.toolsPath) {
      new Notice("LLM-KB: Tools path not set.");
      return -1;
    }
    const view = await this.activateLogView();
    view.append(`\n$ uv run python -m ${module} ${extraArgs.join(" ")}\n`);

    try {
      const code = await runStreaming({
        cmd: this.settings.uvCommand,
        args: ["run", "python", "-m", module, "--vault", vault, ...extraArgs],
        cwd: this.settings.toolsPath,
        onStdout: (c) => view.append(c),
        onStderr: (c) => view.append(c),
      });
      view.append(`[exit ${code}]\n`);
      this.refreshStatusBar();
      return code;
    } catch (e: unknown) {
      view.append(`[error] ${String(e)}\n`);
      return -1;
    }
  }
}

// ── Query modal with mode picker ──────────────────────────

type QueryMode = "quick" | "standard" | "deep";

class QueryModal extends Modal {
  private onSubmit: (query: string, mode: QueryMode) => void;

  constructor(app: App, onSubmit: (q: string, m: QueryMode) => void) {
    super(app);
    this.onSubmit = onSubmit;
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("llm-kb-modal");
    contentEl.createEl("h3", { text: "Query the wiki" });

    const modeRow = contentEl.createDiv({ cls: "llm-kb-modal__mode" });
    modeRow.createEl("label", { text: "Mode: " });
    const modeSelect = modeRow.createEl("select");
    for (const [value, label] of [
      ["quick", "Quick — hot cache + index"],
      ["standard", "Standard — top articles"],
      ["deep", "Deep — full vault + web"],
    ] as const) {
      const opt = modeSelect.createEl("option", { text: label });
      opt.value = value;
    }
    modeSelect.value = "standard";

    const input = contentEl.createEl("textarea", {
      cls: "llm-kb-modal__input",
      attr: { placeholder: "你的問題..." },
    });

    const btn = contentEl.createEl("button", {
      text: "Ask",
      cls: "mod-cta",
    });

    const submit = () => {
      const value = input.value.trim();
      if (!value) return;
      const mode = modeSelect.value as QueryMode;
      this.close();
      this.onSubmit(value, mode);
    };

    btn.addEventListener("click", submit);
    input.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submit();
      }
    });

    input.focus();
  }

  onClose(): void {
    this.contentEl.empty();
  }
}
