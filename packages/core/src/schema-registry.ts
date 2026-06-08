export interface SchemaEntry {
  id: string;
  version: string;
  schema: object;
}

export class SchemaRegistry {
  private registry: Map<string, SchemaEntry> = new Map();

  register(entry: SchemaEntry): void {
    if (!entry.id || !entry.version || !entry.schema) {
      throw new Error(
        'SchemaEntry must contain id, version, and schema properties'
      );
    }
    this.registry.set(entry.id, entry);
  }

  get(id: string): SchemaEntry | undefined {
    return this.registry.get(id);
  }

  list(): SchemaEntry[] {
    return Array.from(this.registry.values());
  }
}
