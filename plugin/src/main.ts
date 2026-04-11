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

export default class LlmKbPlugin extends Plugin {
  settings!: LlmKbSettings;
  statusBar!: HTMLElement;

  async onload(): Promise<void> {
    await this.loadSettings();

    this.registerView(
      LLM_KB_LOG_VIEW,
      (leaf: WorkspaceLeaf) => new LlmKbLogView(leaf),
    );

    this.statusBar = this.addStatusBarItem();
    this.statusBar.setText("🧠 LLM-KB");
    this.refreshStatusBar();

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
      callback: () => this.promptAndQuery(),
    });

    this.addCommand({
      id: "llm-kb-lint",
      name: "Lint wiki",
      callback: () => this.runTool("lint.lint", []),
    });

    this.addCommand({
      id: "llm-kb-open-index",
      name: "Open index.md",
      callback: async () => {
        const file = this.app.vault.getAbstractFileByPath("index.md");
        if (file instanceof TFile) {
          await this.app.workspace.getLeaf(true).openFile(file);
        } else {
          new Notice("index.md not found — create it first.");
        }
      },
    });

    this.addCommand({
      id: "llm-kb-open-log-view",
      name: "Open log sidebar",
      callback: () => this.activateLogView(),
    });

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

  /** Vault's absolute path on disk. */
  private vaultPath(): string {
    // @ts-expect-error — getBasePath is implemented by Obsidian's FileSystemAdapter.
    return this.app.vault.adapter.getBasePath?.() ?? "";
  }

  private async refreshStatusBar(): Promise<void> {
    const vaultPath = this.vaultPath();
    if (!vaultPath) {
      this.statusBar.setText("🧠 LLM-KB ·  ?");
      return;
    }
    try {
      // Count raw/wiki files via vault listing (Obsidian-native).
      const all = this.app.vault.getMarkdownFiles();
      let raw = 0;
      let wiki = 0;
      for (const f of all) {
        if (f.path.startsWith("raw/")) raw++;
        else if (f.path.startsWith("wiki/")) wiki++;
      }
      this.statusBar.setText(`🧠 raw:${raw} · wiki:${wiki}`);
    } catch {
      this.statusBar.setText("🧠 LLM-KB");
    }
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

  /** Move (or copy) the active note into raw/ with a timestamped prefix. */
  private async ingestCurrent(file: TFile): Promise<void> {
    const today = new Date().toISOString().slice(0, 10);
    const slug = file.basename.replace(/[^0-9a-zA-Z\u4e00-\u9fff]+/g, "-");
    const newPath = `raw/${today}_${slug}.md`;

    if (this.app.vault.getAbstractFileByPath(newPath)) {
      new Notice(`${newPath} already exists — skipping.`);
      return;
    }

    const content = await this.app.vault.read(file);
    // Prepend a small frontmatter block if the note doesn't have one.
    let out = content;
    if (!content.startsWith("---\n")) {
      out =
        `---\n` +
        `title: ${file.basename}\n` +
        `ingested_at: ${today}\n` +
        `source: vault:${file.path}\n` +
        `---\n\n` +
        content;
    }
    await this.app.vault.create(newPath, out);
    new Notice(`Ingested → ${newPath}`);
    await this.refreshStatusBar();
  }

  /** Spawn `uv run python -m <module>` with --vault <vaultPath>. */
  private async runTool(module: string, extraArgs: string[]): Promise<void> {
    const vault = this.vaultPath();
    if (!vault) {
      new Notice("Cannot determine vault path.");
      return;
    }
    const view = await this.activateLogView();
    view.clear();
    view.append(`$ ${this.settings.uvCommand} run python -m ${module} --vault ${vault}\n\n`);

    try {
      const code = await runStreaming({
        cmd: this.settings.uvCommand,
        args: [
          "run",
          "python",
          "-m",
          module,
          "--vault",
          vault,
          ...extraArgs,
        ],
        cwd: this.settings.toolsPath,
        onStdout: (c) => view.append(c),
        onStderr: (c) => view.append(c),
      });
      view.append(`\n[exit ${code}]\n`);
      await this.refreshStatusBar();
    } catch (e: unknown) {
      view.append(`\n[error] ${String(e)}\n`);
    }
  }

  private async promptAndQuery(): Promise<void> {
    new QueryModal(this.app, async (question) => {
      if (!question.trim()) return;
      await this.runTool("query.query", [question]);
    }).open();
  }
}

class QueryModal extends Modal {
  constructor(
    app: App,
    private onSubmit: (question: string) => void,
  ) {
    super(app);
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.createEl("h3", { text: "Ask the wiki" });
    const input = contentEl.createEl("textarea", {
      attr: {
        style: "width:100%;height:100px;",
        placeholder: "你的問題...",
      },
    });
    const btn = contentEl.createEl("button", { text: "Ask" });
    btn.style.marginTop = "8px";
    btn.addEventListener("click", () => {
      const q = input.value;
      this.close();
      this.onSubmit(q);
    });
    input.focus();
  }

  onClose(): void {
    this.contentEl.empty();
  }
}
