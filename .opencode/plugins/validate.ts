import { $ } from "bun";
import type { Plugin } from "@opencode-ai/plugin";

function getFilePath(args: any): string | undefined {
  const path = args?.file_path ?? args?.filePath;
  return typeof path === "string" ? path : undefined;
}

function shouldValidate(filePath: string): boolean {
  return filePath.startsWith("knowledge/articles/") && filePath.endsWith(".json");
}

async function runValidation(filePath: string): Promise<void> {
  try {
    const result =
      await $`python3 hooks/validate_json.py ${filePath}`.nothrow();
    if (result.exitCode !== 0) {
      console.warn(
        `[validate] validation failed for ${filePath}:\n${result.stderr.toString()}`,
      );
    }
  } catch (err) {
    console.warn(`[validate] shell error for ${filePath}:`, err);
  }
}

const plugin: Plugin = async () => {
  return {
    async "tool.execute.after"(input: { tool: string; args: any }) {
      const { tool, args } = input;
      if (tool !== "write" && tool !== "edit") return;

      const filePath = getFilePath(args);
      if (!filePath) return;
      if (!shouldValidate(filePath)) return;

      await runValidation(filePath);
    },
  };
};

export default plugin;
