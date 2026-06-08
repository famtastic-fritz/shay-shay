import fs from 'node:fs';

export class CredentialNotFoundError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'CredentialNotFoundError';
  }
}

export class CredentialVault {
  private secretsFilePath?: string;
  private secretsCache?: Record<string, string>;

  constructor(options?: { secretsFilePath?: string }) {
    this.secretsFilePath = options?.secretsFilePath;
  }

  get(name: string): string {
    const envValue = process.env[name];
    if (envValue) {
      return envValue;
    }

    if (this.secretsFilePath && fs.existsSync(this.secretsFilePath)) {
      if (!this.secretsCache) {
        const content = fs.readFileSync(this.secretsFilePath, 'utf-8');
        this.secretsCache = JSON.parse(content);
      }
      const value = this.secretsCache?.[name];
      if (value) {
        return value;
      }
    }

    throw new CredentialNotFoundError(
      `Credential '${name}' not found in environment or secrets file`
    );
  }

  has(name: string): boolean {
    if (process.env[name]) {
      return true;
    }

    if (this.secretsFilePath && fs.existsSync(this.secretsFilePath)) {
      if (!this.secretsCache) {
        try {
          const content = fs.readFileSync(this.secretsFilePath, 'utf-8');
          this.secretsCache = JSON.parse(content);
        } catch {
          return false;
        }
      }
      return this.secretsCache ? name in this.secretsCache : false;
    }

    return false;
  }

  redact(value: string): string {
    if (value.length <= 8) {
      return '****';
    }
    return value.substring(0, 4) + '*'.repeat(value.length - 4);
  }
}
