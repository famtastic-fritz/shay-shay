export interface Credential {
  key: string;
  value: string;
  source: 'env' | 'file' | 'injected';
}

export class CredentialVault {
  private vault: Map<string, Credential> = new Map();

  set(key: string, value: string, source: Credential['source'] = 'injected'): void {
    if (!key || !value) {
      throw new Error('Credential key and value must not be empty');
    }
    this.vault.set(key, { key, value, source });
  }

  get(key: string): Credential | undefined {
    return this.vault.get(key);
  }

  has(key: string): boolean {
    return this.vault.has(key);
  }

  fromEnv(key: string): boolean {
    const value = process.env[key];
    if (value) {
      this.set(key, value, 'env');
      return true;
    }
    return false;
  }

  // TODO(phase 3) — integrate with secrets store.
  // TODO(phase 3) — add encryption for sensitive values.
  // TODO(phase 3) — add disk persistence and secure deletion.
}
