// website/static/js/db.js

const dbPromise = idb.openDB('deco-office-db', 1, {
  upgrade(db) {
    if (!db.objectStoreNames.contains('transactions')) {
      db.createObjectStore('transactions', { keyPath: '_id' });
    }
    if (!db.objectStoreNames.contains('transaction-outbox')) {
      db.createObjectStore('transaction-outbox', { autoIncrement: true, keyPath: 'id' });
    }
  },
});

window.db = {
  async readAllData(st) {
    const db = await dbPromise;
    return db.getAll(st);
  },

  async writeData(st, data) {
    const db = await dbPromise;
    const tx = db.transaction(st, 'readwrite');
    // Handle single object or an array of objects
    if (Array.isArray(data)) {
      await Promise.all(data.map(item => tx.store.put(item)));
    } else {
      await tx.store.put(data);
    }
    return tx.done;
  },

  async deleteOneData(st, id) {
    const db = await dbPromise;
    const tx = db.transaction(st, 'readwrite');
    await tx.store.delete(id);
    return tx.done;
  },

  async clearAllData(st) {
    const db = await dbPromise;
    const tx = db.transaction(st, 'readwrite');
    await tx.store.clear();
    return tx.done;
  }
};