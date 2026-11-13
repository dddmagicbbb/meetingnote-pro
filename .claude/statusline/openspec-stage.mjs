// 상태줄: 전역 claude-hud 출력 아래에 OpenSpec 현재 단계를 한 줄씩 덧붙인다.
// openspec CLI 를 부르지 않고 openspec/ 폴더만 읽는다 (상태줄은 자주 갱신되므로 빨라야 한다).
//
// 단계 (spec-driven 스키마: proposal → specs·design → tasks → apply → archive)
//   ① 제안      proposal.md 없음
//   ② 설계      proposal 은 있고 specs · design · tasks 중 빠진 것이 있음
//   ③ 구현      tasks.md 체크박스 진행 중
//   ④ 아카이브  tasks.md 전부 체크됨 → verify · archive 차례
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const input = fs.readFileSync(0, 'utf8');
let data = {};
try { data = JSON.parse(input); } catch {}

// 1) 기존 claude-hud 출력 (없으면 건너뜀)
const configDir = process.env.CLAUDE_CONFIG_DIR?.trim() || path.join(os.homedir(), '.claude');
const hud = path.join(configDir, 'plugins', 'claude-hud', 'statusline.mjs');
let out = '';
if (fs.existsSync(hud)) {
  const r = spawnSync(process.execPath, [hud], { input, encoding: 'utf8', timeout: 4000, env: process.env });
  out = (r.stdout || '').replace(/\s+$/, '');
}

// 2) OpenSpec 단계
const projectDir = data.workspace?.project_dir || process.env.CLAUDE_PROJECT_DIR || process.cwd();
const osDir = path.join(projectDir, 'openspec');

const C = { dim: '\x1b[2m', cyan: '\x1b[36m', yellow: '\x1b[33m', green: '\x1b[32m', magenta: '\x1b[35m', reset: '\x1b[0m' };
const dirs = (p) => { try { return fs.readdirSync(p, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name); } catch { return []; } };
const has = (p) => fs.existsSync(p);
const hasSpecs = (p) => {
  const walk = (d) => { try { return fs.readdirSync(d, { withFileTypes: true }).some((e) => e.isDirectory() ? walk(path.join(d, e.name)) : e.name.endsWith('.md')); } catch { return false; } };
  return walk(p);
};
const mark = (ok) => (ok ? `${C.green}✓${C.reset}` : `${C.dim}·${C.reset}`);

function stageOf(name) {
  const dir = path.join(osDir, 'changes', name);
  const a = {
    proposal: has(path.join(dir, 'proposal.md')),
    specs: hasSpecs(path.join(dir, 'specs')),
    design: has(path.join(dir, 'design.md')),
    tasks: has(path.join(dir, 'tasks.md')),
  };
  const arts = `proposal${mark(a.proposal)} specs${mark(a.specs)} design${mark(a.design)} tasks${mark(a.tasks)}`;
  if (!a.proposal) return `${C.yellow}① 제안${C.reset} ${arts} ${C.dim}→ /openspec-continue-change${C.reset}`;
  if (!a.specs || !a.design || !a.tasks) return `${C.yellow}② 설계${C.reset} ${arts} ${C.dim}→ /openspec-continue-change${C.reset}`;
  let total = 0, done = 0;
  try {
    for (const line of fs.readFileSync(path.join(dir, 'tasks.md'), 'utf8').split(/\r?\n/)) {
      const m = /^\s*[-*]\s+\[([ xX])\]/.exec(line);
      if (m) { total++; if (m[1] !== ' ') done++; }
    }
  } catch {}
  if (total > 0 && done === total) return `${C.green}④ 아카이브${C.reset} 작업 ${done}/${total} ${C.dim}→ /openspec-verify-change · /openspec-archive-change${C.reset}`;
  return `${C.magenta}③ 구현${C.reset} 작업 ${done}/${total} ${C.dim}→ /openspec-apply-change${C.reset}`;
}

let lines = [];
if (has(osDir)) {
  const changesDir = path.join(osDir, 'changes');
  const active = dirs(changesDir).filter((n) => n !== 'archive')
    .map((n) => ({ n, t: (() => { try { return fs.statSync(path.join(changesDir, n)).mtimeMs; } catch { return 0; } })() }))
    .sort((a, b) => b.t - a.t).map((x) => x.n);
  const specCount = dirs(path.join(osDir, 'specs')).length;
  const archived = dirs(path.join(changesDir, 'archive')).length;
  const tail = `${C.dim}스펙 ${specCount} · 아카이브 ${archived}${C.reset}`;
  if (active.length === 0) {
    lines.push(`${C.cyan}OpenSpec${C.reset} ⓪ 대기 - 진행 중인 change 없음 ${C.dim}→ /openspec-propose${C.reset} │ ${tail}`);
  } else {
    const shown = active.slice(0, 3);
    shown.forEach((n, i) => lines.push(`${C.cyan}OpenSpec${C.reset} ${n} │ ${stageOf(n)}${i === 0 ? ` │ ${tail}` : ''}`));
    if (active.length > shown.length) lines.push(`${C.dim}OpenSpec 외 ${active.length - shown.length}개 진행 중${C.reset}`);
  }
}

process.stdout.write([out, ...lines].filter(Boolean).join('\n') + '\n');
