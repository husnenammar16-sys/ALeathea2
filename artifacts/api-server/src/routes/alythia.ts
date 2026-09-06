import { readFile } from "node:fs/promises";
import path from "node:path";
import { Router, type IRouter } from "express";

const router: IRouter = Router();
const statusPaths = [
  path.resolve(process.cwd(), "discord_bot/runtime_status.json"),
  path.resolve(process.cwd(), "../../discord_bot/runtime_status.json"),
];

router.get("/alythia/status", async (_req, res) => {
  for (const statusPath of statusPaths) {
    try {
      const raw = await readFile(statusPath, "utf8");
      const status = JSON.parse(raw) as Record<string, unknown>;
      res.json(status);
      return;
    } catch {
      // Try the next workspace-relative location.
    }
  }
  res.status(503).json({ error: "Alythia bot status is not available yet." });
});

export default router;