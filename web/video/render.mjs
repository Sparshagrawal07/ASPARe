// Renders web/video/scene.html frame by frame with headless Chrome and encodes public/showreel/aspare-showreel.mp4.
//
//   TOOLS_DIR=<dir with puppeteer-core installed> FFMPEG=<path to ffmpeg with libx264> node video/render.mjs [--frames t1,t2,...]
//
// Nothing here is a dependency of the website: it only produces a static asset that is committed to public/.
import { createRequire } from "node:module";
import { spawn } from "node:child_process";
import { mkdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(join(process.env.TOOLS_DIR, "package.json"));
const puppeteer = require("puppeteer-core");

const CHROME = process.env.CHROME ??
  `${process.env.HOME}/.cache/puppeteer/chrome/mac_arm-140.0.7339.82/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`;
const FPS = 30, DUR = 15, OUT_W = 1280, OUT_H = 720;
const data = JSON.parse(readFileSync(join(here, "data.json"), "utf8"));

const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ["--no-sandbox", "--allow-file-access-from-files", "--font-render-hinting=none"] });
const page = await browser.newPage();
await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
await page.evaluateOnNewDocument((d) => { window.DATA = d; }, data);
await page.goto(pathToFileURL(join(here, "scene.html")).href);
await page.evaluate(() => document.fonts.ready);
await page.evaluate(() => Promise.all([...document.fonts].map((f) => f.load().catch(() => null))));

const framesArg = process.argv.indexOf("--frames");
if (framesArg > -1) {
  const out = process.env.OUT_DIR;
  mkdirSync(out, { recursive: true });
  for (const t of process.argv[framesArg + 1].split(",").map(Number)) {
    await page.evaluate((x) => window.seek(x), t);
    await page.screenshot({ path: join(out, `t${String(t).replace(".", "_")}.png`) });
  }
  await browser.close();
  process.exit(0);
}

mkdirSync(join(here, "..", "public", "showreel"), { recursive: true });
const outFile = join(here, "..", "public", "showreel", "aspare-showreel.mp4");
const ff = spawn(process.env.FFMPEG, [
  "-y", "-hide_banner", "-loglevel", "error",
  "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "mjpeg", "-i", "-",
  "-vf", `scale=${OUT_W}:${OUT_H}:flags=lanczos:out_range=tv,format=yuv420p`,
  "-c:v", "libx264", "-preset", "slow", "-crf", "22", "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-profile:v", "high", "-movflags", "+faststart", "-an", outFile,
], { stdio: ["pipe", "inherit", "inherit"] });
const done = new Promise((res, rej) => { ff.on("close", (c) => (c === 0 ? res() : rej(new Error("ffmpeg exited " + c)))); });

const total = FPS * DUR;
for (let f = 0; f < total; f++) {
  await page.evaluate((x) => window.seek(x), f / FPS);
  const buf = await page.screenshot({ type: "jpeg", quality: 94 });
  if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
  if (f % 45 === 0) process.stdout.write(`frame ${f}/${total}\n`);
}
ff.stdin.end();
await done;

// Poster frame: the headline moment (scene 2, fully resolved and clear of the transition wipes), taken from the encoded video.
const posterFile = join(here, "..", "public", "showreel", "aspare-showreel-poster.jpg");
const pf = spawn(process.env.FFMPEG, ["-y", "-hide_banner", "-loglevel", "error", "-ss", "3.3", "-i", outFile, "-frames:v", "1", "-q:v", "5", posterFile], { stdio: "inherit" });
await new Promise((res) => pf.on("close", res));
await browser.close();
console.log("wrote", outFile);
