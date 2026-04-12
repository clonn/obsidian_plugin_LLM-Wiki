import {
  App,
  Editor,
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

export default class LlmKbPlugin extends Plugin {
  settings!: LlmKbSettings;
  statusBarEl!: HTMLElement;

  async onload(): Promise<void> {
    await this.loadSettings();

    // ── Register view ───────────────────────────────────────
    this.registerView(
      LLM_KB_LOG_VIEW,
      (leaf: WorkspaceLeaf) => new LlmKbLogView(leaf),
    );

    // ── Status bar (desktop only) ───────────────────────────
    this.statusBarEl = this.addStatusBarItem();
    this.statusBarEl.createEl("span", { text: "LLM-KB", cls: "llm-kb-status" });
    this.refreshStatusBar();
    // Refresh counts every 30 seconds
    this.registerInterval(
      window.setInterval(() => this.refreshStatusBar(), 30_000),
    );

    // ── Commands ────────────────────────────────────────────

    // Ingest: only available when a file is open
    this.addCommand({
      id: "llm-kb-ingest-current-note",
      name: "Ingest current note into raw/",
      checkCallback: (checking: boolean) => {
        const file = this.app.workspace.getActiveFile();
        if (!file) return false;
        if (checking) return true;
        this.ingestCurrent(file);
        return true;
      },
    });

    this.addCommand({
      id: "llm-kb-compile",
      name: "Compile wiki from raw/",
      callback: () => this.runTool("compile.compile", []),
    });

    this.addCommand({
      id: "llm-kb-query",
      name: "Ask the wiki",
      callback: () => {
        new InputModal(this.app, {
          title: "Ask the wiki",
          placeholder: "你的問題...",
          buttonText: "Ask",
          onSubmit: (q) => this.runTool("query.query", [q]),
        }).open();
      },
    });

    this.addCommand({
      id: "llm-kb-lint",
      name: "Lint wiki",
      callback: () => this.runTool("lint.lint", []),
    });

    this.addCommand({
      id: "llm-kb-search",
      name: "Search wiki",
      callback: () => {
        new InputModal(this.app, {
          title: "Search wiki",
          placeholder: "搜尋關鍵字...",
          buttonText: "Search",
          onSubmit: (q) => this.runSearch(q),
        }).open();
      },
    });

    this.addCommand({
      id: "llm-kb-export-graph",
      name: "Export link graph (JSON)",
      callback: () => this.runTool("graph.export_graph", []),
    });

    this.addCommand({
      id: "llm-kb-open-index",
      name: "Open index.md",
      callback: async () => {
        const file = this.app.vault.getAbstractFileByPath("index.md");
        if (file instanceof TFile) {
          await this.app.workspace.getLeaf(true).openFile(file);
        } else {
          new Notice("index.md not found — run init first.");
        }
      },
    });

    this.addCommand({
      id: "llm-kb-open-log-view",
      name: "Open log sidebar",
      callback: () => this.activateLogView(),
    });

    // ── Settings tab ────────────────────────────────────────
    this.addSettingTab(new LlmKbSettingTab(this.app, this));
  }

  onunload(): void {
    this.app.workspace.detachLeavesOfType(LLM_KB_LOG_VIEW);
  }

  async loadSettings(): Promise<void> {
    this.settings = Object.assign(
      {},
      DEFAULT_SETTINGS,
      await this.loadData(),
    );
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

  private async ingestCurrent(file: TFile): Promise<void> {
    const today = new Date().toISOString().slice(0, 10);
    const slug = file.basename.replace(/[^0-9a-zA-Z\u4e00-\u9fff]+/g, "-");
    const newPath = `raw/${today}_${slug}.md`;

    if (this.app.vault.getAbstractFileByPath(newPath)) {
      new Notice(`${newPath} already exists — skipping.`);
      return;
    }

    const content = await this.app.vault.read(file);
    let out = content;
    if (!content.startsWith("---\n")) {
      out =
        `---\ntitle: ${file.basename}\ningested_at: ${today}\nsource: vault:${file.path}\n---\n\n` +
        content;
    }
    await this.app.vault.create(newPath, out);
    new Notice(`Ingested → ${newPath}`);
    this.refreshStatusBar();
  }

  /** Spawn `uv run python -m <module>` and stream output to the log view. */
  private async runTool(module: string, extraArgs: string[]): Promise<void> {
    const vault = this.vaultPath();
    if (!vault) {
      new Notice("Cannot determine vault path.");
      return;
    }
    const view = await this.activateLogView();
    view.clear();
    view.append(`$ uv run python -m ${module}\n\n`);

    try {
      const code = await runStreaming({
        cmd: this.settings.uvCommand,
        args: ["run", "python", "-m", module, "--vault", vault, ...extraArgs],
        cwd: this.settings.toolsPath,
        onStdout: (c) => view.append(c),
        onStderr: (c) => view.append(c),
      });
      view.append(`\n[exit ${code}]\n`);
      this.refreshStatusBar();
    } catch (e: unknown) {
      view.append(`\n[error] ${String(e)}\n`);
    }
  }

  /** Run search and render structured results with clickable links. */
  private async runSearch(query: string): Promise<void> {
    const vault = this.vaultPath();
    if (!vault) {
      new Notice("Cannot determine vault path.");
      return;
    }
    const view = await this.activateLogView();
    view.clear();

    let output = "";
    try {
      await runStreaming({
        cmd: this.settings.uvCommand,
        args: [
          "run", "python", "-m", "search.search",
          "--vault", vault, "--json-out", query,
        ],
        cwd: this.settings.toolsPath,
        onStdout: (c) => { output += c; },
        onStderr: (c) => { view.append(c); },
      });

      const results = JSON.parse(output) as Array<{
        path: string;
        score: number;
        title: string;
        context: string;
      }>;

      view.addSearchHeading(query, results.length);
      for (let i = 0; i < results.length; i++) {
        const r = results[i];
        view.addSearchResult({
          rank: i + 1,
          score: r.score.toFixed(4),
          filePath: r.path,
          title: r.title,
          context: r.context,
        });
      }

      if (results.length === 0) {
        new Notice(`No results for: ${query}`);
      }
    } catch (e: unknown) {
      view.append(`\n[error] ${String(e)}\n`);
    }
  }
}

// ── Input Modal ───────────────────────────────────────────

interface InputModalOpts {
  title: string;
  placeholder: string;
  buttonText: string;
  onSubmit: (value: string) => void;
}

class InputModal extends Modal {
  private opts: InputModalOpts;

  constructor(app: App, opts: InputModalOpts) {
    super(app);
    this.opts = opts;
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("llm-kb-modal");

    contentEl.createEl("h3", { text: this.opts.title });

    const input = contentEl.createEl("textarea", {
      cls: "llm-kb-modal__input",
      attr: { placeholder: this.opts.placeholder },
    });

    const btn = contentEl.createEl("button", {
      text: this.opts.buttonText,
      cls: "mod-cta",
    });

    this.registerDomEvent(btn, "click", () => {
      const value = input.value.trim();
      if (!value) return;
      this.close();
      this.opts.onSubmit(value);
    });

    // Submit on Enter (without Shift)
    this.registerDomEvent(input, "keydown", (e: KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        btn.click();
      }
    });

    input.focus();
  }

  onClose(): void {
    this.contentEl.empty();
  }
}
