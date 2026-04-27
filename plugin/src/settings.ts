import { App, PluginSettingTab, Setting } from "obsidian";
import type LlmKbPlugin from "./main";

export interface LlmKbSettings {
  /** Absolute path to this repo's tools/ directory. */
  toolsPath: string;
  /** Command used to run uv (default: `uv`). */
  uvCommand: string;
  /** Command used to invoke Claude Code CLI (default: `claude`). */
  claudeCommand: string;
  /** Preferred KB language. */
  language: "zh-TW" | "en";
  /** Automatically run `pipeline.pipeline --apply` when the plugin loads. */
  autoRunPipelineOnLoad: boolean;
}

export const DEFAULT_SETTINGS: LlmKbSettings = {
  toolsPath: "",
  uvCommand: "uv",
  claudeCommand: "claude",
  language: "zh-TW",
  autoRunPipelineOnLoad: true,
};

export class LlmKbSettingTab extends PluginSettingTab {
  plugin: LlmKbPlugin;

  constructor(app: App, plugin: LlmKbPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "LLM Knowledge Base" });

    new Setting(containerEl)
      .setName("Tools path")
      .setDesc("Absolute path to the tools/ directory of project_Obsidian_graph.")
      .addText((t) =>
        t
          .setPlaceholder("/path/to/project_Obsidian_graph/tools")
          .setValue(this.plugin.settings.toolsPath)
          .onChange(async (v) => {
            this.plugin.settings.toolsPath = v.trim();
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName("uv command")
      .setDesc("Full path to the uv binary (run `which uv` in terminal to find it).")
      .addText((t) =>
        t
          .setValue(this.plugin.settings.uvCommand)
          .onChange(async (v) => {
            this.plugin.settings.uvCommand = v.trim() || "uv";
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName("Claude Code command")
      .setDesc("Claude Code CLI binary used to run compile prompts.")
      .addText((t) =>
        t
          .setValue(this.plugin.settings.claudeCommand)
          .onChange(async (v) => {
            this.plugin.settings.claudeCommand = v.trim() || "claude";
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName("Auto-ingest on startup")
      .setDesc(
        "On plugin load, run pipeline (Clippings → raw/) and autolink. " +
          "Requires a valid tools path.",
      )
      .addToggle((t) =>
        t
          .setValue(this.plugin.settings.autoRunPipelineOnLoad)
          .onChange(async (v) => {
            this.plugin.settings.autoRunPipelineOnLoad = v;
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName("Language")
      .setDesc("Language for compile / query output.")
      .addDropdown((d) =>
        d
          .addOption("zh-TW", "Traditional Chinese")
          .addOption("en", "English")
          .setValue(this.plugin.settings.language)
          .onChange(async (v) => {
            this.plugin.settings.language = v as "zh-TW" | "en";
            await this.plugin.saveSettings();
          }),
      );
  }
}
