import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { DatabaseManager } from '../../src/infrastructure/database/DatabaseManager.js';
import { GroupRepository } from '../../src/repositories/GroupRepository.js';
import * as fs from 'fs';
import * as path from 'path';

describe('CLI group:edit - Trigger Configuration', () => {
  const testDbPath = './data/test-rss2pod.db';
  let dbManager: DatabaseManager;
  let testGroupId: string;

  beforeEach(() => {
    dbManager = new DatabaseManager(testDbPath);
    dbManager.initialize();
    const db = dbManager.getDb();
    const groupRepo = new GroupRepository(db);
    
    testGroupId = `grp-test-${Date.now()}`;
    groupRepo.create({
      id: testGroupId,
      name: 'Test Group',
      sourceIds: ['1', '2'],
      enabled: true,
      triggerType: 'time',
      triggerConfig: { cron: '0 9 * * *' },
      podcastStructure: { type: 'single' },
      learningMode: 'normal',
      retentionDays: 30,
    });
  });

  afterEach(() => {
    dbManager.close();
    if (fs.existsSync(testDbPath)) {
      fs.unlinkSync(testDbPath);
    }
  });

  describe('triggerType updates', () => {
    it('should update trigger type from time to count', () => {
      const db = dbManager.getDb();
      const groupRepo = new GroupRepository(db);
      
      const group = groupRepo.findById(testGroupId);
      if (group) {
        group.triggerType = 'count';
        groupRepo.update(group);
      }
      
      const updated = groupRepo.findById(testGroupId);
      expect(updated?.triggerType).toBe('count');
    });

    it('should update trigger type to llm', () => {
      const db = dbManager.getDb();
      const groupRepo = new GroupRepository(db);
      
      const group = groupRepo.findById(testGroupId);
      if (group) {
        group.triggerType = 'llm';
        groupRepo.update(group);
      }
      
      const updated = groupRepo.findById(testGroupId);
      expect(updated?.triggerType).toBe('llm');
    });

    it('should update trigger type to mixed', () => {
      const db = dbManager.getDb();
      const groupRepo = new GroupRepository(db);
      
      const group = groupRepo.findById(testGroupId);
      if (group) {
        group.triggerType = 'mixed';
        groupRepo.update(group);
      }
      
      const updated = groupRepo.findById(testGroupId);
      expect(updated?.triggerType).toBe('mixed');
    });
  });

  describe('triggerConfig updates', () => {
    it('should update cron expression', () => {
      const db = dbManager.getDb();
      const groupRepo = new GroupRepository(db);
      
      const group = groupRepo.findById(testGroupId);
      if (group) {
        group.triggerConfig = {
          ...group.triggerConfig,
          cron: '0 18 * * *',
        };
        groupRepo.update(group);
      }
      
      const updated = groupRepo.findById(testGroupId);
      expect(updated?.triggerConfig.cron).toBe('0 18 * * *');
    });

    it('should add threshold to existing triggerConfig', () => {
      const db = dbManager.getDb();
      const groupRepo = new GroupRepository(db);
      
      const group = groupRepo.findById(testGroupId);
      if (group) {
        group.triggerConfig = {
          ...group.triggerConfig,
          threshold: 10,
        };
        groupRepo.update(group);
      }
      
      const updated = groupRepo.findById(testGroupId);
      expect(updated?.triggerConfig.threshold).toBe(10);
    });

    it('should update both cron and threshold', () => {
      const db = dbManager.getDb();
      const groupRepo = new GroupRepository(db);
      
      const group = groupRepo.findById(testGroupId);
      if (group) {
        group.triggerConfig = {
          cron: '0 */6 * * *',
          threshold: 5,
        };
        groupRepo.update(group);
      }
      
      const updated = groupRepo.findById(testGroupId);
      expect(updated?.triggerConfig.cron).toBe('0 */6 * * *');
      expect(updated?.triggerConfig.threshold).toBe(5);
    });

    it('should preserve cron when updating threshold', () => {
      const db = dbManager.getDb();
      const groupRepo = new GroupRepository(db);
      
      const group = groupRepo.findById(testGroupId);
      if (group) {
        group.triggerConfig = {
          ...group.triggerConfig,
          threshold: 20,
        };
        groupRepo.update(group);
      }
      
      const updated = groupRepo.findById(testGroupId);
      expect(updated?.triggerConfig.cron).toBe('0 9 * * *');
      expect(updated?.triggerConfig.threshold).toBe(20);
    });
  });

  describe('validation scenarios', () => {
    it('should handle empty triggerConfig gracefully', () => {
      const db = dbManager.getDb();
      const groupRepo = new GroupRepository(db);
      
      const group = groupRepo.findById(testGroupId);
      if (group) {
        group.triggerConfig = {};
        groupRepo.update(group);
      }
      
      const updated = groupRepo.findById(testGroupId);
      expect(updated?.triggerConfig).toEqual({});
    });

    it('should handle triggerConfig with custom fields', () => {
      const db = dbManager.getDb();
      const groupRepo = new GroupRepository(db);
      
      const group = groupRepo.findById(testGroupId);
      if (group) {
        group.triggerConfig = {
          cron: '0 9 * * *',
          customField: 'custom value',
        };
        groupRepo.update(group);
      }
      
      const updated = groupRepo.findById(testGroupId);
      expect(updated?.triggerConfig.cron).toBe('0 9 * * *');
      expect((updated?.triggerConfig as any).customField).toBe('custom value');
    });
  });
});
