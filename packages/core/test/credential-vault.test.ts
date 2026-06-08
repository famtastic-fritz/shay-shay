import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import os from 'node:os';
import fs from 'node:fs';
import path from 'node:path';
import { CredentialVault, CredentialNotFoundError } from '../src/credential-vault.js';

describe('CredentialVault', () => {
  beforeEach(() => {
    delete process.env.TEST_SECRET_XYZ;
  });

  afterEach(() => {
    delete process.env.TEST_SECRET_XYZ;
  });

  it('get returns env var value', () => {
    process.env.TEST_SECRET_XYZ = 'abc123';
    const vault = new CredentialVault();

    const value = vault.get('TEST_SECRET_XYZ');

    expect(value).toBe('abc123');
  });

  it('get throws CredentialNotFoundError for unknown name', () => {
    const vault = new CredentialVault();

    expect(() => {
      vault.get('__NEVER_SET_KEY__');
    }).toThrow(CredentialNotFoundError);
  });

  it('redact masks all but first 4 chars for long secrets', () => {
    const vault = new CredentialVault();
    const result = vault.redact('abcdefghij');

    expect(result).toBe('abcd******');
  });

  it('redact returns **** for short secrets', () => {
    const vault = new CredentialVault();
    const result = vault.redact('hi');

    expect(result).toBe('****');
  });

  it('has returns true for existing env key and false for missing', () => {
    const vault = new CredentialVault();

    process.env.TEST_SECRET_XYZ = 'secret';
    expect(vault.has('TEST_SECRET_XYZ')).toBe(true);

    delete process.env.TEST_SECRET_XYZ;
    expect(vault.has('TEST_SECRET_XYZ')).toBe(false);
  });

  it('get reads from secretsFilePath JSON file', () => {
    const tempFile = path.join(os.tmpdir(), `secrets-${Date.now()}.json`);
    const secretsData = { MY_KEY: 'secret_value' };

    fs.writeFileSync(tempFile, JSON.stringify(secretsData));

    try {
      const vault = new CredentialVault({ secretsFilePath: tempFile });
      const value = vault.get('MY_KEY');

      expect(value).toBe('secret_value');
    } finally {
      fs.unlinkSync(tempFile);
    }
  });
});
