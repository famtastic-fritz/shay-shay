import type { Ajv as AjvInstance } from 'ajv';
import AjvModule from 'ajv';
import addFormatsModule from 'ajv-formats';
import fs from 'node:fs';
import path from 'node:path';

const Ajv = (AjvModule as any).default || AjvModule;
const addFormats = (addFormatsModule as any).default || addFormatsModule;

export class SchemaAlreadyRegisteredError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'SchemaAlreadyRegisteredError';
  }
}

export class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ValidationError';
  }
}

export class SchemaRegistry {
  private ajv: AjvInstance;
  private registeredNames: Set<string> = new Set();

  constructor() {
    this.ajv = new Ajv({ allErrors: true });
    addFormats(this.ajv);
  }

  register(name: string, schema: object): void {
    if (this.registeredNames.has(name)) {
      throw new SchemaAlreadyRegisteredError(
        `Schema '${name}' is already registered`
      );
    }
    const cleanSchema = { ...(schema as any) };
    delete cleanSchema.$schema;
    this.ajv.addSchema(cleanSchema, name);
    this.registeredNames.add(name);
  }

  validate(name: string, payload: unknown): void {
    const validate = this.ajv.getSchema(name);
    if (!validate) {
      throw new ValidationError(`Schema '${name}' not found`);
    }
    const isValid = validate(payload);
    if (!isValid) {
      const errors = JSON.stringify(validate.errors);
      throw new ValidationError(
        `Validation failed for schema '${name}': ${errors}`
      );
    }
  }

  has(name: string): boolean {
    return this.ajv.getSchema(name) !== undefined;
  }

  loadFromDir(dir: string): void {
    const files = fs.readdirSync(dir);
    for (const file of files) {
      if (file.endsWith('.schema.json')) {
        const filePath = path.join(dir, file);
        const content = fs.readFileSync(filePath, 'utf-8');
        const schema = JSON.parse(content);

        let schemaName: string;
        if (schema.$id && typeof schema.$id === 'string') {
          schemaName = schema.$id;
        } else {
          schemaName = file.replace(/\.schema\.json$/, '');
        }

        try {
          this.register(schemaName, schema);
        } catch (error) {
          if (!(error instanceof SchemaAlreadyRegisteredError)) {
            throw error;
          }
        }
      }
    }
  }

  list(): string[] {
    return Array.from(this.registeredNames);
  }
}
