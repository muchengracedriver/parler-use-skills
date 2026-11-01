#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const { version } = JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf8'));
const commands = new Set(['configure', 'usage', 'models', 'image-config', 'mcp', 'run']);
const help = `parler-use-skills ${version}

Usage:
  npx parler-use-skills install [--client codex|other] [--dest <skills-root>] [--skip-image] [--skip-mcp]
  npx parler-use-skills configure
  npx parler-use-skills usage <5h|7d|accountStatus|membership|payments|keys|tokens|logs|all>
  npx parler-use-skills models
  npx parler-use-skills image-config
  npx parler-use-skills mcp
  npx parler-use-skills run <codex|claude|opencode|aider> -- <arguments>

Requires Python 3.10+. Set PARLER_PYTHON to an executable path if needed.
The install command installs the skill, custom-imagegen and local Codex MCP.
Use --client other to install only the skill for a non-Codex harness.
Credentials are entered only by configure in your own interactive terminal.
`;

function python() {
  const candidates = process.env.PARLER_PYTHON
    ? [[process.env.PARLER_PYTHON, []]]
    : process.platform === 'win32'
      ? [['py', ['-3']], ['python3', []], ['python', []]]
      : [['python3', []], ['python', []]];
  for (const [command, args] of candidates) {
    const check = spawnSync(command, [...args, '-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'], { stdio: 'ignore' });
    if (!check.error && check.status === 0) return [command, args];
  }
  throw new Error('Python 3.10+ was not found. Install Python or set PARLER_PYTHON to its executable path.');
}

function main() {
  const [command, ...args] = process.argv.slice(2);
  if (command === '--version' || command === '-v') {
    console.log(version);
    return 0;
  }
  if (!command || command === '--help' || command === '-h' || command === 'help') {
    console.log(help);
    return 0;
  }
  if (command !== 'install' && !commands.has(command)) {
    console.error(`Unknown command: ${command}\nRun parler-use-skills --help for usage.`);
    return 2;
  }
  const [executable, prefix] = python();
  const script = command === 'install'
    ? resolve(root, 'skills/parler-use/scripts/install.py')
    : resolve(root, 'skills/parler-use/scripts/parler.py');
  const forwarded = command === 'install' ? args : [command, ...args];
  const child = spawnSync(executable, [...prefix, script, ...forwarded], { stdio: 'inherit' });
  if (child.error) throw child.error;
  if (child.signal) {
    console.error(`Command interrupted by ${child.signal}.`);
    return 1;
  }
  return child.status ?? 1;
}

try {
  process.exitCode = main();
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const { version } = JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf8'));
const commands = new Set(['configure', 'usage', 'models', 'image-config', 'mcp', 'run']);
const help = `parler-use-skills ${version}

Usage:
  npx parler-use-skills install [--dest <skills-root>] [--skip-image] [--skip-mcp]
  npx parler-use-skills configure
  npx parler-use-skills usage <5h|7d|accountStatus|membership|payments|keys|tokens|logs|all>
  npx parler-use-skills models
  npx parler-use-skills image-config
  npx parler-use-skills mcp
  npx parler-use-skills run <codex|claude|opencode|aider> -- <arguments>

Requires Python 3.10+. Set PARLER_PYTHON to an executable path if needed.
The install command installs the skill, custom-imagegen and local Codex MCP.
Credentials are entered only by configure in your own interactive terminal.
`;

function python() {
  const candidates = process.env.PARLER_PYTHON
    ? [[process.env.PARLER_PYTHON, []]]
    : process.platform === 'win32'
      ? [['py', ['-3']], ['python3', []], ['python', []]]
      : [['python3', []], ['python', []]];
  for (const [command, args] of candidates) {
    const check = spawnSync(command, [...args, '-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'], { stdio: 'ignore' });
    if (!check.error && check.status === 0) return [command, args];
  }
  throw new Error('Python 3.10+ was not found. Install Python or set PARLER_PYTHON to its executable path.');
}

function main() {
  const [command, ...args] = process.argv.slice(2);
  if (command === '--version' || command === '-v') {
    console.log(version);
    return 0;
  }
  if (!command || command === '--help' || command === '-h' || command === 'help') {
    console.log(help);
    return 0;
  }
  if (command !== 'install' && !commands.has(command)) {
    console.error(`Unknown command: ${command}\nRun parler-use-skills --help for usage.`);
    return 2;
  }
  const [executable, prefix] = python();
  const script = command === 'install'
    ? resolve(root, 'skills/parler-use/scripts/install.py')
    : resolve(root, 'skills/parler-use/scripts/parler.py');
  const forwarded = command === 'install' ? args : [command, ...args];
  const child = spawnSync(executable, [...prefix, script, ...forwarded], { stdio: 'inherit' });
  if (child.error) throw child.error;
  if (child.signal) {
    console.error(`Command interrupted by ${child.signal}.`);
    return 1;
  }
  return child.status ?? 1;
}

try {
  process.exitCode = main();
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
