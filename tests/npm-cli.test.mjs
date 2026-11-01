import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const cli = resolve(root, 'bin/parler-use-skills.mjs');
const run = (args, env = {}) => spawnSync(process.execPath, [cli, ...args], {
  encoding: 'utf8', env: { ...process.env, ...env }
});

test('help and version work without Python and unknown commands fail clearly', () => {
  const env = { PARLER_PYTHON: '/nonexistent/parler-python' };
  assert.equal(run(['--version'], env).stdout.trim(), JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf8')).version);
  const help = run(['--help'], env);
  assert.equal(help.status, 0);
  assert.match(help.stdout, /configure/);
  const unknown = run(['not-a-command'], env);
  assert.equal(unknown.status, 2);
  assert.match(unknown.stderr, /Unknown command/);
});

test('missing Python is reported without attempting an installation', () => {
  const result = run(['install'], { PARLER_PYTHON: '/nonexistent/parler-python' });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Python 3.10/);
});

test('npm CLI installs complete skill to a custom path and supports repeated runs', () => {
  const directory = mkdtempSync(resolve(tmpdir(), 'parler-npm-test-'));
  try {
    const args = ['install', '--dest', resolve(directory, 'skills with spaces'), '--skip-image', '--skip-mcp'];
    const first = run(args);
    assert.equal(first.status, 0, first.stderr);
    const installed = resolve(directory, 'skills with spaces/parler-use');
    assert.match(readFileSync(resolve(installed, 'SKILL.md'), 'utf8'), /name: parler-use/);
    assert.equal(readFileSync(resolve(installed, 'scripts/parler.py'), 'utf8'), readFileSync(resolve(root, 'skills/parler-use/scripts/parler.py'), 'utf8'));
    assert.equal(run(args).status, 0);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test('MCP forwarding keeps stdout as valid JSON-RPC and needs no credentials to list tools', () => {
  const message = JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tools/list' });
  const result = spawnSync(process.execPath, [cli, 'mcp'], { input: message + '\n', encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  const response = JSON.parse(result.stdout);
  assert.equal(response.result.tools[0].name, 'parler_usage');
});
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const cli = resolve(root, 'bin/parler-use-skills.mjs');
const run = (args, env = {}) => spawnSync(process.execPath, [cli, ...args], {
  encoding: 'utf8', env: { ...process.env, ...env }
});

test('help and version work without Python and unknown commands fail clearly', () => {
  const env = { PARLER_PYTHON: '/nonexistent/parler-python' };
  assert.equal(run(['--version'], env).stdout.trim(), '1.0.0');
  const help = run(['--help'], env);
  assert.equal(help.status, 0);
  assert.match(help.stdout, /configure/);
  const unknown = run(['not-a-command'], env);
  assert.equal(unknown.status, 2);
  assert.match(unknown.stderr, /Unknown command/);
});

test('missing Python is reported without attempting an installation', () => {
  const result = run(['install'], { PARLER_PYTHON: '/nonexistent/parler-python' });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Python 3.10/);
});

test('npm CLI installs complete skill to a custom path and supports repeated runs', () => {
  const directory = mkdtempSync(resolve(tmpdir(), 'parler-npm-test-'));
  try {
    const args = ['install', '--dest', resolve(directory, 'skills with spaces'), '--skip-image', '--skip-mcp'];
    const first = run(args);
    assert.equal(first.status, 0, first.stderr);
    const installed = resolve(directory, 'skills with spaces/parler-use');
    assert.match(readFileSync(resolve(installed, 'SKILL.md'), 'utf8'), /name: parler-use/);
    assert.equal(readFileSync(resolve(installed, 'scripts/parler.py'), 'utf8'), readFileSync(resolve(root, 'skills/parler-use/scripts/parler.py'), 'utf8'));
    assert.equal(run(args).status, 0);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test('MCP forwarding keeps stdout as valid JSON-RPC and needs no credentials to list tools', () => {
  const message = JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tools/list' });
  const result = spawnSync(process.execPath, [cli, 'mcp'], { input: message + '\n', encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  const response = JSON.parse(result.stdout);
  assert.equal(response.result.tools[0].name, 'parler_usage');
});
