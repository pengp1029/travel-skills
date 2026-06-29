import {existsSync, readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

export function loadOpenClawEnv(importMetaUrl) {
  let current = path.dirname(fileURLToPath(importMetaUrl));
  while (current && current !== path.dirname(current)) {
    if (path.basename(current) === '.openclaw') {
      const envPath = path.join(current, '.env');
      if (!existsSync(envPath)) return;
      for (const rawLine of readFileSync(envPath, 'utf8').split(/\r?\n/)) {
        const line = rawLine.trim();
        if (!line || line.startsWith('#') || !line.includes('=')) continue;
        const index = line.indexOf('=');
        const key = line.slice(0, index).trim();
        let value = line.slice(index + 1).trim();
        if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
          value = value.slice(1, -1);
        }
        if (key) process.env[key] = value;
      }
      return;
    }
    current = path.dirname(current);
  }
}
